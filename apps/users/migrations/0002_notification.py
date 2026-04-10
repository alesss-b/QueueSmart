import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0002_queueentry"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recipient_name", models.CharField(max_length=150)),
                ("service_name", models.CharField(max_length=100)),
                ("notification_type", models.CharField(max_length=50)),
                ("title", models.CharField(max_length=120)),
                ("message", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(choices=[("sent", "Sent"), ("viewed", "Viewed")], default="sent", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "queue_entry",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="notifications",
                        to="operations.queueentry",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at", "-id"],
            },
        ),
    ]
