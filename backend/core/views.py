from django.contrib.auth import get_user_model, authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.views.decorators.csrf import ensure_csrf_cookie
from .models import *
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes,action
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from django.contrib.gis.geos import Point as GEOSPoint
from .serializer import *
from django.http import JsonResponse
from .data_prep import *# load_df returns DataFrame
from shapely.geometry import Point
from django.conf import settings
import pandas as pd
from sqlalchemy import create_engine
from core.ml_model import recommendation_model  # Your pre-loaded LightGBM model
from core.utils import haversine_vector
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework import status,viewsets
from django.shortcuts import get_object_or_404
import os
import json
import base64
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Util.Padding import unpad
import hashlib
from Crypto.PublicKey import RSA
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
import razorpay
import hmac
from decimal import Decimal
import joblib
import lightgbm as lgb
import os
from .ml_model import recommendation_model, feature_cols
from django.contrib.auth.decorators import login_required
User = get_user_model()

# Load RSA private key securely (store private.pem safely on your server)
PRIVATE_KEY_PATH = os.path.join(settings.BASE_DIR, 'private.pem')
with open(PRIVATE_KEY_PATH, 'rb') as key_file:
    PRIVATE_KEY = RSA.import_key(key_file.read())

def decrypt_rsa(encrypted_b64):
    try:
        encrypted_data = base64.b64decode(encrypted_b64)
        cipher_rsa = PKCS1_OAEP.new(PRIVATE_KEY)
        decrypted = cipher_rsa.decrypt(encrypted_data)
        return decrypted  # bytes representing AES key
    except Exception:
        return None

def decrypt_aes(encrypted_b64, aes_key):
    try:
        encrypted_data = base64.b64decode(encrypted_b64)
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        cipher_aes = AES.new(aes_key, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher_aes.decrypt(ciphertext), AES.block_size)
        return decrypted_data.decode('utf-8')
    except Exception:
        return None


@api_view(['POST'])
@permission_classes([AllowAny])
def user_signup(request):
    try:
        payload = request.data
        key_enc = payload.get('key')
        data_enc = payload.get('data')
        if not key_enc or not data_enc:
            return Response({"error": "Missing encryption data."}, status=400)

        aes_key = decrypt_rsa(key_enc)
        if not aes_key:
            return Response({"error": "Invalid encrypted key."}, status=400)

        decrypted = {}
        for field in ['name', 'email', 'password']:
            val = decrypt_aes(data_enc.get(field), aes_key)
            if val is None:
                return Response({"error": f"Failed to decrypt {field}."}, status=400)
            decrypted[field] = val

        email, password, name = decrypted.get('email'), decrypted.get('password'), decrypted.get('name')
        if not all([email, password, name]):
            return Response({"error": "Missing required information."}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already registered."}, status=400)

        try:
            validate_password(password)
        except Exception as e:
            return Response({"error": getattr(e, 'messages', str(e))}, status=400)

        user = User.objects.create_user(email=email, password=password, name=name, is_active=True)
        return Response({"message": "User registered successfully."}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({"detail": "CSRF cookie set"})



@api_view(['POST'])
@permission_classes([AllowAny])
def api_user_login(request):
    try:
        payload = request.data
        key_enc = payload.get('key')
        data_enc = payload.get('data')

        if not key_enc or not data_enc:
            return Response({"error": "Missing encryption data."}, status=400)

        # Decrypt RSA-encrypted AES key
        aes_key = decrypt_rsa(key_enc)
        if not aes_key:
            return Response({"error": "Invalid encrypted key."}, status=400)

        print(f"Decrypted AES Key length: {len(aes_key)} bytes")

        # Extract encrypted email and password from data
        encrypted_email = data_enc.get('email')
        encrypted_password = data_enc.get('password')

        if not encrypted_email or not encrypted_password:
            return Response({"error": "Missing encrypted email or password."}, status=400)

        # Decrypt email and password using AES key
        email = decrypt_aes(encrypted_email, aes_key)
        password = decrypt_aes(encrypted_password, aes_key)

        if email is None:
            return Response({"error": "Failed to decrypt email."}, status=400)

        if password is None:
            return Response({"error": "Failed to decrypt password."}, status=400)

        # Debug logs to inspect decrypted values and their lengths
        

        # Trim decrypted values to ensure no trailing/leading whitespace
        email = email.strip()
        password = password.strip()

        if not email or not password:
            return Response({"error": "Email or password is empty after decryption."}, status=400)

        # Authenticate user using decrypted credentials
        user = authenticate(request, email=email, password=password)
        if not user:
            print(f"Authentication failed for email: {email}")
            return Response({"error": "Invalid credentials."}, status=401)

        # Successfully authenticate and login user
        login(request, user)

        # Get the user's role from UserRole model
        user_role = UserRole.objects.filter(user=user).first()
        role = user_role.role if user_role else ("admin" if user.is_staff else "user")
        
        profile_complete = all([user.phone, user.address, user.location])

        return Response({"message": "Login successful", "role": role, "profile_complete": profile_complete})

    except Exception as e:
        print(f"Exception in login: {str(e)}")
        return Response({"error": "Internal server error during login."}, status=500)



@api_view(['POST'])
def password_reset_request(request):
    email = request.data.get('email')
    if not email:
        return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "User with this email does not exist."}, status=status.HTTP_400_BAD_REQUEST)

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    reset_link = f"http://localhost:3000/reset-password/{uid}/{token}"

    subject = "Password Reset Request"
    message = (
        f"Hi,\n\n"
        f"Click the link below to reset your password:\n{reset_link}\n\n"
        f"If you didn't request this, please ignore this email."
    )

    send_mail(subject, message, 'no-reply@yourdomain.com', [email], fail_silently=False)

    return Response({"message": "Password reset link sent to your email."})
@api_view(['POST'])
def password_reset_confirm(request, uidb64, token):
    payload = request.data
    key_enc = payload.get('key')
    data_enc = payload.get('data')
    if not key_enc or not data_enc:
        return Response({"error": "Missing encryption data."}, status=400)

    # Decrypt AES key with RSA private key
    aes_key = decrypt_rsa(key_enc)
    if not aes_key:
        return Response({"error": "Invalid encrypted key."}, status=400)

    # Decrypt password with AES key
    encrypted_password = data_enc.get('password')
    new_password = decrypt_aes(encrypted_password, aes_key)
    if not new_password:
        return Response({"error": "Failed to decrypt password."}, status=400)

    new_password = new_password.strip()

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        return Response({"error": "Invalid reset link."}, status=400)

    if not default_token_generator.check_token(user, token):
        return Response({"error": "Token is invalid or expired."}, status=400)

    try:
        validate_password(new_password, user=user)
    except Exception as e:
        return Response({"error": e.messages}, status=400)

    user.set_password(new_password)
    user.save()

    is_valid = user.check_password(new_password)
    print(f"Password saved and checked: {is_valid}")

    return Response({"message": "Password has been reset successfully."})


