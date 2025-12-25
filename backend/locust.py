from locust import HttpUser, TaskSet, task, between
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP, AES
from Crypto.Util.Padding import pad
import os
import base64
import random

PUBLIC_KEY_PATH = "public.pem"
with open(PUBLIC_KEY_PATH, "rb") as f:
    PUBLIC_KEY = RSA.import_key(f.read())


class UserWorkerTasks(TaskSet):

    def on_start(self):
        self.aes_key = os.urandom(32)
        self.authenticated = False

        # randomly choose one role per locust user
        self.role = random.choice(["user", "worker"])

        if self.role == "user":
            self.email = "kakshathashetty6@gmail.com"
            self.password = "123456!@"
        else:
            self.email = "leelavathishetty92@gmail.com"
            self.password = "123456!@"

        self.login()

    # ------------------------------ UTILITIES ------------------------------

    def get_csrf(self):
        resp = self.client.get("/api/csrf/")
        return resp.cookies.get("csrftoken", "")

    def rsa_encrypt(self, data: bytes):
        cipher = PKCS1_OAEP.new(PUBLIC_KEY)
        return base64.b64encode(cipher.encrypt(data)).decode()

    def aes_encrypt(self, text: str, key: bytes):
        iv = os.urandom(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        enc = cipher.encrypt(pad(text.encode(), AES.block_size))
        return base64.b64encode(iv + enc).decode()

    # ------------------------------ LOGIN ------------------------------

    def login(self):
        csrf = self.get_csrf()
        key_enc = self.rsa_encrypt(self.aes_key)

        payload = {
            "key": key_enc,
            "data": {
                "email": self.aes_encrypt(self.email, self.aes_key),
                "password": self.aes_encrypt(self.password, self.aes_key),
            }
        }

        headers = {
            "X-CSRFToken": csrf,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        with self.client.post("/api/login/", json=payload, headers=headers, catch_response=True) as resp:
            if resp.status_code == 200:
                self.authenticated = True
                resp.success()
                self.get_csrf()   # refresh CSRF after login
            else:
                resp.failure("Login Failed")

    # ------------------------------ TASKS ------------------------------

    @task(2)
    def fetch_user_profile(self):
        if self.authenticated and self.role == "user":
            self.client.get("/api/user-profile/", name="User Profile")

    @task(2)
    def fetch_worker_homepage(self):
        if self.authenticated and self.role == "worker":
            self.client.get("/api/worker/homepage/", name="Worker Homepage")


class WebsiteUser(HttpUser):
    tasks = [UserWorkerTasks]
    wait_time = between(1, 3)
    def on_start(self):
        self.client.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
