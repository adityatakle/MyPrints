"""
URL configuration for printo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
import os
from django.contrib.staticfiles import finders
from django.http import HttpResponse, Http404
from django.views.static import serve
def service_worker(request):
    # Finds sw.js anywhere in your Django static locations
    sw_path = finders.find('printoapp/sw.js')
    if sw_path:
        with open(sw_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='application/javascript')
    raise Http404("sw.js not found")
urlpatterns = [
    path('admin/', admin.site.urls),
    path('sw.js', service_worker, name='service_worker'),
    path("", include("printoapp.urls"))
]
handler404 = 'printoapp.views.custom_404_view'