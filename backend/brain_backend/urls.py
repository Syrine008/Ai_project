from django.contrib import admin
from django.http import HttpResponse, JsonResponse
from django.urls import include, path


def health(_request):
    return JsonResponse({"status": "ok"})


def api_health(_request):
    return JsonResponse({"status": "ok", "service": "brAIn backend"})


def root(_request):
    """Django serves JSON APIs only; the React UI is a separate dev server (`npm run dev`)."""
    html = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>brAIn API</title>
<style>body{font-family:system-ui,sans-serif;max-width:42rem;margin:2rem;line-height:1.5;}
code{background:#f0f0f0;padding:0.1em 0.35em;border-radius:4px;} a{color:#2563eb;}</style></head>
<body>
<h1>brAIn backend (Django)</h1>
<p>This process is the <strong>REST API</strong>. There is no full web app at <code>/</code> by design.</p>
<ul>
<li><a href="/api/health/">GET /api/health/</a> — quick JSON check that the server is up.</li>
<li><code>POST /api/send-report-email/</code> — JSON body; emails patient HTML summary (console backend in dev — see <code>backend/README.md</code>).</li>
<li>Axis endpoints are under <code>/api/axisN-…/analyze/</code> (POST, multipart). Example:
  <code>curl -X POST http://127.0.0.1:8000/api/axis4-brain-aging/analyze/ -F 'metadata={"demo":true}'</code></li>
</ul>
<p><strong>Local UI:</strong> in the project root run <code>npm run dev</code> and open the URL Vite prints (often <code>http://localhost:5173</code>). Set <code>VITE_API_BASE_URL=http://127.0.0.1:8000</code> in <code>.env</code> so the browser calls this API.</p>
</body></html>"""
    return HttpResponse(html)


urlpatterns = [
    path("", root),
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/", include("common.urls")),
    path("api/health/", api_health),
    path("api/axis1-alzheimer-dementia/", include("axis1_alzheimer_dementia.urls")),
    path("api/axis2-parkinson-atypical/", include("axis2_parkinson_atypical.urls")),
    path("api/axis3-cerebellar-dysfunction/", include("axis3_cerebellar_dysfunction.urls")),
    path("api/axis4-brain-aging/", include("axis4_brain_aging.urls")),
    path("api/axis5-functional-connectivity/", include("axis5_functional_connectivity.urls")),
    path("api/axis6-neuromotor-video/", include("axis6_neuromotor_video.urls")),
    path("api/axis7-epilepsy-network/", include("axis7_epilepsy_network.urls")),
]
