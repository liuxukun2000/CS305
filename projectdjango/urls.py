"""projectdjango URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
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
from django.urls import path
from user.views import *

urlpatterns = [
    path('login/', login),
    path('register/', register),
    path('changename/', change_name),
    path('changepwd/', change_password),
    path('listen/', listen),
    path('changetoken/', change_token),
    path('createmeeting/', create_meeting),
    path('checkmeeting/', check_meeting),
    path('deletemeeting/', delete_meeting),
    path('changeowner/', change_owner)
]
