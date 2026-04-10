from django.db import models
from django.contrib.auth.models import User

from apps.operations.models import QueueEntry

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length = 25)
    contact_info = models.CharField(max_length=50, blank=True, null=True)
    preferences = models.JSONField(blank=True, null = True)

    def __str__(self):
        return self.full_name


class Notification(models.Model):
    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        VIEWED = "viewed", "Viewed"

    queue_entry = models.ForeignKey(
        QueueEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    recipient_name = models.CharField(max_length=150)
    service_name = models.CharField(max_length=100)
    notification_type = models.CharField(max_length=50)
    title = models.CharField(max_length=120)
    message = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SENT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    @property
    def is_read(self):
        return self.status == self.Status.VIEWED

    def __str__(self):
        return f"{self.title} -> {self.recipient_name}"
