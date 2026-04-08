from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django import forms
from django.contrib.auth.models import User
from .models import Product, Category, Artisan, Order, OrderItem

# ── Custom Registration Form with Email ──────────────────
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text='Optional.')

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

# ── Cart helpers ──────────────────────────────────────────
def get_cart(request):
    return request.session.get('cart', {})

def save_cart(request, cart):
    request.session['cart'] = cart
    request.session.modified = True

def cart_items_data(cart):
    items = []
    total = 0
    for product_id, quantity in cart.items():
        try:
            product = Product.objects.get(pk=product_id)
            subtotal = product.price * quantity
            total += subtotal
            items.append({'product': product, 'quantity': quantity, 'subtotal': subtotal})
        except Product.DoesNotExist:
            pass
    return items, total

# ── Views ─────────────────────────────────────────────────
def home(request):
    products = Product.objects.all().order_by('-created_at')
    categories = Category.objects.all()
    artisans = Artisan.objects.all()
    cart = get_cart(request)
    cart_count = sum(cart.values())
    return render(request, 'store/home.html', {
        'products': products,
        'categories': categories,
        'artisans': artisans,
        'cart_count': cart_count,
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart = get_cart(request)
    cart_count = sum(cart.values())
    return render(request, 'store/product_detail.html', {
        'product': product,
        'cart_count': cart_count,
    })

def artisan_profile(request, pk):
    artisan = get_object_or_404(Artisan, pk=pk)
    products = Product.objects.filter(artisan_profile=artisan)
    cart = get_cart(request)
    cart_count = sum(cart.values())
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
    cart = get_cart(request)
    cart_count = sum(cart.values())
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
        cart = get_cart(request)
        cart[str(pk)] = cart.get(str(pk), 0) + 1
        save_cart(request, cart)
    return redirect(request.META.get('HTTP_REFERER', 'home'))

def remove_from_cart(request, pk):
    cart = get_cart(request)
    cart.pop(str(pk), None)
    save_cart(request, cart)
    return redirect('cart')

def increase_cart(request, pk):
    cart = get_cart(request)
    cart[str(pk)] = cart.get(str(pk), 0) + 1
    save_cart(request, cart)
    return redirect('cart')

def decrease_cart(request, pk):
    cart = get_cart(request)
    if str(pk) in cart:
        cart[str(pk)] -= 1
        if cart[str(pk)] <= 0:
            cart.pop(str(pk))
    save_cart(request, cart)
    return redirect('cart')

def cart_view(request):
    cart = get_cart(request)
    cart_items, total = cart_items_data(cart)
    grand_total = total + 150
    cart_count = sum(cart.values())
    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total,
        'grand_total': grand_total,
        'cart_count': cart_count,
    })

@login_required
def checkout(request):
    cart = get_cart(request)
    cart_items, total = cart_items_data(cart)
    grand_total = total + 150
    if request.method == 'POST':
        order = Order.objects.create(
            user=request.user,
            full_name=request.POST.get('full_name'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address'),
            barangay=request.POST.get('barangay'),
            city=request.POST.get('city'),
            province=request.POST.get('province'),
            payment_method=request.POST.get('payment_method'),
            total=grand_total,
        )
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['product'].price,
            )
        save_cart(request, {})
        return redirect('order_success')
    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'grand_total': grand_total,
    })

def order_success(request):
    return render(request, 'store/order_success.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # FIX: Specify the backend because you have multiple authentication backends
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})