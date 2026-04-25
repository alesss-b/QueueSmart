import json
import csv
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View

from apps.users.models import Notification

from .models import Queue, QueueEntry, Service


class OperationsView(TemplateView):
    """Operations default view; redirects to login if not authenticated."""
    template_name = "pages/operations_dashboard.html"

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
        return Service.objects.filter(id=service_id).first()

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
                }
                if editing_service
                else {}
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
            Queue.objects.create(service=service, status="open")
            messages.success(request, "Service created successfully.")

        return redirect(f"{request.path}?service_id={service.id}")


class ServiceDetailsView(TemplateView):
    """Service Details page view."""
    template_name = "pages/service_details.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service_id = self.request.GET.get("service_id")
        selected_service = None

        if service_id:
            selected_service = Service.objects.filter(id=service_id).first()
        if selected_service is None:
            selected_service = Service.objects.first()

        open_entries = (
            QueueEntry.objects.filter(queue__service=selected_service, status=QueueEntry.Status.WAITING)
            if selected_service
            else QueueEntry.objects.none()
        )
        history_entries = (
            QueueEntry.objects.exclude(status=QueueEntry.Status.WAITING).filter(queue__service=selected_service)
            if selected_service
            else QueueEntry.objects.none()
        )

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
    template_name = "pages/service_ticket_fulfillment_form.html"


def _serialize_queue_entry(entry):
    return {
        "id": entry.id,
        "user": entry.user_name,
        "service": entry.queue.service.name,
        "position": entry.position,
        "status": entry.status,
        "joined_at": entry.joined_at.isoformat(),
    }


def _resolve_service(service_value):
    if service_value is None:
        return None
    normalized = str(service_value).strip()
    return Service.objects.filter(name__iexact=normalized).first() or Service.objects.filter(id=normalized).first()


def _get_active_queue(service):
    queue = Queue.objects.filter(service=service, status="open").order_by("-created_at", "-id").first()
    if queue:
        return queue
    return Queue.objects.create(service=service, status="open")


def _renumber_waiting_entries(queue):
    waiting_entries = list(
        QueueEntry.objects.filter(queue=queue, status=QueueEntry.Status.WAITING).order_by("joined_at", "id")
    )
    for index, entry in enumerate(waiting_entries, start=1):
        if entry.position != index:
            entry.position = index
            entry.save(update_fields=["position", "updated_at"])


def _create_notification(entry, notification_type, title, message, metadata=None):
    Notification.objects.create(
        queue_entry=entry,
        recipient_name=entry.user_name,
        service_name=entry.queue.service.name,
        notification_type=notification_type,
        title=title,
        message=message,
        metadata=metadata or {},
    )


def _notify_close_to_served(queue):
    close_entries = QueueEntry.objects.filter(
        queue=queue,
        status=QueueEntry.Status.WAITING,
        position__lte=2,
    ).order_by("position", "id")
    for entry in close_entries:
        already_notified = Notification.objects.filter(
            recipient_name=entry.user_name,
            service_name=entry.queue.service.name,
            notification_type="close_to_served",
            status=Notification.Status.SENT,
            metadata__position=entry.position,
        ).exists()
        if already_notified:
            continue

        _create_notification(
            entry,
            "close_to_served",
            "You are close to being served",
            f"You are now #{entry.position} in the {entry.queue.service.name} queue. Please be ready.",
            metadata={"position": entry.position},
        )

def _user_can_access_reports(user):
    if not user.is_authenticated:
        return False
    return user.is_staff or user.groups.filter(name="Staff").exists()

