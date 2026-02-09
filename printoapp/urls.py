from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("shops", views.shops, name="shops"),
    path("upload/<str:user_id>/<int:shop_id>", views.upload, name="upload"),
    path("cart/<int:shop_id>/<str:user_id>", views.cart, name="cart"),
    path("api/create_user", views.create_user, name="create_user"),
    path("api/item_list/<int:shop_id>", views.item_list, name="item_list"),
    path("my_shop/login", views.shop_login, name="shop_login"),
    path("my_shop/index", views.shop_index, name="shop_index"),
    path("my_shop/logout", views.shop_logout, name="shop_logout"),
    path("my_shop/finances", views.shop_finance, name="shop_finances"),
    path("my_shop/shop_connect/", views.shop_connect, name="shop_connect"),
    path("my_shop/file_update/", views.file_update, name="file_update")
]