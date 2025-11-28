from django.core.management.base import BaseCommand
from core.models import UserWorkerData
import csv
import os

class Command(BaseCommand):
    help = "Export UserWorkerData table to a CSV file"

    def handle(self, *args, **kwargs):
        # Define output path (same folder as manage.py)
        output_file = os.path.join(os.getcwd(), 'userworkerdata.csv')

        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                'id', 'user_id', 'worker_id', 'service_id', 'service_name',
                'worker_experience', 'charge', 'num_bookings', 'total_rating',
                'worker_latitude', 'worker_longitude'
            ])

            for obj in UserWorkerData.objects.select_related('user', 'worker', 'service'):
                writer.writerow([
                    obj.id,
                    obj.user.id,
                    obj.worker.id,
                    obj.service.id,
                    obj.service_name,
                    obj.worker_experience,
                    obj.charge,
                    obj.num_bookings,
                    obj.total_rating,
                    obj.worker_latitude,
                    obj.worker_longitude
                ])

        self.stdout.write(self.style.SUCCESS(f'✅ Export complete! File saved at: {output_file}'))
