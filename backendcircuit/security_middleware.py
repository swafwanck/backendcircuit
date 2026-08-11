"""
Extra security hardening applied to every response.

Django already provides several security protections through
SecurityMiddleware. This middleware adds:

- Content Security Policy (CSP)
- Permissions Policy
- Cross-Origin Opener Policy
- Cross-Origin Resource Policy
- X-Permitted-Cross-Domain-Policies
- Request body size protection
- Server header removal

IMPORTANT:
The frontend and backend are hosted on different domains.

Frontend:
https://circuit.muhammedswafwanck.workers.dev

Backend:
https://backendcircuit.onrender.com

Therefore /media/ resources must allow cross-origin loading.
"""

from django.conf import settings
from django.http import JsonResponse


# ============================================================
# CONTENT SECURITY POLICY
# ============================================================

CSP = (
    "default-src 'self'; "
    "img-src 'self' data: https:; "
    "style-src 'self' 'unsafe-inline'; "
    "script-src 'self' 'unsafe-inline'; "
    "connect-src 'self' https:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "object-src 'none';"
)


# ============================================================
# SECURITY HEADERS MIDDLEWARE
# ============================================================

class SecurityHeadersMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        # ========================================================
        # REQUEST BODY SIZE PROTECTION
        # ========================================================

        max_bytes = getattr(
            settings,
            "MAX_REQUEST_BODY_BYTES",
            50 * 1024 * 1024,
        )

        content_length = request.META.get("CONTENT_LENGTH")

        if (
            content_length
            and str(content_length).isdigit()
            and int(content_length) > max_bytes
        ):
            response = JsonResponse(
                {
                    "code": "payload_too_large",
                    "message": "Request body too large.",
                    "details": {},
                },
                status=413,
            )

            # ====================================================
            # CORS HEADERS FOR SHORT-CIRCUITED RESPONSE
            # ====================================================

            origin = request.headers.get("Origin")

            allowed_origins = getattr(
                settings,
                "CORS_ALLOWED_ORIGINS",
                [],
            ) or []

            allow_all_origins = getattr(
                settings,
                "CORS_ALLOW_ALL_ORIGINS",
                False,
            )

            if (
                origin
                and (
                    allow_all_origins
                    or origin in allowed_origins
                )
            ):
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Credentials"] = "true"
                response["Vary"] = "Origin"

            return response

        # ========================================================
        # NORMAL DJANGO RESPONSE
        # ========================================================

        response = self.get_response(request)

        # ========================================================
        # CONTENT SECURITY POLICY
        # ========================================================

        response.setdefault(
            "Content-Security-Policy",
            CSP,
        )

        # ========================================================
        # PERMISSIONS POLICY
        # ========================================================

        response.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=()",
        )

        # ========================================================
        # CROSS-ORIGIN OPENER POLICY
        # ========================================================

        response.setdefault(
            "Cross-Origin-Opener-Policy",
            "same-origin",
        )

        # ========================================================
        # CROSS-ORIGIN RESOURCE POLICY
        #
        # THIS FIXES:
        #
        # ERR_BLOCKED_BY_RESPONSE.NotSameSite
        #
        # Images uploaded to:
        #
        # https://backendcircuit.onrender.com/media/
        #
        # are displayed by:
        #
        # https://circuit.muhammedswafwanck.workers.dev
        #
        # Therefore media must allow cross-origin loading.
        # ========================================================

        if request.path.startswith("/media/"):

            response["Cross-Origin-Resource-Policy"] = "cross-origin"

        else:

            response.setdefault(
                "Cross-Origin-Resource-Policy",
                "same-origin",
            )

        # ========================================================
        # CROSS-DOMAIN POLICY
        # ========================================================

        response.setdefault(
            "X-Permitted-Cross-Domain-Policies",
            "none",
        )

        # ========================================================
        # REMOVE SERVER INFORMATION
        # ========================================================

        response.headers.pop(
            "Server",
            None,
        )

        return response