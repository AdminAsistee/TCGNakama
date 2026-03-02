import asyncio, sys, os, glob
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

async def test():
    from app.services.appraisal import appraise_card_from_image, get_market_value_jpy

    cards = sorted(glob.glob(r'test_cards/*'))
    for card_path in cards:
        print(f'\n{"="*70}')
        print(f'CARD: {os.path.basename(card_path)}')
        print('='*70)

        with open(card_path, 'rb') as f:
            data = f.read()

        # Step 1: Vision
        vision = await appraise_card_from_image(image_data=data)
        if vision.get('error'):
            print(f'  Vision error: {vision["error"]}')
            continue

        card_name     = vision.get('card_name_english') or vision.get('card_name', '')
        set_name      = vision.get('set_name', '')
        full_set_name = vision.get('full_set_name', '')
        card_number   = vision.get('card_number', '')
        rarity        = vision.get('rarity', '')
        is_japanese   = bool(vision.get('card_name_japanese'))
        variants      = ['Japanese'] if is_japanese else None
        effective_set = set_name or full_set_name

        print(f'  card_name:     {vision.get("card_name")}')
        print(f'  set_name:      {set_name}')
        print(f'  full_set_name: {full_set_name}')
        print(f'  card_number:   {card_number}')
        print(f'  rarity:        {rarity}')
        print(f'  search set:    {effective_set}')
        print()

        # Step 2: Pricing
        print(f'  [PRICING] Searching: name="{card_name}" set="{effective_set}" number="{card_number}"')
        market = await get_market_value_jpy(
            card_name=card_name,
            rarity=rarity,
            set_name=set_name,
            full_set_name=full_set_name,
            card_number=card_number,
            variants=variants,
            force_refresh=True
        )
        print(f'  RESULT: ¥{market.get("market_jpy","?")} (${market.get("market_usd","?")})')
        if market.get('error'):
            print(f'  ERROR: {market["error"]}')

asyncio.run(test())
