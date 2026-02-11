from django.urls import path

from . import views

urlpatterns = [
    path('', views.UsersView.as_view(), name='users'),
    path('login', views.LoginView.as_view(), name='login'),
    path('register', views.RegisterView.as_view(), name='register'),
]