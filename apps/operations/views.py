import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View

from queuesmart.in_memory import NOTIFICATIONS, QUEUE_ENTRIES, QUEUE_HISTORY, next_id
from .models import Service, Queue


class OperationsView(TemplateView):
    """Operations default view; redirects to login if not authenticated."""
    template_name = 'pages/operations_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["services"] = Service.objects.all()
        return context


class ServiceFormView(View):
    """Create, update, and list services."""
    template_name = "pages/service_form.html"

    def get_service(self, request):
        service_id = request.GET.get("service_id") or request.POST.get("service_id")
        if not service_id:
            return None
        try:
            return Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return None

    def get_context(self, request, errors=None, form_data=None):
        editing_service = self.get_service(request)
        return {
            "editing_service": editing_service,
            "services": Service.objects.all(),
            "errors": errors or {},
            "form_data": form_data or (
                {
                    "name": editing_service.name,
                    "description": editing_service.description,
                    "expected_duration": editing_service.expected_duration,
                    "priority": editing_service.priority,
                } if editing_service else {}
            ),
        }

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context(request))

    def post(self, request, *args, **kwargs):
        editing_service = self.get_service(request)
        form_data = {
            "name": request.POST.get("name", "").strip(),
            "description": request.POST.get("description", "").strip(),
            "expected_duration": request.POST.get("expected_duration", "").strip(),
            "priority": request.POST.get("priority", "").strip(),
        }
        errors = {}

        if not form_data["name"]:
            errors["name"] = "Service name is required."
        if not form_data["description"]:
            errors["description"] = "Description is required."

        try:
            expected_duration = int(form_data["expected_duration"])
            if expected_duration <= 0:
                raise ValueError
        except (TypeError, ValueError):
            errors["expected_duration"] = "Expected duration must be a positive number."
            expected_duration = None

        try:
            priority = int(form_data["priority"])
        except (TypeError, ValueError):
            errors["priority"] = "Priority must be a number."
            priority = None

        duplicate = Service.objects.filter(name__iexact=form_data["name"])
        if editing_service:
            duplicate = duplicate.exclude(id=editing_service.id)
        if duplicate.exists():
            errors["name"] = "A service with that name already exists."

        if errors:
            return render(request, self.template_name, self.get_context(request, errors=errors, form_data=form_data))

        if editing_service:
            editing_service.name = form_data["name"]
            editing_service.description = form_data["description"]
            editing_service.expected_duration = expected_duration
            editing_service.priority = priority
            editing_service.save()
            service = editing_service
            messages.success(request, "Service updated successfully.")
        else:
            service = Service.objects.create(
                name=form_data["name"],
                description=form_data["description"],
                expected_duration=expected_duration,
                priority=priority,
            )
            messages.success(request, "Service created successfully.")

        return redirect(f"{request.path}?service_id={service.id}")

class ServiceDetailsView(TemplateView):
    """Service Details page view."""
    template_name = 'pages/service_details.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service_id = self.request.GET.get("service_id")

        selected_service = None
        if service_id:
            selected_service = Service.objects.filter(id=service_id).first()
        if selected_service is None:
            selected_service = Service.objects.first()

        open_entries = [
            entry for entry in QUEUE_ENTRIES
            if selected_service and entry["service_id"] == selected_service.id and entry["status"] == "waiting"
        ]
        history_entries = [
            entry for entry in QUEUE_HISTORY
            if selected_service and entry["service_id"] == selected_service.id
        ]

        context.update(
            {
                "services": Service.objects.all(),
                "selected_service": selected_service,
                "open_entries": open_entries,
                "history_entries": history_entries[:10],
            }
        )
        return context

class ServiceTicketFulfillmentFormView(TemplateView):
    """Service Ticket Fulfillment Form view."""
    template_name = 'pages/service_ticket_fulfillment_form.html'


def _serialize_queue_entry(entry):
    return {
        "id": entry["id"],
        "user": entry["user"],
        "service": entry["service_name"],
        "position": entry["position"],
        "status": entry["status"],
        "joined_at": entry["joined_at"].isoformat(),
    }


def _resolve_service(service_value):
    if service_value is None:
        return None

    try:
        # Try by ID
        return Service.objects.get(id=service_value)
    except:
        try:
            # Try by name
            return Service.objects.get(name__iexact=service_value)
        except:
            return None


def _renumber_waiting_entries(service):
    waiting_entries = [
        entry for entry in QUEUE_ENTRIES
        if entry["service_id"] == service.id and entry["status"] == "waiting"
    ]
    waiting_entries.sort(key=lambda entry: (entry["joined_at"], entry["id"]))
    for index, entry in enumerate(waiting_entries, start=1):
        entry["position"] = index


def _create_notification(entry, notification_type, title, message, metadata=None):
    NOTIFICATIONS.insert(
        0,
        {
            "id": next_id("notification"),
            "recipient_name": entry["user"],
            "service_name": entry["service_name"],
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "metadata": metadata or {},
            "is_read": False,
            "created_at": timezone.now(),
        },
    )


