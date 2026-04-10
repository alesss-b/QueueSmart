import json

from django.test import Client, TestCase

from apps.operations.models import Service
from queuesmart.in_memory import NOTIFICATIONS, QUEUE_ENTRIES, QUEUE_HISTORY


class QueueManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

        # clear in-memory state still used by queue/notifications/history
        QUEUE_ENTRIES.clear()
        QUEUE_HISTORY.clear()
        NOTIFICATIONS.clear()

        # create real database-backed services
        self.advising = Service.objects.create(
            name="Academic Advising",
            description="Help with course planning.",
            expected_duration=15,
            priority=1,
        )
        self.it_help = Service.objects.create(
            name="IT Help Desk",
            description="Technical support.",
            expected_duration=20,
            priority=2,
        )

    def test_join_queue_success(self):
        response = self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "Academic Advising"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["position"], 1)
        self.assertEqual(len(QUEUE_ENTRIES), 1)
        self.assertEqual(NOTIFICATIONS[0]["notification_type"], "close_to_served")
        self.assertEqual(NOTIFICATIONS[1]["notification_type"], "queue_joined")

    def test_join_queue_missing_fields(self):
        response = self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_leave_queue_success(self):
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "Academic Advising"}),
            content_type="application/json",
        )

        response = self.client.post(
            "/operations/queue/leave",
            data=json.dumps({"user": "Cordai", "service": "Academic Advising"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(QUEUE_ENTRIES), 0)
        self.assertEqual(QUEUE_HISTORY[0]["status"], "left")

    def test_view_queue_filters_by_service(self):
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "Academic Advising"}),
            content_type="application/json",
        )
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Amara", "service": "IT Help Desk"}),
            content_type="application/json",
        )

        response = self.client.get("/operations/queue/view?service=Academic%20Advising")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_users"], 1)
        self.assertEqual(response.json()["queue"][0]["service"], "Academic Advising")

    def test_serve_next_triggers_close_notification_for_next_person(self):
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "Academic Advising"}),
            content_type="application/json",
        )
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Amara", "service": "Academic Advising"}),
            content_type="application/json",
        )
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Luis", "service": "Academic Advising"}),
            content_type="application/json",
        )

        response = self.client.post(
            "/operations/queue/serve-next",
            data=json.dumps({"service": "Academic Advising"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["served_user"]["user"], "Cordai")
        self.assertEqual(response.json()["remaining_queue"][0]["position"], 1)
        self.assertTrue(
            any(
                notification["recipient_name"] == "Amara"
                and notification["notification_type"] == "close_to_served"
                and notification["metadata"]["position"] == 1
                for notification in NOTIFICATIONS
            )
        )

    def test_estimate_wait_time_uses_service_duration(self):
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "IT Help Desk"}),
            content_type="application/json",
        )
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Amara", "service": "IT Help Desk"}),
            content_type="application/json",
        )

        response = self.client.get("/operations/queue/wait-time?user=Amara&service=IT%20Help%20Desk")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["estimated_wait_time"], 20)


class ServiceManagementTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_create_service(self):
        response = self.client.post(
            "/operations/service/create",
            data={
                "name": "Registrar",
                "description": "Transcript requests and enrollment verification.",
                "expected_duration": 12,
                "priority": 2,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Service.objects.filter(name="Registrar").exists())

    def test_update_service(self):
        existing_service = Service.objects.create(
            name="Financial Aid",
            description="Original description",
            expected_duration=10,
            priority=1,
        )

        response = self.client.post(
            "/operations/service/edit",
            data={
                "service_id": existing_service.id,
                "name": existing_service.name,
                "description": "Updated description",
                "expected_duration": 18,
                "priority": 3,
            },
        )

        self.assertEqual(response.status_code, 302)

        existing_service.refresh_from_db()
        self.assertEqual(existing_service.description, "Updated description")
        self.assertEqual(existing_service.expected_duration, 18)
        self.assertEqual(existing_service.priority, 3)
        
# last updated: 2026-04-10 1:59 PM