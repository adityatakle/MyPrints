from django.shortcuts import render, redirect, reverse, get_object_or_404
from .models import Client, Shop_owner, Shop_info, Shop_items, Cart, Cart_items, Feedback, Shop_timing, Cart_total
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.db.models import F
from django.db import transaction
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
from decimal import Decimal, ROUND_UP
import random
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
import uuid
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
        if Cart.objects.filter(user__user_id=user_uuid, shop_info_id=shop_id, is_paid=True, is_open=False, is_verified=False).exists():
            return redirect("success", shop_id=shop_id, user_id=user_uuid)
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
    
    # Expiration threshold
    last_24_hours = timezone.now() - timedelta(hours=24)

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
    if created:
        item = Shop_items.objects.filter(
            page_type='A4',
            is_color=False,
            is_b2b=False,
            shop_info_id=shop_id
        ).first()
        Cart_items.objects.create(
            file_id='FrontPage.pdf',
            display_name='FrontPage.pdf',
            quantity=1,
            total_pages=1,
            total_amount=1*item.price,
            cart=cart,
            shop_item=item
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
            s3_filename = f"uploads/{cart.id}/{file.name}"
            
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
                display_name=s3_filename.split('/')[-1],
                quantity=quantity,
                total_pages=total_pages,
                total_amount=total_amount, # This was missing
                cart=cart,
                shop_item=item
            )

            # Update pages (multiplied by quantity for accuracy)
            cart.total_pages += (total_pages * quantity)
            
            # DO NOT update cart.total_amount (Field removed from model)
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
    cart = get_object_or_404(Cart, user__user_id=user_id, shop_info__id=shop_id, is_open=True)
    cart_items = Cart_items.objects.filter(cart=cart)
    
    if request.method == "POST":
        if "subtract" in request.POST:
            item = get_object_or_404(Cart_items, id=request.POST.get("subtract"))
            if item.quantity > 1:
                item.quantity -= 1
                item.total_amount = item.quantity * (item.shop_item.price * item.total_pages)
                item.save()
            else:
                item.delete()
        elif "add" in request.POST:
            item = get_object_or_404(Cart_items, id=request.POST.get("add"))
            item.quantity += 1
            item.total_amount = item.quantity * (item.shop_item.price * item.total_pages)
            item.save()
        elif "remove-item" in request.POST:
            Cart_items.objects.filter(id=request.POST.get("remove-item")).delete()
        elif "add-priority" in request.POST:
            cart.priority = 1
            cart.save()
        elif "remove-priority" in request.POST:
            cart.priority = 0
            cart.save()
        elif "edit" in request.POST:
            item = get_object_or_404(Cart_items, id=request.POST.get('edit'))
            side_preference = request.POST.get('side') == 'True'
            if side_preference != item.shop_item.is_b2b:
                new_item = get_object_or_404(
                    Shop_items,
                    shop_info_id=shop_id,
                    page_type = item.shop_item.page_type,
                    is_color = item.shop_item.is_color,
                    is_b2b = side_preference    
                )
                item.shop_item = new_item
                item.total_amount = item.quantity * (new_item.price * item.total_pages)
                item.save()
        return redirect("cart", shop_id=shop_id, user_id=user_id)
    
    # CALCULATION LOGIC
    sub_total = 0
    shop_share = 0
    platform_share = 0
    front_page_price = 0  # Track the cost of the hidden front page

    for item in cart_items:
        # Calculate totals
        item_unit_price = item.shop_item.price * item.total_pages
        item_total = item_unit_price * item.quantity
        
        # Identify the FrontPage cost to subtract it from the display
        if item.file_id == 'FrontPage.pdf':
            front_page_price = item_total
        
        sub_total += item_total
        shop_share += item_total * (item.shop_item.shop_percent / 100)
        platform_share += item_total * (item.shop_item.platform_percent / 100)

    # This is what the user will see in the "Subtotal" line
    display_subtotal = sub_total - front_page_price

    # Save calculations to Cart_total (Keep the FULL sub_total here for backend records)
    total_data, created = Cart_total.objects.get_or_create(cart=cart)
    total_data.subtotal = sub_total
    total_data.shop_share = shop_share
    total_data.platform_share = platform_share
    
    # Use Decimal(str(...)) for safety
    p_fee_percent = Decimal(str(total_data.platform_charges_percent))
    pg_fee_percent = Decimal(str(total_data.payment_gateway_percent))
    pg_gst_percent = Decimal(str(total_data.payment_gateway_gst_percent))
    
    priority_fee = 0
    if cart.priority:
        priority_fee_percent = Decimal(str(total_data.priority_percent))
        # Usually, fees apply to the whole job (including the front page)
        priority_fee = (sub_total * (priority_fee_percent / Decimal('100'))).quantize(Decimal('0.01'))
        
    p_fee = (sub_total * (p_fee_percent / Decimal('100'))).quantize(Decimal('0.01'))
    pg_fee_raw = sub_total * (pg_fee_percent / Decimal('100'))
    pg_gst_raw = pg_fee_raw * (pg_gst_percent / Decimal('100'))
    pg_total_fee = (pg_fee_raw + pg_gst_raw).quantize(Decimal('0.01'), rounding=ROUND_UP)

    # Final Grand Total (This must include the front_page_price so the shop gets paid)
    total_data.grand_total = (sub_total + p_fee + pg_total_fee + priority_fee).quantize(Decimal('0.01'))
    total_data.save()

    return render(request, "printoapp/cart.html", {
        "cart": cart, 
        "cart_items": cart_items, 
        "shop_id": shop_id, 
        "user_id": user_id,
        "display_subtotal": display_subtotal, # Use this for the UI "Subtotal" line
        "p_fee": p_fee,
        "priority_fee": priority_fee,
        "pg_total_fee": pg_total_fee,
        "total_data": total_data,
        "total_amount": total_data.grand_total,
        "shop": Shop_info.objects.filter(id=shop_id).first()
    })


