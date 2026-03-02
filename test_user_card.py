"""
Test script to appraise user's card image
"""
import asyncio
import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services import appraisal

async def test_appraisal():
    """Test card appraisal with user's image"""
    
    # Path to the user's uploaded image
    image_path = r"C:\Users\amrca\.gemini\antigravity\brain\tempmediaStorage\media__1771306748451.jpg"
    
    print(f"Testing appraisal with image: {image_path}")
    print("=" * 60)
    
    # Read the image file
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        print(f"✓ Image loaded successfully ({len(image_data)} bytes)")
        print()
        
        # Call the appraisal service
        print("Calling appraisal service...")
        result = await appraisal.appraise_card_from_image(image_data=image_data)
        
        print()
        print("=" * 60)
        print("APPRAISAL RESULT:")
        print("=" * 60)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"Card Name: {result.get('card_name', 'N/A')}")
            print(f"Set Name: {result.get('set_name', 'N/A')}")
            print(f"Card Number: {result.get('card_number', 'N/A')}")
            print(f"Rarity: {result.get('rarity', 'N/A')}")
            print(f"Year: {result.get('year', 'N/A')}")
            print(f"Manufacturer: {result.get('manufacturer', 'N/A')}")
            print()
            print(f"Japanese Name: {result.get('card_name_japanese', 'N/A')}")
            print(f"English Name: {result.get('card_name_english', 'N/A')}")
            print(f"Raw Rarity: {result.get('raw_rarity', 'N/A')}")
        
        print("=" * 60)
        
    except FileNotFoundError:
        print(f"❌ Error: Image file not found at {image_path}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_appraisal())
