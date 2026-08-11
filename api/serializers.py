"""DRF serializers. Field names match the admin panel 1:1."""
import json
import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.utils.text import slugify
from rest_framework import serializers

from .constants import EnquiryChannel, EnquiryStatus
from .models import (
    Package, Deal, Hotel, Activity, Visa, GalleryItem, Testimonial,
    Booking, Enquiry, Payment, SiteSetting, ContactMessage, PaymentLink,
    HomeHeroSlide, HomeGallerySlider,
)

User = get_user_model()

JSON_LIST_FIELDS = (
    "highlights", "inclusions_included", "inclusions_not_included", "terms",
    "itinerary", "activity_packages", "good_to_know", "what_to_bring",
    "rooms", "amenities", "policies", "documents_required", "eligibility",
    "gallery_images", "images", "videos",
)


class MediaSerializerMixin:
    """
    Handles multipart (file upload) and JSON payloads with one code path.

    * ``image`` / ``flag`` / ``avatar`` accept an uploaded file **or** a URL string.
      Files are stored through the model's ``*_file`` ImageField and the public
      URL is echoed back on the plain field.
    * multi-file fields (``gallery_images``, ``images``, ``videos``) accept any
      number of uploaded files; already-stored URLs are preserved by sending
      ``<field>_json``.
    * every JSON list/object field may arrive as a JSON string (multipart).
    """
    image_pairs = (("image", "image_file"),)
    multi_media_fields = ("gallery_images",)

    # ---- helpers ----
    def _store_file(self, f):
        path = default_storage.save(f"uploads/media/{uuid.uuid4().hex[:12]}_{f.name}", f)
        return default_storage.url(path)

    def _abs(self, url):
        if not url or str(url).startswith(("http://", "https://", "data:")):
            return url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    # ---- write ----
    def to_internal_value(self, data):
        self._multi_media = {}
        if hasattr(data, "getlist"):
            flat = {}
            for key in data.keys():
                values = data.getlist(key)
                flat[key] = values if len(values) > 1 else values[0]

            # <field>_json -> parsed python value on <field>
            for key in list(flat.keys()):
                if not key.endswith("_json"):
                    continue
                base = key[: -len("_json")]
                raw = flat.pop(key)
                try:
                    parsed = json.loads(raw) if isinstance(raw, str) else raw
                except (TypeError, ValueError):
                    parsed = []
                existing = flat.get(base)
                if base in self.multi_media_fields:
                    kept = [str(x) for x in parsed if x] if isinstance(parsed, list) else []
                    files = existing if isinstance(existing, list) else ([existing] if existing else [])
                    files = [f for f in files if hasattr(f, "read")]
                    flat[base] = [*kept, *[self._store_file(f) for f in files]]
                else:
                    flat[base] = parsed

            # plain JSON strings for list/dict fields
            for name in JSON_LIST_FIELDS:
                value = flat.get(name)
                if isinstance(value, str) and value.strip().startswith(("[", "{")):
                    try:
                        flat[name] = json.loads(value)
                    except ValueError:
                        pass

            # uploaded files
            for src, dest in self.image_pairs:
                value = flat.get(src)
                if hasattr(value, "read"):
                    flat[dest] = value
                    flat.pop(src, None)

            for field in self.multi_media_fields:
                value = flat.get(field)
                if value is None:
                    continue
                values = value if isinstance(value, list) else [value]
                files = [v for v in values if hasattr(v, "read")]
                kept = [v for v in values if isinstance(v, str) and v]
                flat[field] = [*kept, *[self._store_file(f) for f in files]]

            data = flat

        for field in self.multi_media_fields:
            if isinstance(data, dict) and isinstance(data.get(field), list):
                stored = []
                for v in data[field]:
                    stored.append(self._store_file(v) if hasattr(v, "read") else v)
                self._multi_media[field] = [v for v in stored if v]
                data = {k: v for k, v in data.items() if k != field}
        return super().to_internal_value(data)

    def _apply(self, validated_data):
        validated_data.update(getattr(self, "_multi_media", {}) or {})
        return validated_data

    def create(self, validated_data):
        return super().create(self._apply(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._apply(validated_data))

    # ---- read ----
    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for src, dest in self.image_pairs:
            file_field = getattr(instance, dest, None)
            if file_field:
                try:
                    rep[src] = self._abs(file_field.url)
                except ValueError:
                    pass
            if src in rep:
                rep[src] = self._abs(rep.get(src) or "")
            rep.pop(dest, None)
        first = self.image_pairs[0][0]
        rep["image_url"] = rep.get(first, "") or ""
        for field in (*self.multi_media_fields, "images", "videos"):
            if isinstance(rep.get(field), list):
                rep[field] = [self._abs(u) for u in rep[field] if u]
        return rep


class AutoSlugMixin:
    """Generate a unique slug from the given source field when none is sent."""
    slug_source = "title"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if "slug" in self.fields and not attrs.get("slug") and self.instance is None:
            base = slugify(str(attrs.get(self.slug_source) or "item"))[:120] or "item"
            model = self.Meta.model
            slug, i = base, 2
            while model.objects.filter(slug=slug).exists():
                slug = f"{base}-{i}"
                i += 1
            attrs["slug"] = slug
        return attrs


class ContentSerializer(AutoSlugMixin, MediaSerializerMixin, serializers.ModelSerializer):
    class Meta:
        abstract = True


class PackageSerializer(ContentSerializer):
    slug_source = "title"

    class Meta:
        model = Package
        fields = "__all__"
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class ActivitySerializer(ContentSerializer):
    slug_source = "title"

    class Meta:
        model = Activity
        fields = "__all__"
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class VisaSerializer(ContentSerializer):
    slug_source = "destination"
    image_pairs = (("image", "image_file"), ("flag", "flag_file"))

    class Meta:
        model = Visa
        fields = "__all__"
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


class HotelSerializer(ContentSerializer):
    slug_source = "name"

    class Meta:
        model = Hotel
        fields = "__all__"
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def validate_stars(self, v):
        if v and not 1 <= v <= 5:
            raise serializers.ValidationError("Stars must be between 1 and 5.")
        return v


class DealSerializer(ContentSerializer):
    slug_source = "title"

    class Meta:
        model = Deal
        fields = "__all__"
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def validate(self, attrs):
        attrs = super().validate(attrs)
        price = attrs.get("price", getattr(self.instance, "price", None))
        offer = attrs.get("offer_price", getattr(self.instance, "offer_price", None))
        if price is not None and offer:
            if Decimal(offer) > Decimal(price):
                raise serializers.ValidationError({"offer_price": "Offer price must be <= price."})
        return attrs


class GalleryItemSerializer(MediaSerializerMixin, serializers.ModelSerializer):
    multi_media_fields = ("gallery_images", "images", "videos")

    # `kind` is derived from the uploaded media — the admin UI no longer sends it,
    # and any legacy value is normalised instead of rejected.
    kind = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = GalleryItem
        fields = "__all__"

    def validate_kind(self, value):
        return "video" if str(value).lower().startswith("video") else "image"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        data = self.initial_data
        if not attrs.get("kind"):
            has_video = bool(data.get("video_url")) or bool(data.get("videos")) or bool(data.get("videos_json"))
            attrs["kind"] = "video" if has_video else "image"
        return attrs



class TestimonialSerializer(MediaSerializerMixin, serializers.ModelSerializer):
    image_pairs = (("avatar", "avatar_file"),)
    multi_media_fields = ()

    class Meta:
        model = Testimonial
        fields = "__all__"


class HomeHeroSlideSerializer(MediaSerializerMixin, serializers.ModelSerializer):
    class Meta:
        model = HomeHeroSlide
        fields = "__all__"


class HomeGallerySliderSerializer(MediaSerializerMixin, serializers.ModelSerializer):
    multi_media_fields = ("gallery_images", "images")

    class Meta:
        model = HomeGallerySlider
        fields = "__all__"


class BookingSerializer(serializers.ModelSerializer):
    """Accepts the aliases the public website sends (amount / item_id)."""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, write_only=True,
                                      required=False, min_value=Decimal("0"))
    item_id = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Booking
        fields = "__all__"
        read_only_fields = ("reference",)
        extra_kwargs = {"total_amount": {"required": False}}

    def validate(self, attrs):
        amount = attrs.pop("amount", None)
        item_id = attrs.pop("item_id", "")
        if amount is not None and not attrs.get("total_amount"):
            attrs["total_amount"] = amount
        if item_id and not attrs.get("item_slug"):
            attrs["item_slug"] = item_id
        if attrs.get("pax") is not None and attrs["pax"] < 1:
            raise serializers.ValidationError({"pax": "Pax must be >= 1."})
        return attrs


