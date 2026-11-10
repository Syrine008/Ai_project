from django.urls import path

from .views import SendReportEmailView
from .session import session_status

urlpatterns = [
    path("session/", session_status, name="session-status"),
    path("send-report-email/", SendReportEmailView.as_view(), name="send-report-email"),
]
