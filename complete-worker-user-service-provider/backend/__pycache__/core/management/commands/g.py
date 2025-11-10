import numpy as np
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Worker, Service, UserWorkerData

class Command(BaseCommand):
    help = "Populate user-worker dataset with enhanced distance feature"

    def handle(self, *args, **kwargs):
        User = get_user_model()
        updated_count = 0

        def haversine(lat1, lon1, lat2, lon2):
            """Calculate Haversine distance in km"""
            R = 6371.0
            dlat = np.radians(lat2 - lat1)
            dlon = np.radians(lon2 - lon1)
            a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
            return R * c

        for uw in UserWorkerData.objects.select_related('user', 'worker', 'service').all():
            user = uw.user
            worker = uw.worker
            service = uw.service

            if not user or not worker:
                continue

            # Extract lat/lon
            if user.location and worker.location:
                user_lat, user_lon = user.location.y, user.location.x
                worker_lat, worker_lon = worker.location.y, worker.location.x

                distance = haversine(user_lat, user_lon, worker_lat, worker_lon)
                uw.distance_km = distance

                # Distance bucket
                if distance <= 1:
                    uw.distance_bucket = 0
                elif distance <= 3:
                    uw.distance_bucket = 1
                elif distance <= 10:
                    uw.distance_bucket = 2
                else:
                    uw.distance_bucket = 3

                # Scaled distance for ML: closer = higher value
                uw.distance_km_scaled = 1 / (1 + distance)  # ✅ closer workers get higher value

                # Optional: exponential decay to emphasize short distances more
                uw.distance_km_exp = np.exp(-distance / 3)  # decay factor can be tuned

            else:
                uw.distance_km = None
                uw.distance_bucket = None
                uw.distance_km_scaled = 0
                uw.distance_km_exp = 0

            # Service match
            past_services = set(UserWorkerData.objects.filter(user=user).values_list('service', flat=True))
            uw.service_match = 1 if service.id in past_services else 0

            # Rounded total rating (0-5)
            uw.total_rating_int = round(worker.average_rating) if worker.average_rating is not None else 0
            uw.total_rating_int = max(0, min(5, uw.total_rating_int))

            uw.save()
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Updated {updated_count} rows in UserWorkerData"))
