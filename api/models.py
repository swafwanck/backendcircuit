import uuid

from django.core.validators import MinValueValidator
from django.db import models

from .constants import (
    GalleryKind, DealCategory, BookingStatus,
    EnquiryChannel, EnquiryStatus, PaymentStatus, BookingItemType,
    ServiceType,
)
from .validators import validate_slug, validate_phone, validate_non_negative


class TimeStamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def _new_ref(prefix: str) -> str:
    """Short, human-readable reference, e.g. BK-9F3A2C7D."""
    return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"


def media_upload_to(instance, filename):
    folder = instance.__class__.__name__.lower()
    return f"uploads/{folder}/{uuid.uuid4().hex[:12]}_{filename}"



class MediaMixin(models.Model):
    """File-based image storage + an extra multi-image gallery."""
    image = models.CharField(max_length=500, blank=True, default="",
                             help_text="Stored image URL (filled automatically on upload)")
    image_file = models.ImageField(upload_to=media_upload_to, blank=True, null=True)
    gallery_images = models.JSONField(default=list, blank=True)

    class Meta:
        abstract = True

    @property
    def image_url(self):
        if getattr(self, "image_file", None):
            try:
                return self.image_file.url
            except ValueError:
                return ""
        return self.image or ""


class Visibility(models.Model):
    show_on_home = models.BooleanField(default=False, help_text="Show on home page")
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class Package(TimeStamped, MediaMixin, Visibility):
    slug = models.SlugField(max_length=160, unique=True, blank=True, validators=[validate_slug])
    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=160, blank=True, default="")
    duration = models.CharField(max_length=80, blank=True, default="")
    short_description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                validators=[MinValueValidator(0)])
    offer_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                      validators=[MinValueValidator(0)])
    offer_percentage = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="AED")
    overview = models.TextField(blank=True, default="")
    highlights = models.JSONField(default=list, blank=True)
    inclusions_included = models.JSONField(default=list, blank=True)
    inclusions_not_included = models.JSONField(default=list, blank=True)
    itinerary = models.JSONField(default=list, blank=True)
    terms = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-show_on_home", "title"]

    def __str__(self):
        return self.title


class Activity(TimeStamped, MediaMixin, Visibility):
    slug = models.SlugField(max_length=160, unique=True, blank=True, validators=[validate_slug])
    title = models.CharField(max_length=200)
    destination = models.CharField(max_length=160, blank=True, default="")
    duration = models.CharField(max_length=80, blank=True, default="")
    short_description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                validators=[MinValueValidator(0)])
    offer_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                      validators=[MinValueValidator(0)])
    offer_percentage = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="AED")
    activity_packages = models.JSONField(default=list, blank=True)
    overview = models.TextField(blank=True, default="")
    highlights = models.JSONField(default=list, blank=True)
    good_to_know = models.JSONField(default=list, blank=True)
    inclusions_included = models.JSONField(default=list, blank=True)
    inclusions_not_included = models.JSONField(default=list, blank=True)
    meeting_pickup = models.TextField(blank=True, default="")
    location = models.CharField(max_length=200, blank=True, default="")
    pickup_time = models.CharField(max_length=200, blank=True, default="")
    what_to_bring = models.JSONField(default=list, blank=True)
    terms = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-show_on_home", "title"]

    def __str__(self):
        return self.title


class Visa(TimeStamped, MediaMixin, Visibility):
    slug = models.SlugField(max_length=160, unique=True, blank=True, validators=[validate_slug])
    destination = models.CharField(max_length=160)
    visa_type = models.CharField(max_length=120, blank=True, default="")
    processing_days = models.CharField(max_length=120, blank=True, default="")
    validity = models.CharField(max_length=120, blank=True, default="")
    short_description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                validators=[MinValueValidator(0)])
    offer_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                      validators=[MinValueValidator(0)])
    offer_percentage = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="AED")
    flag = models.CharField(max_length=500, blank=True, default="")
    flag_file = models.ImageField(upload_to=media_upload_to, blank=True, null=True)
    overview = models.TextField(blank=True, default="")
    documents_required = models.JSONField(default=list, blank=True)
    eligibility = models.JSONField(default=list, blank=True)
    terms = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-show_on_home", "destination"]

    def __str__(self):
        return f"{self.destination} — {self.visa_type or 'Visa'}"


