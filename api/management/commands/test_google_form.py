from django.core.management.base import BaseCommand, CommandError

from api.notifications import post_to_google_form


class Command(BaseCommand):
    help = "Validate Google Form configuration and optionally submit a test response."

    def add_arguments(self, parser):
        parser.add_argument("--send", action="store_true", help="Send a real test response")

    def handle(self, *args, **options):
        from django.conf import settings

        configured = {key: value for key, value in settings.GOOGLE_FORM_ENTRIES.items() if value}
        if not settings.GOOGLE_FORM_ID:
            raise CommandError("GOOGLE_FORM_ID is empty in .env")
        if not configured:
            raise CommandError("No GOOGLE_FORM_ENTRY_* fields are configured")

        self.stdout.write(f"Configured logical fields: {', '.join(sorted(configured))}")
        if not options["send"]:
            self.stdout.write(self.style.WARNING("Configuration loaded. Add --send to submit a test."))
            return

        result = post_to_google_form({
            "name": "Django delivery test",
            "email": "test@example.com",
            "phone": "+971500000000",
            "message": "Submitted by python manage.py test_google_form --send",
            "type": "diagnostic",
            "item_title": "Backend test",
            "item_type": "diagnostic",
        })
        if not result.get("ok"):
            raise CommandError(f"Submission failed: {result}")
        self.stdout.write(self.style.SUCCESS(f"Google Form accepted the test: {result}"))