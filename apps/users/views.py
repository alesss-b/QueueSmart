from django.views.generic import TemplateView, CreateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login
from django.urls import reverse_lazy


class UsersView(LoginRequiredMixin, TemplateView):
    """Users page view; redirects to login if not authenticated."""
    login_url = 'login'
    template_name = 'pages/users.html'
    

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
