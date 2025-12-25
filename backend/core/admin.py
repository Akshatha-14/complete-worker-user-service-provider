from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.utils.html import format_html
from django.utils import timezone
from leaflet.admin import LeafletGeoAdmin


# ==============================
# Import Models
# ==============================
from .models import *


# ==============================
# LeafletGeoAdmin for models with locations
# ==============================
class WorkerAdmin(LeafletGeoAdmin):
    list_display = ('user', 'location', 'is_available', 'allows_cod', 'experience_years', 'approved_at')
    search_fields = ('user__email', 'user__name')
    list_filter = ('is_available', 'allows_cod')


class RazorpayPaymentInline(admin.StackedInline):
    model = RazorpayPayment
    can_delete = False
    readonly_fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'status')


class AuthenticatedUserAdmin(LeafletGeoAdmin):
    list_display = ('id', 'email', 'name', 'is_staff', 'is_active', 'location')
    search_fields = ('email', 'name')
    list_filter = ('is_staff', 'is_active')


# ==============================
# Normal Admin
# ==============================
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__email', 'user__name')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("service_type", "description", "base_coins_cost")
    search_fields = ("service_type",)


# ==============================
# Worker Application Admin with Verification Workflow
# ==============================
class Verifier1ReviewInline(admin.StackedInline):
    model = Verifier1Review
    can_delete = False
    extra = 0
    readonly_fields = ('verifier', 'assigned_at', 'reviewed_at', 'submitted_at')
    fieldsets = (
        ('Document Checklist', {
            'fields': (
                'all_documents_uploaded',
                'documents_legible',
                'correct_format',
                'no_missing_fields',
                'files_not_corrupted',
                'expiry_dates_valid',
            )
        }),
        ('Review Decision', {
            'fields': ('status', 'comments', 'issues_found')
        }),
        ('Metadata', {
            'fields': ('verifier', 'assigned_at', 'reviewed_at', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )


class Verifier2ReviewInline(admin.StackedInline):
    model = Verifier2Review
    can_delete = False
    extra = 0
    readonly_fields = ('verifier', 'assigned_at', 'reviewed_at', 'submitted_at')
    fieldsets = (
        ('Identity Verification', {
            'fields': (
                'photo_matches_id',
                'aadhaar_verified',
                'aadhaar_number',
                'dob_verified',
                'verified_dob',
                'address_verified',
                'verified_address',
            )
        }),
        ('Union Verification', {
            'fields': (
                'union_membership_verified',
                'union_name',
                'union_id',
                'union_expiry_date',
            )
        }),
        ('Contact Verification', {
            'fields': (
                'phone_verified',
                'otp_sent',
                'otp_verified',
                'email_verified',
            )
        }),
        ('Review Decision', {
            'fields': ('status', 'comments', 'discrepancies_found')
        }),
        ('Metadata', {
            'fields': ('verifier', 'assigned_at', 'reviewed_at', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )


class Verifier3ReviewInline(admin.StackedInline):
    model = Verifier3Review
    can_delete = False
    extra = 0
    readonly_fields = ('verifier', 'assigned_at', 'reviewed_at', 'submitted_at')
    fieldsets = (
        ('Admin Checks', {
            'fields': (
                'previous_stages_verified',
                'policy_compliance_checked',
                'spot_check_performed',
                'background_check_passed',
            )
        }),
        ('Account Creation', {
            'fields': (
                'worker_id_assigned',
                'password_generated_by_admin',
                'permissions_set',
                'notification_sent',
            )
        }),
        ('Final Decision', {
            'fields': (
                'status',
                
            )
        }),
        ('Metadata', {
            'fields': ('verifier', 'assigned_at', 'reviewed_at', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )


class WorkerApplicationAdmin(LeafletGeoAdmin):
    list_display = (
        'name',
        'email',
        'phone',
        'current_stage_display',
        'application_status_badge',
        'applied_at',
        'view_documents_link',
    )
    list_filter = ('application_status', 'current_stage', 'created_at')
    search_fields = ('name', 'email', 'phone')

    readonly_fields = (
        'created_at',
        'applied_at',
        'approved_at',
        'stage1_completed_at',
        'stage2_completed_at',
        'stage3_completed_at',
        'assigned_worker',
        'password_generated',
    )

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name',
                'email',
                'phone',
                'address',
                'location',
                'skills',
                'experience',
                'service_categories',
            )
        }),
        ('Documents', {
            'fields': (
                'photo_id_path',
                'aadhaar_card',
                'union_card_path',
                'certifications',
                'signature_copy',
            )
        }),
        ('Verification Workflow', {
            'fields': (
                'application_status',
                'current_stage',
                'is_fully_verified',
            )
        }),
        ('Stage Assignments', {
            'fields': (
                'verifier1_assigned',
                'verifier2_assigned',
                'verifier3_assigned',
            ),
            'classes': ('collapse',)
        }),
        ('Stage Completion Tracking', {
            'fields': (
                'stage1_completed',
                'stage1_completed_at',
                'stage2_completed',
                'stage2_completed_at',
                'stage3_completed',
                'stage3_completed_at',
            ),
            'classes': ('collapse',)
        }),
        ('Final Status', {
            'fields': (
                'assigned_worker',
                'password_generated',
                'created_at',
                'applied_at',
                'approved_at',
            ),
            'classes': ('collapse',)
        }),
    )

    inlines = [Verifier1ReviewInline, Verifier2ReviewInline, Verifier3ReviewInline]

    default_lon = 77.5946
    default_lat = 12.9716
    default_zoom = 12
    geom_field = "location"

    def current_stage_display(self, obj):
        stages = {
            1: '🔍 Stage 1',
            2: '👤 Stage 2',
            3: '✅ Stage 3',
        }
        return stages.get(obj.current_stage, 'Unknown')
    current_stage_display.short_description = 'Current Stage'

    def application_status_badge(self, obj):
        status_colors = {
            'submitted': '#6c757d',
            'stage1_review': '#0dcaf0',
            'stage1_rejected': '#dc3545',
            'stage2_review': '#0d6efd',
            'stage2_rejected': '#dc3545',
            'stage3_review': '#ffc107',
            'stage3_rejected': '#dc3545',
            'approved': '#198754',
        }
        
        color = status_colors.get(obj.application_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_application_status_display()
        )
    application_status_badge.short_description = 'Status'
    
    def view_documents_link(self, obj):
        if obj.photo_id_path or obj.aadhaar_card or obj.union_card_path:
            return format_html('<a href="#" style="color: #0d6efd;">📄 View Docs</a>')
        return '—'
    view_documents_link.short_description = 'Documents'


# ==============================
# Verification Review Admins
# ==============================
@admin.register(Verifier1Review)
class Verifier1ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'application_name',
        'verifier',
        'status_badge',
        'all_checks_passed',
        'assigned_at',
        'reviewed_at'
    )
    list_filter = ('status', 'is_submitted', 'assigned_at')
    search_fields = ('application__name', 'application__email', 'verifier__email')
    
    readonly_fields = ('verifier', 'assigned_at', 'reviewed_at', 'submitted_at', 'is_submitted')
    
    fieldsets = (
        ('Application', {
            'fields': ('application',)
        }),
        ('Document Checklist', {
            'fields': (
                'all_documents_uploaded',
                'documents_legible',
                'correct_format',
                'no_missing_fields',
                'files_not_corrupted',
                'expiry_dates_valid',
            )
        }),
        ('Review Decision', {
            'fields': ('status', 'comments', 'issues_found')
        }),
        ('Metadata', {
            'fields': ('verifier', 'assigned_at', 'reviewed_at', 'is_submitted', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def application_name(self, obj):
        return obj.application.name
    application_name.short_description = 'Applicant'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'approved': '#198754',
            'rejected': '#dc3545',
            'resubmission_required': '#ffc107',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def all_checks_passed(self, obj):
        checks = [
            obj.all_documents_uploaded,
            obj.documents_legible,
            obj.correct_format,
            obj.no_missing_fields,
            obj.files_not_corrupted,
            obj.expiry_dates_valid,
        ]
        if all(checks):
            return format_html('<span style="color: green;">✅ All Passed</span>')
        return format_html('<span style="color: orange;">⚠️ {} / 6</span>', sum(checks))
    all_checks_passed.short_description = 'Checks'
    
    def save_model(self, request, obj, form, change):
        if not obj.verifier:
            obj.verifier = request.user
        
        # Update application status based on review
        if obj.status == 'approved' and not obj.application.stage1_completed:
            obj.application.stage1_completed = True
            obj.application.stage1_completed_at = timezone.now()
            obj.application.current_stage = 2
            obj.application.application_status = 'stage2_review'
            obj.application.save()
            messages.success(request, f"Application advanced to Stage 2 for {obj.application.name}")
        
        elif obj.status == 'rejected':
            obj.application.application_status = 'stage1_rejected'
            obj.application.save()
            messages.warning(request, f"Application rejected at Stage 1 for {obj.application.name}")
        
        super().save_model(request, obj, form, change)


@admin.register(Verifier2Review)
class Verifier2ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'application_name',
        'verifier',
        'status_badge',
        'identity_checks',
        'union_verified',
        'assigned_at',
        'reviewed_at'
    )
    list_filter = ('status', 'union_membership_verified', 'aadhaar_verified', 'is_submitted')
    search_fields = ('application__name', 'application__email', 'verifier__email', 'union_name')
    
    readonly_fields = ('verifier', 'assigned_at', 'reviewed_at', 'submitted_at', 'is_submitted')
    
    fieldsets = (
        ('Application', {
            'fields': ('application',)
        }),
        ('Identity Verification', {
            'fields': (
                'photo_matches_id',
                'aadhaar_verified',
                'aadhaar_number',
                'dob_verified',
                'verified_dob',
                'address_verified',
                'verified_address',
            )
        }),
        ('Union Verification', {
            'fields': (
                'union_membership_verified',
                'union_name',
                'union_id',
                'union_expiry_date',
            )
        }),
        ('Contact Verification', {
            'fields': (
                'phone_verified',
                'otp_sent',
                'otp_verified',
                'email_verified',
            )
        }),
        ('Review Decision', {
            'fields': ('status', 'comments', 'discrepancies_found')
        }),
        ('Metadata', {
            'fields': ('verifier', 'assigned_at', 'reviewed_at', 'is_submitted', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def application_name(self, obj):
        return obj.application.name
    application_name.short_description = 'Applicant'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'approved': '#198754',
            'rejected': '#dc3545',
            'correction_required': '#ffc107',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def identity_checks(self, obj):
        checks = [
            obj.photo_matches_id,
            obj.aadhaar_verified,
            obj.dob_verified,
            obj.address_verified,
        ]
        if all(checks):
            return format_html('<span style="color: green;">✅ Verified</span>')
        return format_html('<span style="color: orange;">⚠️ {} / 4</span>', sum(checks))
    identity_checks.short_description = 'Identity'
    
    def union_verified(self, obj):
        if obj.union_membership_verified:
            return format_html('<span style="color: green;">✅ {}</span>', obj.union_name or 'Verified')
        return format_html('<span style="color: gray;">❌ Not Verified</span>')
    union_verified.short_description = 'Union'
    
    def save_model(self, request, obj, form, change):
        if not obj.verifier:
            obj.verifier = request.user
        
        # Update application status based on review
        if obj.status == 'approved' and not obj.application.stage2_completed:
            obj.application.stage2_completed = True
            obj.application.stage2_completed_at = timezone.now()
            obj.application.current_stage = 3
            obj.application.application_status = 'stage3_review'
            obj.application.save()
            messages.success(request, f"Application advanced to Stage 3 for {obj.application.name}")
        
        elif obj.status == 'rejected':
            obj.application.application_status = 'stage2_rejected'
            obj.application.save()
            messages.warning(request, f"Application rejected at Stage 2 for {obj.application.name}")
        
        super().save_model(request, obj, form, change)


@admin.register(Verifier3Review)
class Verifier3ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'application_name',
        'verifier',
        'status_badge',
        'admin_checks',
        'account_created',
        'assigned_at',
        'reviewed_at'
    )
    list_filter = ('status', 'is_submitted', 'notification_sent')
    search_fields = ('application__name', 'application__email', 'verifier__email', 'worker_id_assigned')
    
    readonly_fields = ('verifier', 'assigned_at', 'reviewed_at', 'submitted_at', 'is_submitted')
    
    fieldsets = (
        ('Application', {
            'fields': ('application',)
        }),
        ('Admin Checks', {
            'fields': (
                'previous_stages_verified',
                'policy_compliance_checked',
                'spot_check_performed',
                'background_check_passed',
            )
        }),
        ('Account Creation', {
            'fields': (
                'worker_id_assigned',
                'password_generated_by_admin',
                'permissions_set',
                'notification_sent',
            )
        }),
        ('Final Decision', {
            'fields': (
                'status',
                
            )
        }),
        ('Metadata', {
            'fields': ('verifier', 'assigned_at', 'reviewed_at', 'is_submitted', 'submitted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def application_name(self, obj):
        return obj.application.name
    application_name.short_description = 'Applicant'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#6c757d',
            'approved': '#198754',
            'rejected': '#dc3545',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def admin_checks(self, obj):
        checks = [
            obj.previous_stages_verified,
            obj.policy_compliance_checked,
            obj.spot_check_performed,
            obj.background_check_passed,
        ]
        if all(checks):
            return format_html('<span style="color: green;">✅ All Passed</span>')
        return format_html('<span style="color: orange;">⚠️ {} / 4</span>', sum(checks))
    admin_checks.short_description = 'Admin Checks'
    
    def account_created(self, obj):
        if obj.worker_id_assigned and obj.password_generated_by_admin:
            return format_html('<span style="color: green;">✅ Created</span>')
        return format_html('<span style="color: gray;">❌ Pending</span>')
    account_created.short_description = 'Account'
    
    def save_model(self, request, obj, form, change):
        if not obj.verifier:
            obj.verifier = request.user
        
        super().save_model(request, obj, form, change)
        
        # Note: Application status update happens in Verifier3Review.save() method


@admin.register(VerificationWorkflowLog)
class VerificationWorkflowLogAdmin(admin.ModelAdmin):
    list_display = ('application_name', 'stage', 'action', 'verifier', 'created_at')
    list_filter = ('stage', 'action', 'created_at')
    search_fields = ('application__name', 'application__email', 'verifier__email', 'notes')
    readonly_fields = ('created_at',)
    
    def application_name(self, obj):
        return obj.application.name
    application_name.short_description = 'Applicant'
    
    def has_add_permission(self, request):
        return False  # Logs are auto-created
    
    def has_change_permission(self, request, obj=None):
        return False  # Logs are immutable


# ==============================
# Other Admin Classes
# ==============================
@admin.register(WorkerService)
class WorkerServiceAdmin(admin.ModelAdmin):
    list_display = ("worker", "service", "charge")
    search_fields = ("worker__user__email", "service__service_type")
    list_filter = ("service",)


class BookingAdmin(LeafletGeoAdmin):
    list_display = ('user', 'worker', 'service', 'status', 'booking_time', 'payment_method', 'payment_received')
    list_filter = ('status', 'payment_method', 'payment_status')
    search_fields = ('user__email', 'worker__user__email', 'service__service_type')
    
    default_lon = 77.5946
    default_lat = 12.9716
    default_zoom = 12
    geom_field = "job_location"
    
    inlines = [RazorpayPaymentInline]


class SessionLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'event_type', 'ip_address', 'created_at')
    search_fields = ('ip_address', 'user__email')
    list_filter = ('event_type', 'created_at')
    readonly_fields = ('created_at',)


class UserReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'worker', 'booking', 'rating', 'created_at')
    search_fields = ('user__email', 'worker__user__email')
    list_filter = ('rating', 'created_at')
    readonly_fields = ('created_at', 'updated_at')





@admin.register(UserWorkerData)
class UserWorkerDataAdmin(admin.ModelAdmin):
    list_display = ('worker', 'service_name', 'get_service_type', 'num_bookings', 'total_rating')
    search_fields = ('user__email', 'worker__user__email', 'service_name')
    list_filter = ('worker', 'service')
    readonly_fields = ('worker_latitude', 'worker_longitude')

    def get_service_type(self, obj):
        return obj.service.service_type if obj.service else ""
    get_service_type.short_description = 'Service Type'


class BookingPhotoAdmin(admin.ModelAdmin):
    list_display = ('booking', 'image', 'uploaded_at')
    readonly_fields = ('uploaded_at',)
    search_fields = ('booking__id',)


class TariffAdmin(admin.ModelAdmin):
    list_display = ('booking', 'label', 'amount', 'explanation')
    list_filter = ('booking',)
    search_fields = ('label', 'booking__id')


class RazorpayPaymentAdmin(admin.ModelAdmin):
    list_display = ('booking', 'razorpay_order_id', 'razorpay_payment_id', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('razorpay_order_id', 'razorpay_payment_id')
    readonly_fields = ('created_at',)


class WorkerEarningAdmin(admin.ModelAdmin):
    list_display = ('id', 'worker', 'booking', 'amount', 'created_at', 'user_review')
    list_filter = ('created_at', 'worker')
    search_fields = ('worker__user__name', 'booking__id')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)





# ==============================
# Register models to standard admin
# ==============================
# User Management
admin.site.register(AuthenticatedUser, AuthenticatedUserAdmin)
admin.site.register(UserRole, UserRoleAdmin)

# Worker Application & Verification
admin.site.register(WorkerApplication, WorkerApplicationAdmin)

# Worker Management
admin.site.register(Worker, WorkerAdmin)

# Bookings & Transactions
admin.site.register(Booking, BookingAdmin)
admin.site.register(BookingPhoto, BookingPhotoAdmin)
admin.site.register(Tariff, TariffAdmin)
admin.site.register(RazorpayPayment, RazorpayPaymentAdmin)
admin.site.register(WorkerEarning, WorkerEarningAdmin)

# Reviews & Analytics
admin.site.register(UserReview, UserReviewAdmin)

