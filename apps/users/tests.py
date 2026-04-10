from django.test import Client, TestCase
from django.utils import timezone
from django.contrib.auth.models import User, Group
from apps.users.models import UserProfile
from django.urls import reverse, resolve
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
        response = self.client.get('/users/notifications')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Queue joined successfully")


class UserModelTests(TestCase):
    def test_create_user_with_hashed_password(self):
        user = User.objects.create_user(
            username='Julien',
            email='jmg@gmail.com',
            password='password1'
        )
        self.assertEqual(user.username, 'Julien')
        self.assertEqual(user.email, 'jmg@gmail.com')
        self.assertNotEqual(user.password, 'password1')
        self.assertTrue(user.check_password('password1'))

    def test_user_profile_string_representation(self):
        user = User.objects.create_user(
            username='Julien',
            email='jmg@gmail.com',
            password='password1'
        )
        profile = UserProfile.objects.create(user=user, full_name='Julien Garcia')
        self.assertEqual(str(profile), 'Julien Garcia')

    def test_assign_user_role_with_group(self):
        user = User.objects.create_user(
            username='Julien',
            email='jg@gmail.com',
            password='password1'
        )
        customer_group = Group.objects.create(name='Customers')
        user.groups.add(customer_group)
        self.assertTrue(user.groups.filter(name='Customers').exists())
        self.assertFalse(user.groups.filter(name='Staff').exists())