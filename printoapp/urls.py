from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('shops', views.shops, name='shops'),
    path('upload/<str:user_id>/<int:shop_id>', views.upload, name='upload'),
    path('cart/<int:shop_id>/<str:user_id>', views.cart, name='cart'),
    path('my_shop/login', views.shop_login, name='shop_login'),
    path('my_shop/index', views.shop_index, name='shop_index'),
    path('my_shop/logout', views.shop_logout, name='shop_logout'),
    path('my_shop/finances', views.shop_finance, name='shop_finances'),
    path('my_shop/shop_connect/', views.shop_connect, name='shop_connect'),
    path('my_shop/file_update/', views.file_update, name='file_update'),
    path('my_shop/shop_catalogue', views.shop_catalogue, name='shop_catalogue'),
    path('my_shop/account', views.shop_account, name='shop_account'),
    path('privacy_policy', views.privacy_policy, name='privacy_policy'),
    path('tnc', views.tnc, name='tnc'),
    path('payment-status/<int:shop_id>/<str:user_id>', views.payment_status, name='payment_status'),
    path('success/<int:shop_id>/<str:user_id>', views.success, name='success'),

    #apis
    path('initiate-payment/<int:shop_id>/<str:user_id>/', views.initiate_payment, name='initiate_payment'),
    path('api/create_user', views.create_user, name='create_user'),
    path('api/item_list/<int:shop_id>', views.item_list, name='item_list'),
    path('api/shop_list', views.shop_list, name='shop_list'),
    path('api/verify_cart', views.verify_cart, name='verify_cart'),
    path('api/cart_status/<int:cart_id>', views.cart_status, name='cart_status'),
    path('api/queue_size/<int:shop_id>', views.queue_size, name='queue_size'),
    path('api/queue_size/<int:shop_id>/<str:user_id>', views.queue_size, name='queue_size_user')
]