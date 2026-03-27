from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt

# Example login required view:
# class OperationsView(LoginRequiredMixin, TemplateView):
#     """Operations default view; redirects to login if not authenticated."""
#     login_url = 'login'
#     template_name = 'pages/operations_dashboard.html'


class OperationsView(TemplateView):
    """Operations default view; redirects to login if not authenticated."""
    template_name = 'pages/operations_dashboard.html'

class ServiceFormView(TemplateView):
    """Service Form page view."""
    template_name = 'pages/service_form.html'

class ServiceDetailsView(TemplateView):
    """Service Details page view."""
    template_name = 'pages/service_details.html'

class ServiceTicketFulfillmentFormView(TemplateView):
    """Service Ticket Fulfillment Form view."""
    template_name = 'pages/service_ticket_fulfillment_form.html'

from django.http import JsonResponse
import json

# temporary in-memory queue
queue = []


@csrf_exempt
def join_queue(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            user = data.get("user")
            service = data.get("service")
            duration = data.get("duration", 10) #

            # validation
            if not user or not service:
                return JsonResponse({"error": "Missing required fields"}, status=400)

            entry = {
                "user": user,
                "service": service,
                "position": len(queue) + 1
            }

            queue.append(entry)

            return JsonResponse({
                "message": "Joined queue successfully",
                "data": entry
            }, status=200)

        except:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def leave_queue(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user = data.get("user")

            if not user:
                return JsonResponse({"error": "Missing required field: user"}, status=400)

            global queue

            for entry in queue:
                if entry["user"] == user:
                    queue.remove(entry)

                    # reassign positions
                    for index, item in enumerate(queue):
                        item["position"] = index + 1

                    return JsonResponse({
                        "message": "Left queue successfully",
                        "user": user
                    }, status=200)

            return JsonResponse({"error": "User not found in queue"}, status=404)

        except:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

def view_queue(request):
    if request.method == "GET":
        return JsonResponse({
            "queue": queue,
            "total_users": len(queue)
        }, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def serve_next(request):
    if request.method == "POST":
        global queue

        if not queue:
            return JsonResponse({"error": "Queue is empty"}, status=400)

        next_user = queue.pop(0)

        # reassign positions after serving
        for index, item in enumerate(queue):
            item["position"] = index + 1

        return JsonResponse({
            "message": "Served next user successfully",
            "served_user": next_user,
            "remaining_queue": queue
        }, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


def estimate_wait_time(request):
    if request.method == "GET":
        user = request.GET.get("user")

        if not user:
            return JsonResponse({"error": "Missing required field: user"}, status=400)

        for entry in queue:
            if entry["user"] == user:
                position = entry["position"]
                estimated_wait = (position - 1) * 10

                return JsonResponse({
                    "user": user,
                    "position": position,
                    "estimated_wait_time": estimated_wait,
                    "unit": "minutes"
                }, status=200)

        return JsonResponse({"error": "User not found in queue"}, status=404)

    return JsonResponse({"error": "Invalid request"}, status=400) 