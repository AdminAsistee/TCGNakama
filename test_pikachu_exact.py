"""
Test with the exact Pikachu card from Shopify
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Set the API key for testing
os.environ["PRICECHARTING_API_KEY"] = "40d8d65da33130a111830698dac61dfe04099357"

async def test_pikachu_card():
    from app.services.appraisal import get_market_value_jpy
    
    print("=" * 80)
    print("Testing: Pikachu (Pikachu) - Pikachu sA #001/024")
    print("=" * 80)
    
    # This is how the admin dashboard will call it
    result = await get_market_value_jpy(
        card_name="Pikachu",  # Extracted from title
        rarity="Common",
        set_name="sA",  # From tags
        card_number="#001/024",  # From tags
        variants=["Japanese"],
        force_refresh=True
    )
    
    print("\n" + "=" * 80)
    print("RESULT:")
    print("=" * 80)
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Market USD: ${result.get('market_usd')}")
        print(f"Market JPY: JPY{result.get('market_jpy')}")
        print(f"Exchange Rate: {result.get('exchange_rate')}")
        print(f"Rate Date: {result.get('rate_date')}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_pikachu_card())
