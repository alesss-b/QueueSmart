from django.views.generic import TemplateView, CreateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, logout
from django.urls import reverse_lazy
from django.shortcuts import redirect


class UsersView(LoginRequiredMixin, TemplateView):
    """Users page view; redirects to login if not authenticated."""
    login_url = 'login'
    template_name = 'pages/users.html'

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.groups.filter(name='Customers').exists():
            return redirect('portal')
        if user.groups.filter(name='Staff').exists():
            return redirect('operations')
        return super().get(request, *args, **kwargs)
    

class LoginView(FormView):
    """Login page view."""
    form_class = AuthenticationForm
    success_url = reverse_lazy('portal')
    template_name = 'pages/login.html'

    def get_form_kwargs(self):
        """Pass the request into AuthenticationForm which expects it."""
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        """Log the user in and continue to the success URL."""
        login(self.request, form.get_user())
        return super().form_valid(form)


class RegisterView(SuccessMessageMixin, CreateView):
    """Register page view."""
    form_class = UserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'pages/register.html'
    success_message = "Your account was created successfully!"   

class NotificationsView(TemplateView):
    """Notifications page view."""
    template_name = 'pages/notifications.html'

class UserDetailsView(TemplateView):
    """User Details page view."""
    template_name = 'pages/user_details.html'

class EmailVerificationView(TemplateView):
    """Email Verification page view."""
    template_name = 'pages/email_verification.html'

class DashboardView(TemplateView):
    template_name = "pages/dashboard.html"

class JoinQueueView(TemplateView):
        template_name = "pages/join_queue.html"

class QueueStatusView(TemplateView):
        template_name = "pages/queue_status.html"

class HistoryView(TemplateView):
        template_name = "pages/history.html"

def logout_view(request):
    """Log out the user and redirect to the login page."""
    logout(request)
    return redirect('login')

