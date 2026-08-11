from django_filters import rest_framework as filters
from .models import Package, Deal, Hotel, Activity, Visa, GalleryItem, Booking, Enquiry


class PackageFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Package
        fields = ["is_active", "show_on_home", "destination", "slug"]


class DealFilter(filters.FilterSet):
    class Meta:
        model = Deal
        fields = ["is_active", "show_on_home", "category", "destination", "slug"]


class HotelFilter(filters.FilterSet):
    min_price = filters.NumberFilter(field_name="price", lookup_expr="gte")
    max_price = filters.NumberFilter(field_name="price", lookup_expr="lte")

    class Meta:
        model = Hotel
        fields = ["is_active", "show_on_home", "destination", "location", "stars", "slug"]


class ActivityFilter(filters.FilterSet):
    class Meta:
        model = Activity
        fields = ["is_active", "show_on_home", "destination", "slug"]


class VisaFilter(filters.FilterSet):
    class Meta:
        model = Visa
        fields = ["is_active", "show_on_home", "destination", "visa_type", "slug"]


class GalleryFilter(filters.FilterSet):
    class Meta:
        model = GalleryItem
        fields = ["kind", "show_on_home", "is_active"]


class BookingFilter(filters.FilterSet):
    class Meta:
        model = Booking
        fields = ["status", "item_type", "payment_status"]


class EnquiryFilter(filters.FilterSet):
    class Meta:
        model = Enquiry
        fields = ["status", "channel", "is_visa", "item_type", "source", "service"]
