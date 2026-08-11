"""Seed a small demo dataset: `python manage.py seed_demo`."""
from django.core.management.base import BaseCommand

from api.models import (
    Package, Deal, Hotel, Activity, Visa, GalleryItem, Testimonial,
    HomeHeroSlide, HomeGallerySlider,
)


class Command(BaseCommand):
    help = "Create a handful of demo rows for every public resource."

    def handle(self, *args, **options):
        Package.objects.get_or_create(
            slug="dubai-city-break",
            defaults=dict(
                title="Dubai City Break", destination="Dubai", duration="4 Nights / 5 Days",
                price=2499, short_description="City tour, desert safari and Burj Khalifa.",
                overview="A compact Dubai holiday covering the icons of the city.",
                highlights=["Burj Khalifa", "Desert safari", "Dhow cruise"],
                inclusions_included=["Hotel", "Breakfast", "Transfers"],
                inclusions_not_included=["Flights", "Visa"],
                itinerary=[{"title": "Arrival", "description": "Airport pickup and check-in."}],
                terms=["Prices are per person", "Subject to availability"],
                show_on_home=True,
            ),
        )
        Visa.objects.get_or_create(
            slug="uae-tourist-visa",
            defaults=dict(
                destination="United Arab Emirates", visa_type="Tourist e-Visa",
                processing_days="3-5 working days", validity="60 days", price=350,
                short_description="Fast UAE tourist visa processing.",
                documents_required=["Passport copy", "Photograph"],
                eligibility=["Valid passport for 6 months"],
                terms=["Non-refundable once submitted"], show_on_home=True,
            ),
        )
        Hotel.objects.get_or_create(
            slug="palm-beach-resort",
            defaults=dict(
                name="Palm Beach Resort", location="Palm Jumeirah", destination="Dubai",
                price=780, stars=5, short_description="Beachfront resort on the Palm.",
                amenities=["Private beach", "Spa", "Pool"],
                policies=["Check-in 3 PM"], show_on_home=True,
            ),
        )
        Activity.objects.get_or_create(
            slug="desert-safari",
            defaults=dict(
                title="Evening Desert Safari", destination="Dubai", duration="6 hours",
                price=180, short_description="Dune bashing, camel ride and BBQ dinner.",
                activity_packages=[{"title": "Standard", "description": "Shared 4x4", "price": 180}],
                highlights=["Dune bashing", "Live shows"], show_on_home=True,
            ),
        )
        Deal.objects.get_or_create(
            slug="summer-dubai-deal",
            defaults=dict(
                title="Summer Dubai Deal", category="package", destination="Dubai",
                price=2999, offer_price=2199, offer_percentage=27,
                short_description="Limited-period family package offer.",
                show_on_home=True,
            ),
        )
        Testimonial.objects.get_or_create(
            title="Perfect family holiday",
            defaults=dict(description="Everything was organised end to end. Highly recommended!"),
        )
        GalleryItem.objects.get_or_create(title="Dubai Skyline", defaults=dict(kind="image", place="Dubai"))
        HomeHeroSlide.objects.get_or_create(
            title="Discover the world with us",
            defaults=dict(name="Circuit Travel", button_text="Explore packages", button_link="/packages"),
        )
        HomeGallerySlider.objects.get_or_create(title="Home poster strip")
        self.stdout.write(self.style.SUCCESS("Demo data ready."))
