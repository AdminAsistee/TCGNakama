"""
Full appraisal test: Vision identification + PriceCharting market value
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

IMAGE_PATH = r"test_cards/BATCH-22-2026-02-13-PK-High Value 62.jpeg"

async def test_full_appraisal():
    from app.services.appraisal import appraise_card_from_image, get_market_value_jpy
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 80)
    print("STEP 1: Vision AI Identification")
    print("=" * 80)

    with open(IMAGE_PATH, "rb") as f:
        image_data = f.read()

    vision_result = await appraise_card_from_image(image_data=image_data)

    if "error" in vision_result:
        print(f"Vision Error: {vision_result['error']}")
        return

    print(f"  card_name:        {vision_result.get('card_name')}")
    print(f"  card_name_en:     {vision_result.get('card_name_english')}")
    print(f"  set_name (code):  {vision_result.get('set_name')}")
    print(f"  full_set_name:    {vision_result.get('full_set_name')}")
    print(f"  card_number:      {vision_result.get('card_number')}")
    print(f"  rarity:           {vision_result.get('rarity')}")
    print(f"  manufacturer:     {vision_result.get('manufacturer')}")
    print(f"  card_condition:   {vision_result.get('card_condition')}")

    print()
    print("=" * 80)
    print("STEP 2: PriceCharting Market Value")
    print("=" * 80)

    card_name = vision_result.get('card_name_english') or vision_result.get('card_name', '')
    set_name  = vision_result.get('set_name', '')
    full_set_name = vision_result.get('full_set_name', '')
    effective_set = set_name or full_set_name  # use full name if no code
    card_number = vision_result.get('card_number', '')
    rarity    = vision_result.get('rarity', '')
    variants  = ['Japanese'] if vision_result.get('card_name_japanese') else None

    print(f"  Searching with: name='{card_name}', set='{effective_set}', number='{card_number}', rarity='{rarity}'")
    print()

    market = await get_market_value_jpy(
        card_name=card_name,
        rarity=rarity,
        set_name=effective_set,
        card_number=card_number,
        variants=variants,
        force_refresh=True
    )

    print("=" * 80)
    print("MARKET VALUE RESULT:")
    print("=" * 80)
    for k, v in market.items():
        print(f"  {k}: {v}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_full_appraisal())