class Hotel(TimeStamped, MediaMixin, Visibility):
    slug = models.SlugField(max_length=160, unique=True, blank=True, validators=[validate_slug])
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, default="")
    destination = models.CharField(max_length=160, blank=True, default="")
    short_description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                validators=[MinValueValidator(0)])
    offer_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                      validators=[MinValueValidator(0)])
    offer_percentage = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="AED")
    stars = models.PositiveSmallIntegerField(default=5)
    overview = models.TextField(blank=True, default="")
    rooms = models.JSONField(default=list, blank=True)
    amenities = models.JSONField(default=list, blank=True)
    policies = models.JSONField(default=list, blank=True)
    terms = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-show_on_home", "name"]

    def __str__(self):
        return self.name


class Deal(TimeStamped, MediaMixin, Visibility):
    slug = models.SlugField(max_length=160, unique=True, blank=True, validators=[validate_slug])
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=DealCategory.choices,
                                default=DealCategory.PACKAGE)
    destination = models.CharField(max_length=160, blank=True, default="")
    short_description = models.TextField(blank=True, default="")
    price = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                validators=[MinValueValidator(0)])
    offer_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                      validators=[MinValueValidator(0)])
    offer_percentage = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, default="AED")
    valid_until = models.DateField(null=True, blank=True)
    overview = models.TextField(blank=True, default="")

    # package / activity
    duration = models.CharField(max_length=80, blank=True, default="")
    highlights = models.JSONField(default=list, blank=True)
    inclusions_included = models.JSONField(default=list, blank=True)
    inclusions_not_included = models.JSONField(default=list, blank=True)
    itinerary = models.JSONField(default=list, blank=True)

    # activity
    activity_packages = models.JSONField(default=list, blank=True)
    good_to_know = models.JSONField(default=list, blank=True)
    meeting_pickup = models.TextField(blank=True, default="")
    location = models.CharField(max_length=200, blank=True, default="")
    pickup_time = models.CharField(max_length=200, blank=True, default="")
    what_to_bring = models.JSONField(default=list, blank=True)

    # hotel
    rooms = models.JSONField(default=list, blank=True)
    amenities = models.JSONField(default=list, blank=True)
    policies = models.JSONField(default=list, blank=True)

    # visa
    visa_type = models.CharField(max_length=120, blank=True, default="")
    validity = models.CharField(max_length=120, blank=True, default="")
    documents_required = models.JSONField(default=list, blank=True)
    eligibility = models.JSONField(default=list, blank=True)

    terms = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-show_on_home", "-created_at"]

    def __str__(self):
        return self.title


class GalleryItem(TimeStamped, MediaMixin, Visibility):
    title = models.CharField(max_length=200)
    kind = models.CharField(max_length=10, choices=GalleryKind.choices, default=GalleryKind.IMAGE)
    place = models.CharField(max_length=160, blank=True, default="")
    images = models.JSONField(default=list, blank=True)
    videos = models.JSONField(default=list, blank=True)
    video_url = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class HomeHeroSlide(TimeStamped, MediaMixin, Visibility):
    """Full-bleed hero slider on the home page."""
    title = models.CharField(max_length=200)
    name = models.CharField(max_length=160, blank=True, default="")
    short_description = models.TextField(blank=True, default="")
    button_text = models.CharField(max_length=80, blank=True, default="")
    button_link = models.CharField(max_length=200, blank=True, default="/packages")
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]
        verbose_name = "Home hero slide"

    def __str__(self):
        return self.title


class HomeGallerySlider(TimeStamped, MediaMixin, Visibility):
    """Poster/marquee image strip on the home page."""
    title = models.CharField(max_length=200, blank=True, default="")
    images = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Home gallery slider"

    def __str__(self):
        return self.title or f"Slider #{self.pk}"


