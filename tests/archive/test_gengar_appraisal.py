"""
Test the single-prompt chain-of-thought appraisal on all cards in test_cards folder.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from app.services.appraisal import appraise_card_from_image

TEST_CARDS_DIR = r"C:\Users\amrca\Documents\antigravity\tcgnakama\test_cards"

async def main():
    files = [f for f in os.listdir(TEST_CARDS_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    print(f"Found {len(files)} card(s) to test\n")

    for fname in files:
        path = os.path.join(TEST_CARDS_DIR, fname)
        print(f"{'='*60}")
        print(f"FILE: {fname}")
        print('='*60)
        with open(path, "rb") as f:
            image_data = f.read()
        result = await appraise_card_from_image(image_data=image_data)
        print(f"  card_name:        {result.get('card_name')}")
        print(f"  set_name:         {result.get('set_name')}")
        print(f"  card_number:      {result.get('card_number')}")
        print(f"  rarity:           {result.get('rarity')}")
        print(f"  special_variants: {result.get('special_variants')}")
        print()

if __name__ == "__main__":
    asyncio.run(main())
