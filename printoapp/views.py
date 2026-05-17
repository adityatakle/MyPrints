from django.shortcuts import render, redirect, reverse, get_object_or_404
from .models import Client, Shop_owner, Shop_info, Shop_items, Cart, Cart_items, Feedback, Shop_timing, Cart_total, Shop_coupons, Admin_dash, Subscription_transactions, Settlements
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.db.models import F
from django.db import transaction
from django.db.models.functions import ExtractMonth, ExtractYear, TruncDate, TruncMonth
import os
from pypdf import PdfReader, PdfWriter
from .file_upload import upload_file_to_s3, get_presigned_preview_url, get_presigned_url, delete_from_s3 
import re
import os
from django.views.decorators.csrf import csrf_exempt
from io import BytesIO
from django.db.models import Sum, Count
import razorpay
from django.conf import settings
from datetime import timedelta, datetime
from decimal import Decimal, ROUND_UP, ROUND_HALF_UP
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


def creator_login(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()
        if not username or not password:
            return render(request, "printoapp/creator_login.html", {"message": "Enter both fields."})

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if hasattr(user, 'admin_dash'):
                login(request, user)
                return redirect('creator_index')
            else:
                return render(request, "printoapp/creator_login.html", {"message": "Access denied."})
        else:
            return render(request, "printoapp/creator_login.html", {"message": "Invalid username or password."})
    return render(request, "printoapp/creator_login.html")

@login_required
def creator_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse("creator_login"))

