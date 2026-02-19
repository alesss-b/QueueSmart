from django.urls import path

from . import views

urlpatterns = [
    path('', views.UsersView.as_view(), name='users'),
    path('login', views.LoginView.as_view(), name='login'),
    path('logout', views.logout_view, name='logout'),
    path('register', views.RegisterView.as_view(), name='register'),
    path('notifications', views.NotificationsView.as_view(), name='notifications'),
    path('user/verify', views.EmailVerificationView.as_view(), name='email_verification'),
    path('user/details', views.UserDetailsView.as_view(), name='user_details'),
    path('dashboard', views.DashboardView.as_view(), name='dashboard'),
path('join-queue', views.JoinQueueView.as_view(), name='join_queue'),
path('queue-status', views.QueueStatusView.as_view(), name='queue_status'),
path('history', views.HistoryView.as_view(), name='history')
]