@csrf_exempt
def join_queue(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_name = data.get("user")
    service = _resolve_service(data.get("service"))
    if not user_name or not service:
        return JsonResponse({"error": "Missing required fields"}, status=400)

    queue = _get_active_queue(service)
    if QueueEntry.objects.filter(queue=queue, user_name=user_name, status=QueueEntry.Status.WAITING).exists():
        return JsonResponse({"error": "User is already in this queue"}, status=400)

    position = QueueEntry.objects.filter(queue=queue, status=QueueEntry.Status.WAITING).count() + 1
    entry = QueueEntry.objects.create(queue=queue, user_name=user_name, position=position)

    _create_notification(
        entry,
        "queue_joined",
        "Queue joined successfully",
        f"You joined the {service.name} queue at position #{entry.position}.",
        metadata={"position": entry.position},
    )
    _notify_close_to_served(queue)

    return JsonResponse({"message": "Joined queue successfully", "data": _serialize_queue_entry(entry)}, status=200)


@csrf_exempt
def leave_queue(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    user_name = data.get("user")
    service = _resolve_service(data.get("service")) if data.get("service") else None
    if not user_name:
        return JsonResponse({"error": "Missing required field: user"}, status=400)

    entries = QueueEntry.objects.filter(user_name=user_name, status=QueueEntry.Status.WAITING)
    if service:
        entries = entries.filter(queue__service=service)
    entry = entries.order_by("joined_at", "id").first()
    if not entry:
        return JsonResponse({"error": "User not found in queue"}, status=404)

    entry.status = QueueEntry.Status.CANCELED
    entry.save(update_fields=["status", "updated_at"])
    _renumber_waiting_entries(entry.queue)
    _notify_close_to_served(entry.queue)

    return JsonResponse({"message": "Left queue successfully", "user": user_name}, status=200)


def view_queue(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request"}, status=400)

    service = _resolve_service(request.GET.get("service")) if request.GET.get("service") else None
    queue_entries = QueueEntry.objects.filter(status=QueueEntry.Status.WAITING).select_related("queue__service")
    if service:
        queue_entries = queue_entries.filter(queue__service=service)
    return JsonResponse(
        {"queue": [_serialize_queue_entry(entry) for entry in queue_entries], "total_users": queue_entries.count()},
        status=200,
    )


@csrf_exempt
def serve_next(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    service_value = None
    if request.body:
        try:
            data = json.loads(request.body)
            service_value = data.get("service")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

    service = _resolve_service(service_value) if service_value else None
    waiting_entries = QueueEntry.objects.filter(status=QueueEntry.Status.WAITING).select_related("queue__service")
    if service:
        waiting_entries = waiting_entries.filter(queue__service=service)
    next_user = waiting_entries.order_by("queue__service__name", "position", "id").first()
    if not next_user:
        return JsonResponse({"error": "Queue is empty"}, status=400)

    next_user.status = QueueEntry.Status.SERVED
    next_user.save(update_fields=["status", "updated_at"])
    _renumber_waiting_entries(next_user.queue)
    _notify_close_to_served(next_user.queue)
    remaining_queue = QueueEntry.objects.filter(
        queue=next_user.queue,
        status=QueueEntry.Status.WAITING,
    ).select_related("queue__service")

    return JsonResponse(
        {
            "message": "Served next user successfully",
            "served_user": _serialize_queue_entry(next_user),
            "remaining_queue": [_serialize_queue_entry(entry) for entry in remaining_queue],
        },
        status=200,
    )


def estimate_wait_time(request):
    if request.method != "GET":
        return JsonResponse({"error": "Invalid request"}, status=400)

    user_name = request.GET.get("user")
    service = _resolve_service(request.GET.get("service")) if request.GET.get("service") else None
    if not user_name:
        return JsonResponse({"error": "Missing required field: user"}, status=400)

    entries = QueueEntry.objects.filter(user_name=user_name, status=QueueEntry.Status.WAITING).select_related(
        "queue__service"
    )
    if service:
        entries = entries.filter(queue__service=service)
    entry = entries.order_by("joined_at", "id").first()
    if not entry:
        return JsonResponse({"error": "User not found in queue"}, status=404)

    estimated_wait = (entry.position - 1) * entry.queue.service.expected_duration
    return JsonResponse(
        {
            "user": user_name,
            "position": entry.position,
            "service": entry.queue.service.name,
            "estimated_wait_time": estimated_wait,
            "unit": "minutes",
        },
        status=200,
    )
class ReportsView(TemplateView):
    """Queue reporting dashboard view."""
    template_name = "pages/reports.html"

    def dispatch(self, request, *args, **kwargs):
        if not _user_can_access_reports(request.user):
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        service_id = self.request.GET.get("service_id")
        selected_service = None

        entries = QueueEntry.objects.select_related("queue__service").order_by("-joined_at", "-id")
        if service_id:
            selected_service = Service.objects.filter(id=service_id).first()
            if selected_service:
                entries = entries.filter(queue__service=selected_service)

        total_entries = entries.count()
        waiting_count = entries.filter(status=QueueEntry.Status.WAITING).count()
        served_count = entries.filter(status=QueueEntry.Status.SERVED).count()
        canceled_count = entries.filter(status=QueueEntry.Status.CANCELED).count()

        estimated_wait_values = []
        for entry in entries.filter(status=QueueEntry.Status.WAITING):
            estimated_wait_values.append((entry.position - 1) * entry.queue.service.expected_duration)

        average_estimated_wait = 0
        if estimated_wait_values:
            average_estimated_wait = round(sum(estimated_wait_values) / len(estimated_wait_values), 2)

        context.update(
            {
                "services": Service.objects.all(),
                "selected_service": selected_service,
                "entries": entries[:25],
                "total_entries": total_entries,
                "waiting_count": waiting_count,
                "served_count": served_count,
                "canceled_count": canceled_count,
                "average_estimated_wait": average_estimated_wait,
            }
        )
        return context
def export_queue_report_csv(request):
    if not _user_can_access_reports(request.user):
        return redirect("login")

    service_id = request.GET.get("service_id")
    selected_service = None

    entries = QueueEntry.objects.select_related("queue__service").order_by("-joined_at", "-id")
    if service_id:
        selected_service = Service.objects.filter(id=service_id).first()
        if selected_service:
            entries = entries.filter(queue__service=selected_service)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="queue_activity_report.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "User",
            "Service",
            "Queue Status",
            "Position",
            "Expected Duration",
            "Estimated Wait",
            "Joined At",
            "Updated At",
        ]
    )

    for entry in entries:
        estimated_wait = ""
        if entry.status == QueueEntry.Status.WAITING:
            estimated_wait = (entry.position - 1) * entry.queue.service.expected_duration

        writer.writerow(
            [
                entry.user_name,
                entry.queue.service.name,
                entry.status,
                entry.position,
                entry.queue.service.expected_duration,
                estimated_wait,
                entry.joined_at,
                entry.updated_at,
            ]
        )

    return response