@login_required
def creator_index(request):
    now = timezone.localtime()
    today = now.date()
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    # 1. Today's Metrics
    today_cart_placed = Cart.objects.filter(
        updated_at__date=today, 
        is_paid=True
    )
    today_cart_verified = today_cart_placed.filter(is_verified=True)

    # 2. Weekly Metrics (Last 7 days)
    week_cart_placed = Cart.objects.filter(
        updated_at__gte=week_start, 
        is_paid=True, 
        is_verified=True
    )

    # 3. Monthly Metrics (Last 30 days)
    month_cart_placed = Cart.objects.filter(
        updated_at__gte=month_start, 
        is_paid=True, 
        is_verified=True
    )

    # 4. All Time Metrics
    all_time_cart_placed = Cart.objects.filter(
        is_paid=True, 
        is_verified=True
    )
    # total pages count (daily, weekly, monthly, all time)
    stats = Cart_items.objects.filter(cart__updated_at__date=today, cart__is_paid=True).aggregate(total=Sum('total_pages'))
    today_total_pages = stats['total'] or 0
    stats = Cart_items.objects.filter(cart__updated_at__gte=week_start, cart__is_paid=True, cart__is_verified=True).aggregate(total=Sum('total_pages'))
    week_total_pages = stats['total'] or 0
    stats = Cart_items.objects.filter(cart__updated_at__gte=month_start, cart__is_paid = True, cart__is_verified=True).aggregate(total=Sum('total_pages'))
    month_total_pages = stats['total'] or 0
    stats = Cart_items.objects.filter(cart__is_paid = True, cart__is_verified=True).aggregate(total=Sum('total_pages'))
    all_time_total_pages = stats['total'] or 0
    
    # total pages printed count
    stats = Cart_items.objects.filter(cart__updated_at__date=today, is_printed = True).aggregate(total=Sum('total_pages'))
    today_total_pages_printed = stats['total'] or 0
    stats = Cart_items.objects.filter(cart__updated_at__gte=week_start, is_printed = True).aggregate(total=Sum('total_pages'))
    week_total_pages_printed = stats['total'] or 0
    stats = Cart_items.objects.filter(cart__updated_at__gte=month_start, is_printed = True).aggregate(total=Sum('total_pages'))
    month_total_pages_printed = stats['total'] or 0
    stats = Cart_items.objects.filter(cart__is_paid = True, cart__is_verified=True, is_printed=True).aggregate(total=Sum('total_pages'))
    all_time_total_pages_printed = stats['total'] or 0

    today_financials = Cart_total.objects.filter(
        cart__updated_at__date=today, 
        cart__is_printed=True
    ).aggregate(
        shop=Sum('shop_share'),
        platform=Sum('platform_share'),
        total=Sum('grand_total')
    )
    today_shop_share = today_financials['shop'] or 0
    today_my_share = today_financials['platform'] or 0
    today_grand_total = today_financials['total'] or 0

    weekly_financials = Cart_total.objects.filter(
        cart__updated_at__gte=week_start, 
        cart__is_printed=True,
        cart__is_verified=True
    ).aggregate(
        shop=Sum('shop_share'),
        platform=Sum('platform_share'),
        total=Sum('grand_total')
    )
    weekly_shop_share = weekly_financials['shop'] or 0
    weekly_my_share = weekly_financials['platform'] or 0
    weekly_grand_total = weekly_financials['total'] or 0
    
    month_financials = Cart_total.objects.filter(
        cart__updated_at__gte=month_start, 
        cart__is_printed=True,
        cart__is_verified=True
    ).aggregate(
        shop=Sum('shop_share'),
        platform=Sum('platform_share'),
        total=Sum('grand_total')
    )
    month_shop_share = month_financials['shop'] or 0
    month_my_share = month_financials['platform'] or 0
    month_grand_total = month_financials['total'] or 0
    
    all_financials = Cart_total.objects.filter( 
        cart__is_printed=True,
        cart__is_verified=True
    ).aggregate(
        shop=Sum('shop_share'),
        platform=Sum('platform_share'),
        total=Sum('grand_total')
    )
    all_shop_share = all_financials['shop'] or 0
    all_my_share = all_financials['platform'] or 0
    all_grand_total = all_financials['total'] or 0

    # total_shops_on_boarded
    active_shops_onboard = Shop_info.objects.filter(status='Active').count()
    total_shops_onboard = Shop_info.objects.filter().count()

    # total_users
    total_users = Client.objects.filter().count()

    #subscription revenue
    monthly_subscription_revenue = (Subscription_transactions.objects.filter()
    .annotate(year=ExtractYear('trans_time'),month=ExtractMonth('trans_time'))
    .values('year', 'month')
    .annotate(total_revenue=Sum('trans_money'))
    .order_by('-year', '-month')
    )
    monthly_subscription_revenue = list(monthly_subscription_revenue)
    all_time_subscription_revenue = Subscription_transactions.objects.filter().aggregate(total=Sum('trans_money'))

    # remaining to pay all time 
    total_paid_by_students = Cart_total.objects.filter(cart__is_paid=True, cart__is_verified=True).aggregate(total=Sum('shop_share'))['total'] or 0
    total_paid_to_shops = Settlements.objects.filter().aggregate(total=Sum('sett_amount'))['total'] or 0
    to_pay = total_paid_by_students - total_paid_to_shops

    # average_order_value (all time)
    aov = all_grand_total / (all_time_cart_placed.count() or 1)
    return render(request, "printoapp/creator_index.html", {
        "today_total_pages":today_total_pages,
        "week_total_pages":week_total_pages,
        "month_total_pages":month_total_pages,
        "all_time_total_pages":all_time_total_pages,
        "today_total_pages_printed":today_total_pages_printed,
        "week_total_pages_printed":week_total_pages_printed,
        "month_total_pages_printed":month_total_pages_printed,
        "all_time_total_pages_printed":all_time_total_pages_printed,
        "today_shop_share":today_shop_share,
        "today_my_share":today_my_share,
        "today_grand_total":today_grand_total,
        "weekly_shop_share":weekly_shop_share,
        "weekly_my_share":weekly_my_share,
        "weekly_grand_total":weekly_grand_total,
        "month_shop_share":month_shop_share,
        "month_my_share":month_my_share,
        "month_grand_total":month_grand_total,
        "all_shop_share":all_shop_share,
        "all_my_share":all_my_share,
        "all_grand_total":all_grand_total,
        "active_shops_onboard":active_shops_onboard,
        "total_shops_onboard":total_shops_onboard,
        "total_users":total_users,
        "monthly_subscription_revenue":monthly_subscription_revenue,
        "all_time_subscription_revenue":all_time_subscription_revenue,
        "to_pay":to_pay,
        "aov":aov
    })

