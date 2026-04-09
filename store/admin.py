from django.contrib import admin
from .models import Product, Category, Artisan, Order, OrderItem

# Custom admin for Order to display relevant fields
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'email', 'payment_method', 'total', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('full_name', 'email', 'user__username')
    readonly_fields = ('created_at',)

class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
    list_filter = ('order',)

admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Artisan)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderItem, OrderItemAdmin)