@api_view(['POST'])
def google_social_login(request):
    token = request.data.get('token')
    if not token:
        return Response({"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        id_info = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    except ValueError:
        return Response({"error": "Invalid Google token."}, status=status.HTTP_400_BAD_REQUEST)

    email = id_info.get('email')
    if not email:
        return Response({"error": "Google account does not have an email."}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(email=email, defaults={'is_active': True})
    if created:
        user.set_unusable_password()
        user.save()

    login(request, user, backend=settings.AUTHENTICATION_BACKENDS[0])

    return Response({
        "message": "Successfully logged in with Google.",
        "email": user.email,
        "is_new_user": created,
    })
import joblib
import numpy as np
import pandas as pd
import lightgbm as lgb
from shapely.geometry import Point
from sqlalchemy import create_engine
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .utils import haversine_vector
from .models import Worker
from .serializer import WorkerImageSerializer


# ---------------------------------------------------------
# 🔹 Load Trained Model + Feature Columns
# ---------------------------------------------------------
MODEL_PATH = 'ml_models/lgb_ranker.txt'
FEATURE_COLS_PATH = 'ml_models/feature_cols.pkl'

recommendation_model = lgb.Booster(model_file=MODEL_PATH)
feature_cols = joblib.load(FEATURE_COLS_PATH)


# ---------------------------------------------------------
# 🔹 Helper Functions
# ---------------------------------------------------------
def build_user_locs_dict(engine):
    """Build {user_id: Point(lon, lat)} from database."""
    query = """
        SELECT id,
               ST_Y(location::geometry) AS lat,
               ST_X(location::geometry) AS lon
        FROM core_authenticateduser
        WHERE location IS NOT NULL;
    """
    user_locs = pd.read_sql(query, engine)
    return {row["id"]: Point(row["lon"], row["lat"]) for _, row in user_locs.iterrows()}


def normalize(series):
    """Safely normalize a pandas Series between 0–1."""
    if series.max() == series.min():
        return pd.Series(0.5, index=series.index)
    return (series - series.min()) / (series.max() - series.min())


# ---------------------------------------------------------
# 🔹 Core Recommendation Logic
# ---------------------------------------------------------
def recommend_top_n_for_user(user_id, model, engine, top_n=10):
    user_locs_dict = build_user_locs_dict(engine)
    user_point = user_locs_dict.get(user_id)
    if not user_point:
        return []

    # --- User booking history ---
    bookings_df = pd.read_sql(
        "SELECT user_id, worker_id, service_id FROM bookings WHERE status='completed'",
        engine
    )
    user_history = bookings_df[bookings_df["user_id"] == user_id]
    is_new_user = user_history.empty

    user_worker_counts = user_history.groupby("worker_id").size().to_dict()
    past_services = set(user_history["service_id"].unique())

    # --- Candidate workers ---
    cand_sql = """
        SELECT w.id AS worker_id,
               wu.name AS worker_name,
               s.id AS service_id,
               s.service_type AS service_name,
               ST_Y(w.location::geometry) AS worker_lat,
               ST_X(w.location::geometry) AS worker_lon,
               COALESCE(b.total_bookings, 0) AS num_bookings,
               w.average_rating AS total_rating,
               ws.charge,
               w.is_available
        FROM workers w
        LEFT JOIN core_authenticateduser wu ON w.user_id = wu.id
        LEFT JOIN worker_services ws ON w.id = ws.worker_id
        LEFT JOIN core_service s ON ws.service_id = s.id
        LEFT JOIN (
            SELECT worker_id, COUNT(*) AS total_bookings
            FROM bookings
            WHERE status = 'completed'
            GROUP BY worker_id
        ) b ON w.id = b.worker_id
        WHERE w.is_available = TRUE AND w.location IS NOT NULL;
    """
    cand_df = pd.read_sql(cand_sql, engine)
    if cand_df.empty:
        return []

    # --- Fill nulls & clean ---
    cand_df["total_rating"] = cand_df["total_rating"].fillna(0.0).astype(float)
    cand_df["charge"] = cand_df["charge"].fillna(cand_df["charge"].median()).astype(float)
    cand_df["num_bookings"] = cand_df["num_bookings"].fillna(0).astype(int)

    # --- Distance computation ---
    cand_df["distance_km"] = haversine_vector(
        user_point.y, user_point.x,
        cand_df["worker_lat"], cand_df["worker_lon"]
    )

    # --- User-related features ---
    cand_df["service_match"] = cand_df["service_id"].apply(lambda sid: 1 if sid in past_services else 0) if not is_new_user else 0
    cand_df["user_worker_bookings"] = cand_df["worker_id"].map(user_worker_counts).fillna(0).astype(int)

    # --- Feature normalization ---
    cand_df["_loc_rank"] = np.exp(-cand_df["distance_km"] / 10)
    cand_df["_num_bookings_rank"] = normalize(cand_df["num_bookings"])
    cand_df["_charge_rank"] = 1 - normalize(cand_df["charge"])
    cand_df["_rating_rank"] = normalize(cand_df["total_rating"])
    cand_df["_service_match_rank"] = cand_df["service_match"]
    cand_df["_user_worker_bookings_rank"] = normalize(cand_df["user_worker_bookings"])

    # --- Score calculation ---
    if is_new_user:
        # Cold-start user (no booking history)
        cand_df["final_rank_score"] = (
            cand_df["_loc_rank"] * 0.7 +
            cand_df["_rating_rank"] * 0.2 +
            cand_df["_charge_rank"] * 0.1
        )
    else:
        # Experienced user (combine multiple signals)
        cand_df["final_rank_score"] = (
            cand_df["_loc_rank"] * 0.4 +
            cand_df["_service_match_rank"] * 0.2 +
            cand_df["_num_bookings_rank"] * 0.15 +
            cand_df["_user_worker_bookings_rank"] * 0.1 +
            cand_df["_charge_rank"] * 0.05 +
            cand_df["_rating_rank"] * 0.1
        )

    # --- Sort & pick top N ---
    top_workers = cand_df.sort_values("final_rank_score", ascending=False).head(top_n)

    return top_workers[[
        "worker_id", "worker_name", "service_name", "worker_lat", "worker_lon",
        "charge", "num_bookings", "total_rating", "distance_km",
        "user_worker_bookings", "service_match", "final_rank_score"
    ]].to_dict(orient="records")


# ---------------------------------------------------------
# 🔹 API Endpoint
# ---------------------------------------------------------
@api_view(['GET'])
def recommend_view(request, user_id):
    """Returns top-N recommended workers for a given user."""
    db = settings.DATABASES['default']
    conn_str = f"postgresql://{db['USER']}:{db['PASSWORD']}@{db['HOST']}:{db['PORT']}/{db['NAME']}"
    engine = create_engine(conn_str, pool_pre_ping=True)

    recommendations = recommend_top_n_for_user(
        int(user_id), recommendation_model, engine, top_n=10
    ) or []

    # --- Fetch worker images ---
    worker_ids = [rec.get("worker_id") for rec in recommendations if isinstance(rec, dict)]
    workers = Worker.objects.filter(id__in=worker_ids)
    serializer = WorkerImageSerializer(workers, many=True, context={'request': request})
    image_map = {item['id']: item['profile_image_url'] for item in serializer.data}

    # --- Merge images ---
    for rec in recommendations:
        if isinstance(rec, dict):
            rec["avatar"] = image_map.get(rec.get("worker_id"))

    return Response({
        "user_id": user_id,
        "count": len(recommendations),
        "recommendations": recommendations
    })

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    user = request.user

    if request.method == 'GET':
        loc = user.location
        loc_json = {"type": "Point", "coordinates": [loc.x, loc.y]} if loc else None
        return Response({
            "id": user.id,
            "email": user.email,
            "username": user.name or user.email.split("@")[0],
            "address": user.address,
            "phone": str(user.phone) if user.phone else None,
            "location": loc_json,
            "profile_complete": all([user.phone, user.address, user.location]),
        })

    elif request.method == 'POST':
        payload = request.data
        key_enc = payload.get('key')
        data_enc = payload.get('data')

        if not key_enc or not data_enc:
            return Response({"error": "Missing encryption data."}, status=400)

        # Decrypt AES key
        aes_key = decrypt_rsa(key_enc)
        if not aes_key:
            return Response({"error": "Invalid encrypted key."}, status=400)

        decrypted = {}
        for field in ['name', 'address', 'phone', 'location']:
            val_enc = data_enc.get(field)
            if val_enc:
                val = decrypt_aes(val_enc, aes_key)
                if val is None:
                    return Response({"error": f"Failed to decrypt {field}."}, status=400)

                # Parse JSON for location
                if field == 'location':
                    try:
                        val = json.loads(val)
                    except Exception:
                        return Response({"error": "Invalid location JSON."}, status=400)
                decrypted[field] = val

        # Update user fields
        if 'name' in decrypted:
            user.name = decrypted['name']
        if 'address' in decrypted:
            user.address = decrypted['address']
        if 'phone' in decrypted:
            user.phone = decrypted['phone']
        if 'location' in decrypted:
            loc = decrypted['location']
            if isinstance(loc, dict) and loc.get('type') == 'Point':
                coords = loc.get('coordinates')
                if (
                    isinstance(coords, list) and len(coords) == 2
                    and all(isinstance(c, (int, float)) for c in coords)
                ):
                    # GEOSPoint takes (x, y) -> (longitude, latitude)
                    user.location = GEOSPoint(coords[0], coords[1])
                else:
                    return Response({"error": "Invalid location coordinates."}, status=400)
            else:
                return Response({"error": "Invalid location format."}, status=400)

        user.save()
        return Response({"message": "Profile updated"})
    
from django.db.models import Prefetch   
class WorkerListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # Prefetch related WorkerServices and their linked Service to optimize queries
        service_prefetch = Prefetch('services', queryset=WorkerService.objects.select_related('service'))
        workers = Worker.objects.prefetch_related(service_prefetch)

        serializer = WorkerSerializer(workers, many=True, context={'request': request})
        return Response(serializer.data)
class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookingSerializer

    def decrypt_aes(self, encrypted_bytes: bytes, aes_key: bytes) -> bytes:
        """
        Decrypt AES-CBC encrypted data (with first 16 bytes as IV).
        Handles padding issues by stripping null bytes if unpad fails.
        """
        if len(encrypted_bytes) < 16:
            raise ValueError("Invalid encrypted data length")

        iv = encrypted_bytes[:16]
        ciphertext = encrypted_bytes[16:]

        remainder = len(ciphertext) % 16
        if remainder != 0:
            ciphertext += b'\x00' * (16 - remainder)

        cipher = AES.new(aes_key, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(ciphertext)

        try:
            decrypted = unpad(decrypted_padded, AES.block_size)
        except ValueError:
            decrypted = decrypted_padded.rstrip(b'\x00')
        return decrypted

    def post(self, request):
        try:
            payload = request.data
            encrypted_key = payload.get("key")
            encrypted_data_str = payload.get("data")

            if not encrypted_key or not encrypted_data_str:
                return Response({"error": "Missing encryption data."}, status=400)

            aes_key = decrypt_rsa(encrypted_key)
            if not aes_key:
                return Response({"error": "Invalid encryption key."}, status=400)

            encrypted_data = json.loads(encrypted_data_str)
            decrypted_map = {}
            for field in ["userId", "workerId", "contactDates", "description", "equipmentRequirement"]:
                enc_field = encrypted_data.get(field)
                if enc_field:
                    enc_bytes = base64.b64decode(enc_field)
                    decrypted_map[field] = self.decrypt_aes(enc_bytes, aes_key).decode("utf-8")


            serializer = BookingCreateSerializer(data={
                    "userId": int(decrypted_map["userId"]),
                    "workerId": int(decrypted_map["workerId"]),
                    "contactDates": json.loads(decrypted_map["contactDates"]),
                    "description": decrypted_map["description"],
                    "equipmentRequirement": decrypted_map.get("equipmentRequirement", ""),
                })

            serializer.is_valid(raise_exception=True)

            user = get_object_or_404(AuthenticatedUser, id=serializer.validated_data["userId"])
            worker = get_object_or_404(Worker, id=serializer.validated_data["workerId"])
            service = worker.services.first().service if worker.services.exists() else None
            if not service:
                return Response({"error": "Worker has no associated service"}, status=400)

            booking = Booking.objects.create(
                user=user,
                worker=worker,
                service=service,
                status="booked",
                job_location=worker.location,
                payment_method="coins",
                details=f"Equipment Requirement: {serializer.validated_data.get('equipmentRequirement', '')}\n"
                        f"Contact Dates: {', '.join(serializer.validated_data['contactDates'])}\n"
                        f"Description: {serializer.validated_data['description']}",

            )

            # Save photos directly without decrypting
            photos = request.FILES.getlist("photos")
            for photo in photos:
                BookingPhoto.objects.create(booking=booking, image=photo)

            return Response({"message": "Booking created successfully"}, status=201)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_booking_history(request):
    user = request.user
    bookings = Booking.objects.filter(user=user, status__in=['booked', 'in_progress', 'completed'])\
              .prefetch_related('tariffs', 'photos').order_by('-booking_time')
    serializer = BookingDetailSerializer(bookings, many=True, context={'request': request})
    return Response(serializer.data)

from rest_framework.exceptions import PermissionDenied

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_booking_detail(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)
    except Booking.DoesNotExist:
        return Response({"detail": "Not found."}, status=404)
    
    if request.user != booking.user and request.user != booking.worker.user:
        raise PermissionDenied("You do not have permission to view this booking.")

    serializer = BookingDetailSerializer(booking, context={'request': request})
    return Response(serializer.data)

class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        if timezone.now() - booking.booking_time > timedelta(minutes=5):
            return Response({"error": "Cancellation period expired."}, status=400)
        booking.status = "cancelled"
        booking.save()
        return Response({"message": "Booking cancelled."})
    
@login_required(login_url='/login/')
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_homepage(request):
    try:
        worker = request.user.worker_profile
        active_job = Booking.objects.filter(worker=worker, status='in_progress').first()
        earnings = Booking.objects.filter(worker=worker, status='completed').order_by('-booking_time')
        pending_requests = Booking.objects.filter(worker=worker, status='booked').order_by('-booking_time')

        active_job_data = JobSerializer(active_job).data if active_job else None
        earnings_data = JobSerializer(earnings, many=True).data
        pending_requests_data = JobSerializer(pending_requests, many=True).data
        settings_data = WorkerDetailedSerializer(worker, context={'request': request}).data


        avg_rating = worker.userreview_set.aggregate(avg=Avg('rating'))['avg'] or 0.0

        data = {
            'activeJob': active_job_data,
            'earnings': earnings_data,
            'pendingRequests': pending_requests_data,
            'settings': settings_data,
            'available': worker.is_available,
            'paymentStatus': active_job.payment_status if active_job else 'pending',
            'average_rating': avg_rating,
        }

        return Response(data)
    except Worker.DoesNotExist:
        logger.error("Worker profile not found for user %s", request.user.email)
        return Response({'detail': 'Worker not found'}, status=404)
    except Exception as e:
        logger.exception("Unexpected error in worker_homepage: %s", e)
        return Response({'detail': 'Error loading worker homepage'}, status=500)


import logging

logger = logging.getLogger(__name__)
from django.db import transaction
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def accept_job(request):
    user = request.user
    job_id = request.data.get('jobId')
    try:
        worker = Worker.objects.get(user=user)
        logger.debug(f'Worker found: {worker.id}')
        if worker.active_job():
            logger.debug('Worker already has an active job.')
            return Response({'detail': 'You already have an active job.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Lock the booking row for update to prevent concurrent accepts
        job = Booking.objects.select_for_update().get(pk=job_id, status='booked')
        logger.debug(f'Booking found: {job.id} with status {job.status}')
        
        job.worker = worker
        job.status = 'in_progress'
        job.save()
        
        worker.is_available = False
        worker.save()
        
        serializer = JobSerializer(job)
        logger.debug(f'Job accepted and updated for worker {worker.id}')
        return Response(serializer.data)
    except Booking.DoesNotExist:
        logger.debug('Booking not found or not available')
        return Response({'detail': 'Job not found or not available'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f'Unexpected error in accept_job: {e}')
        return Response({'detail': 'Error processing request'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Booking
from django.core.exceptions import ObjectDoesNotExist

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_job(request):
    job_id = request.data.get('jobId')

    if not job_id:
        return Response({'error': 'Job ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Allow either worker user or the booking user to mark job as complete
        if hasattr(request.user, 'worker'):
            booking = Booking.objects.get(id=job_id, worker__user=request.user)
        else:
            booking = Booking.objects.get(id=job_id, user=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found or permission denied'}, status=status.HTTP_404_NOT_FOUND)

    if booking.status == 'completed':
        return Response({'message': 'Job already marked completed'}, status=status.HTTP_200_OK)

    booking.status = 'completed'
    booking.save(update_fields=['status'])

    return Response({'message': 'Job marked as completed successfully'}, status=status.HTTP_200_OK)


from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from .models import Booking, Tariff
from .serializer import BookingDetailSerializer, BookingSerializer

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_tariff(request):
    logger = logging.getLogger(__name__)
    logger.debug(f"Received data: {request.data}")
    user = request.user
    job_id = request.data.get('jobId')
    new_tariffs = request.data.get('tariff', [])

    if not job_id:
        return Response({'detail': 'JobId is required'}, status=400)

    if not isinstance(new_tariffs, list):
        return Response({'detail': 'tariff must be a list'}, status=400)

    try:
        booking = Booking.objects.get(id=job_id, worker__user=user)
    except Booking.DoesNotExist:
        return Response({'detail': 'Booking not found'}, status=404)

    existing_tariffs = {t.id: t for t in booking.tariffs.all()}
    total_amount = Decimal('0')

    for item in new_tariffs:
        tariff_id = item.get('id')
        label = item.get('label', '')
        explanation = item.get('explanation', '')
        amount_val = item.get('amount', 0)

        try:
            amount = Decimal(str(amount_val))
        except Exception:
            amount = Decimal('0')

        total_amount += amount

        if tariff_id and tariff_id in existing_tariffs:
            tariff = existing_tariffs.pop(tariff_id)
            tariff.label = label
            tariff.amount = int(amount)
            tariff.explanation = explanation
            tariff.save()
        else:
            Tariff.objects.create(
                booking=booking,
                label=label,
                amount=int(amount),
                explanation=explanation,
            )

    # Remove tariffs not in new list
    for tariff_to_delete in existing_tariffs.values():
        tariff_to_delete.delete()

    booking.total = total_amount
    booking.tariff_coins = int(total_amount)
    booking.save(update_fields=['total', 'tariff_coins'])

    serializer = BookingDetailSerializer(booking, context={'request': request})
    return Response(serializer.data)

from .models import UserRole

def user_has_worker_role(user):
    try:
        user_role = UserRole.objects.get(user=user)
        return user_role.role == 'worker'
    except UserRole.DoesNotExist:
        return False
@api_view(['GET'])
def job_detail(request, pk):
    try:
        job = Booking.objects.get(pk=pk)
    except Booking.DoesNotExist:
        return Response({"error": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = JobSerializer(job)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_receipt(request):
    booking_id = request.data.get('bookingId')

    try:
        if user_has_worker_role(request.user):
            booking = Booking.objects.get(id=booking_id, worker__user=request.user)
        else:
            booking = Booking.objects.get(id=booking_id, user=request.user)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)

    # Prevent sending receipt if payment is done
    if booking.payment_status == 'paid':
        return Response({'error': 'Cannot send receipt after payment is done'}, status=400)

    # Idempotent response if receipt already sent
    if booking.receipt_sent:
        serializer = BookingSerializer(booking, context={'request': request})
        data = serializer.data
        data['message'] = "Receipt already sent."
        return Response(data, status=200)

    # Send receipt for first-time only
    booking.receipt_sent = True
    booking.save(update_fields=['receipt_sent'])

    serializer = BookingSerializer(booking, context={'request': request})
    data = serializer.data
    data['message'] = "Receipt sent successfully."
    return Response(data, status=200)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_job(request):
    # Your existing pay_job implementation
    # Ensure we parse JSON
    job_id = request.data.get('jobId')
    if not job_id:
        return Response(
            {'error': 'jobId is required in request body.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        booking = Booking.objects.get(id=job_id, user=request.user)
    except Booking.DoesNotExist:
        return Response(
            {'error': f'Booking {job_id} not found for this user.'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Ensure tariff lines exist
    if not booking.tariffs.exists():
        return Response(
            {'error': 'No tariff lines set for this booking.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Ensure total is set
    if booking.total is None:
        return Response(
            {'error': 'Total amount is not set for this booking.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Process payment
    booking.payment_status = 'paid'
    booking.payment_received = True
    if booking.status == 'booked':
        booking.status = 'in_progress'
    booking.save(update_fields=['payment_received', 'status'])

    return Response(
        {'message': 'Payment recorded successfully.'},
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_availability(request):
    user = request.user
    available = request.data.get('available')
    try:
        worker = Worker.objects.get(user=user)
        worker.is_available = available
        worker.save()
        return Response({'available': worker.is_available})
    except Worker.DoesNotExist:
        return Response({'detail': 'Worker not found'}, status=status.HTTP_404_NOT_FOUND)
import os
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

#from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.contrib.gis.geos import Point
from .models import Worker

import os
import json

class WorkerSettingsView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # support file uploads

    def get(self, request):
        try:
            worker = Worker.objects.get(user=request.user)
            serializer = WorkerSettingsSerializer(worker)
            return Response(serializer.data)
        except Worker.DoesNotExist:
            return Response({"error": "Worker not found"}, status=404)

    def put(self, request):
        print("PUT method called with data:", request.data)
        try:
            worker = Worker.objects.get(user=request.user)
            print("Worker found:", worker)
        except Worker.DoesNotExist:
            print("Worker not found")
            return Response({"error": "Worker not found"}, status=404)

        data = request.data.copy()

        # Handle JSON input for nested 'user' (email, phone)
        user_json = data.get('user')
        if user_json and isinstance(user_json, str):
            try:
                data['user'] = json.loads(user_json)
            except json.JSONDecodeError:
                return Response({'user': ['Invalid JSON.']}, status=400)

        # Update profile image
        new_image = data.get('profile_image') or request.FILES.get('profile_image')
        if new_image:
            if worker.profile_image and os.path.exists(worker.profile_image.path):
                os.remove(worker.profile_image.path)
            worker.profile_image = new_image

        # Update location from JSON string or dict
        loc_data = data.get('location')
        if loc_data:
            # If it's a string (from FormData), parse it
            if isinstance(loc_data, str):
                try:
                    loc_data = json.loads(loc_data)
                except json.JSONDecodeError:
                    loc_data = None
            if loc_data and isinstance(loc_data, dict) and loc_data.get('type') == 'Point':
                coords = loc_data.get('coordinates', [])
                if len(coords) == 2:
                    worker.location = Point(coords[0], coords[1])

        # Update editable fields in Worker
        for field in ['is_available', 'allows_cod', 'experience_years', 'address']:
            if field in data:
                setattr(worker, field, data[field])

        # Update nested user fields (email, phone)
        user_data = data.get('user', {})
        if user_data:
            if 'email' in user_data:
                worker.user.email = user_data['email']
            if 'phone' in user_data:
                worker.user.phone = user_data['phone']
            worker.user.save()

        print("Before save, address:", worker.address)
        worker.save()
        print("After save, address:", worker.address)

        serializer = WorkerSettingsSerializer(worker)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_booking_detail(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
        serializer = BookingDetailSerializer(booking, context={'request': request})
        return Response(serializer.data)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)


client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_razorpay_order(request):
    booking_id = request.data.get('bookingId')
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
        if booking.payment_received:
            return Response({'error': 'Already paid'}, status=400)
        if booking.total is None or booking.total <= 0:
            return Response({'error': 'Invalid total amount for payment'}, status=400)

        amount_paise = int(booking.total * 100)
        razorpay_order = client.order.create(dict(
            amount=amount_paise,
            currency="INR",
            payment_capture=1,
            notes={
                "booking_id": str(booking.id),
                "user_id": str(request.user.id),
            }
        ))

        # Create or update RazorpayPayment linked to booking
        razorpay_payment, created = RazorpayPayment.objects.get_or_create(booking=booking)
        razorpay_payment.razorpay_order_id = razorpay_order['id']
        razorpay_payment.status = 'created'
        razorpay_payment.save()

        booking.payment_method = 'online'
        booking.payment_status = 'pending'
        booking.save(update_fields=['payment_method', 'payment_status'])
        booking.status = "progress"  # update the status here
        booking.save(update_fields=['payment_received', 'payment_status', 'status'])
        return Response({
            'order_id': razorpay_order['id'],
            'amount': amount_paise,
            'currency': 'INR',
            'key': settings.RAZORPAY_KEY_ID,
            'receipt': f'Booking_{booking.id}_Receipt'
        })

    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=404)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    data = request.data
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    booking_id = data.get('bookingId')

    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature, booking_id]):
        return Response({"error": "Missing payment parameters"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
    except Booking.DoesNotExist:
        return Response({"error": "Booking not found"}, status=status.HTTP_404_NOT_FOUND)

    msg = razorpay_order_id + "|" + razorpay_payment_id
    expected_signature = hmac.new(
        key=bytes(settings.RAZORPAY_KEY_SECRET, 'utf-8'),
        msg=bytes(msg, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()

    if expected_signature != razorpay_signature:
        return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

    RazorpayPayment.objects.update_or_create(
        booking=booking,
        defaults={
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
            "status": "paid",
        },
    )

    booking.payment_method = 'online'
    booking.payment_received = True
    booking.payment_status = 'paid'
    booking.status = 'in_progress'  # Update status as needed
    booking.save(update_fields=['payment_method', 'payment_received', 'payment_status', 'status'])

    return Response({"message": "Payment verified successfully"})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_cod_payment(request):
    booking_id = request.data.get('bookingId')
    try:
        booking = Booking.objects.get(id=booking_id, user=request.user)
        booking.payment_method = 'cod'
        booking.payment_status = 'pending'
        booking.payment_received = False
        booking.save(update_fields=['payment_method', 'payment_status', 'payment_received'])
        return Response({'message': 'COD payment method set. Please pay during service.'})
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_cod_payment(request):
    booking_id = request.data.get('bookingId')
    try:
        worker = Worker.objects.get(user=request.user)  # get Worker from user
        booking = Booking.objects.get(id=booking_id, worker=worker)
        if booking.payment_method != 'cod':
            return Response({'error': 'Booking is not COD type'}, status=status.HTTP_400_BAD_REQUEST)
        booking.payment_status = 'paid'
        booking.payment_received = True
        booking.status = 'completed'  # Change status to completed on payment confirm
        booking.save(update_fields=['payment_status', 'payment_received', 'status'])
        return Response({'detail': 'COD payment confirmed and job completed'})
    except Worker.DoesNotExist:
        return Response({'error': 'Worker profile not found'}, status=status.HTTP_404_NOT_FOUND)
    except Booking.DoesNotExist:
        return Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)


from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Booking, WorkerEarning

from django.db.models import Q
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def complete_job(request):
    print("Complete job called by user:", request.user)
    job_id = request.data.get('jobId')
    print("Job ID:", job_id)
    try:
        job = Booking.objects.get(id=job_id, worker__user=request.user, status='in_progress')
        print("Found job:", job)
    except Booking.DoesNotExist:
        print("Job not found or not assigned to user")
        return Response({'detail': 'Active job not found'}, status=status.HTTP_404_NOT_FOUND)

    job.status = 'completed'
    job.completed_at = timezone.now()
    job.save(update_fields=['status', 'completed_at'])

    if not WorkerEarning.objects.filter(booking=job).exists():
        WorkerEarning.objects.create(worker=job.worker, booking=job, amount=job.total)

    job.worker.is_available = True
    job.worker.save(update_fields=['is_available'])

    print("Job marked as completed")
    return Response({'detail': 'Job marked as complete.'}, status=status.HTTP_200_OK)


 
@receiver(post_save, sender=Booking)
def create_worker_earning_on_complete(sender, instance, created, **kwargs):
    if (
        instance.status == 'completed'
        and instance.payment_received
        and not WorkerEarning.objects.filter(booking=instance).exists()
        and instance.worker
    ):
        WorkerEarning.objects.create(
            worker=instance.worker,
            booking=instance,
            amount=int(instance.tariff_coins or instance.total or 0)
        )
   
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def worker_earnings_list(request):
    try:
        worker = request.user.worker_profile
    except ObjectDoesNotExist:
        return Response({'error': 'User is not a worker.'}, status=status.HTTP_400_BAD_REQUEST)

    earnings = WorkerEarning.objects.filter(worker=worker).select_related(
        'booking', 'booking__service', 'booking__user'
    )

    serializer = WorkerEarningSerializer(earnings, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_rating(request):
    user = request.user
    booking_id = request.data.get('booking')
    rating_value = request.data.get('rating')

    if not booking_id or rating_value is None:
        return Response({'error': 'booking and rating fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        rating_value = int(rating_value)
        if not (1 <= rating_value <= 5):
            return Response({'error': 'Rating must be between 1 and 5.'}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError:
        return Response({'error': 'Rating must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

    booking = get_object_or_404(Booking, id=booking_id, user=user)

    if booking.payment_status != 'paid':
        return Response({'error': 'Rating is allowed only after successful payment.'}, status=status.HTTP_403_FORBIDDEN)

    # Update existing review or create a new one
    review, created = UserReview.objects.update_or_create(
        user=user,
        booking=booking,
        defaults={
            'worker': booking.worker,
            'rating': rating_value,
        }
    )

    serializer = UserReviewRatingSerializer(review)
    if created:
        return Response({'message': 'Rating submitted successfully.', 'review': serializer.data}, status=status.HTTP_201_CREATED)
    else:
        return Response({'message': 'Rating updated successfully.', 'review': serializer.data}, status=status.HTTP_200_OK)
    




from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.chatbot_inference import chatbot_response as get_bot_reply

@api_view(['POST'])
def chatbot_response_view(request):
    """
    Django REST Framework view for chatbot.
    Expects JSON: { "message": "user input" }
    Returns JSON: { "response": "bot reply" }
    """
    message = request.data.get("message", "").strip()
    
    if not message:
        return Response({"response": "Please enter a message."})
    
    try:
        # Use the same ML + fuzzy + synonyms logic from chatbot_inference.py
        reply = get_bot_reply(message)
    except Exception as e:
        reply = f"Sorry, an error occurred: {str(e)}"
    
    return Response({"response": reply})

# views.py
import asyncio
from django.http import StreamingHttpResponse
from django.utils import timezone

async def sse_stream(request):
    async def event_stream():
        # Send initial event immediately
        yield f"data: {timezone.now().isoformat()}\n\n".encode("utf-8")

        while True:
            await asyncio.sleep(2)  # wait before next event
            yield f"data: {timezone.now().isoformat()}\n\n".encode("utf-8")

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response['Cache-Control'] = 'no-cache'  # disable caching
    return response
# admin/views.py
from datetime import timedelta
import csv
import json

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count
from django.db.models.functions import TruncDay
from django.http import JsonResponse, HttpResponse
from django.utils.timezone import now
from django.views.decorators.http import require_GET

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

from core.models import AuthenticatedUser, Worker, Booking
from core.serializer import UserSerializer, WorkerSerializer, BookingSerializer, VerifierCreateSerializer


# -----------------------------
# Admin Check Decorator
# -----------------------------
def admin_check(user):
    return user.is_staff or user.is_superuser


# -----------------------------
# Helper: Get last N days
# -----------------------------
def get_last_n_days(n=7):
    today = now().date()
    start_day = today - timedelta(days=n - 1)
    return [start_day + timedelta(days=i) for i in range(n)]


# -----------------------------
# Helper: Calculate growth counts
# -----------------------------
def get_growth_counts(queryset, date_field, date_list):
    qs = (
        queryset.filter(**{f"{date_field}__date__gte": date_list[0]})
        .annotate(day=TruncDay(date_field))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    counts_map = {item['day'].strftime('%Y-%m-%d'): item['count'] for item in qs}
    return [counts_map.get(day.strftime('%Y-%m-%d'), 0) for day in date_list]


@login_required
@user_passes_test(admin_check)
@require_GET
def admin_dashboard_api(request):
    date_list = get_last_n_days(7)

    # Admin Info
    admin_data = {
        "name": getattr(request.user, "name", "") or f"{getattr(request.user, 'first_name', '')} {getattr(request.user, 'last_name', '')}".strip(),
        "email": getattr(request.user, "email", ""),
        "phone": str(getattr(request.user, "phone", "")),
        "address": getattr(request.user, "address", ""),
        "location": {
            "lat": request.user.location.y if request.user.location else None,
            "lng": request.user.location.x if request.user.location else None
        } if request.user.location else None,
        "is_verifier": request.user.is_verifier
    }

    # Core counts
    total_users = AuthenticatedUser.objects.count()
    total_workers = Worker.objects.count()
    total_bookings = Booking.objects.count()
    completed_bookings = Booking.objects.filter(status='completed').count()
    pending_bookings = Booking.objects.filter(status='pending').count()
    cancelled_bookings = Booking.objects.filter(status='cancelled').count()

    # User & Worker growth
    user_growth_counts = get_growth_counts(AuthenticatedUser.objects, 'date_joined', date_list)
    worker_growth_counts = get_growth_counts(Worker.objects, 'approved_at', date_list)

    # Booking growth
    booking_growth = []
    for day in date_list:
        day_start = now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=(7 - date_list.index(day) - 1))
        day_end = day_start + timedelta(days=1)
        day_bookings = Booking.objects.filter(booking_time__gte=day_start, booking_time__lt=day_end)
        booking_growth.append({
            'date': day.strftime('%Y-%m-%d'),
            'completed': day_bookings.filter(status='completed').count(),
            'pending': day_bookings.filter(status='pending').count(),
            'cancelled': day_bookings.filter(status='cancelled').count()
        })

    # Worker availability
    available_workers = Worker.objects.filter(is_available=True).count()
    unavailable_workers = total_workers - available_workers

    # Top 5 workers by average rating
    top_workers_qs = Worker.objects.annotate(avg_rating=Count('userreview__rating')).order_by('-avg_rating')[:5]
    top_workers = [
        {
            'id': worker.id,
            'name': worker.user.name if worker.user else f"Worker {worker.id}",
            'average_rating': getattr(worker, 'avg_rating', 0),
            'services': [s.service.service_type for s in worker.services.all()]
        }
        for worker in top_workers_qs
    ]

    payload = {
        "admin": admin_data,  # send full admin info
        "total_users": total_users,
        "total_workers": total_workers,
        "total_bookings": total_bookings,
        "completed_bookings": completed_bookings,
        "pending_bookings": pending_bookings,
        "cancelled_bookings": cancelled_bookings,
        "user_growth_dates": [d.strftime('%Y-%m-%d') for d in date_list],
        "user_growth_counts": user_growth_counts,
        "worker_growth_dates": [d.strftime('%Y-%m-%d') for d in date_list],
        "worker_growth_counts": worker_growth_counts,
        "booking_growth": booking_growth,
        "worker_availability": {
            "available": available_workers,
            "unavailable": unavailable_workers
        },
        "top_workers": top_workers
    }

    return JsonResponse(payload)


# -----------------------------
# CSV Report Download
# -----------------------------
@login_required
@user_passes_test(admin_check)
@require_GET
def admin_download_report(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="admin_dashboard_report.csv"'

    writer = csv.writer(response)
    writer.writerow([f"Admin Dashboard Report - {now().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([])

    # Summary Metrics
    metrics = {
        'Total Users': AuthenticatedUser.objects.count(),
        'Total Workers': Worker.objects.count(),
        'Total Bookings': Booking.objects.count(),
        'Completed Bookings': Booking.objects.filter(status='completed').count(),
        'Pending Bookings': Booking.objects.filter(status='pending').count(),
    }
    writer.writerow(['Metric', 'Value'])
    for k, v in metrics.items():
        writer.writerow([k, v])

    # Growth Data
    date_list = get_last_n_days(7)
    user_growth = get_growth_counts(AuthenticatedUser.objects, 'date_joined', date_list)
    worker_growth = get_growth_counts(Worker.objects, 'approved_at', date_list)

    writer.writerow([])
    writer.writerow(['Date', 'New Users', 'New Workers'])
    for i, day in enumerate(date_list):
        writer.writerow([day.strftime('%Y-%m-%d'), user_growth[i], worker_growth[i]])

    return response


# -----------------------------
# DRF APIs: List Users/Workers/Bookings
# -----------------------------
@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_list_users(request):
    users = AuthenticatedUser.objects.all()
    serializer = UserSerializer(users, many=True, context={'request': request})
    return Response({"users": serializer.data})


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_list_workers(request):
    workers = Worker.objects.select_related('user').prefetch_related('services__service').all()
    serializer = WorkerSerializer(workers, many=True, context={'request': request})
    return Response({"workers": serializer.data})

@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_list_bookings(request):
    bookings = Booking.objects.select_related('user', 'worker', 'service') \
                              .prefetch_related('tariffs') \
                              .all()
    serializer = BookingSerializer(bookings, many=True, context={'request': request})
    return Response({"bookings": serializer.data})
    

# -----------------------------
# Add Verifier
# -----------------------------

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .models import WorkerApplication

class WorkerApplicationView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = WorkerApplicationSerializer(data=request.data)
        if serializer.is_valid():
            application = serializer.save()
            return Response({'message': 'Application submitted', 'id': application.id}, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)  # Print errors to console for debugging
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def put(self, request, pk):
        try:
            application = WorkerApplication.objects.get(pk=pk)
        except WorkerApplication.DoesNotExist:
            return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = WorkerApplicationSerializer(application, data=request.data, partial=True)
        if serializer.is_valid():
            updated_application = serializer.save()
            return Response({'message': 'Application updated', 'id': updated_application.id})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
import razorpay
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .models import WorkerApplication, RazorpayPayment

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CreatePaymentOrderView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        booking_id = request.data.get('booking_id')
        application_id = request.data.get('worker_application_id')

        if booking_id:
            try:
                booking_instance = Booking.objects.get(id=booking_id)
            except Booking.DoesNotExist:
                return Response({'error': 'Invalid booking ID'}, status=status.HTTP_404_NOT_FOUND)
        else:
            booking_instance = None

        if application_id:
            try:
                application = WorkerApplication.objects.get(id=application_id)
            except WorkerApplication.DoesNotExist:
                return Response({'error': 'Invalid application ID'}, status=status.HTTP_404_NOT_FOUND)
        else:
            application = None

        order = client.order.create({
            'amount': 15000,  # 150 INR in paise
            'currency': 'INR',
            'payment_capture': 1
        })

        payment, created = RazorpayPayment.objects.get_or_create(
            booking=booking_instance,
            worker_application=application,
            defaults={'razorpay_order_id': order['id'], 'status': 'created'}
        )
        if not created:
            payment.razorpay_order_id = order['id']
            payment.status = 'created'
            payment.save()

        return Response({'order_id': order['id'], 'amount': order['amount'], 'currency': order['currency']})


class VerifyPaymentView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        data = request.data
        params_dict = {
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        }

        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            return Response({'error': 'Signature verification failed'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = RazorpayPayment.objects.get(razorpay_order_id=params_dict['razorpay_order_id'])
        except RazorpayPayment.DoesNotExist:
            return Response({'error': 'Payment record not found'}, status=status.HTTP_404_NOT_FOUND)

        payment.razorpay_payment_id = params_dict['razorpay_payment_id']
        payment.razorpay_signature = params_dict['razorpay_signature']
        payment.status = 'paid'
        payment.save()

        # Update payment received status based on linked object
        if payment.booking:
            booking = payment.booking
            booking.payment_received = True
            booking.save()
        elif payment.worker_application:
            application = payment.worker_application
            application.coins_paid = True
            application.save()

        return Response({'message': 'Payment verified successfully'})
    
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from .permissions import IsVerifier1  # Temporarily for testing
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from .models import (
    WorkerApplication, 
    Verifier1Review,
    VerificationWorkflowLog
)
from .serializer import (
    WorkerApplicationListSerializer,
    WorkerApplicationDetailSerializer,
    Verifier1ReviewSerializer,
    VerificationWorkflowLogSerializer
)
from django.db.models import Q, Exists, OuterRef
# Temporarily using AllowAny for testing
# Change to IsVerifier1 when permissions are set up
# from .permissions import IsVerifier1


class Verifier1ApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for Verifier 1 to view applications assigned to them
    """
    permission_classes = [IsVerifier1]  # TODO: Change to [IsVerifier1]
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkerApplicationDetailSerializer
        return WorkerApplicationListSerializer
    
    def get_queryset(self):
        """
        Get applications for Stage 1 review
        Shows:
        1. Pending applications (not reviewed yet)
        2. Submitted applications (reviewed within last 2 days - editable)
        """
        two_days_ago = timezone.now() - timedelta(days=2)
        
        # Annotate with review status
        queryset = WorkerApplication.objects.annotate(
            has_recent_review=Exists(
                Verifier1Review.objects.filter(
                    application=OuterRef('pk'),
                    submitted_at__gte=two_days_ago  # ✅ Changed from completed_at to submitted_at
                )
            )
        ).filter(
            Q(stage1_completed=False) |  # Pending
            Q(stage1_completed=True, has_recent_review=True)  # Recently submitted
        ).order_by('-applied_at')
        
        # Filter by status if provided
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            if status_filter == 'pending':
                queryset = queryset.filter(stage1_completed=False)
            elif status_filter == 'submitted':
                queryset = queryset.filter(stage1_completed=True, has_recent_review=True)
            else:
                queryset = queryset.filter(application_status=status_filter)
        
        # Filter by location
        location_filter = self.request.query_params.get('location', None)
        if location_filter:
            queryset = queryset.filter(address__icontains=location_filter)
        
        # Search by name or email
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(email__icontains=search)
            )
        
        return queryset
            
    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Get all document URLs for an application"""
        application = self.get_object()
        
        def get_url(field):
            """Helper to safely get file URL with full path"""
            if field:
                try:
                    # Build full URL including domain
                    if field.url:
                        # Check if it's already a full URL
                        if field.url.startswith('http'):
                            return field.url
                        else:
                            # Build full URL with request domain
                            return request.build_absolute_uri(field.url)
                except Exception as e:
                    print(f"Error getting URL for field: {e}")
                    return None
            return None
        
        documents = {
            'photo_id': get_url(application.photo_id_path),
            'aadhaar_card': get_url(application.aadhaar_card),
            'union_card': get_url(application.union_card_path),
            'certifications': get_url(application.certifications),
            'signature_copy': get_url(application.signature_copy),
        }
        
        return Response(documents)

    
    @action(detail=True, methods=['get'])
    def review_status(self, request, pk=None):
        """Get current review status for this application"""
        application = self.get_object()
        
        try:
            review = Verifier1Review.objects.get(application=application)
            serializer = Verifier1ReviewSerializer(review)
            return Response(serializer.data)
        except Verifier1Review.DoesNotExist:
            # Return empty response instead of 404
            return Response({
                'exists': False,
                'message': 'No review exists yet for this application'
            }, status=status.HTTP_200_OK)  # Changed from 404 to 200
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """Get verification logs for this application"""
        application = self.get_object()
        logs = VerificationWorkflowLog.objects.filter(
            application=application,
            stage=1
        ).order_by('-created_at')
        
        serializer = VerificationWorkflowLogSerializer(logs, many=True)
        return Response(serializer.data)


class Verifier1ReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for creating and updating Verifier1Review
    """
    serializer_class = Verifier1ReviewSerializer
    permission_classes = [IsVerifier1]  # TODO: Change to [IsVerifier1]
    
    def get_queryset(self):
        """Get all reviews"""
        return Verifier1Review.objects.all().order_by('-assigned_at')
    
    def perform_create(self, serializer):
        """Create review and mark submission timestamp"""
        if self.request.user.is_authenticated:
            verifier = self.request.user
        else:
            verifier = AuthenticatedUser.objects.first()
            if not verifier:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'error': 'No users exist'})
        
        application_id = self.request.data.get('application')
        application = get_object_or_404(WorkerApplication, id=application_id)
        
        if Verifier1Review.objects.filter(application=application).exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'application': 'Review already exists'})
        
        if not application.verifier1_assigned:
            application.verifier1_assigned = verifier
        
        review_status = self.request.data.get('status', 'pending')
        
        if review_status == 'approved':
            application.stage1_completed = True
            application.current_stage = 2
            application.application_status = 'stage1_completed'
        elif review_status == 'rejected':
            application.stage1_completed = True
            application.application_status = 'stage1_rejected'
        else:
            application.application_status = 'stage1_review'
        
        application.save()
        
        # Save review with submission timestamp
        serializer.save(
            verifier=verifier,
            submitted_at=timezone.now()  # ✅ Changed from completed_at to submitted_at
        )

    def perform_update(self, serializer):
        """Update review - only allow within 2 days"""
        review = self.get_object()
        two_days_ago = timezone.now() - timedelta(days=2)
        
        # Check if editable (within 2 days)
        if review.submitted_at and review.submitted_at < two_days_ago:  # ✅ Changed from completed_at
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'error': 'Cannot edit review older than 2 days'})
        
        # Update application based on new status
        review_status = self.request.data.get('status', review.status)
        application = review.application
        
        if review_status == 'approved':
            application.stage1_completed = True
            application.current_stage = 2
            application.application_status = 'stage2_review'  # Set to stage 2 review status
        elif review_status == 'rejected':
            application.stage1_completed = True
            application.application_status = 'stage1_rejected'

        application.save()
        serializer.save()


    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get statistics for verifier dashboard"""
        try:
            two_days_ago = timezone.now() - timedelta(days=2)
            
            total_reviewed = Verifier1Review.objects.count()
            approved = Verifier1Review.objects.filter(status='approved').count()
            rejected = Verifier1Review.objects.filter(status='rejected').count()
            pending = WorkerApplication.objects.filter(stage1_completed=False).count()
            
            # Recently submitted (editable within 2 days)
            recently_submitted = Verifier1Review.objects.filter(
                submitted_at__gte=two_days_ago  # ✅ Changed from completed_at to submitted_at
            ).count()
            
            approval_rate = round((approved / total_reviewed * 100) if total_reviewed > 0 else 0, 2)
            
            return Response({
                'total_reviewed': total_reviewed,
                'approved': approved,
                'rejected': rejected,
                'pending': pending,
                'recently_submitted': recently_submitted,
                'approval_rate': approval_rate
            })
        except Exception as e:
            return Response({
                'error': str(e),
                'total_reviewed': 0,
                'approved': 0,
                'rejected': 0,
                'pending': 0,
                'recently_submitted': 0,
                'approval_rate': 0
            })
# views_verifier2.py
from datetime import timedelta
import random
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Exists, OuterRef

from .models import WorkerApplication, Verifier2Review, Verifier1Review, IdentityDocument
from .serializer import (
    WorkerApplicationListSerializer,
    WorkerApplicationDetailSerializer,
    WorkerApplicationSerializer,
    IdentityDocumentSerializer,
    Verifier2ReviewSerializer,
    Verifier1ReviewSerializer
)
from .permissions import IsVerifier2
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
import random

# --------------------------------------------------------
# 📘 VERIFIER 2 APPLICATION VIEWSET
# --------------------------------------------------------
class Verifier2ApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Application listing for Verifier 2 (Stage 2+).
    Supports search, location, and status filters.
    Approved applications (stage 3) remain visible.
    """

    permission_classes = [IsAuthenticated, IsVerifier2]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkerApplicationDetailSerializer
        return WorkerApplicationListSerializer

    def get_queryset(self):
        # Include all stage 2 and stage 3 applications
        queryset = WorkerApplication.objects.select_related(
            'verifier2_review', 'verifier1_review'
        ).filter(
            Q(stage1_completed=True) &
            Q(current_stage__gte=2)  # Stage 2 or higher
        ).order_by('-applied_at')

        # --- Search filter (by name/email)
        search = (self.request.query_params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(email__icontains=search))

        # --- Status filter
        status_filter = (self.request.query_params.get('application_status') or
                         self.request.query_params.get('status') or '').strip().lower()
        if status_filter:
            if status_filter in ['pending', 'stage2_review']:
                queryset = queryset.filter(application_status='stage2_review')
            elif status_filter in ['approved', 'stage3_review', 'stage2_approved']:
                queryset = queryset.filter(application_status='stage3_review')
            elif status_filter in ['rejected', 'stage2_rejected']:
                queryset = queryset.filter(application_status='stage2_rejected')
            else:
                queryset = queryset.filter(application_status=status_filter)

        # --- Location filter
        location_filter = (self.request.query_params.get('location') or '').strip()
        if location_filter:
            queryset = queryset.filter(address__icontains=location_filter)

        return queryset

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsVerifier2])
    def documents(self, request, pk=None):
        application = self.get_object()
        docs = IdentityDocument.objects.filter(application=application)
        serializer = IdentityDocumentSerializer(docs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsVerifier2])
    def review_status(self, request, pk=None):
        application = self.get_object()
        review = Verifier2Review.objects.filter(application=application).first()
        if review:
            serializer = Verifier2ReviewSerializer(review, context={'request': request})
            return Response(serializer.data)
        return Response({'exists': False}, status=status.HTTP_200_OK)

    # -----------------------------
    # 🔹 List all approved (stage 3) applications
    # -----------------------------
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsVerifier2])
    def approved_list(self, request):
        approved_apps = WorkerApplication.objects.filter(application_status='stage3_review').order_by('-applied_at')
        serializer = WorkerApplicationListSerializer(approved_apps, many=True, context={'request': request})
        return Response(serializer.data)


# --------------------------------------------------------
# 📗 VERIFIER 2 REVIEW VIEWSET
# --------------------------------------------------------
class Verifier2ReviewViewSet(viewsets.ModelViewSet):
    queryset = Verifier2Review.objects.all().select_related('application', 'verifier')
    serializer_class = Verifier2ReviewSerializer
    permission_classes = [IsAuthenticated, IsVerifier2]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['application__name', 'application__email']

    def partial_update(self, request, *args, **kwargs):
        review = self.get_object()
        if not review.verifier:
            review.verifier = request.user
            review.save(update_fields=['verifier'])

        serializer = self.get_serializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(verifier=request.user)
        review.refresh_from_db()

        app = review.application

        # 🔄 Status transitions
        if review.status == 'approved':
            app.application_status = 'stage3_review'
            app.current_stage = 3
            app.stage2_completed = True
            app.stage2_completed_at = timezone.now()
        elif review.status == 'rejected':
            app.application_status = 'stage2_rejected'
            app.stage2_completed = True
            app.stage2_completed_at = timezone.now()
        else:
            app.application_status = 'stage2_review'

        app.save(update_fields=['application_status', 'current_stage', 'stage2_completed', 'stage2_completed_at'])
        return Response(self.get_serializer(review).data)

    # -----------------------------
    # 🔐 OTP MANAGEMENT
    # -----------------------------
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsVerifier2])
    def send_otp(self, request, pk=None):
        review = self.get_object()
        otp_code = str(random.randint(100000, 999999))
        review.otp_code = otp_code
        review.otp_sent = True
        review.save(update_fields=['otp_code', 'otp_sent'])

        try:
            send_mail(
                subject="Your Verification OTP",
                message=f"Your OTP is {otp_code}",
                from_email='no-reply@yourdomain.com',
                recipient_list=[review.application.email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({'message': 'OTP sent successfully'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsVerifier2])
    def verify_otp(self, request, pk=None):
        review = self.get_object()
        input_otp = request.data.get('otp_code')
        if input_otp and review.otp_code and input_otp == review.otp_code:
            review.otp_verified = True
            review.otp_code = None
            review.save(update_fields=['otp_verified', 'otp_code'])
            return Response({'verified': True})
        return Response({'verified': False}, status=status.HTTP_400_BAD_REQUEST)

    # -----------------------------
    # 📊 DASHBOARD STATISTICS
    # -----------------------------
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsVerifier2])
    def statistics(self, request):
        # All stage 2+ applications
        stage2_apps = WorkerApplication.objects.filter(current_stage__gte=2)
        reviews = Verifier2Review.objects.filter(application__in=stage2_apps)

        total_reviewed = reviews.filter(status__in=['approved', 'rejected']).count()
        approved = reviews.filter(status='approved').count()
        rejected = reviews.filter(status='rejected').count()
        pending = stage2_apps.exclude(Q(verifier2_review__status='approved') | Q(verifier2_review__status='rejected')).count()
        approval_rate = round((approved / total_reviewed * 100) if total_reviewed else 0, 2)

        return Response({
            "total_reviewed": total_reviewed,
            "approved": approved,
            "rejected": rejected,
            "pending": pending,
            "approval_rate": approval_rate,
            "total_applications": stage2_apps.count(),
        })


# views_verifier3.py
from datetime import timedelta
import random
import string
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q

from .models import WorkerApplication, Verifier3Review, AuthenticatedUser, Worker, UserRole
from .serializer import (
    WorkerApplicationListSerializer,
    WorkerApplicationDetailSerializer,
    WorkerApplicationSerializer,
    Verifier3ReviewSerializer
)
from .permissions import IsVerifier3
from rest_framework.permissions import IsAuthenticated

EDITABLE_WINDOW_DAYS = 2

class Verifier3ApplicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Application listing for Verifier 3 (Stage 3).
    - list: WorkerApplication list (stage3 scope), supports search/status/location filters
    - retrieve: detailed WorkerApplication serializer (with Verifier2 + Verifier3 data)
    - documents: return uploaded documents for a specific application
    - review_status: check if Verifier3Review exists
    """
    permission_classes = [IsAuthenticated, IsVerifier3]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return WorkerApplicationDetailSerializer
        return WorkerApplicationListSerializer




    def get_queryset(self):
        two_days_ago = timezone.now() - timedelta(days=2)
        queryset = WorkerApplication.objects.select_related(
            'verifier1_review', 'verifier2_review', 'verifier3_review'
        ).filter(
            Q(stage2_completed=True)
            & (
                Q(current_stage=3)
                | Q(application_status__in=['stage3_review', 'stage3_rejected'])
                | Q(application_status='approved', approved_at__gte=two_days_ago)   # ✅ keep approved 2 days
            )
        ).order_by('-applied_at')
        # --- Search (by name or email) ---
        search = (self.request.query_params.get('search') or '').strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(email__icontains=search))

        # --- Status Filter ---
        status_filter = (
            self.request.query_params.get('application_status')
            or self.request.query_params.get('status')
            or ''
        ).strip().lower()

        if status_filter:
            status_map = {
                'pending': 'stage3_review',
                'review': 'stage3_review',
                'approved': 'approved',
                'rejected': 'stage3_rejected',
            }
            mapped_status = status_map.get(status_filter, status_filter)
            queryset = queryset.filter(application_status=mapped_status)

        # --- Location Filter ---
        location_filter = (self.request.query_params.get('location') or '').strip()
        if location_filter:
            queryset = queryset.filter(address__icontains=location_filter)

        return queryset

    # =======================
    # Extra endpoints
    # =======================

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsVerifier3])
    def documents(self, request, pk=None):
        """Return identity documents for this application."""
        application = self.get_object()
        docs = IdentityDocument.objects.filter(application=application)
        serializer = IdentityDocumentSerializer(docs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsVerifier3])
    def review_status(self, request, pk=None):
        """Return Verifier3Review status or exists=False if not yet created."""
        application = self.get_object()
        review = Verifier3Review.objects.filter(application=application).first()
        if review:
            
            serializer = Verifier3ReviewSerializer(review, context={'request': request})
            return Response(serializer.data)
        return Response({'exists': False}, status=status.HTTP_200_OK)


class Verifier3ReviewViewSet(viewsets.ModelViewSet):
    """
    Manage Verifier3Review objects:
    - partial_update applies final approval / rejection and triggers worker account creation
    - dashboard returns unified stats
    """
    queryset = Verifier3Review.objects.all().order_by('-assigned_at')
    serializer_class = Verifier3ReviewSerializer
    permission_classes = [IsAuthenticated, IsVerifier3]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['application__name', 'application__email']

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        review = self.get_object()

        serializer = self.get_serializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        review = serializer.save(verifier=request.user)
        review.refresh_from_db()

        app = review.application
        auth_user_instance = None

        if review.status == "approved" and not app.assigned_worker:
            # Generate raw password and hashed representation (do not store raw password permanently)
            raw_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            hashed_password = make_password(raw_password)

            user_obj, created = AuthenticatedUser.objects.get_or_create(
                email=app.email,
                defaults={
                    'name': app.name,
                    'phone': app.phone,
                    'is_active': True
                }
            )

            if created:
                # set password and save
                user_obj.set_password(raw_password)
                user_obj.save(update_fields=['password', 'is_active'])
                # ensure worker role
                UserRole.objects.get_or_create(user=user_obj, role='worker')
                # create worker profile
                Worker.objects.get_or_create(
                    user=user_obj,
                    defaults={
                        'application': app,
                        'location': app.location,
                        'address': app.address,
                        'is_available': True,
                        'experience_years': 0,
                        'approved_at': timezone.now()
                    }
                )

            # link worker to application
            worker = Worker.objects.filter(user=user_obj).first()
            if worker:
                app.assigned_worker = worker

            # update application flags / status
            app.password_generated = hashed_password
            app.approved_at = timezone.now()
            app.application_status = 'approved'
            app.is_fully_verified = True
            app.stage3_completed = True
            app.stage3_completed_at = timezone.now()
            app.save(update_fields=[
                'assigned_worker', 'password_generated', 'approved_at',
                'application_status', 'is_fully_verified', 'stage3_completed', 'stage3_completed_at'
            ])

            # optionally send credentials email (wrap try/except)
            try:
                send_mail(
                    subject="Your Worker Account",
                    message=f"Username: {user_obj.email}\nPassword: {raw_password}",
                    from_email='no-reply@yourdomain.com',
                    recipient_list=[user_obj.email],
                    fail_silently=False
                )
                review.notification_sent = True
            except Exception:
                pass

            auth_user_instance = user_obj

        elif review.status == "rejected":
            app.application_status = 'stage3_rejected'
            app.stage3_completed = True
            app.stage3_completed_at = timezone.now()
            app.save(update_fields=['application_status', 'stage3_completed', 'stage3_completed_at'])

        # Save review changes
        review.save(update_fields=['status', 'notification_sent', 'worker_id_assigned', 'password_generated_by_admin'])

        out = self.get_serializer(review).data
        if auth_user_instance:
            out['created_user'] = {'id': auth_user_instance.id, 'email': auth_user_instance.email}
        return Response(out, status=status.HTTP_200_OK)

    # -------------------------
    # Dashboard statistics (unified format)
    # -------------------------
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsVerifier3])
    def statistics(self, request):
        verifier = request.user
        two_days_ago = timezone.now() - timedelta(days=EDITABLE_WINDOW_DAYS)

        # All stage3 applications assigned to this verifier
        assigned_apps = WorkerApplication.objects.filter(
            current_stage=3,
            verifier3_assigned=verifier
        )

        # Reviews linked to these applications
        reviews = Verifier3Review.objects.filter(application__in=assigned_apps)

        total_reviewed = reviews.filter(status__in=['approved', 'rejected']).count()
        approved = reviews.filter(status='approved').count()
        rejected = reviews.filter(status='rejected').count()
        recently_submitted = reviews.filter(submitted_at__gte=two_days_ago).count()

        # Pending = assigned apps without approved/rejected review
        pending = assigned_apps.exclude(
            Q(verifier3_review__status='approved') |
            Q(verifier3_review__status='rejected')
        ).count()

        approval_rate = round((approved / total_reviewed * 100) if total_reviewed > 0 else 0.0, 2)

        return Response({
            'total_reviewed': total_reviewed,
            'approved': approved,
            'rejected': rejected,
            'pending': pending,
            'recently_submitted': recently_submitted,
            'approval_rate': approval_rate
        })
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsVerifier3], url_path='pending_applications')
    def pending_applications(self, request):
        queryset = WorkerApplication.objects.filter(
            current_stage=3,
            application_status__in=['stage3_review']
        ).order_by('-applied_at')
        serializer = WorkerApplicationListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    from django.utils import timezone
from datetime import timedelta
from core.models import WorkerApplication

# views/verifier3_views.py
from datetime import timedelta
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from core.models import WorkerApplication, Verifier3Review
from core.permissions import IsVerifier3  # your existing permission
from rest_framework import status


class Verifier3ApprovedListView(APIView):
    """
    Returns WorkerApplication objects approved within the last 2 days
    (visible to Verifier 3 dashboard only temporarily).
    Endpoint: GET /api/verifier3/approved-workers/
    """
    permission_classes = [IsAuthenticated, IsVerifier3]

    def get(self, request):
        two_days_ago = timezone.now() - timedelta(days=2)

        approved_apps = WorkerApplication.objects.filter(
            application_status="approved",
            approved_at__isnull=False,
            approved_at__gte=two_days_ago
        ).order_by('-approved_at')

        data = [
            {
                "id": app.id,
                "name": app.name,
                "email": app.email,
                "phone": app.phone,
                "address": app.address,
                "skills": app.skills,
                "approved_at": app.approved_at,
                "applied_at": app.applied_at,
            }
            for app in approved_apps
        ]

        return Response(data, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from core.models import Verifier3Review, WorkerApplication
from core.permissions import IsVerifier3


class Verifier3StatisticsView(APIView):
    """
    Returns dashboard statistics for Verifier 3.
    Endpoint: GET /api/verifier3/statistics/
    """
    permission_classes = [IsAuthenticated, IsVerifier3]

    def get(self, request):
        verifier = request.user
        two_days_ago = timezone.now() - timedelta(days=2)

        # Verifier3Review statistics scoped to current verifier
        reviews_qs = Verifier3Review.objects.filter(verifier=verifier)
        total_reviews = reviews_qs.count()
        approved_reviews = reviews_qs.filter(status='approved').count()
        rejected_reviews = reviews_qs.filter(status='rejected').count()
        pending_reviews = reviews_qs.filter(status__in=['pending', 'under_review']).count()

        # Recently approved workers (global count)
        recently_approved = WorkerApplication.objects.filter(
            application_status='approved',
            approved_at__isnull=False,
            approved_at__gte=two_days_ago
        ).count()

        # Compute approval rate
        approval_rate = round((approved_reviews / total_reviews * 100), 2) if total_reviews > 0 else 0.0

        data = {
            "total_reviews": total_reviews,
            "approved_reviews": approved_reviews,
            "rejected_reviews": rejected_reviews,
            "pending_reviews": pending_reviews,
            "recently_approved": recently_approved,
            "approval_rate": approval_rate,
        }

        return Response(data, status=status.HTTP_200_OK)

# ------------------------------------
# Shared Application Detail View
# ------------------------------------
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

class ApplicationSharedDetailView(APIView):
    """
    Shared read-only endpoint for Verifier 1, 2, 3, or Admin
    to view a specific WorkerApplication.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        from .models import WorkerApplication
        from .serializer import WorkerApplicationDetailSerializer

        try:
            app = WorkerApplication.objects.get(pk=pk)
        except WorkerApplication.DoesNotExist:
            return Response({'error': 'Application not found'}, status=404)

        # Allow verifiers (stage 1–3) or staff
        user = request.user
        if not (
            hasattr(user, 'role')
            and user.role in ['verifier1', 'verifier2', 'verifier3', 'admin']
        ):
            return Response({'error': 'Permission denied'}, status=403)

        serializer = WorkerApplicationDetailSerializer(app, context={'request': request})
        return Response(serializer.data)
