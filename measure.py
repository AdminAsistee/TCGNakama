import time
import requests
import re

base_url = 'http://127.0.0.1:8001'
pages = {
    'Homepage': '/',
    'Admin Login': '/admin/login'
}

print('=== Measuring Page Load Times ===')

for name, path in pages.items():
    try:
        # warmup
        requests.get(base_url + path)
        
        start = time.time()
        res = requests.get(base_url + path)
        duration = time.time() - start
        print(f'{name} ({path}): {duration:.3f}s')
        
        if path == '/':
            match = re.search(r'href=\"(/card/[^\"]+)\"', res.text)
            if match:
                card_path = match.group(1)
                
                # warmup
                requests.get(base_url + card_path)
                
                start_card = time.time()
                res_card = requests.get(base_url + card_path)
                duration_card = time.time() - start_card
                print(f'Card Details ({card_path}): {duration_card:.3f}s')
    except Exception as e:
        print(f'{name} ({path}): Failed - {e}')
