from django.urls import path

from . import views

urlpatterns = [
    path("", views.PortalView.as_view(), name="portal"),
]