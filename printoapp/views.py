from django.shortcuts import render, redirect, reverse, get_object_or_404
from .models import Client, Shop_owner, Shop_info, Shop_items, Cart, Cart_items, Feedback, Shop_timing
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
import os
from fpdf import FPDF
from pypdf import PdfReader, PdfWriter
from PIL import Image
from .file_upload import upload_file_to_s3, get_presigned_url
import re
import platform 
import os
from django.views.decorators.csrf import csrf_exempt
from io import BytesIO
from django.db.models import Sum, Q
import razorpay
from django.conf import settings
from datetime import timedelta

# Create your views here.

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_TEST, settings.RAZORPAY_SECRET_TEST))

def index(request):
    if request.method == "POST":
        name = request.POST.get('name')
        message = request.POST.get('message')
        Feedback.objects.create(name=name, message=message)
        return redirect('index')
    return render(request,"printoapp/index.html")


def privacy_policy(request):
    return render(request, "printoapp/privacy_policy.html")

def tnc(request):
    return render(request, "printoapp/tnc.html")

def shops(request):
    now = timezone.localtime()
    now_day = now.strftime('%A')
    now_time = now.time()
    
    shops_info = Shop_info.objects.filter(status='Active').prefetch_related('timings')
    
    # Prepare shop data for JavaScript
    shops_data = []
    for shop in shops_info:
        today_open = shop.timings.filter(weekday=now_day).first()
        is_open = False
        
        if today_open:
            start = today_open.start_time
            end = today_open.end_time
            if start <= end:
                is_open = start <= now_time <= end
            else:
                is_open = now_time >= start or now_time <= end
        
        shops_data.append({
            "id": shop.id,
            "name": shop.name,
            "location": shop.location,
            "landmark": shop.landmark,
            "city": shop.city,
            "state": shop.state,
            "latitude": float(shop.latitude) if shop.latitude else None,
            "longitude": float(shop.longitude) if shop.longitude else None,
            "is_open": is_open
        })

    if request.method == "POST":
        user_uuid = request.POST.get("user_id")
        shop_id = request.POST.get("shop_id")
        return redirect('upload', user_id=user_uuid, shop_id=shop_id)

    # Convert to JSON string safely
    context = {
        "shops_json": shops_data,
    }
    return render(request, "printoapp/shops.html", context)


