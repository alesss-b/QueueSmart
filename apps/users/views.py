from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class UsersView(LoginRequiredMixin, TemplateView):
    """Users page view; redirects to login if not authenticated."""
    login_url = 'login'
    template_name = 'pages/users.html'
    
class LoginView(TemplateView):
    """Login page view."""
    template_name = 'pages/login.html'

class RegisterView(TemplateView):
    """Register page view."""
    template_name = 'pages/register.html'
