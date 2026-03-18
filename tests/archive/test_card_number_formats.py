"""
Test card number filtering with different formats
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Set the API key for testing
os.environ["PRICECHARTING_API_KEY"] = "40d8d65da33130a111830698dac61dfe04099357"

async def test_card(card_name, set_name, card_number, description):
    from app.services.appraisal import get_market_value_jpy
    
    print("\n" + "=" * 80)
    print(f"Test: {description}")
    print(f"Card: {card_name}, Set: {set_name}, Number: {card_number}")
    print("=" * 80)
    
    result = await get_market_value_jpy(
        card_name=card_name,
        rarity="Common",
        set_name=set_name,
        card_number=card_number,
        variants=["Japanese"],
        force_refresh=True
    )
    
    print(f"\nResult: ${result.get('market_usd')} USD = ¥{result.get('market_jpy')} JPY")
    print("=" * 80)

async def main():
    # Test different card number formats
    await test_card("Pikachu", "sA", "#001/024", "Format: #001/024")
    await test_card("Pikachu", "sA", "001/024", "Format: 001/024 (no #)")
    await test_card("Pikachu", "sA", "#1", "Format: #1 (short)")
    await test_card("Pikachu", "sA", "1", "Format: 1 (just number)")

if __name__ == "__main__":
    asyncio.run(main())
