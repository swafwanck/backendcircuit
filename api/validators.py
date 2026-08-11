"""Reusable field validators."""
import re
from django.core.exceptions import ValidationError

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PHONE_RE = re.compile(r"^\+?[0-9\s\-()]{7,20}$")


def validate_slug(value: str):
    if not SLUG_RE.match(value or ""):
        raise ValidationError("Slug must be lowercase letters, numbers and dashes only.")


def validate_phone(value: str):
    if value and not PHONE_RE.match(value):
        raise ValidationError("Enter a valid phone number.")


def validate_non_negative(value):
    if value is not None and value < 0:
        raise ValidationError("Value must be zero or positive.")
