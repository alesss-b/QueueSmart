from django.contrib import admin

from .models import Notification, UserProfile


admin.site.register(UserProfile)
admin.site.register(Notification)
