from django.urls import path

from .views import SendReportEmailView

urlpatterns = [
    path("send-report-email/", SendReportEmailView.as_view(), name="send-report-email"),
]
