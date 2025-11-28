import pytest
import requests

BASE_URL = "http://127.0.0.1:8000/api"

@pytest.fixture(scope="session")
def user_token():
    # Signup if not exists
    requests.post(f"{BASE_URL}/signup/", json={
        "email": "pytestuser@example.com",
        "password": "Test@1234",
        "name": "Pytest User"
    })

    # Login
    r = requests.post(f"{BASE_URL}/login/", json={
        "email": "pytestuser@example.com",
        "password": "Test@1234"
    })
    if r.status_code in [200, 201] and "access" in r.json():
        return r.json()["access"]
    return None
