from django.test import TestCase, Client
import json

from .views import queue


class QueueManagementTests(TestCase):
    def setUp(self):
        self.client = Client()
        queue.clear()

    def test_join_queue_success(self):
        response = self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "Advising"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Joined queue successfully", response.json()["message"])
        self.assertEqual(response.json()["data"]["position"], 1)

    def test_join_queue_missing_fields(self):
        response = self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_leave_queue_success(self):
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "Advising"}),
            content_type="application/json"
        )

        response = self.client.post(
            "/operations/queue/leave",
            data=json.dumps({"user": "Cordai"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"], "Cordai")

    def test_leave_queue_user_not_found(self):
        response = self.client.post(
            "/operations/queue/leave",
            data=json.dumps({"user": "Nobody"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 404)

    def test_view_queue(self):
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "Advising"}),
            content_type="application/json"
        )
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Amara", "service": "Registration"}),
            content_type="application/json"
        )

        response = self.client.get("/operations/queue/view")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total_users"], 2)

    def test_serve_next_success(self):
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "Advising"}),
            content_type="application/json"
        )
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Amara", "service": "Registration"}),
            content_type="application/json"
        )

        response = self.client.post("/operations/queue/serve-next")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["served_user"]["user"], "Cordai")
        self.assertEqual(len(response.json()["remaining_queue"]), 1)

    def test_serve_next_empty_queue(self):
        response = self.client.post("/operations/queue/serve-next")
        self.assertEqual(response.status_code, 400)

    def test_estimate_wait_time_success(self):
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Cordai", "service": "Advising"}),
            content_type="application/json"
        )
        self.client.post(
            "/operations/queue/join",
            data=json.dumps({"user": "Amara", "service": "Registration"}),
            content_type="application/json"
        )

        response = self.client.get("/operations/queue/wait-time?user=Amara")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["position"], 2)
        self.assertEqual(response.json()["estimated_wait_time"], 10)

    def test_estimate_wait_time_user_not_found(self):
        response = self.client.get("/operations/queue/wait-time?user=Nobody")
        self.assertEqual(response.status_code, 404)
