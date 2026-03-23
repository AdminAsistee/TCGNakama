import httpx
import re

r = httpx.get('http://127.0.0.1:8001/blog', timeout=10)

slugs = list(dict.fromkeys(re.findall(r'href="/blog/([^"]+)"', r.text)))
print(f'Status: {r.status_code}')
print(f'Posts found: {len(slugs)}')
for s in slugs:
    print(s.encode('ascii', 'replace').decode())

# Also hit the admin/blog endpoint for title info
r2 = httpx.get('http://127.0.0.1:8001/admin/blog', timeout=10)
titles = re.findall(r'<p class="font-bold text-white[^"]*"[^>]*>(.*?)</p>', r2.text, re.DOTALL)
for t in titles:
    clean = re.sub(r'<[^>]+>', '', t).strip()
    if clean:
        print('Title:', clean.encode('ascii', 'replace').decode())
