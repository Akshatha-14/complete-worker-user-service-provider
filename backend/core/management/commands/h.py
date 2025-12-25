from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from faker import Faker
import random
from core.models import AuthenticatedUser, Worker, Service, Booking, WorkerEarning, UserReview

class Command(BaseCommand):
    help = "Generate random bookings, worker earnings, and ratings"

    def handle(self, *args, **kwargs):
        fake = Faker()
        TOTAL_BOOKINGS = 50  # adjust as needed

        users = list(AuthenticatedUser.objects.all())
        workers = list(Worker.objects.all())
        services = list(Service.objects.all())

        if not users or not workers or not services:
            self.stdout.write(self.style.ERROR("Users, workers, or services are missing!"))
            return

        for _ in range(TOTAL_BOOKINGS):
            user = random.choice(users)
            worker = random.choice(workers)
            service = random.choice(services)

            # Random job location
            latitude = float(fake.latitude())
            longitude = float(fake.longitude())
            job_location = Point(longitude, latitude)

            # Create booking
            booking = Booking.objects.create(
                user=user,
                worker=worker,
                service=service,
                job_location=job_location,
                tariff_coins=random.randint(100, 500),
                status=random.choice(['booked', 'in_progress', 'completed']),
                payment_status=random.choice(['pending', 'paid', 'failed']),
                payment_method=random.choice(['coins', 'cod', 'online']),
                total=random.randint(100, 500),
                details=fake.sentence()
            )

            # Random rating (if booking completed)
            rating_value = None
            if booking.status == 'completed':
                rating_value = random.randint(1, 5)
                UserReview.objects.create(
                    user=user,
                    worker=worker,
                    booking=booking,
                    rating=rating_value
                )

            # Create WorkerEarning safely
            if not WorkerEarning.objects.filter(booking=booking).exists():
                WorkerEarning.objects.create(
                    worker=worker,
                    booking=booking,
                    amount=random.randint(50, 500),
                    user_review=UserReview.objects.filter(booking=booking).first()  # attach review if exists
                )

            self.stdout.write(self.style.SUCCESS(f"Created booking #{booking.id} with worker {worker.worker_name}"))

        self.stdout.write(self.style.SUCCESS("Data generation complete!"))
