from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length = 25)
    contact_info = models.CharField(max_length=50, blank=True, null=True)
    preferences = models.JSONField(blank=True, null = True)

    def __str__(self):
        return self.full_name

