from django.core.management.base import BaseCommand
from core.models import Worker, WorkerApplication, WorkerService, Service

class Command(BaseCommand):
    help = "Populate WorkerService table using WorkerApplication"

    def handle(self, *args, **options):
        workers = Worker.objects.all()
        self.stdout.write(f"Found {workers.count()} workers.\n")

        created = 0
        skipped = 0

        for worker in workers:
            # -------- FIXED HERE --------
            try:
                app = WorkerApplication.objects.get(assigned_worker=worker)
            except WorkerApplication.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"No application for worker {worker.worker_name}, skipping."
                ))
                skipped += 1
                continue

            # get service category
            service_name = app.selected_service_category

            if not service_name:
                if isinstance(app.service_categories, list) and app.service_categories:
                    service_name = app.service_categories[0]
                else:
                    self.stdout.write(self.style.ERROR(
                        f"Worker {worker.worker_name} has no service category!"
                    ))
                    skipped += 1
                    continue

            try:
                service_obj = Service.objects.get(service_type=service_name)
            except Service.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"Service '{service_name}' does not exist!"
                ))
                skipped += 1
                continue

            charge = app.base_charge if app.base_charge else 100

            if WorkerService.objects.filter(worker=worker, service=service_obj).exists():
                self.stdout.write(
                    f"Service already exists for {worker.worker_name}, skipping."
                )
                skipped += 1
                continue

            WorkerService.objects.create(
                worker=worker,
                service=service_obj,
                charge=charge
            )

            self.stdout.write(self.style.SUCCESS(
                f"Created WorkerService → {worker.worker_name} | {service_name} | {charge}"
            ))
            created += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nCompleted! Created={created}, Skipped={skipped}"
        ))
