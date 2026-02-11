from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

class OperationsView(LoginRequiredMixin, TemplateView):
    """Operations default view; redirects to login if not authenticated."""
    login_url = 'login'
    template_name = 'pages/operations_dashboard.html'