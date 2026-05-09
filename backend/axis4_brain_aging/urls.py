from django.urls import path
from .views import AnalyzeView

urlpatterns = [
    path("analyze/", AnalyzeView.as_view(), name="axis4_brain_aging-analyze"),
]
