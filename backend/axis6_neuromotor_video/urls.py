from django.urls import path
from .views import AnalyzeView

urlpatterns = [
    path("analyze/", AnalyzeView.as_view(), name="axis6_neuromotor_video-analyze"),
]
