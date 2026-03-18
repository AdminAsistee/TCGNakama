"""
Test script to check what the bulk upload appraisal endpoint returns
"""
import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8001"
session = requests.Session()

print("=" * 70)
print("BULK UPLOAD APPRAISAL RESPONSE TEST")
print("=" * 70)

# Step 1: Login
print("\n[1] Logging in...")
login_response = session.post(
    f"{BASE_URL}/admin/login",
    data={"email": "admin@asistee.com", "password": "nakama2026"},
    allow_redirects=False
)

if login_response.status_code != 303:
    print(f"    [FAIL] Login failed: {login_response.status_code}")
    exit(1)

print("    [OK] Login successful")

# Step 2: Check if there are any test images in the temp directory
temp_dir = Path("app/static/uploads/temp")
if temp_dir.exists():
    test_images = list(temp_dir.glob("*.jpg")) + list(temp_dir.glob("*.png"))
    if test_images:
        print(f"\n[2] Found {len(test_images)} test images in temp directory")
        print("    Using existing images for test")
        
        # Use the first image for testing
        test_image = test_images[0]
        print(f"    Test image: {test_image.name}")
        
        # Upload the image
        with open(test_image, 'rb') as f:
            files = {'images': (test_image.name, f, 'image/jpeg')}
            response = session.post(f"{BASE_URL}/admin/bulk-upload/appraise", files=files)
        
        print(f"\n[3] Appraisal response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n[4] Response data:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if data and len(data) > 0:
                print("\n[5] First card data:")
                first_card = data[0]
                print(f"    card_name: {first_card.get('card_name')}")
                print(f"    set_name: {first_card.get('set_name')}")
                print(f"    card_number: {first_card.get('card_number')}")
                print(f"    rarity: {first_card.get('rarity')}")
                print(f"    price: {first_card.get('price')}")
                print(f"    exists: {first_card.get('exists')}")
                print(f"    image_url: {first_card.get('image_url')}")
        else:
            print(f"    [FAIL] Appraisal failed: {response.text}")
    else:
        print("\n[2] No test images found in temp directory")
        print("    Please upload some cards through the web interface first")
else:
    print("\n[2] Temp directory doesn't exist")
    print("    Please upload some cards through the web interface first")

print("\n" + "=" * 70)
