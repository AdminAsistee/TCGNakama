#!/usr/bin/env python3
"""Test the bulk upload route directly"""

import requests

# Test the route
url = "http://localhost:8001/admin/bulk-upload"
print(f"Testing: {url}")
print()

try:
    response = requests.get(url, allow_redirects=False)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code == 302:
        print(f"\nRedirect to: {response.headers.get('Location')}")
        print("(This is expected - you need to login first)")
except Exception as e:
    print(f"Error: {e}")
