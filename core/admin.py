from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Order, Rating, Rider, Settlement, StockItem, User, Vendor


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'phone', 'role', 'first_name', 'last_name', 'is_staff')
    list_filter = ('role', 'is_staff')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('QuickRefill', {'fields': ('phone', 'role')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('QuickRefill', {'fields': ('email', 'phone', 'role')}),
    )


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'lat', 'lng', 'accepting_orders', 'verified', 'rating')
    list_editable = ('location', 'lat', 'lng', 'accepting_orders', 'verified')
    search_fields = ('name', 'location')


@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ('user', 'vehicle_plate', 'online', 'lat', 'lng', 'trips_count', 'rating')
    list_editable = ('vehicle_plate', 'online', 'lat', 'lng')


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ('vendor', 'brand', 'size_kg', 'price_refill', 'price_exchange', 'quantity')
    list_editable = ('price_refill', 'price_exchange', 'quantity')
    list_filter = ('vendor', 'size_kg', 'brand')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'customer', 'vendor', 'rider', 'delivery_address',
        'address_note', 'status', 'payment_method', 'payment_status', 'created_at',
    )
    list_filter = ('status', 'payment_method', 'payment_status')
    search_fields = ('code', 'delivery_address', 'address_note')


admin.site.register(Rating)
admin.site.register(Settlement)
