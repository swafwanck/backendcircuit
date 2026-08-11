"""Enumerated choices used across models & serializers."""
from django.db import models


class GalleryKind(models.TextChoices):
    IMAGE = "image", "Image"
    VIDEO = "video", "Video"


class DealCategory(models.TextChoices):
    PACKAGE = "package", "Package"
    VISA = "visa", "Visa"
    ACTIVITY = "activity", "Activity"
    HOTEL = "hotel", "Hotel"


class ServiceType(models.TextChoices):
    PACKAGE = "package", "Package"
    VISA = "visa", "Visa"
    ACTIVITY = "activity", "Activity"
    DEAL = "deal", "Deal"
    HOTEL = "hotel", "Hotel"


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"
    COMPLETED = "completed", "Completed"


class EnquiryChannel(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    GOOGLE_FORM = "google_form", "Google Form"
    EMAIL = "email", "Email"
    PHONE = "phone", "Phone"
    FORM = "form", "Form"


class EnquiryStatus(models.TextChoices):
    NEW = "new", "New"
    IN_PROGRESS = "in_progress", "In Progress"
    CLOSED = "closed", "Closed"


class PaymentStatus(models.TextChoices):
    INITIATED = "initiated", "Initiated"
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    AUTHORISED = "authorised", "Authorised"
    CAPTURED = "captured", "Captured"
    REFUNDED = "refunded", "Refunded"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class BookingItemType(models.TextChoices):
    PACKAGE = "package", "Package"
    HOTEL = "hotel", "Hotel"
    ACTIVITY = "activity", "Activity"
    VISA = "visa", "Visa"
    DEAL = "deal", "Deal"


ENQUIRY_SOURCES = [
    "home", "assistance", "package", "deal", "visa", "activity", "hotel",
    "deal package", "deal visa", "deal activity", "deal hotel",
]
