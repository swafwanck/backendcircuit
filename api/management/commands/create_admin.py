import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update the Django admin superuser"

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.getenv(
            "DJANGO_SUPERUSER_USERNAME",
            "circuits"
        )

        email = os.getenv(
            "DJANGO_SUPERUSER_EMAIL",
            ""
        )

        password = os.getenv(
            "DJANGO_SUPERUSER_PASSWORD",
            "circuits@123"
        )

        if not password:
            self.stdout.write(
                self.style.ERROR(
                    "DJANGO_SUPERUSER_PASSWORD is not configured."
                )
            )
            return

        user, created = User.objects.get_or_create(
            username=username,
        )

        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Superuser '{username}' created successfully."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Superuser '{username}' updated successfully."
                )
            )