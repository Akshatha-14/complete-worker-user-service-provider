from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import *


class UserSerializer(serializers.ModelSerializer):
    phone = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = AuthenticatedUser
        fields = ('email', 'name', 'first_name', 'last_name', 'address', 'phone', 'location')

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


class WorkerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    services = WorkerServiceSerializer(many=True, read_only=True)
    cost_per_hour = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    is_available = serializers.BooleanField(read_only=True)  # explicitly expose availability

    class Meta:
        model = Worker
        fields = [
            'id', 'user', 'name', 'services', 'cost_per_hour', 'is_available',
            'allows_cod', 'experience_years', 'profile_image'
        ]

    def get_cost_per_hour(self, obj):
        first_service = obj.services.first()
        return first_service.charge if first_service else 0

    def get_name(self, obj):
        if obj.application and obj.application.name:
            return obj.application.name
        return obj.user.name if obj.user and obj.user.name else f"Worker {obj.id}"

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
        review = obj.userreview_set.filter(user=obj.user).first()
        if review:
            print(f"Booking {obj.id} has rating: {review.rating}")
            return review.rating
        else:
            print(f"Booking {obj.id} has no rating")
            return None

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

    class Meta:
        model = Worker
        fields = [
            'id', 'name', 'avatar', 'service', 'description',
            'rating', 'costPerHour', 'available', 'difficulty'
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


class WorkerSettingsSerializer(serializers.ModelSerializer):
    user = UserSerializerone()

    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    contactNumber = serializers.SerializerMethodField()

    class Meta:
        model = Worker
        fields = ['id', 'user', 'is_available', 'profile_image', 'allows_cod', 'experience_years', 'name', 'email', 'contactNumber']

    def get_name(self, obj):
        return obj.user.name if obj.user else ""

    def get_email(self, obj):
        return obj.user.email if obj.user else ""

    def get_contactNumber(self, obj):
        return str(obj.user.phone) if obj.user and obj.user.phone else ""

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data:
            user = instance.user
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
class WorkerDetailedSerializer(WorkerSerializer):
    user = UserSerializerone(read_only=True)

    email = serializers.SerializerMethodField()
    contactNumber = serializers.SerializerMethodField()

    class Meta(WorkerSerializer.Meta):
        fields = WorkerSerializer.Meta.fields + ['user', 'email', 'contactNumber']

    def get_email(self, obj):
        return obj.user.email if obj.user else ""

    def get_contactNumber(self, obj):
        return str(obj.user.phone) if obj.user and obj.user.phone else ""
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