@login_required
def creator_shop_view(request):
    shops = Shop_info.objects.filter()
    if request.method == 'POST':
        now = timezone.localtime()
        today = now.date()
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        # shop_info
        shop_id = request.POST.get('shop_id')
        shop = Shop_info.objects.get(id=shop_id)
        shop_name = shop.name
        shop_location = shop.location
        shop_landmark = shop.landmark
        shop_city = shop.city
        shop_state = shop.state
        shop_status = shop.status

        # shops subsription details
        shop_sub_details = Subscription_transactions.objects.filter(shop=shop)
        
        # shops payout details
        shop_settlements_details = Settlements.objects.filter(shop=shop)
        
        # shops summary
        stats = Cart_items.objects.filter(cart__updated_at__date=today, cart__is_paid=True, cart__shop_info=shop).aggregate(total=Sum('total_pages'))
        today_total_pages = stats['total'] or 0
        stats = Cart_items.objects.filter(cart__updated_at__gte=week_start, cart__is_paid=True, cart__is_verified=True, cart__shop_info=shop).aggregate(total=Sum('total_pages'))
        week_total_pages = stats['total'] or 0
        stats = Cart_items.objects.filter(cart__updated_at__gte=month_start, cart__is_paid = True, cart__is_verified=True, cart__shop_info=shop).aggregate(total=Sum('total_pages'))
        month_total_pages = stats['total'] or 0
        stats = Cart_items.objects.filter(cart__is_paid = True, cart__is_verified=True, cart__shop_info=shop).aggregate(total=Sum('total_pages'))
        all_time_total_pages = stats['total'] or 0
        stats = Cart_items.objects.filter(cart__updated_at__date=today, is_printed = True, cart__shop_info=shop).aggregate(total=Sum('total_pages'))
        today_total_pages_printed = stats['total'] or 0

        # shop income
        stats = Cart_total.objects.filter(cart__updated_at__date=today, cart__is_printed=True, cart__shop_info=shop).aggregate(total=Sum('shop_share'))
        today_shop_share = stats['total'] or 0
        stats = Cart_total.objects.filter(cart__updated_at__gte=week_start, cart__is_printed=True, cart__is_verified=True, cart__shop_info=shop).aggregate(total=Sum('shop_share'))
        week_shop_share = stats['total'] or 0
        stats = Cart_total.objects.filter(cart__updated_at__gte=month_start, cart__is_printed=True, cart__is_verified=True, cart__shop_info=shop).aggregate(total=Sum('shop_share'))
        month_shop_share = stats['total'] or 0
        stats = Cart_total.objects.filter(cart__is_printed=True, cart__is_verified=True, cart__shop_info=shop).aggregate(total=Sum('shop_share'))
        all_time_shop_share = stats['total'] or 0
        shop_monthly_revenue = (
            Cart_total.objects.filter(cart__is_printed=True, cart__is_verified=True, cart__shop_info=shop)
            .annotate(year=ExtractYear('cart__updated_at'),month=ExtractMonth('cart__updated_at')
            )
            .values('year', 'month')  # Group by both
            .annotate(total_revenue=Sum('shop_share'))
            .order_by('-year', '-month')
        )

        # my income from specific shop
        stats = Cart_total.objects.filter(cart__updated_at__date=today, cart__is_printed=True, cart__shop_info=shop).aggregate(total=Sum('platform_share'))
        today_my_share = stats['total'] or 0
        stats = Cart_total.objects.filter(cart__updated_at__gte=week_start, cart__is_printed=True, cart__is_verified=True, cart__shop_info=shop).aggregate(total=Sum('platform_share'))
        week_my_share = stats['total'] or 0
        stats = Cart_total.objects.filter(cart__updated_at__gte=month_start, cart__is_printed=True, cart__is_verified=True, cart__shop_info=shop).aggregate(total=Sum('platform_share'))
        month_my_share = stats['total'] or 0
        stats = Cart_total.objects.filter(cart__is_printed=True, cart__is_verified=True, cart__shop_info=shop).aggregate(total=Sum('platform_share'))
        all_time_my_share = stats['total'] or 0
        my_monthly_revenue = (
            Cart_total.objects.filter(cart__is_printed=True, cart__is_verified=True, cart__shop_info=shop)
            .annotate(year=ExtractYear('cart__updated_at'),month=ExtractMonth('cart__updated_at')
            )
            .values('year', 'month')  # Group by both
            .annotate(total_revenue=Sum('platform_share'))
            .order_by('-year', '-month')
        )
        shop_items = Shop_items.objects.filter(shop_info=shop)
        shop_monthly_revenue = list(shop_monthly_revenue)
        my_monthly_revenue = list(my_monthly_revenue)
        if request.POST.get('shop_item_id') and request.POST.get('platform_price'):
            shop_item_id = request.POST.get('shop_item_id')
            platform_price = request.POST.get('platform_price')
            item = Shop_items.objects.get( id=shop_item_id)
            item.platform_price = platform_price
            item.save()
        return render(request, 'printoapp/creator_shop_view.html', {
            'shop_id':shop_id,
            'shop_name':shop_name,
            'shop_location':shop_location,
            'shop_landmark':shop_landmark,
            'shop_city':shop_city,
            'shop_state':shop_state,
            'shop_status':shop_status,
            'shop_sub_details':shop_sub_details,
            'shop_settlements_details':shop_settlements_details,
            'today_total_pages':today_total_pages,
            'week_total_pages':week_total_pages,
            'month_total_pages':month_total_pages,
            'all_time_total_pages':all_time_total_pages,
            'today_total_pages_printed':today_total_pages_printed,
            'today_shop_share':today_shop_share,
            'week_shop_share':week_shop_share,
            'month_shop_share':month_shop_share,
            'all_time_shop_share':all_time_shop_share,
            'shop_monthly_revenue':shop_monthly_revenue,
            'today_my_share':today_my_share,
            'week_my_share':week_my_share,
            'month_my_share':month_my_share,
            'all_time_my_share':all_time_my_share,
            'my_monthly_revenue':my_monthly_revenue,
            'shop_items':shop_items
        })
    return render(request, 'printoapp/creator_shop_view.html', {
            'shops':shops
        })
        
