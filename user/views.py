from django.http.request import *
from django.http.response import *
from user.models import User, Meeting
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


def register(request: HttpRequest) -> JsonResponse:
    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    if not all((username, password)):
        return JsonResponse(dict(status=400))
    if User.objects.filter(username=username).exists():
        return JsonResponse(dict(status=401))
    else:
        token = str(time.time_ns())[-9:]
        User.objects.create(username=username, password=password, token=token)
        request.session['is_login'] = True
        request.session['username'] = username
        return JsonResponse(dict(status=200, token=token))


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


def change_token(request: HttpRequest):
    if request.session.get('is_login'):
        token = str(time.time_ns())[-9:]
        User.objects.filter(username=request.session['username']).update(token=token)
        return JsonResponse(dict(status=200, token=token))
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


def create_meeting(request: HttpRequest):
    if request.session.get('is_login'):
        _id = request.POST.get('token', '')
        password = request.POST.get('password', '')
        if _id:
            if not Meeting.objects.filter(meeting_id=_id).exists():
                user = User.objects.filter(username=request.session['username'])
                Meeting.objects.create(meeting_id=_id, password=password, create_user=user[0])
                return JsonResponse(dict(status=200))
    return JsonResponse(dict(status=403))


def check_meeting(request: HttpRequest):
    if request.session.get('is_login'):
        _id = request.POST.get('token', '')
        password = request.POST.get('password', '')
        if _id:
            meeting = Meeting.objects.filter(meeting_id=_id, password=password)
            if meeting:
                owner = meeting[0].create_user.username == request.session['username']
                return JsonResponse(dict(status=200, is_owner=owner))
    return JsonResponse(dict(status=403))


def delete_meeting(request: HttpRequest):
    if request.session.get('is_login'):
        _id = request.POST.get('token', '')
        if _id:
            user = User.objects.get(username=request.session['username'])
            Meeting.objects.filter(meeting_id=_id, create_user=user).delete()
            return JsonResponse(dict(status=200))
    return JsonResponse(dict(status=403))


def change_owner(request: HttpRequest):
    if request.session.get('is_login'):
        _id = request.POST.get('token', '')
        newname = request.POST.get('username', '')
        if _id and newname:
            user = User.objects.get(username=request.session['username'])
            newuser = User.objects.get(username=newname)
            Meeting.objects.filter(meeting_id=_id, create_user=user).update(create_user=newuser)
            return JsonResponse(dict(status=200))
    return JsonResponse(dict(status=403))
