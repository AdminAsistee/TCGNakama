import asyncio, sys, os, glob
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()

async def test():
    from app.services.appraisal import appraise_card_from_image
    cards = sorted(glob.glob(r'test_cards/*'))
    for card_path in cards:
        print(f'\n{"="*60}')
        print(f'FILE: {os.path.basename(card_path)}')
        print('='*60)
        with open(card_path, 'rb') as f:
            data = f.read()
        result = await appraise_card_from_image(image_data=data)
        for k in ('card_name_japanese','card_name_english','set_name','full_set_name','card_number','rarity','card_condition','manufacturer'):
            print(f'  {k}: {result.get(k, "")}')

asyncio.run(test())
