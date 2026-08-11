from django.contrib import admin

from .models import (
    Package, Deal, Hotel, Activity, Visa, GalleryItem, Testimonial,
    Booking, Enquiry, Payment, SiteSetting, ContactMessage, PaymentLink,
    HomeHeroSlide, HomeGallerySlider,
)
from .notifications import deliver_enquiry, deliver_contact_message


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("title", "destination", "duration", "price", "show_on_home", "is_active")
    list_filter = ("show_on_home", "is_active")
    search_fields = ("title", "destination", "slug")


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("title", "destination", "duration", "price", "show_on_home", "is_active")
    list_filter = ("show_on_home", "is_active")
    search_fields = ("title", "destination", "slug")


@admin.register(Visa)
class VisaAdmin(admin.ModelAdmin):
    list_display = ("destination", "visa_type", "price", "show_on_home", "is_active")
    list_filter = ("show_on_home", "is_active")
    search_fields = ("destination", "visa_type", "slug")


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "destination", "price", "show_on_home", "is_active")
    list_filter = ("show_on_home", "is_active")
    search_fields = ("name", "location", "slug")


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "destination", "price", "offer_price", "show_on_home")
    list_filter = ("category", "show_on_home", "is_active")
    search_fields = ("title", "slug", "destination")


@admin.register(GalleryItem)
class GalleryItemAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "place", "show_on_home", "is_active")
    list_filter = ("kind", "show_on_home", "is_active")


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "order")


@admin.register(HomeHeroSlide)
class HomeHeroSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active")


@admin.register(HomeGallerySlider)
class HomeGallerySliderAdmin(admin.ModelAdmin):
    list_display = ("__str__", "is_active")


@admin.action(description="Re-send delivery (WhatsApp / Google Form / email)")
def resend_enquiries(modeladmin, request, queryset):
    for enquiry in queryset:
        deliver_enquiry(enquiry)


@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "item_type", "item_title", "phone", "email",
                    "channel", "status", "created_at")
    list_filter = ("source", "item_type", "channel", "status", "is_visa")
    search_fields = ("name", "email", "phone", "item_title", "message")
    actions = [resend_enquiries]


@admin.action(description="Re-send contact message")
def resend_contacts(modeladmin, request, queryset):
    for msg in queryset:
        deliver_contact_message(msg)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "service", "email", "phone", "handled", "created_at")
    list_filter = ("service", "handled")
    search_fields = ("name", "email", "phone", "message")
    actions = [resend_contacts]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "customer_name", "item_type", "item_title",
                    "total_amount", "status", "payment_status")
    list_filter = ("item_type", "status", "payment_status")
    search_fields = ("reference", "customer_name", "customer_email")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("provider_reference", "amount", "currency", "status", "created_at")
    list_filter = ("status", "provider")


@admin.register(PaymentLink)
class PaymentLinkAdmin(admin.ModelAdmin):
    list_display = ("reference", "customer_name", "amount", "currency", "status", "created_at")
    list_filter = ("status",)


admin.site.register([SiteSetting])
