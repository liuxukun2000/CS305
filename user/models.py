from django.db import models


class User(models.Model):
    id = models.AutoField(primary_key=True, help_text='用户主键')
    username = models.CharField(max_length=32, unique=True, null=False, blank=False, db_index=True, help_text='用户名')
    password = models.CharField(max_length=256, null=False, blank=False, db_index=True, help_text='密码')
    token = models.CharField(max_length=16, null=False, blank=False, help_text='token')
    # control = 1
