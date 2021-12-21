from django.http.request import *
from django.http.response import *
from user.models import User
import time
from typing import Dict
import redis

connection = redis.StrictRedis(host='127.0.0.1', port=6379, db=3)


def login(request: HttpRequest) -> JsonResponse:
    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    if not all((username, password)):
        return JsonResponse(dict(status=400))
    users = User.objects.filter(username=username, password=password)
    if users:
        request.session['is_login'] = True
        request.session['username'] = username
        return JsonResponse(dict(status=200, token=users[0].token))
    return JsonResponse(dict(status=404))

def change_name(request: HttpRequest):
    if request.session.get('is_login'):
        username = request.session['username']
        newname = request.POST.get('newname', '')
        if not all((username, newname)):
            return JsonResponse(dict(status=400))
        if User.objects.filter(username=newname).exists():
            return JsonResponse(dict(status=401))
        User.objects.filter(username=username).update(username=newname)
        return JsonResponse(dict(status=200))
    return JsonResponse(dict(status=403))

def change_password(request: HttpRequest):
    if request.session.get('is_login'):
        password = request.POST.get('password', '')
        if not all((password,)):
            return JsonResponse(dict(status=400))
        User.objects.filter(username=request.session['username']).update(password=password)
        return JsonResponse(dict(status=200))
    return JsonResponse(dict(status=403))

def listen(request: HttpRequest):
    if request.session.get('is_login'):
        if request.session.get('using'):
            return JsonResponse(dict(status=403))
        _ = str(time.time_ns())
        connection.sadd('REMOTE', _)
        return JsonResponse(dict(status=200, id=_))
    return JsonResponse(dict(status=403))


def control(request: HttpRequest):
    ID = request.session.get('id', None)
    if not ID:
        return JsonResponse(dict(status=400))
    if request.session.get('is_login'):
        if request.session.get('using'):
            return JsonResponse(dict(status=403))
        if connection.sismember('REMOTE', ID):
            connection.srem('REMOTE', ID)
        return JsonResponse(dict(status=200))
    return JsonResponse(dict(status=403))


