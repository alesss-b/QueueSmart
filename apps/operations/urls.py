from django.urls import path

from . import views

urlpatterns = [
    path('', views.OperationsView.as_view(), name="operations"),
    path('service/details', views.ServiceDetailsView.as_view(), name='service_details'),
    path('service/create', views.ServiceFormView.as_view(), name='create_service'),
    path('service/edit', views.ServiceFormView.as_view(), name='edit_service'),
    path('service_ticket/fulfill', views.ServiceTicketFulfillmentFormView.as_view(), name='fulfill_service_ticket'),
    path('queue/join', views.join_queue, name='join_queue'),
    path('queue/leave', views.leave_queue, name='leave_queue'),
    path('queue/view', views.view_queue, name='view_queue'),
    path('queue/serve-next', views.serve_next, name='serve_next'),
    path('queue/wait-time', views.estimate_wait_time, name='estimate_wait_time'),
    path("reports", views.ReportsView.as_view(), name="reports"),
    path("reports/export-csv", views.export_queue_report_csv, name="export_queue_report_csv"),
]