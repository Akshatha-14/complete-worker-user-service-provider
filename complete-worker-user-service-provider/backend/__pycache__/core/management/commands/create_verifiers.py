from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from core.models import AuthenticatedUser, UserRole


class Command(BaseCommand):
    help = "Create or update verifier accounts (verifier1, verifier2, verifier3)"

    def handle(self, *args, **options):
        verifiers = [
            ("verifier1@gmail.com", "123456!@", "verifier1"),
            ("verifier2@gmail.com", "123456!@", "verifier2"),
            ("verifier3@gmail.com", "123456!@", "verifier3"),
        ]

        for email, password, role_name in verifiers:
            user, created = AuthenticatedUser.objects.get_or_create(
                email=email,
                defaults={
                    "name": email.split("@")[0],
                    "phone": "0000000000",
                    "password": make_password(password),
                    "is_active": True,
                    "is_staff": False,
                },
            )

            if not created:
                user.password = make_password(password)
                user.is_active = True
                user.save()
                self.stdout.write(self.style.WARNING(f"Updated existing user: {email}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"Created new user: {email}"))

            UserRole.objects.get_or_create(user=user, role=role_name)
            self.stdout.write(f" → Assigned role: {role_name}\n")

        self.stdout.write(self.style.SUCCESS("✅ All verifier accounts are ready!"))