def create_order(request, amount):
    amount = int(amount * 100)
    currency = 'INR'
    data = {
        "amount": amount, 
        "currency": currency
        }
    '''
    data = {
        "amount":amount,
        "currency":currency,
        "transfers":[
            {
                "account":'', // shop_account_id
                "amount":'', // shop_share_in_paise
                "currency": currency
            }
            ]
        }
    '''
    razorpay_order = razorpay_client.order.create(data=data)
    return {"order-id":razorpay_order['id'], 'amount':amount}

def initiate_payment(request, shop_id, user_id):
    if request.method == 'POST':
        cart_total = Cart_total.objects.filter(
            cart__user__user_id=user_id, 
            cart__shop_info_id=shop_id, 
            cart__is_open=True
        ).first() 
        total_amount = cart_total.grand_total

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
            while True:
                pickup_code = random.randint(10,9999)
                if not Cart.objects.filter(shop_info_id=shop_id,
                                        is_paid=True, 
                                        is_verified=False, 
                                        pickup_code=pickup_code).exists():
                    cart.pickup_code = pickup_code
                    cart.save()
                    break
            
        
        
            front_page_item = Cart_items.objects.filter(
                file_id='FrontPage.pdf',
                display_name='FrontPage.pdf',
                cart=cart
            ).first()

            if front_page_item and "stamped" not in front_page_item.file_id:
                # Generate the buffer using your ReportLab logic
                stamped_buffer = test_local_pdf_stamping(cart.pickup_code)
                
                # Define the new filename
                s3_filename = f"uploads/{cart.id}/FrontPage_stamped.pdf"
                
                # Upload to S3 and update the database
                success_upload = upload_file_to_s3(stamped_buffer, s3_filename)
                if success_upload:
                    front_page_item.file_id = s3_filename
                    front_page_item.display_name = "Receipt_Cover.pdf"
                    front_page_item.save()
        
        
            return redirect("success", shop_id=shop_id, user_id=user_id)
        except Exception as e:
            print(f"Verification Failed Error: {e}")
            return redirect("cart", shop_id=shop_id, user_id=user_id)

