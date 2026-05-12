from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok", "service": "brAIn backend"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/axis1-alzheimer-dementia/", include("axis1_alzheimer_dementia.urls")),
    path("api/axis2-parkinson-atypical/", include("axis2_parkinson_atypical.urls")),
    path("api/axis3-cerebellar-dysfunction/", include("axis3_cerebellar_dysfunction.urls")),
    path("api/axis4-brain-aging/", include("axis4_brain_aging.urls")),
    path("api/axis5-functional-connectivity/", include("axis5_functional_connectivity.urls")),
    path("api/axis6-neuromotor-video/", include("axis6_neuromotor_video.urls")),
    path("api/axis7-epilepsy-network/", include("axis7_epilepsy_network.urls")),
]
