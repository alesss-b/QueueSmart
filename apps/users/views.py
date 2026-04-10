from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, TemplateView

from apps.operations.models import QueueEntry, Service

from .models import Notification


def _request_names(request):
    if not request.user.is_authenticated:
        return []
    names = {request.user.username}
    full_name = request.user.get_full_name().strip()
    if full_name:
        names.add(full_name)
    return [name for name in names if name]


class UsersView(LoginRequiredMixin, TemplateView):
    """Users page view; redirects to login if not authenticated."""
    login_url = "login"
    template_name = "pages/users.html"

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.groups.filter(name="Customers").exists():
            return redirect("portal")
        if user.groups.filter(name="Staff").exists():
            return redirect("operations")
        return super().get(request, *args, **kwargs)


class LoginView(FormView):
    """Login page view."""
    form_class = AuthenticationForm
    success_url = reverse_lazy("portal")
    template_name = "pages/login.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        login(self.request, form.get_user())
        return super().form_valid(form)


class RegisterView(SuccessMessageMixin, CreateView):
    """Register page view."""
    form_class = UserCreationForm
    success_url = reverse_lazy("login")
    template_name = "pages/register.html"
    success_message = "Your account was created successfully!"


class NotificationsView(TemplateView):
    """Notifications page view."""
    template_name = "pages/notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        notifications = Notification.objects.all()
        request_names = _request_names(self.request)
        if request_names:
            filtered_notifications = notifications.filter(recipient_name__in=request_names)
            if filtered_notifications.exists():
                notifications = filtered_notifications
        notifications = list(notifications)
        for notification in notifications:
            notification.notification_type_label = notification.notification_type.replace("_", " ").title()
        context["notifications"] = notifications
        context["unread_count"] = sum(1 for notification in notifications if not notification.is_read)
        context["selected_notification"] = notifications[0] if notifications else None
        return context


class UserDetailsView(TemplateView):
    """User Details page view."""
    template_name = "pages/user_details.html"


class EmailVerificationView(TemplateView):
    """Email Verification page view."""
    template_name = "pages/email_verification.html"


class DashboardView(TemplateView):
    template_name = "pages/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_names = _request_names(self.request)
        current_entry = QueueEntry.objects.filter(status=QueueEntry.Status.WAITING).select_related("queue__service")
        notifications = Notification.objects.all()

        if request_names:
            matching_entries = current_entry.filter(user_name__in=request_names)
            if matching_entries.exists():
                current_entry = matching_entries
            matching_notifications = notifications.filter(recipient_name__in=request_names)
            if matching_notifications.exists():
                notifications = matching_notifications

        current_entry = current_entry.order_by("joined_at", "id").first()
        context["current_entry"] = current_entry
        context["estimated_wait"] = (
            (current_entry.position - 1) * current_entry.queue.service.expected_duration if current_entry else None
        )
        context["active_services"] = Service.objects.all()
        context["recent_notifications"] = notifications[:2]
        return context


class JoinQueueView(TemplateView):
    template_name = "pages/join_queue.html"


class QueueStatusView(TemplateView):
    template_name = "pages/queue_status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_names = _request_names(self.request)
        current_entry = QueueEntry.objects.filter(status=QueueEntry.Status.WAITING).select_related("queue__service")
        updates = Notification.objects.all()

        if request_names:
            matching_entries = current_entry.filter(user_name__in=request_names)
            if matching_entries.exists():
                current_entry = matching_entries
            matching_updates = updates.filter(recipient_name__in=request_names)
            if matching_updates.exists():
                updates = matching_updates

        current_entry = current_entry.order_by("joined_at", "id").first()
        context["current_entry"] = current_entry
        context["estimated_wait"] = (
            (current_entry.position - 1) * current_entry.queue.service.expected_duration if current_entry else None
        )
        context["recent_updates"] = list(updates[:5])
        return context


class HistoryView(TemplateView):
    template_name = "pages/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        history_entries = QueueEntry.objects.exclude(status=QueueEntry.Status.WAITING).select_related(
            "queue__service"
        )
        request_names = _request_names(self.request)
        if request_names:
            matching_history = history_entries.filter(user_name__in=request_names)
            if matching_history.exists():
                history_entries = matching_history
        context["history_entries"] = history_entries.order_by("-updated_at", "-id")[:20]
        return context


def logout_view(request):
    """Log out the user and redirect to the login page."""
    logout(request)
    return redirect("login")
