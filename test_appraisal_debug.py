"""
Test script to check PriceCharting pricing for Ho-Oh card
and debug appraisal issues
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import appraisal

async def test_hooh_pricing():
    """Test PriceCharting pricing for Ho-Oh promotional card"""
    print("=" * 60)
    print("Testing Ho-Oh Card Pricing")
    print("=" * 60)
    
    # Card details from the appraisal
    card_name = "Ho-Oh"
    set_name = "OtQ/P"  # or whatever was extracted
    card_number = "010/P"
    
    print(f"\nCard: {card_name}")
    print(f"Set: {set_name}")
    print(f"Number: {card_number}")
    print("\nFetching market value from PriceCharting...")
    
    try:
        result = await appraisal.get_market_value_jpy(
            card_name=card_name,
            rarity="Rare",
            set_name=set_name,
            card_number=card_number
        )
        
        print("\n" + "=" * 60)
        print("RESULT:")
        print("=" * 60)
        print(f"Market Value (JPY): ¥{result.get('market_jpy', 'N/A')}")
        print(f"Market Value (USD): ${result.get('market_usd', 'N/A')}")
        print(f"Source: {result.get('source', 'N/A')}")
        print(f"Error: {result.get('error', 'None')}")
        
    except Exception as e:
        print(f"\nERROR: {e}")

async def test_card_appraisal(image_path: str, card_description: str):
    """Test appraisal for a specific card image"""
    print("\n" + "=" * 60)
    print(f"Testing: {card_description}")
    print("=" * 60)
    
    try:
        # Read image file
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        print(f"Image loaded: {len(image_data)} bytes")
        print("Calling appraisal service...")
        
        result = await appraisal.appraise_card_from_image(image_data=image_data)
        
        print("\n" + "=" * 60)
        print("APPRAISAL RESULT:")
        print("=" * 60)
        for key, value in result.items():
            print(f"{key}: {value}")
        
        return result
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    print("\n" + "=" * 60)
    print("CARD APPRAISAL TEST SUITE")
    print("=" * 60)
    
    # Test 1: Ho-Oh pricing
    await test_hooh_pricing()
    
    # Test 2: Gengar Prism card (if image available)
    print("\n\nWould you like to test specific card images?")
    print("Please provide the image paths in the script.")
    
    # Example usage:
    # gengar_path = "path/to/gengar.png"
    # await test_card_appraisal(gengar_path, "Gengar Prism Card")
    
    # trainer_path = "path/to/trainer.png"
    # await test_card_appraisal(trainer_path, "Impostor Oak's Revenge Trainer")

if __name__ == "__main__":
    asyncio.run(main())
