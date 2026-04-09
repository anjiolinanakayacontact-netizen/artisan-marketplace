from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class Artisan(models.Model):
    name = models.CharField(max_length=200)
    specialty = models.CharField(max_length=200, default='Artisan')
    location = models.CharField(max_length=200, default='Philippines')
    bio = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    photo = models.ImageField(upload_to='artisans/', blank=True)
    craftsmanship_note = models.TextField(blank=True, default='Every piece is handcrafted with care.')
    production_time = models.CharField(max_length=100, default='3-5 Days / Piece')
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    artisan = models.CharField(max_length=200)
    artisan_profile = models.ForeignKey(Artisan, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name

class Order(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address = models.CharField(max_length=300)
    barangay = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=50)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"Order #{self.pk} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"

# ========== NEW CART MODELS ==========
class Cart(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, null=True, blank=True, related_name='cart')
    session_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.username}"
        return f"Cart (session: {self.session_key})"

    def get_total(self):
        return sum(item.subtotal() for item in self.items.all())

    def get_item_count(self):
        return sum(item.quantity for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')  # one product per cart

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    def subtotal(self):
        return self.product.price * self.quantity