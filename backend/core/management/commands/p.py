import random
import re
from django.core.management.base import BaseCommand
from core.models import Worker

class Command(BaseCommand):
    help = "Replace worker user names containing numbers with unique readable names (FirstName + Initial, non-repeating)."

    def handle(self, *args, **options):
        # Possible first names and initials
        first_names = [
            "Aarav", "Vihaan", "Aditya", "Arjun", "Kabir", "Rohan", "Ishaan", "Reyansh", "Arnav", "Dhruv",
            "Ananya", "Diya", "Aadhya", "Kiara", "Anika", "Meera", "Pooja", "Simran", "Priya", "Ritika",
            "Aditi", "Shruti", "Sia", "Myra", "Tara", "Sanjana", "Riya", "Lavanya", "Sneha", "Divya"
        ]
        initials = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

        pattern = re.compile(r'\d')

        # Access worker.user.name
        workers_to_fix = Worker.objects.filter(user__name__regex=r'\d')
        total = workers_to_fix.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS("✅ No workers with numeric names found."))
            return

        # Collect all existing user names to avoid duplicates
        existing_names = set(Worker.objects.values_list("user__name", flat=True))
        used_names = set()
        all_possible_names = [f"{f} {i}." for f in first_names for i in initials]
        random.shuffle(all_possible_names)

        updated_count = 0

        for worker in workers_to_fix.iterator():
            user = worker.user
            new_name = None

            while all_possible_names:
                candidate = all_possible_names.pop(0)
                if candidate not in existing_names and candidate not in used_names:
                    new_name = candidate
                    used_names.add(candidate)
                    break

            if not new_name:
                self.stdout.write(self.style.WARNING("⚠️ Ran out of unique names!"))
                break

            old_name = user.name
            user.name = new_name
            user.save(update_fields=["name"])

            updated_count += 1
            self.stdout.write(f"🔁 {updated_count}/{total}: '{old_name}' → '{new_name}'")

        self.stdout.write(self.style.SUCCESS(f"✅ Successfully updated {updated_count} worker names."))
