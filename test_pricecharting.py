"""
Test script to debug PriceCharting scraping for Sugar card
"""
import asyncio
from app.services.appraisal import get_market_value_jpy

async def test_sugar_card():
    """Test market value lookup for Sugar OP04-024"""
    
    print("=" * 60)
    print("Testing PriceCharting Market Value Lookup")
    print("=" * 60)
    
    # Test parameters from the add card form
    card_name = "Sugar"
    set_name = "Kingdom of Intrigue"
    card_number = "OP04-024"
    rarity = "Common"
    
    print(f"\nSearch Parameters:")
    print(f"  Card Name: {card_name}")
    print(f"  Set Name: {set_name}")
    print(f"  Card Number: {card_number}")
    print(f"  Rarity: {rarity}")
    print("\n" + "=" * 60)
    
    # Call the market value function
    result = await get_market_value_jpy(
        card_name=card_name,
        rarity=rarity,
        set_name=set_name,
        card_number=card_number,
        variants=None,
        force_refresh=True
    )
    
    print("\n" + "=" * 60)
    print("Result:")
    print("=" * 60)
    print(f"Market Value JPY: {result.get('market_value_jpy')}")
    print(f"Market Value USD: {result.get('market_value_usd')}")
    print(f"Source: {result.get('source')}")
    print(f"\nFull Response:")
    print(result)
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_sugar_card())