class Testimonial(TimeStamped, Visibility):
    title = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")
    avatar = models.CharField(max_length=500, blank=True, default="")
    avatar_file = models.ImageField(upload_to=media_upload_to, blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return self.title


class Booking(TimeStamped):
    reference = models.CharField(max_length=40, unique=True, blank=True)
    customer_name = models.CharField(max_length=180)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=32, blank=True, validators=[validate_phone])

    item_type = models.CharField(max_length=20, choices=BookingItemType.choices,
                                 default=BookingItemType.PACKAGE)
    item_slug = models.CharField(max_length=200, blank=True, default="")
    item_title = models.CharField(max_length=200, blank=True, default="")

    travel_date = models.DateField(null=True, blank=True)
    pax = models.PositiveIntegerField(default=1)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                       validators=[validate_non_negative])
    currency = models.CharField(max_length=8, default="AED")
    status = models.CharField(max_length=20, choices=BookingStatus.choices,
                              default=BookingStatus.PENDING)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices,
                                      default=PaymentStatus.INITIATED)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = _new_ref("BK")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference} — {self.customer_name}"


class Enquiry(TimeStamped):
    name = models.CharField(max_length=180)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True, validators=[validate_phone])
    channel = models.CharField(max_length=20, choices=EnquiryChannel.choices,
                               default=EnquiryChannel.FORM)
    service = models.CharField(max_length=20, choices=ServiceType.choices, blank=True, default="")
    message = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=EnquiryStatus.choices,
                              default=EnquiryStatus.NEW)

    # Routing: visa + call-back enquiries are delivered to WhatsApp.
    is_visa = models.BooleanField(default=False)

    source = models.CharField(max_length=40, blank=True, default="",
                              help_text="home | assistance | package | deal visa | …")
    item_type = models.CharField(max_length=30, blank=True, default="")
    item_title = models.CharField(max_length=200, blank=True, default="")
    item_slug = models.CharField(max_length=200, blank=True, default="")
    source_page = models.CharField(max_length=200, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    google_form_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    whatsapp_url = models.URLField(max_length=1200, blank=True, default="")
    delivery_log = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Enquiries"

    def __str__(self):
        return f"{self.name} — {self.item_title or self.channel}"


class ContactMessage(TimeStamped):
    """Messages submitted from the public Contact page."""
    name = models.CharField(max_length=180)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True, default="")
    service = models.CharField(max_length=20, choices=ServiceType.choices, blank=True, default="")
    message = models.TextField(blank=True, default="")
    handled = models.BooleanField(default=False)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    email_sent = models.BooleanField(default=False)
    google_form_sent = models.BooleanField(default=False)
    delivery_log = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Contact message"

    def __str__(self):
        return f"{self.name} — {self.service or 'Contact'}"


class Payment(TimeStamped):
    """Adyen payment record linked to a booking."""
    booking = models.ForeignKey(Booking, null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="payments")
    provider = models.CharField(max_length=20, default="adyen")
    provider_reference = models.CharField(max_length=80, blank=True, default="")
    session_id = models.CharField(max_length=120, blank=True, default="")
    payment_link = models.URLField(blank=True, default="")
    invoice_url = models.URLField(blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                 validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=8, default="AED")
    status = models.CharField(max_length=20, choices=PaymentStatus.choices,
                              default=PaymentStatus.INITIATED)
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.provider_reference or self.id} — {self.status}"


class PaymentLink(TimeStamped):
    """Adyen Pay By Link records generated from the admin panel."""
    reference = models.CharField(max_length=80, blank=True, default="")
    customer_name = models.CharField(max_length=180, blank=True, default="")
    customer_email = models.EmailField(blank=True)
    description = models.CharField(max_length=250, blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0,
                                 validators=[MinValueValidator(0)])
    currency = models.CharField(max_length=8, default="AED")
    payment_link = models.URLField(max_length=600, blank=True, default="")
    status = models.CharField(max_length=20, choices=PaymentStatus.choices,
                              default=PaymentStatus.INITIATED)
    raw = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reference or str(self.pk)


class SiteSetting(TimeStamped):
    """Simple key/value store for website content."""
    key = models.CharField(max_length=80, unique=True)
    value = models.TextField(blank=True, default="")
    label = models.CharField(max_length=180, blank=True, default="")

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key
