from django.contrib import admin
from .models import Client, Shop_owner, Shop_info, Shop_items, Cart, Cart_items
# Register your models here.
admin.site.register(Client)
admin.site.register(Shop_owner)
admin.site.register(Shop_info)
admin.site.register(Shop_items)
admin.site.register(Cart)
admin.site.register(Cart_items)