def success(request, user_id, shop_id):
    cart = Cart.objects.filter(
        user__user_id=user_id, 
        shop_info_id=shop_id, 
        is_paid=True
    ).order_by('-id').first()

    if not cart:
        return redirect('cart', shop_id=shop_id, user_id=user_id)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        message = request.POST.get('message')
        rating = request.POST.get('rating')
        Feedback.objects.create(name=name, message=message, rating=rating)
        return redirect('success', user_id=user_id, shop_id=shop_id)

    return render(request, 'printoapp/success.html', {
        'cart': cart,
        'shop_id':shop_id,
        'user_id':user_id,
        'pickup_code': cart.pickup_code,
        'shop_lat': cart.shop_info.latitude,
        'shop_long': cart.shop_info.longitude,
        'shop_name': cart.shop_info.name,
        'is_verified': cart.is_verified
    })

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
    if request.method == 'POST':
        shop_token = request.headers.get('Shop-Token')
        shop_id = request.headers.get('Shop-Id')
        
        shop_data = get_object_or_404(Shop_info, id=shop_id, script_token=str(shop_token))
        
        # Sorted by: Processing first, then Priority (Premium), then Oldest first (FIFO)
        print_query = Cart.objects.filter(
            is_paid=True, 
            is_printed=False, 
            shop_info=shop_data
        ).order_by('-is_processing', '-priority', 'created_at')

        print_carts = []
        for cart in print_query:
            items_list = []
            requires_b2b = False
            
            for item in cart.cart_items.all():
                if item.shop_item.is_b2b:
                    requires_b2b = True
                
                file_url = get_presigned_url(item.file_id)
                if file_url:
                    items_list.append({
                        'id': item.id,
                        'file_name': item.display_name,
                        'file_url': file_url,
                        'page_type': item.shop_item.page_type,
                        'is_color': item.shop_item.is_color,
                        'is_b2b': item.shop_item.is_b2b,
                        'copies': item.quantity
                    })

            print_carts.append({
                'id': cart.id,
                'priority': cart.priority,
                'is_b2b': requires_b2b,
                'is_color': False, 
                'items': items_list
            })

        # 3. Get Carts for CLEANUP (Verified/Picked up, but NOT yet deleted locally)
        clean_carts = list(Cart.objects.filter(
            shop_info=shop_data,
            is_verified=True, 
            is_cleaned=False
        ).values_list('id', flat=True))

        return JsonResponse({
            'print_carts': print_carts,
            'clean_carts': clean_carts
        })

@csrf_exempt
def file_update(request):
    # Strictly check the method first
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    # 1. Use HYPHENS for headers to prevent server-side stripping
    shop_token = request.headers.get('Shop-Token')
    shop_id    = request.headers.get('Shop-Id')
    update_type = request.headers.get('Update-Type') # Use Update-Type
    item_id    = request.headers.get('Item-Id')
    cart_id    = request.headers.get('Cart-Id')

    try:
        # Security check
        get_object_or_404(Shop_info, id=shop_id, script_token=shop_token)

        # 2. Logic Gates (Exhaustive)
        if update_type == 'processing' and cart_id:
            cart = get_object_or_404(Cart, id=cart_id)
            cart.is_processing = True
            cart.save()
            return JsonResponse({'status': 'success', 'update': 'cart_processing'})

        elif update_type == 'printed' and item_id:
            item = get_object_or_404(Cart_items, id=item_id)
            item.is_printed = True
            item.save()

            # Trigger parent cart check
            parent_cart = item.cart
            still_waiting = Cart_items.objects.filter(cart=parent_cart, is_printed=False).exists()
            if not still_waiting:
                parent_cart.is_printed = True
                parent_cart.is_processing = False 
                parent_cart.save()
            
            return JsonResponse({'status': 'success', 'update': 'item_printed'})

        elif update_type == 'cleaned' and cart_id:
            cart = get_object_or_404(Cart, id=cart_id)
            cart.is_cleaned = True
            cart.save()
            return JsonResponse({'status': 'success', 'update': 'cart_cleaned'})

        # 3. If it's a POST but nothing matched, return 400 (Bad Request)
        # This prevents the "Logic Leak" to the 405
        return JsonResponse({
            'status': 'error', 
            'message': f'Logic Leak: Check your headers. Received update-type: {update_type}'
        }, status=400)

    except Exception as e:
         return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


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
    
    # CRITICAL: 'is_printed' must be in this list!
    fields = [
        'id', 'pickup_code', 'total_pages', 'total_amount', 
        'is_verified', 'is_processing', 'is_printed', 'priority', 'updated_at'
    ]

    # Use .annotate to pull 'grand_total' from the related 'Cart_total' model
    active_carts = Cart.objects.filter(
        shop_info=shop, is_paid=True, is_processing=True
    ).annotate(
        total_amount=F('cart_total__grand_total')
    ).order_by('-updated_at').values(*fields)
    
    other_carts = Cart.objects.filter(
        shop_info=shop, is_paid=True, is_processing=False
    ).annotate(
        total_amount=F('cart_total__grand_total')
    ).order_by('-priority', '-updated_at').values(*fields)

    return JsonResponse({
        'cart_info': list(active_carts) + list(other_carts)
    })

