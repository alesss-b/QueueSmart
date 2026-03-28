from django.test import Client, TestCase
from django.utils import timezone

from queuesmart.in_memory import NOTIFICATIONS, reset_state


class NotificationPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        reset_state()

    def test_notifications_page_renders_in_memory_notifications(self):
        NOTIFICATIONS.append(
            {
                "id": 1,
                "recipient_name": "Cordai",
                "service_name": "Academic Advising",
                "notification_type": "queue_joined",
                "title": "Queue joined successfully",
                "message": "You joined the Academic Advising queue at position #1.",
                "metadata": {"position": 1},
                "is_read": False,
                "created_at": timezone.now(),
            }
        )

        response = self.client.get("/users/notifications")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Queue joined successfully")
