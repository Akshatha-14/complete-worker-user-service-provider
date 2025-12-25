from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from core.models import (
    UserReview,
    WorkerApplication,
    Verifier3Review,
    Worker,
    WorkerService,
    Service,
    UserRole
)

# ---------------------------------------------------------
# 1. UPDATE WORKER AVG RATING WHEN REVIEWS CHANGE
# ---------------------------------------------------------
@receiver([post_save, post_delete], sender=UserReview)
def update_worker_avg_rating(sender, instance, **kwargs):
    """Keep worker's average rating updated whenever reviews change."""
    if instance.worker:
        instance.worker.update_average_rating()


# ---------------------------------------------------------
# 2. AUTOMATICALLY CREATE Verifier3Review WHEN STAGE 3 STARTS
# ---------------------------------------------------------
@receiver(post_save, sender=WorkerApplication)
def ensure_verifier3_review(sender, instance, created, **kwargs):
    """
    Creates a Verifier3Review ONLY when application reaches Stage 3.
    """
    if instance.current_stage == 3 and instance.application_status == "stage3_review":
        Verifier3Review.objects.get_or_create(application=instance)


# ---------------------------------------------------------
# 3. CREATE WORKER WHEN USER ROLE BECOMES 'worker'
# ---------------------------------------------------------
@receiver(post_save, sender=UserRole)
def create_worker_for_user(sender, instance, created, **kwargs):
    """Automatically create Worker profile when a user becomes a worker."""
    if instance.role != "worker":
        return

    user = instance.user

    # Prevent duplicates
    if hasattr(user, 'worker_profile'):
        return

    # Fetch application if exists
    application = getattr(user, "workerapplication", None)

    Worker.objects.create(
        user=user,
        application=application,
        address=getattr(application, "address", "") or getattr(user, "address", ""),
        location=getattr(application, "location", None) or getattr(user, "location", None),
        is_available=True,
        allows_cod=False,
        experience_years=getattr(application, "experience_years", 0),
    )


# ---------------------------------------------------------
# 4. CREATE WorkerService ONLY WHEN WORKER IS APPROVED
# ---------------------------------------------------------
@receiver(post_save, sender=WorkerApplication)
def create_worker_service_after_approval(sender, instance, created, **kwargs):
    if instance.application_status == 'approved' and instance.selected_service_category:

        # Ensure Worker exists
        worker = instance.assigned_worker
        if not worker:
            worker = Worker.objects.create(
                name=instance.name,
                phone=instance.phone
            )
            WorkerApplication.objects.filter(id=instance.id).update(assigned_worker=worker)

        # Ensure Service exists with required fields
        service_obj, _ = Service.objects.get_or_create(
            service_type=instance.selected_service_category,
            defaults={'base_coins_cost': instance.base_charge or 0}
        )

        # Link WorkerService
        WorkerService.objects.get_or_create(
            worker=worker,
            service=service_obj,
            defaults={'charge': instance.base_charge or 0}
        )