def _notify_close_to_served(service):
    close_entries = [
        entry for entry in QUEUE_ENTRIES
        if entry["service_id"] == service.id and entry["status"] == "waiting" and entry["position"] <= 2
    ]
    close_entries.sort(key=lambda entry: entry["position"])
    for entry in close_entries:
        already_notified = any(
            notification["recipient_name"] == entry["user"]
            and notification["service_name"] == entry["service_name"]
            and notification["notification_type"] == "close_to_served"
            and notification["metadata"].get("position") == entry["position"]
            and not notification["is_read"]
            for notification in NOTIFICATIONS
        )
        if already_notified:
            continue

        _create_notification(
            entry,
            "close_to_served",
            "You are close to being served",
            f"You are now #{entry['position']} in the {entry['service_name']} queue. Please be ready.",
            metadata={"position": entry["position"]},
        )


@csrf_exempt
def join_queue(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            user_name = data.get("user")
            service = _resolve_service(data.get("service"))

            if not user_name or not service:
                return JsonResponse({"error": "Missing required fields"}, status=400)

            position = sum(
                1 for entry in QUEUE_ENTRIES
                if entry["service_id"] == service.id and entry["status"] == "waiting"
            ) + 1
            entry = {
                "id": next_id("queue"),
                "user": user_name,
                "service_id": service.id,
                "service_name": service.name,
                "position": position,
                "status": "waiting",
                "joined_at": timezone.now(),
            }
            QUEUE_ENTRIES.append(entry)
            
            Queue.objects.create(
                service=service,
                status="open"
            )

            _create_notification(
                entry,
                "queue_joined",
                "Queue joined successfully",
                f"You joined the {service.name} queue at position #{entry['position']}.",
                metadata={"position": entry["position"]},
            )
            _notify_close_to_served(service)

            return JsonResponse({
                "message": "Joined queue successfully",
                "data": _serialize_queue_entry(entry)
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def leave_queue(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_name = data.get("user")
            service = _resolve_service(data.get("service")) if data.get("service") else None

            if not user_name:
                return JsonResponse({"error": "Missing required field: user"}, status=400)

            entry = next(
                (
                    queue_entry for queue_entry in QUEUE_ENTRIES
                    if queue_entry["user"] == user_name
                    and queue_entry["status"] == "waiting"
                    and (service is None or queue_entry["service_id"] == service.id)
                ),
                None,
            )
            if not entry:
                return JsonResponse({"error": "User not found in queue"}, status=404)

            QUEUE_ENTRIES.remove(entry)
            entry["status"] = "left"
            QUEUE_HISTORY.insert(0, entry)
            service_for_entry = _resolve_service(entry["service_id"])
            _renumber_waiting_entries(service_for_entry)
            _notify_close_to_served(service_for_entry)

            return JsonResponse({
                "message": "Left queue successfully",
                "user": user_name
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)


def view_queue(request):
    if request.method == "GET":
        service = _resolve_service(request.GET.get("service")) if request.GET.get("service") else None
        queue_entries = [entry for entry in QUEUE_ENTRIES if entry["status"] == "waiting"]
        if service:
            queue_entries = [entry for entry in queue_entries if entry["service_id"] == service.id]
        return JsonResponse({
            "queue": [_serialize_queue_entry(entry) for entry in queue_entries],
            "total_users": len(queue_entries)
        }, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def serve_next(request):
    if request.method == "POST":
        service_value = None
        if request.body:
            try:
                data = json.loads(request.body)
                service_value = data.get("service")
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON"}, status=400)

        service = _resolve_service(service_value) if service_value else None
        waiting_entries = [entry for entry in QUEUE_ENTRIES if entry["status"] == "waiting"]
        if service:
            waiting_entries = [entry for entry in waiting_entries if entry["service_id"] == service.id]
        waiting_entries.sort(key=lambda entry: (entry["service_id"], entry["position"], entry["id"]))
        next_user = waiting_entries[0] if waiting_entries else None

        if not next_user:
            return JsonResponse({"error": "Queue is empty"}, status=400)

        QUEUE_ENTRIES.remove(next_user)
        next_user["status"] = "served"
        QUEUE_HISTORY.insert(0, next_user)
        service_for_entry = _resolve_service(next_user["service_id"])
        _renumber_waiting_entries(service_for_entry)
        _notify_close_to_served(service_for_entry)
        remaining_queue = [
            entry for entry in QUEUE_ENTRIES
            if entry["service_id"] == next_user["service_id"] and entry["status"] == "waiting"
        ]

        return JsonResponse({
            "message": "Served next user successfully",
            "served_user": _serialize_queue_entry(next_user),
            "remaining_queue": [_serialize_queue_entry(entry) for entry in remaining_queue]
        }, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)


def estimate_wait_time(request):
    if request.method == "GET":
        user_name = request.GET.get("user")
        service = _resolve_service(request.GET.get("service")) if request.GET.get("service") else None

        if not user_name:
            return JsonResponse({"error": "Missing required field: user"}, status=400)

        entry = next(
            (
                queue_entry for queue_entry in QUEUE_ENTRIES
                if queue_entry["user"] == user_name
                and queue_entry["status"] == "waiting"
                and (service is None or queue_entry["service_id"] == service.id)
            ),
            None,
        )
        if not entry:
            return JsonResponse({"error": "User not found in queue"}, status=404)

        service_for_entry = _resolve_service(entry["service_id"])
        estimated_wait = (entry["position"] - 1) * service_for_entry.expected_duration
        
        return JsonResponse({
            "user": user_name,
            "position": entry["position"],
            "service": service_for_entry.name,
            "estimated_wait_time": estimated_wait,
            "unit": "minutes"
        }, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)

# last updated: 2026-04-10 2:09 PM