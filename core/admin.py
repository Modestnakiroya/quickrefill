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


admin.site.register(Vendor)
admin.site.register(StockItem)
admin.site.register(Rider)
admin.site.register(Order)
admin.site.register(Rating)
admin.site.register(Settlement)
