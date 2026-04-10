from django.core.validators import MinValueValidator
from django.db import models


# ========================
# SERVICE MODEL
# ========================
class Service(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    expected_duration = models.IntegerField()
    priority = models.IntegerField(default=1)

    def __str__(self):
        return self.name


# ========================
# QUEUE MODEL
# ========================
class Queue(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default="open")  # open / closed
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Queue for {self.service.name}"


class QueueEntry(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Waiting"
        SERVED = "served", "Served"
        CANCELED = "canceled", "Canceled"

    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, related_name="entries")
    user_name = models.CharField(max_length=150)
    position = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.WAITING)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["queue__service__name", "position", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["queue", "user_name"],
                condition=models.Q(status="waiting"),
                name="unique_waiting_entry_per_user_queue",
            ),
        ]

    def __str__(self):
        return f"{self.user_name} - {self.queue.service.name}"
