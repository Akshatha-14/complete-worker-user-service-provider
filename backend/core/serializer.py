from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import *

from rest_framework import serializers
from .models import AuthenticatedUser

class UserSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(format="%Y-%m-%d", read_only=True)

    class Meta:
        model = AuthenticatedUser
        fields = (
            'email',
            'name',
            'first_name',
            'last_name',
            'address',
            'phone',
            'location',
            'latitude',
            'longitude',
            'date_joined',
        )

    def get_phone(self, obj):
        return str(obj.phone) if obj.phone else None

    def get_first_name(self, obj):
        if obj.name:
            parts = obj.name.split()
            return parts[0] if parts else ''
        return ''

    def get_last_name(self, obj):
        if obj.name:
            parts = obj.name.split()
            return ' '.join(parts[1:]) if len(parts) > 1 else ''
        return ''

    def get_latitude(self, obj):
        try:
            return obj.location.y if obj.location else None
        except AttributeError:
            return None

    def get_longitude(self, obj):
        try:
            return obj.location.x if obj.location else None
        except AttributeError:
            return None

class ServiceSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='service_type', read_only=True)

    class Meta:
        model = Service
        fields = ['id', 'service_type', 'name', 'description']


class WorkerServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)

    class Meta:
        model = WorkerService
        fields = ['id', 'service', 'charge']
from rest_framework import serializers

class WorkerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    services = serializers.SerializerMethodField()
    is_available = serializers.BooleanField(read_only=True)  # show availability
    status = serializers.SerializerMethodField()  # computed status (Approved/Available/Unavailable)
    cost_per_hour = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()  # full URL or placeholder for profile_image

    class Meta:
        model = Worker
        fields = [
            'id', 'user', 'services', 'cost_per_hour', 'is_available', 'status',
            'allows_cod', 'experience_years', 'profile_image', 'avatar'
        ]

    def get_services(self, obj):
        services_qs = obj.services.select_related('service')
        return [service.service.service_type for service in services_qs if service.service]

    def get_status(self, obj):
        if hasattr(obj, 'approved_at') and obj.approved_at:
            return "Approved"
        if obj.is_available:
            return "Available"
        return "Unavailable"

    def get_cost_per_hour(self, obj):
        first_service = obj.services.first()
        return first_service.charge if first_service else 0

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.profile_image and request:
            return request.build_absolute_uri(obj.profile_image.url)
        # Return placeholder URL if no profile_image set
        return f"https://i.pravatar.cc/80?u={obj.id}"



class BookingPhotoSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BookingPhoto
        fields = ['id', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:  # If there’s an image
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        # Return placeholder instead of None
        return "https://via.placeholder.com/150"



class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ('label', 'amount', 'explanation')


class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    worker = WorkerSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    tariffs = TariffSerializer(many=True, read_only=True)
    worker_id = serializers.IntegerField(source='worker.id', read_only=True)
    worker_phone = serializers.CharField(source='worker.user.phone', read_only=True)
    rating = serializers.SerializerMethodField()
    class Meta:
        model = Booking
        fields = ['id', 'user','worker_id', 'worker_phone', 'rating','worker', 'service', 'booking_time', 'status', 'tariffs', 'total','payment_status']
    def get_rating(self, obj):
        review = obj.userreview_set.filter(user=obj.user).first()
        if review:
            print(f"Booking {obj.id} has rating: {review.rating}")
            return review.rating
        else:
            print(f"Booking {obj.id} has no rating")
            return None

class RazorpayPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RazorpayPayment
        fields = ('razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'status')

class BookingDetailSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)
    worker = WorkerSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    photos = BookingPhotoSerializer(many=True, read_only=True)
    tariffs = TariffSerializer(many=True, read_only=True)
    razorpay_payment = RazorpayPaymentSerializer(read_only=True)
    
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = '__all__'

    def get_rating(self, obj):
        # Get the first review for this booking and user
        review = obj.userreview_set.filter(user=obj.user).first()
        if review:
            return review.rating  # Return rating if exists
        return None  # Return None if no review, without printing anything

class BookingSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    worker = WorkerSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    tariffs = TariffSerializer(many=True, read_only=True)
    worker_id = serializers.IntegerField(source='worker.id', read_only=True)
    worker_phone = serializers.CharField(source='worker.user.phone', read_only=True)
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'worker_id', 'worker_phone', 'rating',
            'worker', 'service', 'booking_time', 'status', 'tariffs',
            'total', 'payment_status'
        ]

    def get_rating(self, obj):
        review = obj.userreview_set.filter(user=obj.user).first()
        if review:
            return review.rating  # Return rating if exists
        return None  # Return None if no review

from rest_framework import serializers
from django.db.models import Avg

class WorkerSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    service = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    rating = serializers.FloatField(source='average_rating')
    costPerHour = serializers.SerializerMethodField()
    available = serializers.BooleanField(source='is_available')
    difficulty = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()




    class Meta:
        model = Worker
        fields = [
            'id', 'name', 'avatar', 'service', 'description',
            'rating', 'costPerHour', 'available', 'difficulty',
            'address'
        ]

    def get_name(self, obj):
        return obj.worker_name or obj.user.name or f"Worker {obj.id}"

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.profile_image:
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        return f"https://i.pravatar.cc/80?u={obj.id}"

    def get_service(self, obj):
        services_qs = obj.services.select_related('service')
        service_entity = services_qs.first()
        if service_entity and service_entity.service:
            return {'service_type': service_entity.service.service_type}
        return {'service_type': 'Service not specified'}

    def get_costPerHour(self, obj):
        services_qs = obj.services.all()
        if services_qs.exists():
            avg_charge = services_qs.aggregate(avg=Avg('charge'))['avg']
            return round(avg_charge or 0, 2)
        return 0

    def get_description(self, obj):
        return obj.application.experience if obj.application else ""

    def get_difficulty(self, obj):
        years = obj.experience_years
        if years >= 10:
            return "Hard"
        if years >= 5:
            return "Medium"
        return "Easy"
    def get_address(self, obj):
        return obj.get_address()
# serializers.py
from rest_framework import serializers
from .models import Worker

class WorkerImageSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Worker
        fields = ['id', 'profile_image_url']

    def get_profile_image_url(self, obj):
        request = self.context.get('request')
        if obj.profile_image:
            if request:
                return request.build_absolute_uri(obj.profile_image.url)
            return obj.profile_image.url
        # fallback image
        return f"https://i.pravatar.cc/80?u={obj.id}"

class BookingCreateSerializer(serializers.Serializer):
    userId = serializers.IntegerField()
    workerId = serializers.IntegerField()
    contactDates = serializers.ListField(child=serializers.CharField())
    description = serializers.CharField()
    equipmentRequirement = serializers.CharField(required=False, allow_blank=True)


    def validate(self, data):
        if not data.get('workerId'):
            raise serializers.ValidationError("workerId is required")
        if not data.get('userId'):
            raise serializers.ValidationError("userId is required")
        return data


class UserProfileSerializer(GeoFeatureModelSerializer):
    phone = serializers.SerializerMethodField()

    class Meta:
        model = AuthenticatedUser
        geo_field = 'location'
        fields = ('email', 'name', 'address', 'phone', 'location')

    def get_phone(self, obj):
        return str(obj.phone) if obj.phone else None

class JobSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    worker = WorkerSerializer(read_only=True, allow_null=True)
    service = ServiceSerializer(read_only=True)
    description = serializers.CharField(source='details', allow_blank=True, default='')
    equipmentRequirement = serializers.CharField(allow_blank=True, required=False)
    tariffs = TariffSerializer(many=True)
    photos = BookingPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'user', 'worker', 'service', 'booking_time', 'description', 'equipmentRequirement',
            'tariffs', 'status', 'photos', 'job_location', 'tariff_coins',
            'payment_method', 'payment_received'
        ]

    def to_representation(self, instance):
        repr = super().to_representation(instance)
        if not instance.worker:
            repr['worker'] = {'name': 'Unassigned', 'id': None}
        return repr



from rest_framework import serializers


class UserSerializerone(serializers.ModelSerializer):
    phone = serializers.CharField(allow_blank=True, required=False)
    email = serializers.EmailField(required=False)
    name = serializers.CharField(required=False)
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = AuthenticatedUser
        fields = ('email', 'name', 'first_name', 'last_name', 'address', 'phone', 'location')

    def get_first_name(self, obj):
        if obj.name:
            parts = obj.name.split()
            return parts[0] if parts else ''
        return ''

    def get_last_name(self, obj):
        if obj.name:
            parts = obj.name.split()
            return ' '.join(parts[1:]) if len(parts) > 1 else ''
        return ''

    def get_phone(self, obj):
        return str(obj.phone) if obj.phone else None

from django.contrib.gis.geos import Point
from rest_framework import serializers
import json
# serializers.py

from rest_framework import serializers
from django.contrib.gis.geos import Point
import json
from .models import Worker

class WorkerSettingsSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField(read_only=True)
    email = serializers.EmailField(source='user.email', required=False)
    phone = serializers.CharField(source='user.phone', required=False)
    profile_image_url = serializers.SerializerMethodField(read_only=True)
    address = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Worker
        fields = ['name', 'profile_image', 'profile_image_url', 'location', 'address', 'email', 'phone']
        read_only_fields = ['name', 'profile_image_url']

    def get_name(self, obj):
       
        return obj.worker_name


    def get_profile_image_url(self, obj):
        if obj.profile_image:
            return obj.profile_image.url
        return None

    def update(self, instance, validated_data):
        request = self.context.get('request')

        # Update nested user fields
        user_data = validated_data.pop('user', None)
        if not user_data and request and 'user' in request.data:
            try:
                user_data = json.loads(request.data.get('user'))
            except json.JSONDecodeError:
                user_data = {}

        if user_data:
            instance.user.email = user_data.get('email', instance.user.email)
            instance.user.phone = user_data.get('phone', instance.user.phone)
            instance.user.save()

        # Update Worker address
        if request and 'address' in request.data:
            instance.address = request.data['address']

        # Update location
        if request and 'location' in request.data:
            try:
                loc_data = json.loads(request.data['location'])
                if loc_data.get('type') == 'Point':
                    coords = loc_data.get('coordinates', [])
                    if len(coords) == 2:
                        instance.location = Point(coords[0], coords[1])
            except json.JSONDecodeError:
                pass

        # Update profile image
        profile_image = validated_data.get('profile_image') or request.FILES.get('profile_image')
        if profile_image:
            instance.profile_image = profile_image

        instance.save()
        return instance


from rest_framework import serializers

class WorkerDetailedSerializer(WorkerSerializer):
    user = UserSerializerone(read_only=True)
    email = serializers.SerializerMethodField()
    contactNumber = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()  # Override avatar for detailed serializer

    class Meta(WorkerSerializer.Meta):
        fields = WorkerSerializer.Meta.fields + ['user', 'email', 'contactNumber', 'avatar']

    def get_email(self, obj):
        return obj.user.email if obj.user else ""

    def get_contactNumber(self, obj):
        return str(obj.user.phone) if obj.user and obj.user.phone else ""

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.profile_image and request:
            return request.build_absolute_uri(obj.profile_image.url)
        return f"https://i.pravatar.cc/80?u={obj.id}"
    
from rest_framework import serializers

class ServiceSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = ['id', 'service_type', 'name', 'description']

    def get_name(self, obj):
        return obj.service_type

class TariffSerializer(serializers.Serializer):
    label = serializers.CharField()
    amount = serializers.IntegerField()

class WorkerEarningSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(source='booking.service', read_only=True)
    customer = serializers.CharField(source='booking.user.name', read_only=True)
    date = serializers.DateTimeField(source='booking.booking_time', format="%Y-%m-%d", read_only=True)
    address = serializers.CharField(source='booking.address', read_only=True)
    payment_method = serializers.CharField(source='booking.payment_method', read_only=True)  # Added payment_method field
    rating = serializers.SerializerMethodField()
    tariff = serializers.SerializerMethodField()

    class Meta:
        model = WorkerEarning
        fields = ['id', 'service', 'customer', 'amount', 'date', 'address', 'payment_method', 'rating', 'tariff']

    def get_rating(self, obj):
        review = obj.booking.userreview_set.filter(user=obj.booking.user).first()
        return review.rating if review else None

    def get_tariff(self, obj):
        return getattr(obj, 'tariff', []) or []


class UserReviewRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserReview
        fields = ['booking', 'rating']  # only necessary fields

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value
    
class WorkerApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkerApplication
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Serializer fields:", list(self.fields.keys()))
        
