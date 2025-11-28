from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.db import models as gis_models
from django.utils import timezone
from django.db.models import Avg, Count
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField
from django.db.models import Q
from django.contrib.gis.geos import Point
import requests
from decouple import config
import string
# ==============================
# User Management
# ==============================

class AuthenticatedUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class AuthenticatedUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    phone = PhoneNumberField(blank=True, default="", max_length=30)
    address = models.CharField(max_length=255, blank=True)
    location = gis_models.PointField(geography=True, null=True, blank=True)
    is_verifier = models.BooleanField(default=False)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    objects = AuthenticatedUserManager()

    def __str__(self):
        return self.name or self.email

    def is_profile_complete(self):
        return all([self.name, self.phone, self.address, self.location])

    @property
    def role(self):
        user_role, created = UserRole.objects.get_or_create(
            user=self,
            defaults={'role': 'customer'}
        )
        return user_role.role


class UserRole(models.Model):
    """Defines roles for users: customer, worker, admin, verifier."""
    user = models.ForeignKey(AuthenticatedUser, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField(max_length=16, choices=[
        ('customer', 'Customer'),
        ('worker', 'Worker'),
        ('admin', 'Admin'),
        ('verifier1', 'Verifier 1'),
        ('verifier2', 'Verifier 2'),
        ('verifier3', 'Verifier 3'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.email} - {self.role}"


# ==============================
# Services
# ==============================

class Service(models.Model):
    """Types of services offered (e.g., Plumbing, Cleaning) with base cost."""
    service_type = models.CharField(max_length=80)
    description = models.TextField()
    base_coins_cost = models.PositiveIntegerField()

    def __str__(self):
        return self.service_type


from django.db import models
from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.geos import Point
from django.utils import timezone
import requests


from django.contrib.gis.db import models as gis_models
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.geos import Point
import requests

class WorkerApplication(models.Model):
    """Worker application with 3-stage verification workflow."""

    # ==============================
    # Basic Information
    # ==============================
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20)
    location = gis_models.PointField(geography=True, srid=4326, null=True, blank=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    skills = models.TextField()
    experience = models.TextField(blank=True, null=True)

    # ==============================
    # Document Fields
    # ==============================
    photo_id_path = models.FileField(upload_to='photo_ids/', blank=True, null=True)
    aadhaar_card = models.FileField(upload_to='aadhaar_cards/', blank=True, null=True)
    union_card_path = models.FileField(upload_to='union_cards/', blank=True, null=True)
    certifications = models.FileField(upload_to='certifications/', blank=True, null=True)
    signature_copy = models.ImageField(upload_to='signatures/', null=True, blank=True)

    # ==============================
    # Application Status
    # ==============================
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('stage1_review', 'Stage 1 - Document Review'),
        ('stage1_rejected', 'Stage 1 - Rejected'),
        ('stage2_review', 'Stage 2 - Identity Verification'),
        ('stage2_rejected', 'Stage 2 - Rejected'),
        ('stage3_review', 'Stage 3 - Admin Approval'),
        ('stage3_rejected', 'Stage 3 - Rejected'),
        ('approved', 'Approved'),
    ]
    application_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='submitted')

    current_stage = models.IntegerField(
        default=1,
        choices=[
            (1, 'Stage 1 - Document Check'),
            (2, 'Stage 2 - Identity & Union Check'),
            (3, 'Stage 3 - Admin Approval'),
        ]
    )

    # ==============================
    # Stage Assignments
    # ==============================
    verifier1_assigned = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stage1_applications'
    )
    verifier2_assigned = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stage2_applications'
    )
    verifier3_assigned = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='stage3_applications'
    )

    # ==============================
    # Stage Completion Tracking
    # ==============================
    stage1_completed = models.BooleanField(default=False)
    stage1_completed_at = models.DateTimeField(null=True, blank=True)
    stage2_completed = models.BooleanField(default=False)
    stage2_completed_at = models.DateTimeField(null=True, blank=True)
    stage3_completed = models.BooleanField(default=False)
    stage3_completed_at = models.DateTimeField(null=True, blank=True)

    # ==============================
    # Service Categories
    # ==============================
    service_categories = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        default=list
    )

    # ==============================
    # Final Approval
    # ==============================
    is_fully_verified = models.BooleanField(default=False)
    password_generated = models.CharField(max_length=128, blank=True, null=True)
    assigned_worker = models.ForeignKey(
        'Worker',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_application'
    )

    # ==============================
    # Timestamps
    # ==============================
    created_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    # ==============================
    # Utility Methods
    # ==============================
    def save(self, *args, **kwargs):
        if not self.location and self.address:
            try:
                api_key = "1dec767eff4b49419346e6adb2815a1d"
                url = f"https://api.geoapify.com/v1/geocode/search?text={self.address}&format=json&apiKey={api_key}"
                res = requests.get(url, timeout=5).json()
                if res.get('results'):
                    first = res['results'][0]
                    self.location = Point(first['lon'], first['lat'])
            except Exception:
                pass
        super().save(*args, **kwargs)

    def mark_stage_completed(self, stage):
        now = timezone.now()
        if stage == 1:
            self.stage1_completed = True
            self.stage1_completed_at = now
            self.application_status = 'stage2_review'
            self.current_stage = 2
        elif stage == 2:
            self.stage2_completed = True
            self.stage2_completed_at = now
            self.application_status = 'stage3_review'
            self.current_stage = 3
        elif stage == 3:
            self.stage3_completed = True
            self.stage3_completed_at = now
            self.application_status = 'approved'
            self.is_fully_verified = True
            self.approved_at = now
        self.save()

    def reject_stage(self, stage):
        if stage == 1:
            self.application_status = 'stage1_rejected'
        elif stage == 2:
            self.application_status = 'stage2_rejected'
        elif stage == 3:
            self.application_status = 'stage3_rejected'
        self.save()

    def __str__(self):
        return f"{self.name} - {self.get_application_status_display()}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application_status']),
            models.Index(fields=['current_stage']),
            models.Index(fields=['created_at']),
        ]


class IdentityDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ('aadhaar', 'Aadhaar'),
        ('passport', 'Passport'),
        ('union', 'Union ID'),
        ('signature', 'Signature'),
        ('certification', 'Certification'),
    ]

    application = models.ForeignKey(
        'WorkerApplication',
        on_delete=models.CASCADE,
        related_name='identity_documents'
    )
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    image = models.ImageField(upload_to='documents/')

    def __str__(self):
        return f"{self.application.name} - {self.get_doc_type_display()}"

    class Meta:
        ordering = ['application', 'doc_type']
        verbose_name = 'Identity Document'
        verbose_name_plural = 'Identity Documents'

# ==============================
# Verification Stage Models
# ==============================
# In Verifier1Review model
class Verifier1Review(models.Model):
    """Stage 1: Document Completeness & Basic Validity Check"""
    
    application = models.OneToOneField(
        WorkerApplication,
        on_delete=models.CASCADE,
        related_name='verifier1_review'
    )
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    # Document Checklist
    all_documents_uploaded = models.BooleanField(default=False)
    documents_legible = models.BooleanField(default=False)
    correct_format = models.BooleanField(default=False)
    no_missing_fields = models.BooleanField(default=False)
    files_not_corrupted = models.BooleanField(default=False)
    expiry_dates_valid = models.BooleanField(default=False)
    
    # Review Status - CHANGED max_length from 20 to 25
    status = models.CharField(max_length=25, choices=[
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('resubmission_required', 'Resubmission Required'),
    ], default='pending')
    
    # Comments and Issues
    comments = models.TextField(blank=True)
    issues_found = models.TextField(blank=True, help_text="List of issues that need correction")
    
    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status in ['approved', 'rejected'] and not self.reviewed_at:
            self.reviewed_at = timezone.now()
            self.is_submitted = True
            self.submitted_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Stage 1 Review - {self.application.name} by {self.verifier}"

    class Meta:
        db_table = 'verifier1_reviews'


