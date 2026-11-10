from django.conf import settings
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

@never_cache
@require_GET
def session_status(request):
    return JsonResponse({"csrfToken": get_token(request), "authenticated": request.user.is_authenticated,
                         "authenticationRequired": not settings.DEBUG})
