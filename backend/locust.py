from locust import HttpUser, task, between
import json
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Util.Padding import pad
import random

# ------------------------------------------------------------
# 🔐 Encryption Setup (matches your frontend)
# ------------------------------------------------------------
with open("backend/public.pem", "rb") as f:
    PUBLIC_KEY = RSA.import_key(f.read())

def encrypt_rsa(aes_key: bytes) -> str:
    cipher_rsa = PKCS1_OAEP.new(PUBLIC_KEY)
    return base64.b64encode(cipher_rsa.encrypt(aes_key)).decode("utf-8")

def encrypt_aes(data: str, aes_key: bytes) -> str:
    iv = random.randbytes(16)
    cipher_aes = AES.new(aes_key, AES.MODE_CBC, iv)
    encrypted = cipher_aes.encrypt(pad(data.encode(), AES.block_size))
    return base64.b64encode(iv + encrypted).decode("utf-8")

# ------------------------------------------------------------
# 🧪 Locust Test Class
# ------------------------------------------------------------
class WebsiteUser(HttpUser):
    wait_time = between(1, 5)
    host = "http://127.0.0.1:8000"

    def on_start(self):
        """Get CSRF token before any requests"""
        response = self.client.get("/api/csrf/", name="Get CSRF")
        if response.status_code == 200 and "csrftoken" in response.cookies:
            self.csrftoken = response.cookies["csrftoken"]
            self.cookies = response.cookies
            print(f"✅ CSRF token fetched: {self.csrftoken}")
        else:
            print("❌ Failed to get CSRF token")
            self.csrftoken = None
            self.cookies = {}

        # Auto-login when starting
        self.login_user()

    def login_user(self):
        """Encrypt login credentials and authenticate"""
        if not self.csrftoken:
            print("❌ No CSRF token available for login")
            return

        aes_key = random.randbytes(16)
        key_enc = encrypt_rsa(aes_key)
        encrypted_email = encrypt_aes("kakshathashetty6@gmail.com", aes_key)
        encrypted_password = encrypt_aes("123456!@", aes_key)

        payload = {
            "key": key_enc,
            "data": {
                "email": encrypted_email,
                "password": encrypted_password
            }
        }

        headers = {
            "X-CSRFToken": self.csrftoken,
            "Content-Type": "application/json"
        }

        with self.client.post(
            "/api/login/",
            json=payload,
            headers=headers,
            cookies=self.cookies,
            catch_response=True,
            name="Login"
        ) as response:
            if response.status_code == 200:
                response.success()
                print("✅ Login success")
            else:
                response.failure(f"❌ Login failed: {response.status_code} {response.text}")

    # ------------------------------------------------------------
    # 🌐 TEST IMPORTANT URLS
    # ------------------------------------------------------------

    @task(2)
    def view_profile(self):
        """Test user profile API"""
        with self.client.get(
            "/api/user-profile/",
            cookies=self.cookies,
            name="User Profile",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Profile fetch failed: {response.status_code}")

    @task(3)
    def get_recommendations(self):
        """Fetch recommendations for a sample user"""
        with self.client.get(
            "/api/recommend/1/",
            cookies=self.cookies,
            name="Recommendations",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Recommendation failed: {response.status_code}")

    @task(2)
    def list_workers(self):
        """Test worker list view"""
        with self.client.get(
            "/api/workers/",
            cookies=self.cookies,
            name="Worker List",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Workers fetch failed: {response.status_code}")

    @task(1)
    def get_bookings(self):
        """Test user booking history"""
        with self.client.get(
            "/api/user/bookings/",
            cookies=self.cookies,
            name="User Booking History",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Booking history failed: {response.status_code}")

    # ------------------------------------------------------------
    # 🧰 NEW UNENCRYPTED TESTS
    # ------------------------------------------------------------
    @task(2)
    def worker_homepage(self):
        """Test worker homepage endpoint"""
        with self.client.get(
            "/api/worker/homepage/",
            cookies=self.cookies,
            name="Worker Homepage",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Worker homepage failed: {response.status_code}")

    