class Verifier2Review(models.Model):
    """Stage 2: Identity Match & Union Verification"""
    
    application = models.OneToOneField(
        WorkerApplication,
        on_delete=models.CASCADE,
        related_name='verifier2_review'
    )
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Identity Verification
    photo_matches_id = models.BooleanField(default=False)
    aadhaar_verified = models.BooleanField(default=False)
    aadhaar_number = models.CharField(max_length=12, blank=True)
    dob_verified = models.BooleanField(default=False)
    verified_dob = models.DateField(null=True, blank=True)
    address_verified = models.BooleanField(default=False)
    verified_address = models.CharField(max_length=512, blank=True)

    # Union Verification
    union_membership_verified = models.BooleanField(default=False)
    union_name = models.CharField(max_length=255, blank=True)
    union_id = models.CharField(max_length=100, blank=True)
    union_expiry_date = models.DateField(null=True, blank=True)

    # Contact Verification
    phone_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, null=True, blank=True)
    otp_sent = models.BooleanField(default=False)
    otp_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)

    # Review Status
    status = models.CharField(
        max_length=25,
        choices=[
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('correction_required', 'Correction Required'),
        ],
        default='pending'
    )

    comments = models.TextField(blank=True)
    discrepancies_found = models.TextField(blank=True)

    assigned_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status in ['approved', 'rejected'] and not self.reviewed_at:
            self.reviewed_at = timezone.now()
            self.is_submitted = True
            self.submitted_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Stage 2 Review - {self.application.name} by {self.verifier}"

    class Meta:
        db_table = 'verifier2_reviews'
# models.py
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
import random
from django.db import models
from django.conf import settings