class WorkerApplicationListSerializer(serializers.ModelSerializer):
    days_pending = serializers.SerializerMethodField()
    location_display = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    selected_service_category = serializers.PrimaryKeyRelatedField(
    queryset=Service.objects.all()
)

    class Meta:
        model = WorkerApplication
        fields = [
            'id', 'name', 'email', 'phone',
            'address', 'latitude', 'longitude', 'location_display',
            'skills', 'experience',
            'base_charge',  # added
            'selected_service_category',  # added
            'application_status', 'current_stage', 'stage1_completed',
            'applied_at', 'days_pending'
        ]

    def get_days_pending(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.applied_at
        return delta.days

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None

    def get_location_display(self, obj):
        if obj.location:
            lat = round(obj.location.y, 6)
            lng = round(obj.location.x, 6)
            return f"{obj.address} (Lat: {lat}, Long: {lng})"
        return obj.address or "No location provided"


class WorkerApplicationDetailSerializer(serializers.ModelSerializer):
    photo_id_url = serializers.SerializerMethodField()
    aadhaar_card_url = serializers.SerializerMethodField()
    union_card_url = serializers.SerializerMethodField()
    certifications_url = serializers.SerializerMethodField()
    signature_copy_url = serializers.SerializerMethodField()
    location_data = serializers.SerializerMethodField()
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()
    days_pending = serializers.SerializerMethodField()
    verifier1_summary = serializers.SerializerMethodField()
    class Meta:
        model = WorkerApplication
        fields = '__all__'

    def get_days_pending(self, obj):
        from django.utils import timezone
        delta = timezone.now() - obj.applied_at
        return delta.days

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None

    def get_location_data(self, obj):
        if obj.location:
            lat = round(obj.location.y, 6)
            lng = round(obj.location.x, 6)
            return {
                'address': obj.address or '',
                'latitude': lat,
                'longitude': lng,
                'display': f"{obj.address} (Lat: {lat}, Long: {lng})",
                'google_maps_url': f"https://www.google.com/maps?q={lat},{lng}"
            }
        return {
            'address': obj.address or '',
            'latitude': None,
            'longitude': None,
            'display': obj.address or "No location",
            'google_maps_url': None
        }

    def _get_file_url(self, file_field):
        if file_field:
            try:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(file_field.url)
                return file_field.url
            except:
                return None
        return None

    def get_photo_id_url(self, obj):
        return self._get_file_url(obj.photo_id_path)

    def get_aadhaar_card_url(self, obj):
        return self._get_file_url(obj.aadhaar_card)

    def get_union_card_url(self, obj):
        return self._get_file_url(obj.union_card_path)

    def get_certifications_url(self, obj):
        return self._get_file_url(obj.certifications)

    def get_signature_copy_url(self, obj):
        return self._get_file_url(obj.signature_copy)
    def get_verifier1_summary(self, obj):
        review = getattr(obj, 'verifier1_review', None)
        if not review:
            return {"status": "Not reviewed", "comments": "—"}

        return {
            "status": review.status,
            "comments": review.comments or "—"
        }

# ================================
# Verifier 1
# ================================
class Verifier1ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Verifier1Review
        fields = '__all__'
        read_only_fields = ['verifier', 'assigned_at', 'submitted_at', 'reviewed_at']


# ================================
# Verifier 2
# ================================
# serializers.py
from rest_framework import serializers
from .models import Verifier2Review
class Verifier2ReviewSerializer(serializers.ModelSerializer):
    applicant = serializers.CharField(source='application.name', read_only=True)
    verifier_name = serializers.SerializerMethodField()

    class Meta:
        model = Verifier2Review
        fields = [
            'id',
            'applicant',
            'verifier_name',
            'status',
            'photo_matches_id',
            'aadhaar_verified',
            'dob_verified',
            'address_verified',
            'union_membership_verified',
            'assigned_at',
            'reviewed_at',
            'application'  # include this to accept POST
        ]

    def create(self, validated_data):
        return Verifier2Review.objects.create(**validated_data)

    def get_verifier_name(self, obj):
        """Always show verifier2 if missing"""
        if obj.verifier and obj.verifier.name:
            return obj.verifier.name
        return "verifier2"


# ================================
# Verifier 3
# ================================
class Verifier3ReviewSerializer(serializers.ModelSerializer):
    application_name = serializers.CharField(source='application.name', read_only=True)
    application_email = serializers.CharField(source='application.email', read_only=True)
    # serializers.py
    verifier2_review = Verifier2ReviewSerializer(source='application.verifier2_review', read_only=True)


    class Meta:
        model = Verifier3Review
        fields = [
            'id', 'application', 'verifier',
            'application_name', 'application_email',
            'previous_stages_verified', 'policy_compliance_checked',
            'spot_check_performed', 'background_check_passed',
            'worker_id_assigned', 'password_generated_by_admin',
            'permissions_set', 'notification_sent', 'status',
            'assigned_at', 'reviewed_at', 'is_submitted', 'submitted_at',
            'location_verified', 'skill_verified',
            'comments',
            'verifier2_review'
        ]


# ================================
# Identity Document
# ================================
class IdentityDocumentSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = IdentityDocument
        fields = ['doc_type', 'image_url']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


# ================================
# Workflow Logs
# ================================
class VerificationWorkflowLogSerializer(serializers.ModelSerializer):
    verifier_name = serializers.SerializerMethodField()

    class Meta:
        model = VerificationWorkflowLog
        fields = '__all__'

    def get_verifier_name(self, obj):
        return obj.verifier.username if obj.verifier else None
# core/serializers.py
from rest_framework import serializers
from .models import AuthenticatedUser
from django.contrib.auth.hashers import make_password

class VerifierCreateSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=True)
    
    class Meta:
        model = AuthenticatedUser
        fields = ['name', 'email', 'role', 'phone']

    def create(self, validated_data):
        import random, string
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
        user = AuthenticatedUser.objects.create(
            username=validated_data['email'],
            email=validated_data['email'],
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            roles=validated_data['role'],
            password=make_password(password)
        )

        # Send email with credentials
        from django.core.mail import send_mail
        subject = "Your Verifier Account Created"
        message = f"Hello {user.name},\n\nYour verifier account has been created.\nEmail: {user.email}\nPassword: {password}\n\nPlease log in and change your password."
        send_mail(subject, message, "admin@yourdomain.com", [user.email])

        return user
