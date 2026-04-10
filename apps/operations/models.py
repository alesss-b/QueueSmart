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

# last updated: 2026-04-10 1:58 PM