class Verifier3Review(models.Model):
    """Stage 3: On-site verification, final admin review, and account creation trigger."""

    application = models.OneToOneField(
        'WorkerApplication',
        on_delete=models.CASCADE,
        related_name='verifier3_review'
    )
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # On-site verification flags
    location_verified = models.BooleanField(default=False)
    skill_verified = models.BooleanField(default=False)
    comments = models.TextField(blank=True)

    # Admin / On-site Checks
    previous_stages_verified = models.BooleanField(default=False)
    policy_compliance_checked = models.BooleanField(default=False)
    spot_check_performed = models.BooleanField(default=False)
    background_check_passed = models.BooleanField(default=False)

    # Account Creation Info
    worker_id_assigned = models.CharField(max_length=100, blank=True)
    password_generated_by_admin = models.CharField(max_length=128, blank=True)
    permissions_set = models.BooleanField(default=False)
    notification_sent = models.BooleanField(default=False)

    # Review Status
    status = models.CharField(
        max_length=25,
        choices=[
            ('pending', 'Pending Review'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )

    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
    # Always track submission timestamp once reviewer updates
        if not self.reviewed_at:
            self.reviewed_at = timezone.now()

        # ----- Status-specific handling -----
        if self.status in ['approved', 'rejected']:
            self.is_submitted = True
            self.submitted_at = timezone.now()
        else:
            # still under review / pending
            self.is_submitted = False

        # ----- On approval -----
        if self.status == 'approved' and not self.application.assigned_worker:
            raw_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

            user, created = AuthenticatedUser.objects.get_or_create(
                email=self.application.email,
                defaults={
                    'name': self.application.name,
                    'phone': self.application.phone,
                    'address': self.application.address,
                    'location': self.application.location,
                    'is_active': True,
                }
            )
            user.set_password(raw_password)      # ✅ ensures correct hashing
            user.save()

            UserRole.objects.get_or_create(user=user, role='worker')
            worker, _ = Worker.objects.get_or_create(
                user=user,
                defaults={
                    'application': self.application,
                    'location': self.application.location,
                    'address': self.application.address,
                    'is_available': True,
                    'experience_years': 0,
                    'approved_at': timezone.now(),
                }
            )

            self.application.assigned_worker = worker
            self.application.password_generated = raw_password  # keep raw only for audit (or encrypt)
            self.application.approved_at = timezone.now()
            self.application.application_status = 'approved'
            self.application.is_fully_verified = True
            self.application.stage3_completed = True
            self.application.stage3_completed_at = timezone.now()
            self.application.save()

            try:
                send_mail(
                    "Your Worker Account Credentials",
                    f"Username: {user.email}\nPassword: {raw_password}",
                    "no-reply@yourdomain.com",
                    [user.email],
                    fail_silently=False,
                )
                self.notification_sent = True
            except Exception:
                pass

        elif self.status == 'rejected':
            self.application.application_status = 'stage3_rejected'
            self.application.save(update_fields=['application_status'])

        super().save(*args, **kwargs)


    def __str__(self):
        return f"Stage 3 Review - {self.application.name} by {self.verifier}"

    class Meta:
        db_table = 'verifier3_reviews'


# Verifier3Review is already max_length=20 which is fine since longest is 'rejected' (8 chars)
# But for consistency, you can update it to 25 as well


class VerificationWorkflowLog(models.Model):
    """Track complete verification workflow history"""
    
    application = models.ForeignKey(
        WorkerApplication,
        on_delete=models.CASCADE,
        related_name='workflow_logs'
    )
    stage = models.IntegerField(choices=[
        (1, 'Stage 1'),
        (2, 'Stage 2'),
        (3, 'Stage 3'),
    ])
    verifier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    action = models.CharField(max_length=50, choices=[
        ('assigned', 'Assigned'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        
    ])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.application.name} - Stage {self.stage} - {self.action}"

    class Meta:
        ordering = ['-created_at']
        db_table = 'verification_workflow_logs'


# ==============================
# Worker Profile
# ==============================

class Worker(models.Model):
    """Approved worker profiles with location, availability, and review stats."""
    user = models.OneToOneField(AuthenticatedUser, on_delete=models.CASCADE, related_name='worker_profile')
    application = models.OneToOneField(WorkerApplication, on_delete=models.CASCADE, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    location = gis_models.PointField(geography=True, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    allows_cod = models.BooleanField(default=False)
    experience_years = models.PositiveIntegerField(default=0)
    profile_image = models.ImageField(upload_to='worker_profiles/', blank=True, null=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    
    # Review statistics
    average_rating = models.FloatField(default=0.0)
    total_reviews = models.PositiveIntegerField(default=0)

    def active_job(self):
        return self.bookings.filter(Q(status='in_progress') | Q(status='active')).first()

    @property
    def worker_name(self):
        return self.application.name if self.application else self.user.name

    def update_average_rating(self):
        """Recalculate average rating based on all reviews."""
        reviews = self.userreview_set.filter(rating__isnull=False)
        agg = reviews.aggregate(avg_rating=models.Avg("rating"), total=models.Count("id"))
        self.average_rating = round(agg["avg_rating"] or 0.0, 2)
        self.total_reviews = agg["total"] or 0
        self.save(update_fields=["average_rating", "total_reviews"])

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Automatically create WorkerService entries from application service categories
        if self.application and self.application.service_categories:
            for service_type in self.application.service_categories:
                try:
                    service = Service.objects.get(service_type=service_type)
                    WorkerService.objects.get_or_create(
                        worker=self,
                        service=service,
                        defaults={'charge': service.base_coins_cost}
                    )
                except Service.DoesNotExist:
                    pass

    def __str__(self):
        return self.worker_name

    class Meta:
        db_table = 'workers'
        verbose_name = 'Worker'
        verbose_name_plural = 'Workers'


class WorkerService(models.Model):
    """Link between workers and their offered services with individual pricing."""
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name='services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    charge = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('worker', 'service')
        db_table = 'worker_services'
        verbose_name = 'Worker Service'
        verbose_name_plural = 'Worker Services'

    def __str__(self):
        return f"{self.worker.worker_name} - {self.service.service_type}"


# ==============================
# Bookings & Transactions
# ==============================

class Booking(models.Model):
    """Tracks service bookings, status, locations, payments."""
    user = models.ForeignKey(AuthenticatedUser, on_delete=models.CASCADE, related_name='bookings')
    worker = models.ForeignKey(
        Worker,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings'
    )
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    booking_time = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_sent = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=[
        ('booked', 'Booked'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], default='booked')
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('paid', 'Paid'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    job_location = gis_models.PointField(geography=True, null=True, blank=True)
    tariff_coins = models.PositiveIntegerField(null=True, blank=True)
    admin_commission_coins = models.PositiveIntegerField(null=True, blank=True)
    payment_method = models.CharField(max_length=10, choices=[
        ('coins', 'Coins'),
        ('cod', 'Cash on Delivery'),
        ('online', 'Online')
    ], default='coins')
    payment_received = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    details = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'bookings'
        verbose_name = 'Booking'
        verbose_name_plural = 'Bookings'

    def __str__(self):
        return f"Booking #{self.id} - {self.user.name} - {self.service.service_type}"


class BookingPhoto(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='booking_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking_photos'
        verbose_name = 'Booking Photo'
        verbose_name_plural = 'Booking Photos'


class Tariff(models.Model):
    booking = models.ForeignKey(Booking, related_name='tariffs', on_delete=models.CASCADE)
    label = models.CharField(max_length=100)
    amount = models.PositiveIntegerField()
    explanation = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "tariffs"

    def __str__(self):
        return f"{self.label} - {self.amount}"


class RazorpayPayment(models.Model):
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='razorpay_payment',
        null=True,
        blank=True
    )
    worker_application = models.ForeignKey(
        WorkerApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='razorpay_payments'
    )
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('created', 'Created'),
            ('paid', 'Paid'),
            ('failed', 'Failed')
        ],
        default='created'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'razorpay_payments'
        verbose_name = 'Razorpay Payment'
        verbose_name_plural = 'Razorpay Payments'


class WorkerEarning(models.Model):
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE, related_name="earnings")
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE)
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    user_review = models.OneToOneField(
        'UserReview',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="worker_earning"
    )

    class Meta:
        db_table = 'worker_earnings'

    def __str__(self):
        return f"{self.worker.worker_name} - {self.amount} coins"


# ==============================
# Reviews & ML Dataset
# ==============================

class UserReview(models.Model):
    """User reviews for workers."""
    user = models.ForeignKey(AuthenticatedUser, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review by {self.user} for {self.worker} - Rating: {self.rating}"


class UserWorkerData(models.Model):
    """Expanded data for ML: links user, worker, service, review and other metrics."""
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(AuthenticatedUser, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    worker_location = gis_models.PointField()
    service_name = models.CharField(max_length=100)
    worker_experience = models.IntegerField()
    charge = models.IntegerField(default=0)
    num_bookings = models.IntegerField(default=0)
    total_rating = models.FloatField(default=0.0)
    worker_latitude = models.FloatField(null=True, blank=True)
    worker_longitude = models.FloatField(null=True, blank=True)

    class Meta:
        db_table = "user_worker_data"
        unique_together = ('user', 'worker', 'service')

    def __str__(self):
        return f"{self.user} → {self.worker} ({self.service_name})"


@receiver(post_save, sender=Booking)
def update_worker_data(sender, instance, **kwargs):
    booking = instance
    service = booking.service
    worker = booking.worker
    user = booking.user

    if not (worker and service):
        return

    # ✅ Aggregate more realistic data
    avg_rating = worker.userreview_set.aggregate(avg=Avg('rating'))['avg'] or 0.0
    total_bookings = worker.bookings.filter(status='completed').count()
    total_earnings = worker.earnings.aggregate(total=Avg('amount'))['total'] or 0

    # ✅ Add some controlled variation to avoid identical data
    experience_factor = worker.experience_years + (total_bookings // 5)
    rating_factor = avg_rating + (0.05 * (total_bookings % 3))
    charge_variation = (booking.tariff_coins or service.base_coins_cost) * (0.9 + (total_bookings % 5) / 20)

    UserWorkerData.objects.update_or_create(
        user=user,
        worker=worker,
        service=service,
        defaults={
            "service_name": service.service_type,
            "worker_location": worker.location,
            "worker_experience": int(experience_factor),
            "charge": int(charge_variation),
            "num_bookings": total_bookings,
            "total_rating": round(rating_factor, 2),
            "worker_latitude": worker.location.y if worker.location else None,
            "worker_longitude": worker.location.x if worker.location else None,
        }
    )


