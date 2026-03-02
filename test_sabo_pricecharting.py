"""
Test PriceCharting API for Sabo ST13 #ST13-007
Filter order:
  1. Card name  -> pricecharting title
  2. Card number -> pricecharting title
  3. Set name   -> pricecharting title
  4. Language   -> pricecharting title first, then console-name (set)
  5. Cheapest   -> pricecharting price
"""
import asyncio
import httpx
import re
from urllib.parse import quote_plus

API_KEY = "40d8d65da33130a111830698dac61dfe04099357"

CARD_NAME = "Sabo"
SET_NAME = "ST13"
CARD_NUMBER = "ST13-007"
IS_JAPANESE = True


def clean_card_name(card_name: str) -> str:
    name = card_name.split('(')[0].strip()
    name = re.sub(r'\s*-\s*\d+.*$', '', name)
    name = re.sub(r'\s*#\d+.*$', '', name)
    return name.strip()


def filter_by_language(results: list, is_japanese: bool) -> list:
    """
    Language filter order:
    1. Try to match by title (product-name) containing language keyword
    2. If no title match, fall back to console-name (set name) containing language keyword
    """
    japanese_keywords = ['japanese', 'japan', 'jpn']
    english_keywords  = ['english', 'eng']

    if is_japanese:
        # Step 1: Check title for Japanese keyword
        title_matches = [r for r in results
                         if any(kw in r['name'].lower() for kw in japanese_keywords)]
        if title_matches:
            print(f"  -> Language (Japanese) via TITLE: {len(title_matches)} matches")
            for r in title_matches:
                print(f"     '{r['name']}' = ${r['price']:.2f}")
            return title_matches

        # Step 2: Fall back to console-name (set name)
        console_matches = [r for r in results
                           if any(kw in r.get('console_name', '').lower() for kw in japanese_keywords)]
        if console_matches:
            print(f"  -> Language (Japanese) via CONSOLE-NAME: {len(console_matches)} matches")
            for r in console_matches:
                print(f"     '{r['name']}' | Set: '{r['console_name']}' = ${r['price']:.2f}")
            return console_matches

        # Step 3: Fallback - exclude English listings
        non_english = [r for r in results
                       if not any(kw in r['name'].lower() for kw in english_keywords)
                       and not any(kw in r.get('console_name', '').lower() for kw in english_keywords)]
        if non_english and len(non_english) < len(results):
            print(f"  -> Language (Japanese) fallback - excluded English: {len(non_english)} remain")
            return non_english

        print(f"  -> Language filter: No language labels found, keeping all {len(results)}")
        return results

    else:
        # Step 1: Check title for English keyword
        title_matches = [r for r in results
                         if any(kw in r['name'].lower() for kw in english_keywords)]
        if title_matches:
            print(f"  -> Language (English) via TITLE: {len(title_matches)} matches")
            return title_matches

        # Step 2: Fall back to console-name
        console_matches = [r for r in results
                           if any(kw in r.get('console_name', '').lower() for kw in english_keywords)]
        if console_matches:
            print(f"  -> Language (English) via CONSOLE-NAME: {len(console_matches)} matches")
            return console_matches

        # Step 3: Fallback - exclude Japanese listings
        non_japanese = [r for r in results
                        if not any(kw in r['name'].lower() for kw in japanese_keywords)
                        and not any(kw in r.get('console_name', '').lower() for kw in japanese_keywords)]
        if non_japanese and len(non_japanese) < len(results):
            print(f"  -> Language (English) fallback - excluded Japanese: {len(non_japanese)} remain")
            return non_japanese

        print(f"  -> Language filter: No language labels found, keeping all {len(results)}")
        return results


def filter_by_card_number(results: list, card_number: str) -> list:
    if not card_number:
        return results
    clean_number = card_number.replace('#', '').strip()
    matches = [r for r in results if clean_number.upper() in r['name'].upper()]
    if matches:
        print(f"  -> Card number '{clean_number}' via TITLE: {len(matches)} matches")
        return matches
    print(f"  -> Card number '{clean_number}': No matches, keeping all {len(results)}")
    return results


def filter_by_set_name(results: list, set_name: str) -> list:
    if not set_name or set_name == "Unknown":
        return results
    matches = [r for r in results if set_name.upper() in r['name'].upper()]
    if matches:
        print(f"  -> Set name '{set_name}' via TITLE: {len(matches)} matches")
        return matches
    print(f"  -> Set name '{set_name}': No matches in title, keeping all {len(results)}")
    return results


async def test_pricecharting():
    print("=" * 60)
    print(f"Card:     {CARD_NAME}")
    print(f"Set:      {SET_NAME}")
    print(f"Number:   {CARD_NUMBER}")
    print(f"Japanese: {IS_JAPANESE}")
    print("=" * 60)

    clean_name = clean_card_name(CARD_NAME)
    search_query = f"{clean_name} {SET_NAME} {CARD_NUMBER.replace('#', '')}"
    print(f"\n[1] Search query: '{search_query}'")

    url = f"https://www.pricecharting.com/api/products?t={API_KEY}&q={quote_plus(search_query)}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(url)
        print(f"[2] Status: {response.status_code}")

        data = response.json()
        products = data.get('products', [])
        print(f"[3] Found {len(products)} products")

        # Build valid price list with console-name
        valid = []
        print(f"\n[4] Products with prices:")
        for p in products:
            name         = p.get('product-name', 'Unknown')
            console_name = p.get('console-name', '')
            price        = None
            price_type   = None

            for field, ptype in [('loose-price', 'loose'), ('cib-price', 'complete'), ('new-price', 'new')]:
                if p.get(field):
                    try:
                        price = float(p[field]) / 100
                        price_type = ptype
                        break
                    except (ValueError, TypeError):
                        pass

            if price and price > 0:
                valid.append({'name': name, 'console_name': console_name, 'price': price, 'type': price_type})
                print(f"  + '{name}' | Set: '{console_name}' = ${price:.2f} ({price_type})")
            else:
                print(f"  - '{name}' | Set: '{console_name}' = no price")

        if not valid:
            print("No priced products found!")
            return

        print(f"\n[5] Applying filters to {len(valid)} priced products...")

        # 1. Card name -> title
        f = [r for r in valid if clean_name.upper() in r['name'].upper()]
        if f:
            print(f"  -> Card name '{clean_name}' via TITLE: {len(f)} matches")
        else:
            print(f"  -> Card name '{clean_name}': No matches, keeping all")
            f = valid

        # 2. Card number -> title
        f = filter_by_card_number(f, CARD_NUMBER)

        # 3. Set name -> title
        f = filter_by_set_name(f, SET_NAME)

        # 4. Language -> title first, then console-name
        f = filter_by_language(f, IS_JAPANESE)

        # 5. Cheapest
        if f:
            best = min(f, key=lambda x: x['price'])
            print(f"\n[6] RESULT: '{best['name']}' | Set: '{best['console_name']}' = ${best['price']:.2f} ({best['type']})")
        else:
            print("\n[6] No results after filtering!")


if __name__ == "__main__":
    asyncio.run(test_pricecharting())
