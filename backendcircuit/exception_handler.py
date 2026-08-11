"""Uniform error response: {code, message, details}."""
import logging

from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    ValidationError, NotFound, PermissionDenied, NotAuthenticated,
    AuthenticationFailed, Throttled, MethodNotAllowed,
)
from rest_framework.response import Response
from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied


logger = logging.getLogger(__name__)


def _code_for(exc):
    if isinstance(exc, ValidationError):
        return "validation_error"
    if isinstance(exc, (NotFound, Http404)):
        return "not_found"
    if isinstance(exc, (PermissionDenied, DjangoPermissionDenied)):
        return "permission_denied"
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return "not_authenticated"
    if isinstance(exc, Throttled):
        return "throttled"
    if isinstance(exc, MethodNotAllowed):
        return "method_not_allowed"
    return "error"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        view = context.get("view")
        request = context.get("request")
        logger.exception(
            "Unhandled API error in %s %s (%s)",
            getattr(request, "method", "UNKNOWN"),
            getattr(request, "path", "unknown path"),
            view.__class__.__name__ if view else "unknown view",
            exc_info=(type(exc), exc, exc.__traceback__),
        )
        return Response(
            {"code": "server_error", "message": "Internal server error", "details": None},
            status=500,
        )
    data = response.data
    message = "Request failed"
    details = None
    if isinstance(data, dict):
        message = str(data.get("detail", message)) if "detail" in data else message
        details = {k: v for k, v in data.items() if k != "detail"} or None
        if not details and "detail" not in data:
            details = data
    elif isinstance(data, list):
        details = data
    response.data = {"code": _code_for(exc), "message": message, "details": details}
    return response
