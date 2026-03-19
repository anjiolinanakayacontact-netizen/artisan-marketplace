from django.contrib import admin
from .models import Product, Category, Artisan, Order, OrderItem

admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Artisan)
admin.site.register(Order)
admin.site.register(OrderItem)