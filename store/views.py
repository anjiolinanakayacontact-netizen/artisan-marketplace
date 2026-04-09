from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django import forms
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import Product, Category, Artisan, Order, OrderItem, Cart, CartItem

# ── Custom Registration Form with Email ──────────────────
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text='Optional.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'This email is already registered. Please sign in instead.'
            )
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

# ── Cart helpers using database models ──────────────────
def get_or_create_cart(request):
    """Return the Cart object for the current user/session."""
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user, session_key=None)
        if request.session.session_key:
            session_cart = Cart.objects.filter(session_key=request.session.session_key, user=None).first()
            if session_cart:
                for item in session_cart.items.all():
                    cart_item, created = CartItem.objects.get_or_create(
                        cart=cart,
                        product=item.product,
                        defaults={'quantity': item.quantity}
                    )
                    if not created:
                        cart_item.quantity += item.quantity
                        cart_item.save()
                session_cart.delete()
        return cart
    else:
        if not request.session.session_key:
            request.session.create()
        cart, _ = Cart.objects.get_or_create(session_key=request.session.session_key, user=None)
        return cart

def cart_items_data(cart):
    """Return list of dicts and total price from a Cart object."""
    items = []
    total = 0
    for cart_item in cart.items.select_related('product').all():
        subtotal = cart_item.product.price * cart_item.quantity
        total += subtotal
        items.append({
            'product': cart_item.product,
            'quantity': cart_item.quantity,
            'subtotal': subtotal,
            'id': cart_item.id,
        })
    return items, total

# ── Views ─────────────────────────────────────────────────
def home(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    artisans = Artisan.objects.all()
    cart = get_or_create_cart(request)
    cart_count = cart.get_item_count()
    return render(request, 'store/home.html', {
        'products': products,
        'categories': categories,
        'artisans': artisans,
        'cart_count': cart_count,
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = get_or_create_cart(request)
    cart_count = cart.get_item_count()
    return render(request, 'store/product_detail.html', {
        'product': product,
        'cart_count': cart_count,
    })

def artisan_profile(request, pk):
    artisan = get_object_or_404(Artisan, pk=pk)
    products = Product.objects.filter(artisan_profile=artisan)
    cart = get_or_create_cart(request)
    cart_count = cart.get_item_count()
    return render(request, 'store/artisan_profile.html', {
        'artisan': artisan,
        'products': products,
        'cart_count': cart_count,
    })

def search(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    sort = request.GET.get('sort', 'newest')
    products = Product.objects.all()
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(artisan__icontains=query)
        )
    if category_id:
        products = products.filter(category__id=category_id)
    if sort == 'price_asc':
        products = products.order_by('price')
    elif sort == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('-created_at')
    categories = Category.objects.all()
    cart = get_or_create_cart(request)
    cart_count = cart.get_item_count()
    return render(request, 'store/search.html', {
        'products': products,
        'categories': categories,
        'query': query,
        'sort': sort,
        'selected_category': category_id,
        'cart_count': cart_count,
    })

def add_to_cart(request, pk):
    if request.method == 'POST':
        cart = get_or_create_cart(request)
        product = get_object_or_404(Product, pk=pk)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += 1
            cart_item.save()
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def remove_from_cart(request, pk):
    cart = get_or_create_cart(request)
    cart.items.filter(product__pk=pk).delete()
    return redirect('cart')

def increase_cart(request, pk):
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, pk=pk)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    else:
        cart_item.quantity = 1
        cart_item.save()
    return redirect('cart')

def decrease_cart(request, pk):
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, pk=pk)
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except CartItem.DoesNotExist:
        pass
    return redirect('cart')

def cart_view(request):
    cart = get_or_create_cart(request)
    cart_items, total = cart_items_data(cart)
    cart_count = cart.get_item_count()
    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart_count,
    })

@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    cart_items, total = cart_items_data(cart)

    if request.method == 'POST':
        # Create order
        order = Order.objects.create(
            user=request.user,
            full_name=request.user.get_full_name() or request.user.username,
            email=request.user.email,          # use logged-in user's email
            payment_method=request.POST.get('payment_method'),
            total=total,
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['product'].price,
            )

        # ---- Send email to buyer with software product ----
        subject = f'Your digital product from Artisan Market (Order #{order.id})'
        # Build a simple plain text message
        message = f"""
Hello {order.full_name},

Thank you for your purchase! Here is your software product:

Order ID: {order.id}
Total paid: ₱{total}

Items:
"""
        for item in cart_items:
            message += f"- {item['product'].name} x{item['quantity']} = ₱{item['subtotal']}\n"
        message += """
Your download link (valid for 24 hours):
https://yourdomain.com/download/software.zip

(Replace with your actual download link or attachment)

Thank you for shopping at Artisan Market!
"""
        # For HTML email, you can use render_to_string with a template.
        # For now, we use plain text.

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,   # set in settings.py
            [order.email],
            fail_silently=False,
        )
        # ------------------------------------------------

        # Clear cart after order
        cart.items.all().delete()
        return redirect('order_success')

    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'cart_count': cart.get_item_count(),
    })

def order_success(request):
    return render(request, 'store/order_success.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})