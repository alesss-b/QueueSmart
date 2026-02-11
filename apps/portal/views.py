from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class PortalView(LoginRequiredMixin, TemplateView):
    """Portal default view; redirects to login if not authenticated."""
    login_url = 'login'
    template_name = 'pages/portal_dashboard.html'