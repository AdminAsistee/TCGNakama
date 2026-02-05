
import httpx

url = "https://github.com/AdminAsistee/TCGNakama"
try:
    response = httpx.get(url, follow_redirects=True)
    print(f"Status Code for {url}: {response.status_code}")
    if response.status_code == 200:
        print("Repository appears to exist publicly.")
    elif response.status_code == 404:
        print("Repository NOT found (404).")
    else:
        print(f"Received status {response.status_code}. It might be private or require auth.")
except Exception as e:
    print(f"Error checking URL: {e}")
