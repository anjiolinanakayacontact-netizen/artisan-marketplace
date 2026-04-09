from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django import forms
from django.contrib.auth.models import User
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
        # If there's an existing session cart, merge it (optional but good)
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
    # pk here is product id (consistent with old url naming)
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
    # No shipping fee – grand_total is same as total
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
    # No shipping fee – total is the final amount
    if request.method == 'POST':
        order = Order.objects.create(
            user=request.user,
            full_name=request.POST.get('full_name'),
            email=request.POST.get('email'),          # Only email, no phone/address
            payment_method=request.POST.get('payment_method'),
            total=total,                              # Subtotal only (no shipping)
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['product'].price,
            )
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