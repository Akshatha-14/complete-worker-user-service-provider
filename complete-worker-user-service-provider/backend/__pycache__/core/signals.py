from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import UserReview

@receiver([post_save, post_delete], sender=UserReview)
def update_worker_avg_rating(sender, instance, **kwargs):
    """Keep worker's average rating and review count updated whenever reviews change"""
    if instance.worker:
        instance.worker.update_average_rating()
        
from django.db.models.signals import post_save
from django.dispatch import receiver
from core.models import WorkerApplication, Verifier3Review

@receiver(post_save, sender=WorkerApplication)
def ensure_verifier3_review(sender, instance, created, **kwargs):
    # Trigger only when application is at stage3_review
    if instance.current_stage == 3 and instance.application_status == 'stage3_review':
        # Create Verifier3Review if absent
        Verifier3Review.objects.get_or_create(application=instance)
