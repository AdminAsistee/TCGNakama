"""
Compare appraisal results across different Gemini models for the same card.
"""
import asyncio
import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

import google.generativeai as genai
from PIL import Image
import io

IMAGE_PATH = r"C:\Users\amrca\Documents\antigravity\tcgnakama\test_cards\BATCH-22-2026-02-13-PK-High Value 60.jpeg"

MODELS_TO_TEST = [
    "gemini-2.5-flash-image",   # current
    "gemini-2.5-flash",         # fast + smart
    "gemini-2.5-pro",           # most capable
]

PASS1 = "Look at this trading card image and identify it. Tell me: what card is this, what set/series is it from, what is the card number, what is the rarity, and are there any special variants (like holographic, 1st edition, prism, etc.)? Be specific and detailed."

async def test_model(model_name, img):
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    try:
        resp = model.generate_content([PASS1, img])
        return resp.text.strip()
    except Exception as e:
        return f"ERROR: {e}"

async def main():
    print(f"Loading image: {IMAGE_PATH}\n")
    with open(IMAGE_PATH, "rb") as f:
        image_data = f.read()
    img = Image.open(io.BytesIO(image_data))

    for model_name in MODELS_TO_TEST:
        print(f"\n{'='*60}")
        print(f"MODEL: {model_name}")
        print('='*60)
        result = await test_model(model_name, img)
        print(result.encode('ascii', 'replace').decode())

if __name__ == "__main__":
    asyncio.run(main())