def upload(request, user_id, shop_id):
    user_uuid = user_id
    if not user_uuid or not shop_id:
        return redirect('shops')    
    try:
        current_user = Client.objects.get(user_id=user_uuid) 
    except Exception as e:
        print(f"User error: {e}")
        return redirect('shops')
    
    # Define the expiration threshold
    last_24_hours = timezone.now() - timedelta(hours=24)

    # Delete the old cart directly using a filter
    Cart.objects.filter(
        user=current_user,
        shop_info_id=shop_id,
        is_open=True,
        created_at__lte=last_24_hours  # "Less than or equal to" the threshold
    ).delete()

    # Get or create the fresh cart
    cart, created = Cart.objects.get_or_create(
        user=current_user,
        shop_info_id=shop_id,
        is_open=True
    )
    # Get context data
    item_number = Cart_items.objects.filter(
        cart__user__user_id=user_id, 
        cart__shop_info_id=shop_id, 
        cart__is_open=True
    ).count()
    
    shop_item_list = Shop_items.objects.filter(shop_info_id=shop_id)
    
    if request.method == "POST":
        if "document" in request.FILES:
            page_type = request.POST.get('page_type')
            file = request.FILES["document"]
            is_color = request.POST.get('is_color').title()
            file_rename = request.POST.get('rename-file')
            is_b2b = request.POST.get('is_b2b').title()

            try:
                quantity = int(request.POST.get('quantity', 1))
            except (ValueError, TypeError):
                quantity = 1
            
            if quantity < 1:
                return render(request, "printoapp/upload.html", {
                    "error_message": "Copies cant be negative.",
                    "shop_item_list": shop_item_list,
                    "shop_id": shop_id,
                    "user_id": current_user,
                    "item_number": item_number
                })
            if file_rename:
                if re.fullmatch(r"[A-Za-z0-9_]+", file_rename) and file_rename.strip() != file.name:
                    file.name = f"{file_rename}.pdf"
            try:
                item = Shop_items.objects.get(
                    is_color=is_color, 
                    is_b2b=is_b2b, 
                    page_type=page_type, 
                    shop_info__id=shop_id
                )
            except Exception as e:
                return render(request, "printoapp/upload.html", {
                    "error_message": f"Configuration does not match shop items. {e}",
                    "shop_item_list": shop_item_list, 
                    "shop_id": shop_id, 
                    "user_id": user_uuid,
                    "item_number": item_number   
                })
            try:       
                reader = PdfReader(file)
             
                total_pages = len(reader.pages)
                output_stream = BytesIO()
                writer = PdfWriter()
                for page in reader.pages:
                    writer.add_page(page)
                writer.write(output_stream)
                output_stream.seek(0)
            except Exception as e:
                return render(request, "printoapp/upload.html", {
                    "error_message": f"PDF parsing error: {e}",
                    "shop_item_list": shop_item_list,
                    "shop_id": shop_id, 
                    "user_id": user_uuid,
                    "item_number": item_number
                })
            
            total_amount = total_pages * item.price * quantity
            s3_filename = f"uploads/{current_user.id}/{file.name}"
            
            if Cart_items.objects.filter(cart=cart, file_id=s3_filename).exists():
                return render(request, "printoapp/upload.html", {
                    "error_message": "This file is already in your cart.",
                    "shop_item_list": shop_item_list, 
                    "shop_id": shop_id, 
                    "user_id": user_uuid,
                    "item_number": item_number    
                })
            
            success = upload_file_to_s3(output_stream, s3_filename)
            
            if not success:
                return render(request, "printoapp/upload.html", {
                    "error_message": "Upload error (S3 Connection Failed).",
                    "shop_item_list": shop_item_list, 
                    "shop_id": shop_id, 
                    "user_id": user_uuid,
                    "item_number": item_number     
                })
            
            cart_item = Cart_items.objects.create(
                file_id=s3_filename,
                quantity=quantity,
                total_pages=total_pages,
                total_amount=total_amount,
                cart=cart,
                shop_item=item
            )
            cart.total_pages += total_pages
            cart.total_amount += cart_item.total_amount
            cart.save()

            
            message = f"{file.name} added to cart successfully."
            item_number = Cart_items.objects.filter(cart=cart).count()

            request.session['upload_success'] = message
            return redirect('upload', user_id=user_uuid, shop_id=shop_id)
        
    success_message = request.session.pop('upload_success', '')

    return render(request, "printoapp/upload.html", {
        "shop_item_list": shop_item_list, 
        "shop_id": shop_id, 
        "user_id": user_uuid, 
        "success_message": success_message, 
        "error_message": "", 
        "item_number": item_number
    })


