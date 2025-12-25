from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Worker, WorkerApplication, Verifier1Review, Verifier2Review, Verifier3Review, Service, WorkerService

class Command(BaseCommand):
    help = "Create WorkerApplications for existing Workers and mark them fully verified by all verifiers"

    def handle(self, *args, **kwargs):
        workers = Worker.objects.all()
        self.stdout.write(f"Found {workers.count()} workers.\n")

        for worker in workers:
            # Skip if worker already has an assigned application
            if worker.application:
                self.stdout.write(f"Worker {worker.worker_name} already has application, skipping.\n")
                continue

            user = worker.user

            # Create WorkerApplication
            app = WorkerApplication.objects.create(
                name=user.name,
                email=user.email,
                phone=user.phone,
                address=worker.address,
                location=worker.location,
                experience=str(worker.experience_years),
                service_categories=[ws.service.service_type for ws in worker.services.all()],
                stage1_completed=True,
                stage2_completed=True,
                stage3_completed=True,
                current_stage=3,
                application_status='approved',
                is_fully_verified=True,
                assigned_worker=worker,
                approved_at=timezone.now()
            )

            # Stage 1 verification
            Verifier1Review.objects.create(
                application=app,
                status='approved',
                all_documents_uploaded=True,
                documents_legible=True,
                correct_format=True,
                no_missing_fields=True,
                files_not_corrupted=True,
                expiry_dates_valid=True,
                reviewed_at=timezone.now(),
                is_submitted=True,
                submitted_at=timezone.now()
            )

            # Stage 2 verification
            Verifier2Review.objects.create(
                application=app,
                status='approved',
                photo_matches_id=True,
                aadhaar_verified=True,
                dob_verified=True,
                address_verified=True,
                phone_verified=True,
                email_verified=True,
                union_membership_verified=True,
                reviewed_at=timezone.now(),
                is_submitted=True,
                submitted_at=timezone.now()
            )

            # Stage 3 verification
            Verifier3Review.objects.create(
                application=app,
                status='approved',
                location_verified=True,
                skill_verified=True,
                previous_stages_verified=True,
                policy_compliance_checked=True,
                spot_check_performed=True,
                background_check_passed=True,
                reviewed_at=timezone.now(),
                is_submitted=True,
                submitted_at=timezone.now()
            )

            # Link back to Worker
            worker.application = app
            worker.save(update_fields=['application'])

            self.stdout.write(self.style.SUCCESS(f"Created and fully verified application for worker {worker.worker_name}"))

        self.stdout.write(self.style.SUCCESS("All workers processed successfully."))
