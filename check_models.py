import httpx, os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
r = httpx.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}&pageSize=100")
models = r.json().get("models", [])

# Filter to generateContent-capable models only
gen_models = [m["name"] for m in models if "generateContent" in m.get("supportedGenerationMethods", [])]
print(f"Available generateContent models ({len(gen_models)}):")
for m in sorted(gen_models):
    print(" ", m)
