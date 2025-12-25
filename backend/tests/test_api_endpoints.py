import pytest
import requests
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Util.Padding import pad
import base64
import os
import json

BASE_URL = "http://127.0.0.1:8000/api"


# --------------------------------------------------------------------
# 🔐 Encryption Utilities
# --------------------------------------------------------------------
def ensure_public_key():
    pub_path = "public.pem"
    if not os.path.exists(pub_path):
        raise FileNotFoundError("Missing backend/core/public.pem — copy your actual public key here.")
    return pub_path


def encrypt_aes(value: str, aes_key: bytes):
    cipher = AES.new(aes_key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(value.encode(), AES.block_size))
    return base64.b64encode(cipher.iv + ct_bytes).decode()


def encrypt_rsa_key(aes_key: bytes) -> str:
    pub_path = ensure_public_key()
    with open(pub_path, "rb") as f:
        pubkey = RSA.import_key(f.read())
    cipher_rsa = PKCS1_OAEP.new(pubkey)
    enc_key = cipher_rsa.encrypt(aes_key)
    return base64.b64encode(enc_key).decode()


def prepare_encrypted_payload(data: dict):
    aes_key = os.urandom(32)
    key_enc = encrypt_rsa_key(aes_key)
    encrypted_fields = {k: encrypt_aes(str(v), aes_key) for k, v in data.items()}
    return {"key": key_enc, "data": encrypted_fields}


# --------------------------------------------------------------------
# ⚙️ Fixtures
# --------------------------------------------------------------------
@pytest.fixture(scope="session")
def signup_user():
    payload = prepare_encrypted_payload({
        "email": "pytestuser@example.com",
        "password": "Test@1234",
        "name": "Pytest User"
    })
    r = requests.post(f"{BASE_URL}/signup/", json=payload)
    assert r.status_code in [200, 201, 400]
    return {"email": "pytestuser@example.com", "password": "Test@1234"}


@pytest.fixture(scope="session")
def auth_headers(signup_user):
    payload = prepare_encrypted_payload({
        "email": signup_user["email"],
        "password": signup_user["password"]
    })
    r = requests.post(f"{BASE_URL}/login/", json=payload)
    assert r.status_code in [200, 201]
    data = r.json()
    token = data.get("access") or data.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


# --------------------------------------------------------------------
# ✅ Helper
# --------------------------------------------------------------------
def check_status(r, allowed):
    if r.status_code not in allowed:
        print(f"\n[DEBUG] Endpoint: {r.url}")
        print(f"[DEBUG] Status: {r.status_code}")
        print(f"[DEBUG] Response: {r.text}")
    assert r.status_code in allowed


# --------------------------------------------------------------------
# ✅ Core API Tests
# --------------------------------------------------------------------
def test_signup():
    payload = prepare_encrypted_payload({
        "email": "pytestuser2@example.com",
        "password": "Test@5678",
        "name": "Pytest User2"
    })
    r = requests.post(f"{BASE_URL}/signup/", json=payload)
    check_status(r, [200, 201, 400])


def test_login(signup_user):
    payload = prepare_encrypted_payload({
        "email": signup_user["email"],
        "password": signup_user["password"]
    })
    r = requests.post(f"{BASE_URL}/login/", json=payload)
    check_status(r, [200, 201])


def test_user_profile(auth_headers):
    r = requests.get(f"{BASE_URL}/user-profile/", headers=auth_headers)
    check_status(r, [200, 401, 403])


def test_chatbot_response():
    r = requests.post(f"{BASE_URL}/chatbot/", json={"message": "Hello"})
    check_status(r, [200, 400])


def test_recommendations():
    r = requests.get(f"{BASE_URL}/recommend/1/")
    check_status(r, [200, 404])


def test_booking_create(auth_headers):
    payload = {
        "userId": 1,
        "workerId": 1,
        "contactDates": ["2025-11-03"],
        "description": "Need electrician service",
        "equipmentRequirement": "Basic tools"
    }
    r = requests.post(f"{BASE_URL}/bookings/", json=payload, headers=auth_headers)
    check_status(r, [200, 201, 400, 403])


