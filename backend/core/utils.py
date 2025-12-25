# core/utils.py
import numpy as np

def haversine_vector(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1))*np.cos(np.radians(lat2))*np.sin(dlon/2)**2
    c = 2*np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c
import os
from cryptography.fernet import Fernet
from django.conf import settings

# Path to your secret.key file
KEY_FILE = os.path.join(settings.BASE_DIR, "secret.key")

# Read or generate encryption key
if not os.path.exists(KEY_FILE):
    with open(KEY_FILE, "wb") as f:
        f.write(Fernet.generate_key())

with open(KEY_FILE, "rb") as f:
    ENCRYPTION_KEY = f.read()

fernet = Fernet(ENCRYPTION_KEY)

def decrypt_rsa(file_path):
    """
    Decrypts the given encrypted file and returns bytes.
    file_path: path to the encrypted file
    """
    with open(file_path, "rb") as f:
        encrypted_data = f.read()
    decrypted_data = fernet.decrypt(encrypted_data)
    return decrypted_data

def encrypt_and_save(uploaded_file, save_path):
    """
    Encrypt file content and save as .enc file
    """
    data = uploaded_file.read()
    encrypted = fernet.encrypt(data)
    with open(save_path, "wb") as f:
        f.write(encrypted)
