"""ModelViewSets for every resource."""
import logging
import uuid

from django.core.files.storage import default_storage
from rest_framework import viewsets
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .filters import (
    PackageFilter, DealFilter, HotelFilter, ActivityFilter,
    VisaFilter, GalleryFilter, BookingFilter, EnquiryFilter,
)
from .models import (
    Package, Deal, Hotel, Activity, Visa, GalleryItem, Testimonial,
    Booking, Enquiry, Payment, SiteSetting, ContactMessage, PaymentLink,
    HomeHeroSlide, HomeGallerySlider,
)
from .notifications import (
    deliver_enquiry, deliver_contact_message, prepare_enquiry, run_in_background,
)
from rest_framework import permissions
from .permissions import IsAdminOrReadOnly, PublicCreateReadAdminWrite, IsAdmin
from .serializers import (
    PackageSerializer, DealSerializer, HotelSerializer, ActivitySerializer,
    VisaSerializer, GalleryItemSerializer, TestimonialSerializer,
    BookingSerializer, EnquirySerializer, PaymentSerializer, SiteSettingSerializer,
    ContactMessageSerializer, PaymentLinkSerializer,
    HomeHeroSlideSerializer, HomeGallerySliderSerializer,
)
from .constants import PaymentStatus

logger = logging.getLogger(__name__)


class SlugLookupMixin:
    """Look up by slug when the URL segment is not numeric."""
    def get_object(self):
        lookup = self.kwargs.get(self.lookup_field or "pk")
        qs = self.filter_queryset(self.get_queryset())
        model = qs.model
        if lookup and not str(lookup).isdigit() and any(f.name == "slug" for f in model._meta.fields):
            obj = qs.filter(slug=lookup).first()
            if obj:
                self.check_object_permissions(self.request, obj)
                return obj
        return super().get_object()


class BaseContentViewSet(SlugLookupMixin, viewsets.ModelViewSet):
    """Public content: anonymous visitors can always READ (no login needed).

    Read requests are exempt from throttling so a busy landing page that hits
    many endpoints at once never gets 429s for logged-out visitors.
    """
    permission_classes = [IsAdminOrReadOnly]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_throttles(self):
        if self.request and self.request.method in permissions.SAFE_METHODS:
            return []
        return super().get_throttles()


class UploadView(APIView):
    """POST a file (multipart, field name ``file``) -> {"url": "<absolute url>"}."""
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        files = request.FILES.getlist("file") or request.FILES.getlist("files")
        if not files:
            return Response({"detail": "No file provided (field name: file)."}, status=400)
        urls = []
        for f in files:
            path = default_storage.save(f"uploads/direct/{uuid.uuid4().hex[:12]}_{f.name}", f)
            urls.append(request.build_absolute_uri(default_storage.url(path)))
        return Response({"url": urls[0], "urls": urls}, status=201)