def cart(request, shop_id, user_id):
    cart = get_object_or_404(Cart, user__user_id =user_id, shop_info__id=shop_id, is_open=True)
    cart_items = Cart_items.objects.filter( cart=cart)
    total_amount = 0
    for cart_item in cart_items:
        item = cart_item.file_id.split('/')[-1]
        cart_item.file_id = item
        total_amount += cart_item.total_amount
    shop = Shop_info.objects.filter(id=shop_id).first()
    if request.method == "POST":
        shop_id = request.POST.get("shop_id")
        user_id = request.POST.get("user_id")
        if "subtract" in request.POST:
            item_id = request.POST.get("subtract")
            item = get_object_or_404(Cart_items , id=item_id)
            unit_price = item.shop_item.price * item.total_pages
            
            if item.quantity > 1:
                cart.total_pages -= item.total_pages 
                cart.total_amount -= unit_price
                cart.save()
                item.quantity -= 1
                item.total_amount = item.quantity * unit_price
                item.save()
                
            else:
                cart.total_amount -= unit_price
                cart.total_pages -= item.total_pages
                cart.save()
                item.delete()

        elif "add" in request.POST:
            item_id = request.POST.get("add")
            item = get_object_or_404(Cart_items , id=item_id)
            unit_price = item.shop_item.price * item.total_pages
            
            cart.total_pages += item.total_pages
            cart.total_amount += item.shop_item.price * item.total_pages
            cart.save()
            item.quantity += 1
            item.total_amount = item.quantity * unit_price
            item.save()
            
        elif "remove-item" in request.POST:
            item_id = request.POST.get("remove-item")
            item = get_object_or_404(Cart_items, id=item_id)
            
            unit_price = item.shop_item.price * item.total_pages
            cart.total_amount -= unit_price * item.quantity
            cart.total_pages -= item.total_pages * item.quantity
            cart.save()
            item.delete()
        
        elif "add-priority" in request.POST:
            cart.priority = 1
            cart.save()
        
        elif "remove-priority" in request.POST:
            cart.priority = 0
            cart.save()

        cart_amount = 0
        cart_pages = 0
        for item in cart_items:
            cart_amount += item.total_amount
            cart_pages += item.total_pages * item.quantity
        cart.total_amount = cart_amount
        cart.total_pages = cart_pages
        cart.save()
        return redirect("cart", shop_id=shop_id, user_id=user_id)
    
    return render(request, "printoapp/cart.html", {"cart":cart, "cart_items":cart_items, "shop_id":shop_id, "user_id":user_id, "total_amount":total_amount, "shop":shop})

def create_order(request, amount):
    amount = int(amount * 100)
    currency = 'INR'
    data = {
        "amount": amount, 
        "currency": currency
        }
    razorpay_order = razorpay_client.order.create(data=data)
    return {"order-id":razorpay_order['id'], 'amount':amount}

def initiate_payment(request, shop_id, user_id):
    if request.method == 'POST':
        # Get current cart items to calculate the fresh total
        cart_items = Cart_items.objects.filter(
            cart__user__user_id=user_id, 
            cart__shop_info_id=shop_id, 
            cart__is_open=True
        )
        
        total_amount = sum(item.total_amount for item in cart_items)

        if total_amount <= 0:
            return JsonResponse({'error': 'Cart is empty'}, status=400)

        # Create the actual Razorpay Order
        order_data = create_order(request, total_amount) 
        
        return JsonResponse({
            'order_id': order_data['order-id'],
            'amount': order_data['amount'],
            'key_id': settings.RAZORPAY_KEY_TEST
        })
    else:
        return JsonResponse({'error':'ONLY POST METHOD ALLOWED'})


@csrf_exempt
def payment_status(request, shop_id, user_id):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id')
        order_id = request.POST.get('razorpay_order_id')
        signature = request.POST.get('razorpay_signature')

        try:
            razorpay_client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            cart = get_object_or_404(Cart, user__user_id=user_id, shop_info_id=shop_id, is_open=True)
            cart.is_open = False
            cart.is_paid = True
            cart.save()
            return render(request, 'printoapp/success.html', {'cart':cart})
        except Exception as e:
            print(f"Verification Failed Error: {e}")
            return render(request, 'printoapp/failure.html')


def shop_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            return render(request, "printoapp/shop_login.html", {"message": "Enter both fields."})
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if hasattr(user, 'shop_owner'): 
                login(request, user)
                return redirect('shop_index')
            else:
                return render(request, "printoapp/shop_login.html", {"message": "Access denied. Account is not a shop owner."})
        else:
            return render(request, "printoapp/shop_login.html", {"message": "Invalid username or password."})

    return render(request, "printoapp/shop_login.html")

@login_required
def shop_index(request):
    now_obj = timezone.localtime()
    hour = now_obj.hour
    greeting = "Morning" if 0 <= hour < 12 else "Noon" if hour == 12 else "Afternoon" if 12 < hour < 18 else "Evening"

    my_shop = my_shop = Shop_info.objects.filter(shop_owner__user=request.user).first()

    return render(request, "printoapp/shop_index.html", {
        "time": greeting,
        "username": request.user.username,
        "shop_name": my_shop.name
    })


