from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import (
    PackageViewSet, DealViewSet, HotelViewSet, ActivityViewSet, VisaViewSet,
    GalleryViewSet, TestimonialViewSet, BookingViewSet,
    EnquiryViewSet, PaymentViewSet, SiteSettingViewSet,
    HomeHeroSlideViewSet, HomeGallerySliderViewSet,
    ContactMessageViewSet, PaymentLinkViewSet, UploadView,
)

router = DefaultRouter()
router.register(r"packages", PackageViewSet)
router.register(r"deals", DealViewSet)
router.register(r"hotels", HotelViewSet)
router.register(r"activities", ActivityViewSet)
router.register(r"visas", VisaViewSet)
router.register(r"gallery", GalleryViewSet)
router.register(r"testimonials", TestimonialViewSet)
router.register(r"bookings", BookingViewSet)
router.register(r"enquiries", EnquiryViewSet)
# Keep the legacy URL for existing clients and expose the canonical endpoint
# used by the admin panel. Explicit basenames avoid DRF router collisions.
router.register(r"payments", PaymentViewSet, basename="payment")
router.register(r"payments-log", PaymentViewSet, basename="payment-log")
router.register(r"settings", SiteSettingViewSet)
router.register(r"home-hero-slider", HomeHeroSlideViewSet)
router.register(r"home-gallery-slider", HomeGallerySliderViewSet)
router.register(r"contacts", ContactMessageViewSet)
router.register(r"payment-links", PaymentLinkViewSet)

urlpatterns = [
    path("uploads/", UploadView.as_view(), name="media-upload"),
    path("", include(router.urls)),
]