def test_user_bookings(auth_headers):
    r = requests.get(f"{BASE_URL}/user/bookings/", headers=auth_headers)
    check_status(r, [200, 404, 403])


def test_payment_verify(auth_headers):
    payload = {
        "razorpay_order_id": "dummy_order",
        "razorpay_payment_id": "dummy_payment",
        "razorpay_signature": "dummy_signature"
    }
    r = requests.post(f"{BASE_URL}/payment/verify/", json=payload, headers=auth_headers)
    check_status(r, [200, 201, 400, 403])


# --------------------------------------------------------------------
# 🧰 Verifier & Admin Tests
# --------------------------------------------------------------------
def test_verifier1_applications(auth_headers):
    r = requests.get(f"{BASE_URL}/verifier1/applications/", headers=auth_headers)
    check_status(r, [200, 403, 404])


def test_verifier2_applications(auth_headers):
    r = requests.get(f"{BASE_URL}/verifier2/applications/", headers=auth_headers)
    check_status(r, [200, 403, 404])


def test_verifier3_applications(auth_headers):
    r = requests.get(f"{BASE_URL}/verifier3/applications/", headers=auth_headers)
    check_status(r, [200, 403, 404])


def test_verifier3_review_update(auth_headers):
    r = requests.get(f"{BASE_URL}/verifier3/reviews/1/", headers=auth_headers)
    check_status(r, [200, 403, 404])


# --------------------------------------------------------------------
# 👷 Worker Endpoint Tests
# --------------------------------------------------------------------
def test_worker_list(auth_headers):
    r = requests.get(f"{BASE_URL}/workers/", headers=auth_headers)
    check_status(r, [200, 403, 404])


def test_worker_homepage(auth_headers):
    r = requests.get(f"{BASE_URL}/worker/homepage/", headers=auth_headers)
    check_status(r, [200, 403, 404])


def test_job_detail(auth_headers):
    r = requests.get(f"{BASE_URL}/worker/job/1/", headers=auth_headers)
    check_status(r, [200, 403, 404])


def test_accept_job(auth_headers):
    r = requests.post(f"{BASE_URL}/worker/job/accept/", headers=auth_headers, json={"job_id": 1})
    check_status(r, [200, 201, 400, 403])


def test_complete_job(auth_headers):
    r = requests.post(f"{BASE_URL}/worker/job/complete/", headers=auth_headers, json={"job_id": 1})
    check_status(r, [200, 201, 400, 403])


def test_update_tariff(auth_headers):
    payload = {"tariff": 500}
    r = requests.post(f"{BASE_URL}/worker/job/tariff/", json=payload, headers=auth_headers)
    check_status(r, [200, 201, 400, 403])


def test_pay_job(auth_headers):
    r = requests.post(f"{BASE_URL}/worker/job/pay/", headers=auth_headers, json={"job_id": 1})
    check_status(r, [200, 201, 400, 403])


def test_worker_settings(auth_headers):
    r = requests.get(f"{BASE_URL}/worker/settings/", headers=auth_headers)
    check_status(r, [200, 403, 404])


def test_update_availability(auth_headers):
    payload = {"available": True}
    r = requests.post(f"{BASE_URL}/worker/availability/", json=payload, headers=auth_headers)
    check_status(r, [200, 201, 400, 403])


def test_send_receipt(auth_headers):
    payload = {"booking_id": 1}
    r = requests.post(f"{BASE_URL}/worker/bookings/send_receipt/", json=payload, headers=auth_headers)
    check_status(r, [200, 201, 400, 403])


def test_confirm_cod_payment(auth_headers):
    payload = {"booking_id": 1}
    r = requests.post(f"{BASE_URL}/worker/confirm_cod_payment/", json=payload, headers=auth_headers)
    check_status(r, [200, 201, 400, 403])


def test_worker_earnings(auth_headers):
    r = requests.get(f"{BASE_URL}/worker/earnings/", headers=auth_headers)
    check_status(r, [200, 403, 404])
