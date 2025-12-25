from locust import HttpUser, TaskSet, task, between
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Util.Padding import pad
import os
import base64
import json

# Load public key (matches your backend private key)
PUBLIC_KEY_PATH = "public.pem"
with open(PUBLIC_KEY_PATH, "rb") as f:
    PUBLIC_KEY = RSA.import_key(f.read())


class UserWorkerTasks(TaskSet):
    def on_start(self):
        # Generate random 256-bit AES key for each virtual user
        self.aes_key = os.urandom(32)

    def get_csrf_token(self):
        """
        Fetch a fresh CSRF token from the backend.
        Django usually sets it in a cookie named 'csrftoken'.
        """
        response = self.client.get("/api/csrf/")
        if "csrftoken" in response.cookies:
            return response.cookies["csrftoken"]
        else:
            print("⚠️ CSRF token not found!")
            return ""

    def rsa_encrypt(self, data: bytes) -> str:
        cipher_rsa = PKCS1_OAEP.new(PUBLIC_KEY)
        encrypted = cipher_rsa.encrypt(data)
        return base64.b64encode(encrypted).decode("utf-8")

    def aes_encrypt(self, data: str, key: bytes) -> str:
        iv = os.urandom(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded = pad(data.encode("utf-8"), AES.block_size)
        encrypted = cipher.encrypt(padded)
        return base64.b64encode(iv + encrypted).decode("utf-8")

    def post_with_csrf(self, url, payload):
        csrf_token = self.get_csrf_token()
        headers = {
            "X-CSRFToken": csrf_token,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        return self.client.post(url, json=payload, headers=headers, catch_response=True)

    # -------------------------
    # USER LOGIN
    # -------------------------
    @task(1)
    def user_login(self):
        email = "kakshathashetty6@gmail.com"
        password = "123456!@"
        key_enc = self.rsa_encrypt(self.aes_key)
        payload = {
            "key": key_enc,
            "data": {
                "email": self.aes_encrypt(email, self.aes_key),
                "password": self.aes_encrypt(password, self.aes_key)
            }
        }
        with self.post_with_csrf("/api/login/", payload) as response:
            if response.status_code == 200:
                response.success()
                print(f"✅ User login success: {response.json()}")
            else:
                response.failure(f"User login failed: {response.status_code}")

    # -------------------------
    # WORKER LOGIN
    # -------------------------
    @task(1)
    def worker_login(self):
        email = "leelavathishetty92@gmail.com"
        password = "123456!@"
        key_enc = self.rsa_encrypt(self.aes_key)
        payload = {
            "key": key_enc,
            "data": {
                "email": self.aes_encrypt(email, self.aes_key),
                "password": self.aes_encrypt(password, self.aes_key)
            }
        }
        with self.post_with_csrf("/api/login/", payload) as response:
            if response.status_code == 200:
                response.success()
                print(f"✅ Worker login success: {response.json()}")
            else:
                response.failure(f"Worker login failed: {response.status_code}")


class WebsiteUser(HttpUser):
    tasks = [UserWorkerTasks]
    wait_time = between(1, 3)

    def on_start(self):
        self.client.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

