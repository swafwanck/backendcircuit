"""Lenient JWT authentication.

DRF's default JWTAuthentication raises 401 for ANY malformed/expired token,
even on endpoints that allow anonymous access (AllowAny / IsAdminOrReadOnly).
That made every public GET fail with 401 whenever the browser still had a
stale admin token in localStorage.

This class simply ignores a bad token and lets the request continue as an
anonymous visitor; endpoints that really require staff still reject it via
their permission classes.
"""
import logging

from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)


class OptionalJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (InvalidToken, TokenError, AuthenticationFailed) as exc:
            logger.debug("Ignoring invalid JWT: %s", exc)
            return None
