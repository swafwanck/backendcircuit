"""
Extra hardening applied to every response.

Django already ships XSS/nosniff/HSTS/clickjacking protection via
SecurityMiddleware; this adds a strict CSP, Permissions-Policy and
cross-origin isolation headers, plus a simple oversized-body guard.
"""
from django.conf import settings
from django.http import JsonResponse

CSP = (
    "default-src 'self'; "
    "img-src 'self' data: https:; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; "   # required by Swagger UI / Redoc
    "connect-src 'self' https:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none'"
)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        max_bytes = getattr(settings, "MAX_REQUEST_BODY_BYTES", 50 * 1024 * 1024)
        length = request.META.get("CONTENT_LENGTH")
        if length and str(length).isdigit() and int(length) > max_bytes:
            response = JsonResponse(
                {"code": "payload_too_large", "message": "Request body too large.", "details": {}},
                status=413,
            )
            # The CORS middleware never runs for short-circuited responses, so the
            # browser would report a misleading "No Access-Control-Allow-Origin"
            # error instead of 413. Add the headers here.
            origin = request.headers.get("Origin")
            allowed = getattr(settings, "CORS_ALLOWED_ORIGINS", []) or []
            if origin and (getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False) or origin in allowed):
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Credentials"] = "true"
                response["Vary"] = "Origin"
            return response

        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CSP)
        response.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault("Cross-Origin-Resource-Policy", "same-site")
        response.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        response.headers.pop("Server", None)
        return response