class PackageViewSet(BaseContentViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    filterset_class = PackageFilter
    search_fields = ["title", "destination", "slug", "short_description"]
    ordering_fields = ["price", "created_at", "title"]


class ActivityViewSet(BaseContentViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    filterset_class = ActivityFilter
    search_fields = ["title", "destination", "slug"]
    ordering_fields = ["price", "created_at", "title"]


class VisaViewSet(BaseContentViewSet):
    queryset = Visa.objects.all()
    serializer_class = VisaSerializer
    filterset_class = VisaFilter
    search_fields = ["destination", "visa_type", "slug"]
    ordering_fields = ["price", "destination", "created_at"]


class HotelViewSet(BaseContentViewSet):
    queryset = Hotel.objects.all()
    serializer_class = HotelSerializer
    filterset_class = HotelFilter
    search_fields = ["name", "location", "destination", "slug"]
    ordering_fields = ["price", "stars", "created_at"]


class DealViewSet(BaseContentViewSet):
    queryset = Deal.objects.all()
    serializer_class = DealSerializer
    filterset_class = DealFilter
    search_fields = ["title", "slug", "category", "destination"]
    ordering_fields = ["price", "offer_price", "created_at"]


class GalleryViewSet(BaseContentViewSet):
    queryset = GalleryItem.objects.all()
    serializer_class = GalleryItemSerializer
    filterset_class = GalleryFilter
    search_fields = ["title", "place"]
    ordering_fields = ["created_at"]


class TestimonialViewSet(BaseContentViewSet):
    queryset = Testimonial.objects.all()
    serializer_class = TestimonialSerializer
    search_fields = ["title", "description"]
    ordering_fields = ["order", "created_at"]
    filterset_fields = ["is_active"]


class HomeHeroSlideViewSet(BaseContentViewSet):
    queryset = HomeHeroSlide.objects.all()
    serializer_class = HomeHeroSlideSerializer
    search_fields = ["title", "name"]
    ordering_fields = ["order", "created_at"]
    filterset_fields = ["is_active"]


class HomeGallerySliderViewSet(BaseContentViewSet):
    queryset = HomeGallerySlider.objects.all()
    serializer_class = HomeGallerySliderSerializer
    search_fields = ["title"]
    ordering_fields = ["created_at"]
    filterset_fields = ["is_active"]


class SiteSettingViewSet(viewsets.ModelViewSet):
    queryset = SiteSetting.objects.all()
    serializer_class = SiteSettingSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "key"
    search_fields = ["key", "label"]


class BookingViewSet(viewsets.ModelViewSet):
    """Public may POST (create booking); admin manages the rest."""
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [PublicCreateReadAdminWrite]
    filterset_class = BookingFilter
    search_fields = ["reference", "customer_name", "customer_email", "item_title"]
    ordering_fields = ["created_at", "total_amount"]


def _client_ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class EnquiryViewSet(viewsets.ModelViewSet):
    """
    Public POST /api/enquiries/ — stored in PostgreSQL, then delivered:
      * visa or "request a call back" -> WhatsApp deep link (`whatsapp_url`)
      * everything else               -> Google Form (+ optional email)
    """
    queryset = Enquiry.objects.all()
    serializer_class = EnquirySerializer
    permission_classes = [PublicCreateReadAdminWrite]
    filterset_class = EnquiryFilter
    search_fields = ["name", "email", "phone", "item_title", "message", "service"]
    ordering_fields = ["created_at"]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "public_form"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer):
        enquiry = serializer.save(ip_address=_client_ip(self.request))
        try:
            prepare_enquiry(enquiry)
        except Exception:
            logger.exception("Enquiry link build failed for %s", enquiry.pk)
        run_in_background(deliver_enquiry, enquiry)


class ContactMessageViewSet(viewsets.ModelViewSet):
    """Public POST from the contact form -> PostgreSQL + Gmail + Google Form."""
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [PublicCreateReadAdminWrite]
    search_fields = ["name", "email", "phone", "message", "service"]
    ordering_fields = ["created_at"]
    filterset_fields = ["handled", "service"]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "public_form"
            return [ScopedRateThrottle()]
        return super().get_throttles()

    def perform_create(self, serializer):
        msg = serializer.save(ip_address=_client_ip(self.request))
        run_in_background(deliver_contact_message, msg)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("booking").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAdmin]
    search_fields = ["provider_reference", "session_id", "booking__reference"]
    ordering_fields = ["created_at", "amount"]
    filterset_fields = ["status", "provider", "currency"]


class PaymentLinkViewSet(viewsets.ModelViewSet):
    """Generate + list Adyen payment links. Records are immutable (no update)."""
    queryset = PaymentLink.objects.all()
    serializer_class = PaymentLinkSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "delete", "head", "options"]
    search_fields = ["reference", "customer_name", "customer_email", "description"]
    ordering_fields = ["created_at", "amount"]
    filterset_fields = ["status", "currency"]

    def perform_create(self, serializer):
        reference = f"PL-{uuid.uuid4().hex[:10].upper()}"
        url, raw = "", {}
        try:
            from payments import adyen_client
            raw = adyen_client.create_pay_by_link(
                reference=reference,
                amount=serializer.validated_data["amount"],
                currency=serializer.validated_data.get("currency", "AED"),
                description=serializer.validated_data.get("description") or reference,
                shopper_email=serializer.validated_data.get("customer_email", ""),
            )
            url = raw.get("url", "")
        except Exception as exc:  # Adyen not configured / network error
            raw = {"error": str(exc)}
        serializer.save(reference=reference, payment_link=url, raw=raw,
                        status=PaymentStatus.INITIATED)