@login_required
def creator_settings(request):
    """Simply loads the settings page when clicked from the sidebar."""
    return render(request, 'printoapp/creator_settings.html')

@login_required
def create_new_owner(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        password = request.POST.get('password')
        mobile_number = request.POST.get('mobile_number')
        payee_name = request.POST.get('payee_name')
        nickname = request.POST.get('nickname')
        account_number = request.POST.get('account_number')
        IFSC_code = request.POST.get('IFSC_code')
        account_type = request.POST.get('account_type')
        if User.objects.filter(username=username).exists():
            return render(request, 'printoapp/creator_settings.html')
        required_fields = [ first_name, last_name, username, password, mobile_number, payee_name, account_number, IFSC_code]
        if not all(required_fields):
            return render(request, 'printoapp/creator_settings.html', {
                'message':'Enter all fields.'
            })
        if username and password:
            # create new shop user
            new_user = User.objects.create_user(
                first_name=first_name,
                last_name = last_name,
                username=username,
                password=password,
                is_active=True
                )    
            Shop_owner.objects.create(
                user=new_user, 
                mobile_number=mobile_number, 
                payee_name=payee_name, 
                nickname=nickname, 
                account_number=account_number, 
                IFSC_code=IFSC_code, 
                account_type=account_type
            )
        return render(request, 'printoapp/creator_settings.html', {
            'message':f'User with username {username} created successfully.'
        })
    return render(request, 'printoapp/creator_settings.html')
        

@login_required
def create_shop(request):
    if request.method == 'POST':
        shop_owner = request.POST.get('username')
        shop_name = request.POST.get('name')
        shop_location = request.POST.get('location')
        shop_landmark = request.POST.get('landmark')
        shop_city = request.POST.get('city')
        shop_state = request.POST.get('state')
        shop_latitude = request.POST.get('latitude')
        shop_longitude = request.POST.get('longitude')
        gst_number = request.POST.get('gst_number')
        required = [shop_owner, shop_name, shop_location, shop_landmark, shop_city, shop_state, shop_latitude, shop_longitude, gst_number]
        if not all(required):
            return render(request, 'printoapp/creator_settings.html', {
                'message':'Enter all fields.'
            })
        user_obj = User.objects.get(username=shop_owner)
        shop_owner = Shop_owner.objects.get(user=user_obj)
        Shop_info.objects.create(
            shop_owner=shop_owner, 
            name=shop_name, 
            location=shop_location, 
            landmark=shop_landmark, 
            city=shop_city, 
            state=shop_state, 
            latitude=shop_latitude, 
            longitude=shop_longitude, 
            gst_number=gst_number
        )
        return render(request, 'printoapp/creator_settings.html', {
            'message':f'Shop with name: {shop_name} created successfully'
        })
    return render(request, 'printoapp/creator_settings.html')

@login_required
def password_reset(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        new_password = request.POST.get('password')
        if not username or not new_password:
            return render(request, 'printoapp/creator_settings.html', {
                'message': 'Enter all fields'
            })
        try:
            # 1. Fetch the User object directly
            user_to_update = User.objects.get(username=username)
            
            # 2. Use set_password to hash the string
            user_to_update.set_password(new_password)
            user_to_update.save()

        except User.DoesNotExist:
            return render(request, 'printoapp/creator_settings.html', {
                'message':'username does not exist'
            })
        return render(request, 'printoapp/creator_settings.html', {
            'message':'Password reset success.'
        })
    return render(request, 'printoapp/creator_settings.html')

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
            raw_pages_count=1,
            total_amount=1*item.final_price,
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
            file_rename = request.POST.get('rename-file')
            is_color = request.POST.get('is_color') == 'True' or request.POST.get('is_color') == 'true'
            is_b2b = request.POST.get('is_b2b') == 'True' or request.POST.get('is_b2b') == 'true'
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
                reader = PdfReader(file)
                raw_pages_count = len(reader.pages)
                size_warning = ""
                # A4 bounds with a ~5% margin
                MAX_WIDTH, MAX_HEIGHT = 625.0, 885.0
                MIN_WIDTH, MIN_HEIGHT = 565.0, 800.0

                # ─── NEW: FAST ITERATION CHECK ───
                for i, page in enumerate(reader.pages):
                    width = float(page.mediabox.width)
                    height = float(page.mediabox.height)
                    requires_scaling = False
                    if width > MAX_WIDTH or height > MAX_HEIGHT:
                        size_warning = " ⚠️ (Note: One or more pages are larger than A4 and will be scaled to fit.)"
                        requires_scaling = True
                        break

                    elif width < MIN_WIDTH or height < MIN_HEIGHT:
                        size_warning = " ⚠️ (Note: One or more pages are smaller than A4 and will be scaled to fit.)"
                        requires_scaling = True
                        break

                if not is_b2b:
                    total_pages = raw_pages_count
                else:
                    if len(reader.pages) %2 == 0:
                        total_pages = len(reader.pages) // 2
                    else:
                        total_pages = (len(reader.pages) // 2 )+ 1

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
            try:
                if raw_pages_count == 1:
                    item = Shop_items.objects.get(
                        is_color=is_color,
                        is_b2b=False,
                        page_type=page_type,
                        shop_info__id=shop_id
                    )
                else:
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

            total_amount = total_pages * (item.final_price) * quantity
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
                requires_scaling = requires_scaling,
                total_pages=total_pages,
                raw_pages_count = raw_pages_count,
                total_amount=total_amount, # This was missing
                cart=cart,
                shop_item=item
            )

            # Update pages (multiplied by quantity for accuracy)
            cart.total_pages += (total_pages * quantity)

            cart.save()

            message = f"{file.name} added to cart successfully. \n{size_warning}"
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

def update_cart_financial_records(cart):
    """
    Helper function to recalculate and permanently save all financial aggregates
    to the Cart_total database ledger whenever items inside a cart change.
    """
    cart_items = Cart_items.objects.filter(cart=cart)

    sub_total = Decimal('0.00')
    shop_share = Decimal('0.00')
    platform_share = Decimal('0.00')
    fp_price = Decimal('0.00')
    page_count = 0
    platform_fee = Decimal('0.00')
    for item in cart_items:
        item_unit_price = (item.shop_item.final_price) * item.total_pages
        item_total = item_unit_price * item.quantity
        page_count += item.raw_pages_count * item.quantity
        sub_total += item_total
        shop_share += (item.shop_item.price) * item.total_pages * item.quantity
        platform_share += (item.shop_item.platform_price) * item.total_pages * item.quantity
        if item.file_id == 'FrontPage.pdf':
            fp_price = item.shop_item.final_price * item.total_pages * item.quantity
            sub_total -= fp_price

    cart.total_pages = page_count
    cart.save()
        
    # Fetch or instantiate the ledger baseline row
    total_data, created = Cart_total.objects.get_or_create(cart=cart)
    total_data.total_pages = page_count
    total_data.subtotal = sub_total
    total_data.shop_share = shop_share
    total_data.platform_share = platform_share
    if cart.total_pages < 5:
        platform_fee = fp_price
    total_data.platform_fee = platform_fee
    # Cast fields using explicit String to Decimal formatting bounds
    pg_fee_percent = Decimal(str(total_data.payment_gateway_percent))
    pg_gst_percent = Decimal(str(total_data.payment_gateway_gst_percent))

    priority_fee = Decimal('0.00')
    if cart.priority:
        priority_fee_percent = Decimal(str(total_data.priority_percent))
        priority_fee = (sub_total * (priority_fee_percent / Decimal('100'))).quantize(Decimal('0.01'))
    total_data.priority_fee = priority_fee
    pg_fee_raw = (sub_total + platform_fee + priority_fee) * (pg_fee_percent / Decimal('100'))
    pg_gst_raw = pg_fee_raw * (pg_gst_percent / Decimal('100'))
    pg_total_fee = (pg_fee_raw + pg_gst_raw).quantize(Decimal('0.01'), rounding=ROUND_UP)
    total_data.payment_gateway_total_fee = pg_total_fee
    raw_total = (sub_total + pg_total_fee + priority_fee + platform_fee).quantize(Decimal('0.01'))

    rounded_total = (raw_total * Decimal('2')).quantize(Decimal('1'), rounding=ROUND_HALF_UP) / Decimal('2')
    total_data.round_up = rounded_total - raw_total
    total_data.raw_total = raw_total
    total_data.grand_total = rounded_total
    total_data.save()

    return total_data


def cart(request, shop_id, user_id):
    cart = get_object_or_404(Cart, user__user_id=user_id, shop_info__id=shop_id, is_open=True)
    cart_items = Cart_items.objects.filter(cart=cart)

    if request.method == "POST":
        # Wrap modifications inside a transaction block to maintain absolute database integrity
        with transaction.atomic():
            if "subtract" in request.POST:
                item = get_object_or_404(Cart_items, id=request.POST.get("subtract"))
                if item.quantity > 1:
                    item.quantity -= 1
                    item.total_amount = item.quantity * ((item.shop_item.final_price) * item.total_pages)
                    item.save()
                else:
                    item.delete()

            elif "add" in request.POST:
                item = get_object_or_404(Cart_items, id=request.POST.get("add"))
                item.quantity += 1
                item.total_amount = item.quantity * ((item.shop_item.final_price) * item.total_pages)
                item.save()
                
            elif "remove-item" in request.POST:
                item = get_object_or_404(Cart_items, id = request.POST.get("remove-item"))
                delete_from_s3(item.file_id)
                item.delete()

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
                        page_type=item.shop_item.page_type,
                        is_color=item.shop_item.is_color,
                        is_b2b=side_preference
                    )

                    if item.file_id != 'FrontPage.pdf':
                        if not side_preference:
                            item.total_pages = item.raw_pages_count
                        else:
                            if item.raw_pages_count % 2 == 0:
                                item.total_pages = item.raw_pages_count // 2
                            else:
                                item.total_pages = (item.raw_pages_count // 2) + 1

                    item.shop_item = new_item
                    item.total_amount = item.quantity * ((new_item.final_price )* item.total_pages)
                    item.save()

            # Recalculate your ledger records BEFORE redirecting
            update_cart_financial_records(cart)

        return redirect("cart", shop_id=shop_id, user_id=user_id)

    # ─── GET REQUEST RENDERING ───
    # Run a fresh calculation check to capture context data cleanly
    total_data = update_cart_financial_records(cart)

    display_subtotal = total_data.subtotal
    priority_fee = total_data.priority_fee
    platform_fee = total_data.platform_fee
    payment_gateway_percent = total_data.payment_gateway_percent
    payment_gateway_gst_percent = total_data.payment_gateway_gst_percent
    payment_gateway_total = total_data.payment_gateway_total_fee
    raw_total = total_data.raw_total
    round_up = total_data.round_up
    grand_total = total_data.grand_total
    needed_pages = 0
    if total_data.total_pages < 5:
        needed_pages = 5 - total_data.total_pages
    is_round_down = round_up < 0
    abs_round_up = abs(round_up)
    
    return render(request, "printoapp/cart.html", {
        "cart": cart,
        "cart_items": cart_items,
        "shop_id": shop_id,
        "user_id": user_id,
        "display_subtotal": display_subtotal,
        "priority_fee": priority_fee,
        'needed_pages':needed_pages,
        'platform_fee':platform_fee,
        'payment_gateway_percent':payment_gateway_percent,
        'payment_gateway_gst_percent':payment_gateway_gst_percent,
        'payment_gateway_total':payment_gateway_total,
        'round_up':round_up,
        'abs_round_up': abs_round_up,
        'is_round_down': is_round_down,
        "total_data": total_data,
        "total_amount": grand_total,
        "shop": Shop_info.objects.filter(id=shop_id).first()
    })


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
        return redirect('shops')

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

                items_list.append({
                    'id': item.id,
                    'file_name': item.display_name,
                    'file_url': None,
                    'page_type': item.shop_item.page_type,
                    'is_color': item.shop_item.is_color,
                    'is_b2b': item.shop_item.is_b2b,
                    'copies': item.quantity
                })

            print_carts.append({
                'id': cart.id,
                'is_processing':cart.is_processing,
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
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Only POST allowed'}, status=405)

    shop_token = request.headers.get('Shop-Token')
    shop_id    = request.headers.get('Shop-Id')
    update_type = request.headers.get('Update-Type')
    item_id    = request.headers.get('Item-Id')
    cart_id    = request.headers.get('Cart-Id')

    try:
        get_object_or_404(Shop_info, id=shop_id, script_token=shop_token)

        if update_type == 'processing' and cart_id:
            cart = get_object_or_404(Cart, id=cart_id, shop_info_id=shop_id)
            cart.is_processing = True
            cart.save()
            items = Cart_items.objects.filter(cart=cart)
            cart_data = []
            for item in items:
                file_url =  get_presigned_url(item.file_id, 1800)
                cart_data.append({
                    'id':item.id,
                    'file_url':file_url
                })
            return JsonResponse({'status': 'success', 'update': 'cart_processing', 'cart_data':cart_data})

        elif update_type == 'printed' and item_id:
            item = get_object_or_404(Cart_items, id=item_id, cart__shop_info_id=shop_id)
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
            cart = get_object_or_404(Cart, id=cart_id, shop_info_id=shop_id)
            cart.is_cleaned = True
            cart.save()
            items = Cart_items.objects.filter(cart=cart)
            for item in items:
                delete_from_s3(item.file_id)
            items.update(is_cleaned=True)
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
    now_obj = timezone.localtime()
    hour = now_obj.hour
    greeting = "Morning" if 0 <= hour < 12 else "Noon" if hour == 12 else "Afternoon" if 12 < hour < 18 else "Evening"
    shop = get_object_or_404(Shop_info, shop_owner__user=request.user)
    
    # 1. Base Queryset: Only verified carts for this shop
    base_qs = Cart_total.objects.filter(cart__shop_info=shop, cart__is_verified=True)

    # 2. Date Variables Setup
    today = timezone.localdate()
    week_start = today - timedelta(days=7)

    # 3. Helper Function for Panels
    # This keeps our code DRY (Don't Repeat Yourself)
    def get_stats(qs):
        stats = qs.aggregate(
            money=Sum('shop_share'),
            orders=Count('id'),
            pages=Sum('cart__total_pages')
        )
        return {
            'money': stats['money'] or 0,
            'orders': stats['orders'] or 0,
            'pages': stats['pages'] or 0,
        }

    # --- PANEL 1: Specific Day (Defaults to Today) ---
    selected_day_str = request.GET.get('day')
    if selected_day_str:
        try:
            selected_day = datetime.strptime(selected_day_str, '%Y-%m-%d').date()
        except ValueError:
            selected_day = today
    else:
        selected_day = today

    day_stats = get_stats(base_qs.filter(cart__updated_at__date=selected_day))

    # --- PANEL 2: Past 7 Days (Week) ---
    week_stats = get_stats(base_qs.filter(cart__updated_at__date__gte=week_start))

    # --- PANEL 3: Current Month ---
    current_month_stats = get_stats(base_qs.filter(
        cart__updated_at__year=today.year,
        cart__updated_at__month=today.month
    ))

    # --- PANEL 4: Custom Month ---
    selected_month_str = request.GET.get('month') # Format expected: 'YYYY-MM'
    custom_month_stats = None
    if selected_month_str:
        try:
            year, month = map(int, selected_month_str.split('-'))
            custom_month_stats = get_stats(base_qs.filter(
                cart__updated_at__year=year,
                cart__updated_at__month=month
            ))
        except ValueError:
            pass # Failsafe if the URL is manipulated incorrectly

    # Dropdown Options: Find all unique months where the shop had sales
    available_months = base_qs.annotate(
        month=TruncMonth('cart__updated_at')
    ).values('month').annotate(
        order_count=Count('id')
    ).order_by('-month')

    # --- DAILY AGGREGATED LEDGER (For the Table) ---
    daily_ledger = base_qs.annotate(
        day=TruncDate('cart__updated_at')
    ).values('day').annotate(
        daily_earnings=Sum('shop_share'),
        daily_orders=Count('id'),
        daily_pages=Sum('cart__total_pages')
    ).order_by('-day')

    return render(request, 'printoapp/shop_finances.html', {
        'time': greeting,
        'username': request.user.username,
        'selected_day': selected_day.strftime('%Y-%m-%d'),
        'day_stats': day_stats,
        'week_stats': week_stats,
        'current_month_stats': current_month_stats,
        'selected_month': selected_month_str,
        'custom_month_stats': custom_month_stats,
        'available_months': available_months,
        'daily_ledger': daily_ledger,
    })


@login_required
def shop_catalogue(request):
    now_obj = timezone.localtime()
    hour = now_obj.hour
    greeting = "Morning" if 0 <= hour < 12 else "Noon" if hour == 12 else "Afternoon" if 12 < hour < 18 else "Evening"

    shop = Shop_info.objects.filter( shop_owner__user=request.user).first()
    items = Shop_items.objects.filter(shop_info=shop).order_by('page_type', 'is_color')
    timings = Shop_timing.objects.filter(shop__shop_owner__user=request.user).first()
    coupons = Shop_coupons.objects.filter(shop_info=shop)
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

        elif request_type == "Add_coupon":
            code = request.POST.get('code').strip().upper()
            discount_percent = request.POST.get('discount_percent')
            max_use = request.POST.get('max_use') or None
            days_valid = request.POST.get('days_valid') or None
            max_amount = request.POST.get('max_amount') or None
            min_cart_value = request.POST.get('min_cart_value') or None
            if not Shop_coupons.objects.filter(code=code,shop_info=shop).exists():
                Shop_coupons.objects.create(
                    code=code,
                    shop_info=shop,
                    max_use=max_use,
                    discount_percent=discount_percent,
                    max_amount=max_amount,
                    days_valid=days_valid,
                    min_cart_value=min_cart_value)

        elif request_type == "Delete_coupon":
            coupon_id = request.POST.get('coupon_id')
            coupon = Shop_coupons.objects.get(id=coupon_id)
            coupon.delete()

        elif request_type == "Update_catalogue":
            item_id = request.POST.get('item_id')
            edit = Shop_items.objects.get(id = item_id, shop_info = shop)
            edit.page_type = page_type
            edit.is_color = is_color
            edit.is_b2b = is_b2b
            edit.price = price
            edit.save()

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
        'coupons': coupons,
        'items' : items,
        'open_days': timings
    })

@login_required
def shop_account(request):
    now_obj = timezone.localtime()
    hour = now_obj.hour
    greeting = "Morning" if 0 <= hour < 12 else "Noon" if hour == 12 else "Afternoon" if 12 < hour < 18 else "Evening"
    owner = Shop_owner.objects.get(user=request.user)
    shop = Shop_info.objects.get(shop_owner__user = request.user)
    return render(request, 'printoapp/shop_account.html', {
        'time': greeting,
        'username': request.user.username,
        'shop':shop,
        'owner':owner
    })




# api routes

def create_user(request):
    new_user = Client.objects.create()
    new_user.save()
    return JsonResponse({'user_id': str(new_user.user_id)})

def check_user(request, uuid):
    if not Client.objects.filter(user_id=uuid).exists():
        return JsonResponse({'status':'Create new'})
    else:
        return JsonResponse({'status':'Exists'})

def item_list(request, shop_id):
    unique_keys = Shop_items.objects.filter(
        shop_info_id=shop_id
        ).values_list(
            'page_type', flat=True
            ).distinct().order_by('page_type')

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

    # 1. Grab today's date using timezone awareness
    today = timezone.localtime().date()

    fields = [
        'id', 'pickup_code', 'total_pages', 'total_amount',
        'is_verified', 'is_processing', 'is_printed', 'priority', 'updated_at'
    ]

    # 2. Add `updated_at__date=today` to both filters
    active_carts = Cart.objects.filter(
        shop_info=shop, 
        is_paid=True, 
        is_processing=True,
        updated_at__date=today  # <-- NEW: Filters for today only
    ).annotate(
        total_amount=F('cart_total__grand_total')
    ).order_by('-updated_at').values(*fields)

    other_carts = Cart.objects.filter(
        shop_info=shop, 
        is_paid=True, 
        is_processing=False,
        updated_at__date=today  # <-- NEW: Filters for today only
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
        active_priority_queue = Cart.objects.filter(
            shop_info__id=shop_id,
            priority=1,
            is_paid=True,
            is_verified=False,
            is_printed=False
        ).order_by('-is_processing', '-priority', 'created_at')

        active_queue = Cart.objects.filter(
            shop_info__id=shop_id,
            is_paid=True,
            is_verified=False,
            is_printed=False
        ).order_by('-is_processing', '-priority', 'created_at')
        if not user_id:
            return JsonResponse({'queue_size':active_queue.count(), 'priority_queue_size': active_priority_queue.count() })
        else:
            queue_list = list(active_queue.values_list('user__user_id', flat=True))
            try:
                target_uuid = uuid.UUID(user_id)
                user_position = queue_list.index(target_uuid)
                return JsonResponse({'queue_size': user_position})
            except ValueError:
                return JsonResponse({'queue_size': 0})


def create_preview_link(request, file_id):
    if request.method == 'POST':
        item = get_object_or_404(Cart_items, id=file_id)
        file_url = get_presigned_preview_url(item.file_id, 300)
        return JsonResponse({'file_url': file_url})

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

    final_pdf_buffer = BytesIO()
    writer.write(final_pdf_buffer)
    final_pdf_buffer.seek(0)
    return final_pdf_buffer