@login_required
def shop_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse("shop_login"))


@csrf_exempt
def shop_connect(request):
    if request.method == "POST":
        shop_token = request.headers.get('Shop-token')
        shop_id = request.headers.get('Shop-id')
        shop_data = get_object_or_404(Shop_info, id=shop_id, script_token=str(shop_token))
        if shop_data:
            items = Cart_items.objects.filter(cart__is_paid=True, shop_item__shop_info__id = shop_id, is_printed=False)
            print_list = []
            
            for item in items:
                file_url = get_presigned_url(item.file_id)
                if file_url:
                    item_data = {
                        'id':item.id,
                        'file_name':item.file_id.split('/')[-1],
                        'file_url':file_url,
                        'page_type':item.shop_item.page_type,
                        'is_color':item.shop_item.is_color,
                        'is_b2b':item.shop_item.is_b2b,
                        'copies':item.quantity
                    }
                    print_list.append(item_data)
            items = Cart_items.objects.filter(cart__is_verified=True, shop_item__shop_info__id = shop_id, is_cleaned=False)
            clean_list = []
            
            for item in items:
                file_url = get_presigned_url(item.file_id)
                if file_url:
                    item_data = {
                        'id':item.id,
                        'file_name':item.file_id.split('/')[-1],
                        'file_url':file_url
                    }
                    clean_list.append(item_data)
            
            return JsonResponse({'status':'success', 'print_items':print_list, 'clean_items':clean_list})
        return JsonResponse({'status':"error"}, status=405)

@csrf_exempt
def file_update(request):
    if request.method == "POST":
        shop_token = request.headers.get('Shop-token')
        shop_id = request.headers.get('Shop-id')
        item_id = request.headers.get('item-id')
        update_type = request.headers.get('update_type')
        if not (shop_token and shop_id and item_id and update_type):
            return JsonResponse({'status': 'error', 'message': 'Missing headers'}, status=400)
         
        try:
            get_object_or_404(Shop_info, id=shop_id, script_token=shop_token)
            item = Cart_items.objects.get(id=item_id)
            if update_type == 'processing':
                parent_cart = item.cart
                parent_cart.is_processing = True
                parent_cart.save()
                print(f"Cart {parent_cart.id} is now Active (Processing).")
            else:
                field_name = f"is_{update_type}"
                setattr(item, field_name, True) 
                item.save()
                print(f"Job {item_id} marked as {update_type}.")
            
            return JsonResponse({'status': 'success'})

        except Shop_info.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid Shop Credentials'}, status=403)
        except Cart_items.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)
        except Exception as e:
             return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    return JsonResponse({'status': "error", "message": "Method not allowed"}, status=405)


@login_required
def shop_finance(request):
    shop = get_object_or_404(Shop_info, Shop_owner = request.user)
    trans = Cart_items.objects.filter(cart__shop_info=shop, cart__is_verified = True)
    trans = JsonResponse(list(trans))
    return trans
    

