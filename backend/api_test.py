import requests
import time
from prettytable import PrettyTable

# List of API endpoints to test (adjust to your urls)
apis = [
    "http://localhost:8000/api/signup/",
    "http://localhost:8000/api/login/",
    "http://localhost:8000/api/user-profile/",
    "http://localhost:8000/api/recommend/1/",
    "http://localhost:8000/api/bookings/",
]

num_requests = 5  # number of requests per API
max_expected_time = 1.5  # seconds

# Create table for display
table = PrettyTable()
table.field_names = ["API Endpoint", "Avg Response Time (s)", "Status"]

for api in apis:
    total_time = 0
    for i in range(num_requests):
        start = time.time()
        try:
            response = requests.get(api)  # Use POST if required
        except Exception as e:
            print(f"Error calling {api}: {e}")
            continue
        end = time.time()

        duration = end - start
        total_time += duration
        print(f"Request {i+1} to {api} took {duration:.3f}s")

    avg_time = total_time / num_requests
    status = "Pass" if avg_time <= max_expected_time else "Fail"
    table.add_row([api, f"{avg_time:.3f}", status])

print("\n+-------------------- Performance Test Result --------------------+")
print(table)
