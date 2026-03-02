"""
Test alphanumeric card number matching
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Set the API key for testing
os.environ["PRICECHARTING_API_KEY"] = "40d8d65da33130a111830698dac61dfe04099357"

async def test_card_number_matching():
    from app.services.appraisal import _try_pricecharting_api
    
    test_cases = [
        ("Pikachu", "sA", "#001/024", "Numeric with slash"),
        ("Luffy", "One Piece", "OP09-051", "Alphanumeric with prefix"),
        ("Charizard", "SV", "SV1-123", "Alphanumeric set code"),
    ]
    
    for card_name, set_name, card_number, description in test_cases:
        print("\n" + "=" * 80)
        print(f"Test: {description}")
        print(f"Card: {card_name}, Set: {set_name}, Number: {card_number}")
        print("=" * 80)
        
        price = await _try_pricecharting_api(card_name, set_name, card_number, False)
        
        if price:
            print(f"\nResult: ${price} USD")
        else:
            print("\nResult: No price found")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_card_number_matching())
