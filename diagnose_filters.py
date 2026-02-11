import httpx
import asyncio

async def test_filters():
    base_url = "http://localhost:8001"
    
    async with httpx.AsyncClient() as client:
        print("Testing /filter with rarity=Rare...")
        try:
            resp = await client.get(f"{base_url}/filter", params={"rarity": "Rare"})
            print(f"Status: {resp.status_code}")
            # Check for specific rare product or rarity text
            if "Rare" in resp.text:
                print("SUCCESS: Found 'Rare' in response.")
            else:
                print("WARNING: 'Rare' text not found in response.")
            
            # Compare with unfiltered
            print("\nTesting /filter with no params...")
            resp_none = await client.get(f"{base_url}/filter")
            if resp.text == resp_none.text:
                print("CRITICAL: Filtered response is IDENTICAL to unfiltered response.")
            else:
                print("SUCCESS: Filtered response differs from unfiltered response.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_filters())