class EnquirySerializer(serializers.ModelSerializer):
    """Public create + admin manage. Delivery fields are server-controlled."""
    website = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Enquiry
        fields = "__all__"
        read_only_fields = ("google_form_sent", "email_sent", "whatsapp_url",
                            "delivery_log", "ip_address")
        extra_kwargs = {"channel": {"required": False}}

    def validate_name(self, v):
        v = (v or "").strip()
        if len(v) < 2:
            raise serializers.ValidationError("Please enter your name.")
        return v

    def validate_message(self, v):
        if v and len(v) > 2000:
            raise serializers.ValidationError("Message must be under 2000 characters.")
        return v

    def validate_channel(self, v):
        v = (v or "").strip().lower().replace("-", "_").replace(" ", "_")
        alias = {"whats_app": EnquiryChannel.WHATSAPP, "wa": EnquiryChannel.WHATSAPP,
                 "googleform": EnquiryChannel.GOOGLE_FORM, "gform": EnquiryChannel.GOOGLE_FORM,
                 "web": EnquiryChannel.FORM, "website": EnquiryChannel.FORM}
        v = alias.get(v, v)
        return v if v in EnquiryChannel.values else EnquiryChannel.FORM

    def validate(self, attrs):
        if attrs.pop("website", ""):
            raise serializers.ValidationError("Submission rejected.")
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Provide email or phone.")

        item_type = (attrs.get("item_type") or "").strip().lower()
        source = (attrs.get("source") or "").strip().lower()
        attrs["item_type"] = item_type
        attrs["source"] = source or (f"deal {item_type}".strip() if item_type == "deal" else item_type or "home")

        # Visa + "request a call back" (assistance) enquiries go to WhatsApp.
        is_visa = bool(attrs.get("is_visa")) or item_type == "visa" or source.endswith("visa")
        to_whatsapp = is_visa or source == "assistance"
        attrs["is_visa"] = is_visa
        attrs["channel"] = EnquiryChannel.WHATSAPP if to_whatsapp else (
            attrs.get("channel") or EnquiryChannel.GOOGLE_FORM
        )
        if self.instance is None:
            attrs["status"] = EnquiryStatus.NEW
        return attrs


class ContactMessageSerializer(serializers.ModelSerializer):
    website = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = ContactMessage
        fields = "__all__"
        read_only_fields = ("email_sent", "google_form_sent", "delivery_log", "ip_address")

    def validate_message(self, v):
        if v and len(v) > 4000:
            raise serializers.ValidationError("Message must be under 4000 characters.")
        return v

    def validate(self, attrs):
        if attrs.pop("website", ""):
            raise serializers.ValidationError("Submission rejected.")
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Provide an email address or a phone number.")
        return attrs


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"


class PaymentLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLink
        fields = "__all__"
        read_only_fields = ("payment_link", "status", "raw", "reference")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "is_staff", "is_superuser")
