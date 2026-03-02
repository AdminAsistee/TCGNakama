"""
Test appraisal with API key to verify cheapest price selection
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Set the API key for testing
os.environ["PRICECHARTING_API_KEY"] = "40d8d65da33130a111830698dac61dfe04099357"

async def test_appraisal():
    from app.services.appraisal import get_market_value_jpy
    
    # Test with the Pikachu card
    print("=" * 80)
    print("Testing Pikachu sA #001/024 appraisal WITH API KEY")
    print("=" * 80)
    
    result = await get_market_value_jpy(
        card_name="Pikachu",
        rarity="Common",
        set_name="sA",
        card_number="#001/024",
        variants=["Japanese"],
        force_refresh=True
    )
    
    print("\n" + "=" * 80)
    print("RESULT:")
    print("=" * 80)
    for key, value in result.items():
        print(f"{key}: {value}")
    print("=" * 80)
    
    # Expected: Should use API and select $3.24 (cheapest), not $7.99

if __name__ == "__main__":
    asyncio.run(test_appraisal())
