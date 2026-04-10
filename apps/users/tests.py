from django.contrib.auth.models import Group, User
from django.test import Client, TestCase

from apps.operations.models import QueueEntry, Queue, Service
from apps.users.models import Notification, UserProfile


class NotificationPageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.service = Service.objects.create(
            name="Academic Advising",
            description="Help with course planning.",
            expected_duration=15,
            priority=1,
        )
        self.queue = Queue.objects.create(service=self.service, status="open")
        self.entry = QueueEntry.objects.create(queue=self.queue, user_name="Cordai", position=1)

    def test_notifications_page_renders_database_notifications(self):
        Notification.objects.create(
            queue_entry=self.entry,
            recipient_name="Cordai",
            service_name="Academic Advising",
            notification_type="queue_joined",
            title="Queue joined successfully",
            message="You joined the Academic Advising queue at position #1.",
            metadata={"position": 1},
        )
        response = self.client.get("/users/notifications")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Queue joined successfully")

    def test_history_page_renders_completed_queue_entries(self):
        self.entry.status = QueueEntry.Status.SERVED
        self.entry.save(update_fields=["status", "updated_at"])
        response = self.client.get("/users/history")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Academic Advising")
        self.assertContains(response, "Served")


class UserModelTests(TestCase):
    def test_create_user_with_hashed_password(self):
        user = User.objects.create_user(
            username="Julien",
            email="jmg@gmail.com",
            password="password1",
        )
        self.assertEqual(user.username, "Julien")
        self.assertEqual(user.email, "jmg@gmail.com")
        self.assertNotEqual(user.password, "password1")
        self.assertTrue(user.check_password("password1"))

    def test_user_profile_string_representation(self):
        user = User.objects.create_user(
            username="Julien",
            email="jmg@gmail.com",
            password="password1",
        )
        profile = UserProfile.objects.create(user=user, full_name="Julien Garcia")
        self.assertEqual(str(profile), "Julien Garcia")

    def test_assign_user_role_with_group(self):
        user = User.objects.create_user(
            username="Julien",
            email="jg@gmail.com",
            password="password1",
        )
        customer_group = Group.objects.create(name="Customers")
        user.groups.add(customer_group)
        self.assertTrue(user.groups.filter(name="Customers").exists())
        self.assertFalse(user.groups.filter(name="Staff").exists())
