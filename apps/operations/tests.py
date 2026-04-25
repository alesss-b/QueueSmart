import json

from django.test import Client, TestCase
from django.contrib.auth.models import Group, User
from apps.operations.models import Queue, QueueEntry, Service
from apps.users.models import Notification


class QueueManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
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
        self.assertEqual(QueueEntry.objects.count(), 1)
        notifications = list(Notification.objects.order_by("-created_at", "-id"))
        self.assertEqual(notifications[0].notification_type, "close_to_served")
        self.assertEqual(notifications[1].notification_type, "queue_joined")

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
        self.assertEqual(QueueEntry.objects.filter(status=QueueEntry.Status.WAITING).count(), 0)
        self.assertEqual(QueueEntry.objects.get(user_name="Cordai").status, QueueEntry.Status.CANCELED)

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
            Notification.objects.filter(
                recipient_name="Amara",
                notification_type="close_to_served",
                metadata__position=1,
            ).exists()
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
        service = Service.objects.get(name="Registrar")
        self.assertTrue(Queue.objects.filter(service=service, status="open").exists())

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
class ReportingTests(TestCase):
    def setUp(self):
        self.client = Client()

        self.staff_group = Group.objects.create(name="Staff")
        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="testpass123",
        )
        self.staff_user.groups.add(self.staff_group)

        self.customer_user = User.objects.create_user(
            username="customeruser",
            password="testpass123",
        )

        self.service = Service.objects.create(
            name="Academic Advising",
            description="Help with course planning.",
            expected_duration=15,
            priority=1,
        )
        self.queue = Queue.objects.create(
            service=self.service,
            status="open",
        )
        self.entry = QueueEntry.objects.create(
            queue=self.queue,
            user_name="Cordai",
            position=1,
            status=QueueEntry.Status.WAITING,
        )

    def test_staff_can_view_reports_page(self):
        self.client.login(username="staffuser", password="testpass123")

        response = self.client.get("/operations/reports")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Queue Reports")
        self.assertContains(response, "Cordai")
        self.assertContains(response, "Academic Advising")

    def test_customer_cannot_view_reports_page(self):
        self.client.login(username="customeruser", password="testpass123")

        response = self.client.get("/operations/reports")

        self.assertEqual(response.status_code, 302)

    def test_staff_can_export_queue_report_csv(self):
        self.client.login(username="staffuser", password="testpass123")

        response = self.client.get("/operations/reports/export-csv")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("queue_activity_report.csv", response["Content-Disposition"])

        csv_content = response.content.decode()
        self.assertIn("User,Service,Queue Status,Position", csv_content)
        self.assertIn("Cordai", csv_content)
        self.assertIn("Academic Advising", csv_content)

    def test_csv_report_can_filter_by_service(self):
        self.client.login(username="staffuser", password="testpass123")

        other_service = Service.objects.create(
            name="IT Help Desk",
            description="Technical support.",
            expected_duration=20,
            priority=2,
        )
        other_queue = Queue.objects.create(
            service=other_service,
            status="open",
        )
        QueueEntry.objects.create(
            queue=other_queue,
            user_name="Amara",
            position=1,
            status=QueueEntry.Status.WAITING,
        )

        response = self.client.get(f"/operations/reports/export-csv?service_id={self.service.id}")

        csv_content = response.content.decode()
        self.assertIn("Cordai", csv_content)
        self.assertIn("Academic Advising", csv_content)
        self.assertNotIn("Amara", csv_content)
        self.assertNotIn("IT Help Desk", csv_content)