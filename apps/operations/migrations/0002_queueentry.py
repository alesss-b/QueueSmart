import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="QueueEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_name", models.CharField(max_length=150)),
                ("position", models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("waiting", "Waiting"), ("served", "Served"), ("canceled", "Canceled")],
                        default="waiting",
                        max_length=10,
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "queue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to="operations.queue",
                    ),
                ),
            ],
            options={
                "ordering": ["queue__service__name", "position", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="queueentry",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "waiting")),
                fields=("queue", "user_name"),
                name="unique_waiting_entry_per_user_queue",
            ),
        ),
    ]