@login_required
def shop_catalogue(request):
    now_obj = timezone.localtime()
    hour = now_obj.hour
    greeting = "Morning" if 0 <= hour < 12 else "Noon" if hour == 12 else "Afternoon" if 12 < hour < 18 else "Evening"

    shop = Shop_info.objects.filter( shop_owner__user=request.user).first()
    items = Shop_items.objects.filter(
        shop_info = shop
        ).values(
            'id', 'page_type', 'is_color', 'is_b2b', 'price'
            ).order_by('page_type', 'is_color')
    timings = Shop_timing.objects.filter(shop__shop_owner__user=request.user).first()
    
    if request.method == "POST":
        request_type = request.POST.get('request_type')
        page_type = request.POST.get('page_type')
        is_color = request.POST.get('is_color') == 'on'
        is_b2b = request.POST.get('is_b2b') == 'on'
        price = request.POST.get('price')
        weekday = request.POST.get('weekday')
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        
        if request_type == "Add_catalogue":
            if Shop_items.objects.filter(shop_info=shop, page_type=page_type, is_color=is_color, is_b2b=is_b2b).exists():
                return redirect('shop_catalogue')
            Shop_items.objects.create(
                page_type = page_type,
                is_color=is_color,
                is_b2b = is_b2b, 
                price = price, 
                shop_info = shop
                )
            
        elif request_type == "Update_catalogue":
            item_id = request.POST.get('item_id')
            edit = Shop_items.objects.get(id = item_id, shop_info = shop)
            edit.page_type = page_type
            edit.is_color = is_color
            edit.is_b2b = is_b2b
            edit.price = price
            edit.save()
        
        elif request_type == "Delete_catalogue":
            item_id = request.POST.get('item_id')
            item = Shop_items.objects.get(id = item_id, shop_info = shop)
            item.delete()
            
        elif request_type == "Add_timing":
            if not Shop_timing.objects.filter(shop=shop, weekday=weekday).exists():
                Shop_timing.objects.create(
                    weekday=weekday,
                    start_time=start_time,
                    end_time=end_time,
                    shop=shop
                )
        
        elif request_type == "Update_timing":
            timing_id = request.POST.get('timing_id')
            timing = Shop_timing.objects.get(id = timing_id, shop = shop)
            timing.weekday = weekday
            timing.start_time = start_time
            timing.end_time = end_time
            timing.save()

        elif request_type == "Delete_timing":
            timing_id = request.POST.get('timing_id')
            timing = Shop_timing.objects.get(id = timing_id, shop = shop)
            timing.delete()

        return redirect('shop_catalogue')
    return render(request, 'printoapp/shop_catalogue.html', {
        'time': greeting,
        'username': request.user.username,
        'shop_info': shop,
        'items' : items,
        'open_days': timings
    })

@login_required
def shop_account(request):
    now_obj = timezone.localtime()
    hour = now_obj.hour
    greeting = "Morning" if 0 <= hour < 12 else "Noon" if hour == 12 else "Afternoon" if 12 < hour < 18 else "Evening"
    shop = Shop_info.objects.get(shop_owner__user = request.user)
    return render(request, 'printoapp/shop_account.html', {
        'time': greeting,
        'username': request.user.username,
        'shop':shop
    })




# api routes

def create_user(request):
    new_user = Client.objects.create()
    new_user.save()
    return JsonResponse({'user_id': str(new_user.user_id)})

def item_list(request, shop_id):
    unique_keys = Shop_items.objects.filter(shop_info_id=shop_id)\
                  .values_list('page_type', flat=True).distinct().order_by('page_type')

    # Result: { "A4": [item1, item2], "A3": [item3] }
    response_data = {}
    
    for page_type in unique_keys:
        items = Shop_items.objects.filter(
            shop_info_id=shop_id, 
            page_type=page_type
        ).values('id', 'is_color', 'is_b2b', 'price')
        
        response_data[page_type] = list(items)
            
    return JsonResponse(response_data)


@login_required
def shop_list(request):
    shop = get_object_or_404(Shop_info, shop_owner__user=request.user)
    
    fields = [
        'id', 'pickup_code', 'total_pages', 'total_amount', 
        'cart_status', 'is_verified', 'is_processing', 'priority'
    ]

    active_carts = Cart.objects.filter(
        shop_info=shop, is_paid=True, is_processing=True
    ).order_by('updated_at').values(*fields)
    
    other_carts = Cart.objects.filter(
        shop_info=shop, is_paid=True, is_processing=False
    ).order_by('-priority', 'updated_at').values(*fields)

    return JsonResponse({
        'cart_info': list(active_carts) + list(other_carts)
    })


@login_required
def verify_cart(request):
    shop = get_object_or_404(Shop_info, shop_owner__user=request.user)
    if request.method == 'POST':
        cart_id = request.headers.get('cart-id')
        cart = Cart.objects.filter(id=cart_id, shop_info=shop).first()
        
        if cart and not cart.is_verified:
            cart.is_verified = True
            cart.cart_status = "Verified"
            cart.save()
            return JsonResponse({'status': 'Verified successfully'})
            
    return JsonResponse({'status': 'Failed or already verified'}, status=400)

