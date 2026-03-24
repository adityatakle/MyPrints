from django.shortcuts import render, redirect, reverse, get_object_or_404
from .models import Client, Shop_owner, Shop_info, Shop_items, Cart, Cart_items, Feedback
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
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

# Create your views here.
def index(request):
    if request.method == "POST":
        name = request.POST.get('name')
        message = request.POST.get('message')
        Feedback.objects.create(name=name, message=message)
        return redirect('index')
    return render(request,"printoapp/index.html")

def shops(request):
    now = timezone.localtime()
    now_day = now.weekday()
    now = now.time() 
    shops_info = Shop_info.objects.all()
    if request.method == "POST":
        user_uuid = request.POST.get("user_id")
        shop_id = request.POST.get("shop_id")
        return redirect('upload', user_id=user_uuid, shop_id=shop_id)
    return render(request, "printoapp/shops.html", {"shops_info":shops_info, "now":now, "now_day":now_day})


def upload(request, user_id, shop_id):
    user_uuid = user_id
    if not user_uuid or not shop_id:
        return redirect('shops')    
    try:
        current_user = Client.objects.get(user_id=user_uuid) 
    except Exception as e:
        print(f"User error: {e}")
        return redirect('shops')
    
    # Get context data
    item_number = Cart_items.objects.filter(
        cart__user__user_id=user_id, 
        cart__shop_info_id=shop_id, 
        cart__cart_status="Open"
    ).count()
    
    shop_item_list = Shop_items.objects.filter(shop_info_id=shop_id)
    
    # Get or create cart
    cart, _ = Cart.objects.get_or_create(
        user=current_user,
        shop_info_id=shop_id,
        cart_status="Open",
        defaults={'total_amount': 0.00}
    )
    
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
    cart_items = Cart_items.objects.filter( cart__user__user_id=user_id, cart__shop_info_id=shop_id, cart__cart_status="Open")
    total_amount = 0
    for cart_item in cart_items:
        item = cart_item.file_id.split('/')[-1]
        cart_item.file_id = item
        total_amount += cart_item.total_amount

    if request.method == "POST":
        shop_id = request.POST.get("shop_id")
        user_id = request.POST.get("user_id")
        if "subtract" in request.POST:
            item_id = request.POST.get("subtract")
            item = get_object_or_404(Cart_items , id=item_id)
            unit_price = item.shop_item.price * item.total_pages
            parent_cart = item.cart
            if item.quantity > 1:
                parent_cart.total_pages -= item.total_pages 
                parent_cart.total_amount -= unit_price
                parent_cart.save()
                item.quantity -= 1
                item.total_amount = item.quantity * unit_price
                item.save()
                
            else:
                parent_cart.total_amount -= unit_price
                parent_cart.total_pages -= item.total_pages
                parent_cart.save()
                item.delete()

        elif "add" in request.POST:
            item_id = request.POST.get("add")
            item = get_object_or_404(Cart_items , id=item_id)
            unit_price = item.shop_item.price * item.total_pages
            parent_cart = item.cart
            parent_cart.total_pages += item.total_pages
            parent_cart.total_amount += item.shop_item.price * item.total_pages
            parent_cart.save()
            item.quantity += 1
            item.total_amount = item.quantity * unit_price
            item.save()
            
        if "remove-item" in request.POST:
            item_id = request.POST.get("remove-item")
            item = get_object_or_404(Cart_items, id=item_id)
            unit_price = item.shop_item.price * item.total_pages
            parent_cart.total_amount -= unit_price * item.quantity
            parent_cart.total_pages -= item.total_pages * item.quantity
            parent_cart.save()
            item.delete()
        
        check_items = Cart_items.objects.filter( cart__user__user_id=user_id, cart__shop_info_id=shop_id, cart__cart_status="Open")
        check_cart = Cart.objects.filter(user__user_id=user_id, shop_info_id =shop_id, cart_status="Open").first()
        cart_amount = 0
        cart_pages = 0
        for item in check_items:
            cart_amount += item.total_amount
            cart_pages += item.total_pages * item.quantity
        check_cart.total_amount = cart_amount
        check_cart.total_pages = cart_pages
        check_cart.save()
        
        return redirect("cart", shop_id=shop_id, user_id=user_id)
    return render(request, "printoapp/cart.html", {"cart_items":cart_items, "shop_id":shop_id, "user_id":user_id, "total_amount":total_amount})

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

    if request.method == "POST":
        order_id = request.POST.get('order_id')
        order = get_object_or_404(Cart, id=order_id, shop_info=my_shop)
        order.cart_status = "Verified" if order.cart_status == "Paid" else "Paid"
        order.save()
        return redirect("shop_index")

    carts = Cart.objects.filter(
        shop_info=my_shop, 
        cart_status__in=[ "Paid", "Verified"]
    ).annotate(
        pages_sum=Sum('cart_items__total_pages') 
    ).order_by('cart_status', 'created_at')

    return render(request, "printoapp/shop_index.html", {
        "time": greeting, 
        "carts": carts,
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
            items = Cart_items.objects.filter(cart__cart_status="Paid", shop_item__shop_info__id = shop_id, is_printed=False)
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
            items = Cart_items.objects.filter(cart__cart_status="Verified", shop_item__shop_info__id = shop_id, is_cleaned=False)
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
    trans = Cart_items.objects.filter(cart__shop_info=shop, cart__cart_status = "Verified")
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
    if request.method == "POST":
        request_type = request.POST.get('request_type')
        page_type = request.POST.get('page_type')
        is_color = request.POST.get('is_color') == 'on'
        is_b2b = request.POST.get('is_b2b') == 'on'
        price = request.POST.get('price')
        if request_type == "Add":
            if Shop_items.objects.filter(shop_info=shop, page_type=page_type, is_color=is_color, is_b2b=is_b2b).exists():
                return redirect('shop_catalogue')
            Shop_items.objects.create(
                page_type = page_type,
                is_color=is_color,
                is_b2b = is_b2b, 
                price = price, 
                shop_info = shop
                )
            
        elif request_type == "Edit":
            item_id = request.POST.get('item_id')
            edit = Shop_items.objects.get(id = item_id, shop_info = shop)
            edit.page_type = page_type
            edit.is_color = is_color
            edit.is_b2b = is_b2b
            edit.price = price
            edit.save()
        return redirect('shop_catalogue')
    return render(request, 'printoapp/shop_catalogue.html', {
        'time': greeting,
        'username': request.user.username,
        'shop_name': shop.name,
        'items' : items
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
    shop = get_object_or_404(Shop_info, shop_owner__user = request.user)
    carts = Cart.objects.filter(shop_info=shop, cart_status__in = ['Paid', 'Verified']).order_by(
        'cart_status', 'created_at'
        ).values(
            'id', 'payment_id', 'pickup_code', 'total_pages', 'total_amount', 'cart_status'
            )
    response_data = {}
    response_data['cart_info'] = list(carts)
   
    return JsonResponse(response_data)

@login_required
def verify_cart(request):
    shop = get_object_or_404(Shop_info, shop_owner__user = request.user)
    response_data = {}
    if request.method == 'POST':
        cart_id = request.headers.get('cart-id')
        print(cart_id)
        cart = Cart.objects.filter(id=cart_id, shop_info=shop).first()
        if cart:
            if cart.cart_status == 'Paid':
                cart.cart_status = 'Verified'
                cart.save()
                response_data['status'] = f'Cart id {cart_id} verified'
            else:
                cart.cart_status = 'Paid'
                cart.save()
                response_data['status'] = f'Cart id {cart_id} status changed back to PAID'
        else:
            response_data['status'] = 'db error'
    else:
        response_data['status'] = 'ONLY POST ALLOWED.'
    print(response_data)
    return JsonResponse(response_data)