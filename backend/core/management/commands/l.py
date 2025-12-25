from django.core.management.base import BaseCommand
from core.models import UserRole

class Command(BaseCommand):
    help = "Switch 5000 users with customer role to worker role"

    def handle(self, *args, **kwargs):
        # Fetch customer roles
        customer_roles = UserRole.objects.filter(role="customer")[:5000]  # Limit to 5000
        total_customers = customer_roles.count()

        if total_customers == 0:
            self.stdout.write(self.style.WARNING("No customer roles found to update."))
            return

        # Bulk update selected customers to worker
        updated_count = 0
        for user_role in customer_roles:
            user_role.role = "worker"
            user_role.save()
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully switched {updated_count} users from customer -> worker role!"
        ))
