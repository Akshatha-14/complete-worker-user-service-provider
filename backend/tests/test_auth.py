import os
import json
import uuid
import pytest
from django.contrib.auth import get_user_model
from core.models import UserRole, Worker
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Util.Padding import pad, unpad
import base64
import warnings
warnings.filterwarnings("ignore", category=pytest.PytestWarning)

# ----------------------
# 🔐 Encryption helpers
# ----------------------
def encrypt_aes(plaintext: str, key: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    return base64.b64encode(cipher.iv + ct_bytes).decode("utf-8")

def encrypt_rsa(aes_key: bytes) -> str:
    with open("public.pem", "rb") as f:
        public_key = RSA.import_key(f.read())
    cipher_rsa = PKCS1_OAEP.new(public_key)
    enc_key = cipher_rsa.encrypt(aes_key)
    return base64.b64encode(enc_key).decode("utf-8")

# ----------------------
# ⚙️ Test fixture
# ----------------------
@pytest.fixture
def test_user(db):
    User = get_user_model()
    email = f"integration_{uuid.uuid4().hex[:6]}@example.com"
    user = User.objects.create_user(
        email=email,
        password="Test@1234",
        name="Integration User"
    )
    UserRole.objects.get_or_create(user=user, role="worker")
    Worker.objects.filter(user=user).delete()
    Worker.objects.create(user=user, address="Test Address", experience_years=2)
    print(f"\n✅ Test user created: {email}")
    return user

# ----------------------
# 🔄 Full integration test
# ----------------------
# ----------------------
# 🔄 Full integration test with progress
# ----------------------
@pytest.mark.django_db
def test_full_integration(client, test_user):
    print("\n🔹 STEP 1: Fetch CSRF token")
    csrf = client.get("/api/csrf/").cookies["csrftoken"]
    print(f"CSRF token fetched successfully")

    print("\n🔹 STEP 2: Encrypt credentials for login")
    aes_key = os.urandom(16)
    payload = {
        "key": encrypt_rsa(aes_key),
        "data": {
            "email": encrypt_aes(test_user.email, aes_key),
            "password": encrypt_aes("Test@1234", aes_key),
        }
    }
    print(f"Payload prepared for login.")

    print("\n🔹 STEP 3: Login")
    resp = client.post(
        "/api/login/",
        json.dumps(payload),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=csrf
    )
    print(f"Login response status: {resp.status_code}")
    assert resp.status_code == 200, "Login failed"

    print("\n🔹 STEP 4: Integration endpoint testing with progress")
    endpoints = [
        ("/api/user-profile/", "GET"),
        ("/api/user/bookings/", "GET"),
        ("/api/workers/", "GET"),
        ("/api/worker/homepage/", "GET"),
        ("/api/worker/settings/", "GET"),
        ("/api/worker/earnings/", "GET"),
        ("/api/worker/bookings/send_receipt/", "POST"),
        ("/api/chatbot/", "POST"),
        ("/api/recommend/1/", "GET"),
    ]
    allowed_status = [200, 201, 400, 401, 403, 404]

    total = len(endpoints)
    for idx, (ep, method) in enumerate(endpoints, start=1):
        progress = int((idx / total) * 100)
        if method == "GET":
            r = client.get(ep)
        else:
            payload = {"booking_id": 1} if ep == "/api/worker/bookings/send_receipt/" else {"message": "Hello"}
            r = client.post(ep, json.dumps(payload), content_type="application/json")

        print(f"\n➡️ {method} {ep}")
        print(f"Status: {r.status_code} | Response: {r.json() if r.content else '{}'}")
        print(f"🔹 Progress: {progress}% integration testing completed")

        assert r.status_code in allowed_status, f"{ep} returned {r.status_code}"
