from django.db import models
from django.contrib.auth.models import User
import secrets
import uuid

class Shop_owner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

class Client(models.Model):
    user_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Shop_info(models.Model):
    name = models.CharField(max_length =100)
    location = models.CharField(max_length =255)
    landmark = models.CharField(max_length =255)
    city = models.CharField(max_length =255)
    state = models.CharField(max_length =255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    join_date = models.DateField(auto_now_add=True)
    script_token = models.CharField(max_length=255, blank=True)
    shop_owner = models.ForeignKey("Shop_owner", related_name="shops", on_delete=models.CASCADE)
    status = models.CharField(max_length=255, default="Active")
    def save(self, *args, **kwargs):
        if not self.script_token:
            self.script_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)


class Shop_timing(models.Model):
    weekday = models.CharField(max_length=10)
    start_time = models.TimeField()
    end_time = models.TimeField()
    shop = models.ForeignKey("Shop_info", related_name="timings", on_delete=models.CASCADE)


class Shop_items(models.Model):
    page_type = models.CharField(max_length =255)
    is_color = models.BooleanField(default=False)
    is_b2b = models.BooleanField(default=False)
    price = models.DecimalField(decimal_places=2, max_digits=6)
    shop_percent = models.DecimalField(decimal_places=2, max_digits=5, default=100.00)
    platform_percent = models.DecimalField(decimal_places=2, max_digits=5, default=0.00)
    shop_info = models.ForeignKey("Shop_info", related_name="items", on_delete=models.CASCADE)

class Cart(models.Model):
    payment_id = models.CharField(max_length =255, blank=True)
    pickup_code = models.IntegerField(blank=True, null=True)
    is_open = models.BooleanField(default=True)
    is_paid = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_printed = models.BooleanField(default=False)
    is_processing = models.BooleanField(default=False)
    is_cleaned = models.BooleanField(default=False)
    total_pages = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    priority = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey("Client", on_delete=models.PROTECT)
    shop_info = models.ForeignKey("Shop_info", related_name="cart", on_delete=models.CASCADE)

class Cart_total(models.Model):
    subtotal = models.DecimalField(max_digits=9,decimal_places=2, default=0.00)
    shop_share = models.DecimalField(max_digits=9,decimal_places=2, default=0.00)
    priority_percent = models.DecimalField(max_digits=9, decimal_places=2, default=25.00)
    platform_share = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    platform_charges_percent = models.DecimalField(max_digits=5,decimal_places=2, default=20.00)
    payment_gateway_percent = models.DecimalField(max_digits=5, decimal_places=2, default=2.00)
    payment_gateway_gst_percent = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    grand_total = models.DecimalField(max_digits=9, decimal_places=2, default=0.00)
    cart = models.ForeignKey("Cart", related_name='cart_total' ,on_delete=models.CASCADE)
    
class Cart_items(models.Model):
    file_id = models.CharField(max_length =255)
    display_name = models.CharField(max_length=255, null=True, blank=True)
    quantity = models.IntegerField()
    total_pages = models.IntegerField()
    total_amount = models.DecimalField(max_digits=9, decimal_places=2)
    is_printed = models.BooleanField(default=False)
    is_cleaned = models.BooleanField(default=False) 
    cart = models.ForeignKey("Cart", related_name="cart_items", on_delete=models.CASCADE)
    shop_item = models.ForeignKey("Shop_items", related_name="cart_items", on_delete=models.PROTECT)

class Feedback(models.Model):
    name = models.CharField(max_length=50)
    message = models.CharField(max_length=255)
    rating = models.IntegerField(null=True, blank=True)