@login_required
def verify_cart(request):
    shop = get_object_or_404(Shop_info, shop_owner__user=request.user)
    if request.method == 'POST':
        cart_id = request.headers.get('cart-id')
        cart = Cart.objects.filter(id=cart_id, shop_info=shop).first()

        if cart and cart.is_printed and not cart.is_verified:
            cart.is_verified = True
            cart.save()
            return JsonResponse({'status': 'Verified successfully'})
            
    return JsonResponse({'status': 'Not ready for verification (is_printed might be False)'}, status=400)

@csrf_exempt
def cart_status(request, cart_id):
    if request.method == 'POST':
        # Just grab the cart; no need to loop through items anymore!
        cart = get_object_or_404(Cart, id=cart_id)
        
        return JsonResponse({
            # Use the boolean field we just automated
            'cart_status': 'Printed' if cart.is_printed else 'Not Printed',
            'is_verified': cart.is_verified
        })


def queue_size(request, shop_id, user_id=None):
    if request.method == 'POST':
        active_queue = Cart.objects.filter(
            shop_info__id=shop_id,
            is_paid=True,
            is_verified=False,
            is_printed=False
        ).order_by('-is_processing', '-priority', 'created_at')
        if not user_id:
            return JsonResponse({'queue_size':active_queue.count()})
        else:
            queue_list = list(active_queue.values_list('user__user_id', flat=True))
            try:
                target_uuid = uuid.UUID(user_id) 
                user_position = queue_list.index(target_uuid)
                return JsonResponse({'queue_size': user_position})
            except ValueError:
                return JsonResponse({'queue_size': 0})


#helper function

def test_local_pdf_stamping(pickup_code="0000"):
    static_base   = os.path.join(settings.BASE_DIR, 'printoapp', 'static', 'printoapp')
    template_path = os.path.join(static_base, 'FP_template.pdf')

    if not os.path.exists(template_path):
        return None

    PW, PH = 1860.0, 2631.12
    otp_str = str(pickup_code).zfill(4)

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))

    # Box 1 — top-left small reference box
    c.setFont("Helvetica-Bold", 52)
    c.setFillColor(HexColor("#000000"))
    tw = c.stringWidth(otp_str, "Helvetica-Bold", 52)
    c.drawString(178 - tw/2, 2426 - 26, otp_str)

    # Box 2 — main center inner box (large OTP number)
    c.setFont("Helvetica-Bold", 260)
    c.setFillColor(HexColor("#000000"))
    tw = c.stringWidth(otp_str, "Helvetica-Bold", 260)
    c.drawString(1090 - tw/2, 1371 - 260*0.35, otp_str)

    # Box 3 — bottom-right small reference box
    c.setFont("Helvetica-Bold", 52)
    c.setFillColor(HexColor("#000000"))
    tw = c.stringWidth(otp_str, "Helvetica-Bold", 52)
    c.drawString(1674 - tw/2, 153 - 26, otp_str)

    c.save()
    buf.seek(0)

    template_reader = PdfReader(template_path)
    overlay_reader  = PdfReader(buf)
    main_page = template_reader.pages[0]
    main_page.merge_page(overlay_reader.pages[0])

    writer = PdfWriter()
    writer.add_page(main_page)
    
    # NEW OUTPUT LOGIC: Return buffer instead of saving locally
    final_pdf_buffer = BytesIO()
    writer.write(final_pdf_buffer)
    final_pdf_buffer.seek(0)
    return final_pdf_buffer