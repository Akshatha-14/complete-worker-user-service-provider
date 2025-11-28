import random
import numpy as np
from django.core.management.base import BaseCommand
from core.models import UserWorkerData, AuthenticatedUser, Worker, Service
from django.contrib.gis.geos import Point

class Command(BaseCommand):
    help = "Generate full dataset with user/worker locations and varied distance-based relevance (0-5) for ML ranking."

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING("🧹 Deleting existing UserWorkerData records..."))
        UserWorkerData.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("✅ Existing data cleared."))

        users = list(AuthenticatedUser.objects.all())
        workers = list(Worker.objects.all())
        services = list(Service.objects.all())

        if not users or not workers or not services:
            self.stdout.write(self.style.ERROR("❌ Need users, workers, and services before populating data!"))
            return

        for user in users:
            if not hasattr(user, 'location') or user.location is None:
                lat = random.uniform(12.80, 13.05)
                lon = random.uniform(77.45, 77.75)
                user.location = Point(lon, lat)
                user.save()

        for worker in workers:
            if not hasattr(worker, 'worker_location') or worker.worker_location is None:
                lat = random.uniform(12.80, 13.05)
                lon = random.uniform(77.45, 77.75)
                worker.worker_location = Point(lon, lat)
                worker.save()

        def distance_km(p1, p2):
            lat1, lon1 = p1.y, p1.x
            lat2, lon2 = p2.y, p2.x
            R = 6371.0
            dlat = np.radians(lat2 - lat1)
            dlon = np.radians(lon2 - lon1)
            a = (np.sin(dlat / 2) ** 2 +
                 np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2)
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
            return R * c

        records = []
        seen_keys = set()
        rng = np.random.default_rng(seed=42)

        for user in users:
            user_loc = user.location
            user_preferred_service = random.choice(services)
            user_budget = random.randint(400, 1400)

            for _ in range(random.randint(20, 25)):
                worker = random.choice(workers)
                service = random.choice(services)
                key = (user.id, worker.id, service.id)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                worker_loc = worker.worker_location
                dist = distance_km(user_loc, worker_loc)

                base_relevance = max(0, 5 - dist / 3)
                service_bonus = 1.0 if service == user_preferred_service else 0.0
                budget_diff = abs(user_budget - random.randint(300, 2000))
                budget_factor = max(0, 1 - budget_diff / 2000)

                # Increased noise scale for more variance:
                noise = rng.normal(loc=0, scale=1.2)

                relevance_raw = base_relevance + service_bonus + budget_factor + noise

                # Clip relevance to 0-5 and round to 2 decimals:
                total_rating = round(min(max(relevance_raw, 0), 5), 2)

                # Add label flips and random shifts to reduce overfitting:
                if rng.random() < 0.2:  # 20% chance of shift
                    shift = rng.integers(-2, 3)  # -2 to +2 shift
                    total_rating = np.clip(total_rating + shift, 0, 5)

                # Add some randomness to number of bookings:
                num_bookings = max(0, int(total_rating * 15 + rng.integers(-7, 8)))

                record = UserWorkerData(
                    user=user,
                    worker=worker,
                    service=service,
                    worker_location=worker_loc,
                    service_name=service.service_type,
                    worker_experience=random.randint(1, 12),
                    charge=random.randint(300, 2000),
                    num_bookings=num_bookings,
                    total_rating=total_rating,
                    worker_latitude=worker_loc.y,
                    worker_longitude=worker_loc.x,
                )
                records.append(record)

        if records:
            UserWorkerData.objects.bulk_create(records, batch_size=500)
            self.stdout.write(self.style.SUCCESS(f"✅ Added {len(records)} UserWorkerData records with varied relevance labels!"))
        else:
            self.stdout.write(self.style.NOTICE("ℹ️ No records created."))

        self.stdout.write(self.style.SUCCESS("🎯 Dataset generation complete — ready for training with good label variance."))
