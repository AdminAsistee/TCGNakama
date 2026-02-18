"""
Card Appraisal Service

Provides market value estimation and currency conversion for trading cards.
Integrates card appraisal logic with real-time currency conversion.
"""

import httpx
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import asyncio
import os
import re
import json  # Import at module level to avoid scope issues in exception handlers


# Simple in-memory cache for appraisal results (5 minute TTL)
_appraisal_cache = {}  # Cleared cache
_cache_ttl = timedelta(minutes=5)

# Lock to prevent concurrent Gemini API calls (rate limiting)
_gemini_lock = asyncio.Lock()


def safe_print(message: str):
    """Print with Unicode error handling for Windows cp932 codec."""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: encode to ASCII with backslashreplace for Unicode chars
        print(message.encode('ascii', 'backslashreplace').decode('ascii'))


async def appraise_card_from_image(image_data: bytes = None, image_url: str = None) -> Dict:
    """
    Analyze a card image using Gemini AI vision to extract card details.
    
    Args:
        image_data: Raw image bytes (for uploaded files)
        image_url: URL to image (for URL-based images)
    
    Returns:
        dict: Extracted card information including title, set, card_number, rarity, year, manufacturer
    """
    try:
        import google.generativeai as genai
        import base64
        from PIL import Image
        import io
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            return {'error': 'Gemini API key not configured'}
        
        # Use lock to prevent concurrent Gemini API calls (rate limiting)
        async with _gemini_lock:
            genai.configure(api_key=api_key)
            # Use image-specific model (found in list_gemini_models.py output)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Prepare image for Gemini
            if image_data:
                # Convert bytes to PIL Image
                img = Image.open(io.BytesIO(image_data))
            elif image_url:
                # Download image from URL
                import httpx
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(image_url)
                    if response.status_code != 200:
                        return {'error': f'Failed to download image from URL: {response.status_code}'}
                    img = Image.open(io.BytesIO(response.content))
            else:
                return {'error': 'No image data or URL provided'}
            
            # Single prompt — Gemini thinks internally then outputs ONLY JSON.
            # The JSON parser extracts the last { } block so any leading reasoning text is ignored.
            prompt = """Analyze this trading card image carefully, then output ONLY a JSON object with the fields below. Do not write any explanation — output JSON only.

Before filling in the JSON, mentally note:
- Card name, set/series, card number (exactly as printed), rarity symbol
- Holographic effects (sparkly art box only? or full card rainbow?)
- Border style, set symbol shape, any special markings

Then fill in:

1. card_type: "TRAINER" header → "Trainer" | "ENERGY" → "Energy" | otherwise → "Pokemon"
2. card_name_japanese: Japanese name if visible, else ""
3. card_name_english: ALWAYS provide English name — translate if needed. Never leave empty for known cards.
4. set_name:
   - Japanese modern (2016+): set code at bottom left (e.g. "SV5M", "sA", "s10b") — ignore single regulation letters (D/E/F/G/H)
   - English Pokémon: identify the set from the set symbol icon on the card (e.g. crown = Chilling Reign, fusion symbol = Fusion Strike)
   - PROMO: card number ends with "/P" → "PROMO"
   - Vintage (pre-2016): identify from set symbol or style (e.g. "Base Set", "Jungle", "Fossil", "Carddass Vending")
   - One Piece: prefix from card number (e.g. "OP12" from "OP12-008"); "P-044" format → ""
   - If truly unknown → ""
5. card_number: bottom right corner. Valid: "###/###", "###/P", "No.094", "094", "26", "P-044". Invalid: "ID:..." → ""
6. rarity: ◆=Common, ●=Uncommon, ★=Rare, R, C, U, SR, UR — or "" if not visible
7. special_variants: comma-separated or ""
   - Holo Rare (sparkly art box only, normal borders) → NOT a variant, do NOT write "Prism"
   - Prism Star: ONLY if "Prism Star" is literally in the card name AND full-card rainbow effect
   - Crystal, Reverse Holo, 1st Edition if visible
8. year: copyright year if visible, else ""
9. manufacturer: publisher if visible, else ""

Output ONLY this JSON, nothing else:
{
  "card_type": "",
  "card_name_japanese": "",
  "card_name_english": "",
  "set_name": "",
  "card_number": "",
  "rarity": "",
  "special_variants": "",
  "year": "",
  "manufacturer": ""
}"""

            # Generate content with image
            response = model.generate_content([prompt, img])
            response_text = response.text.strip()

            safe_print(f"[APPRAISE_IMAGE] Gemini response: {response_text}")

            # Parse JSON — extract the last { } block to handle any leading reasoning text
            import re

            
            # Convert null values to empty strings
            # Robust JSON extraction: handle markdown blocks or leading reasoning text
            if "```" in response_text:
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(1)
            else:
                # Extract the last { } block in case model output reasoning text before JSON
                json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
                if json_match:
                    response_text = json_match.group(0)

            card_data = json.loads(response_text)

            # Convert null values to empty strings
            for key in ['card_name_japanese', 'card_name_english', 'set_name', 'card_number', 'year', 'manufacturer', 'rarity', 'special_variants']:
                if card_data.get(key) is None or card_data.get(key) == 'null':
                    card_data[key] = ''

            
            # Post-processing: Filter out ID format card numbers
            card_number = card_data.get('card_number', '')
            if card_number and card_number.upper().startswith('ID:'):
                # Remove ID format completely
                card_data['card_number'] = ''
                card_number = ''
            
            # Post-processing: Detect PROMO set from card number
            # Only applies to Pokémon PROMO format (e.g. "010/P"), NOT One Piece P-prefix (e.g. "P-044")
            set_name = card_data.get('set_name', '')
            is_op_promo = bool(re.match(r'^P-\d+$', card_number))  # One Piece P-044 format
            if card_number and card_number.endswith('/P') and not set_name and not is_op_promo:
                card_data['set_name'] = 'PROMO'
                set_name = 'PROMO'
            elif is_op_promo and set_name.upper() == 'PROMO':
                # Gemini incorrectly set PROMO for a One Piece P-### card — clear it
                card_data['set_name'] = ''
                set_name = ''

            # Post-processing: Strip regulation marks mistaken for set names
            # English Pokémon cards print a single regulation letter (D, E, F, G, H) near the set symbol
            # These are NOT set names — clear them if that's all we got
            REGULATION_MARKS = {'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'}
            if set_name.strip().lower() in REGULATION_MARKS:
                safe_print(f"[APPRAISE] Clearing regulation mark '{set_name}' mistaken for set name")
                card_data['set_name'] = ''
                set_name = ''

            # Extract card type (new field)
            card_type = card_data.get('card_type', 'Pokemon')
            
            # Extract and parse special variants
            special_variants_str = card_data.get('special_variants', '')
            special_variants = [v.strip() for v in special_variants_str.split(',') if v.strip()]
            
            # Get set name and card number
            set_name = card_data.get('set_name', '')
            card_number = card_data.get('card_number', '')
            
            # Post-processing: If Prism variant detected and no set name, use "Prism" as set name
            if 'Prism' in special_variants and not set_name:
                set_name = 'Prism'
                card_data['set_name'] = 'Prism'
            
            # Heuristic: Detect likely Prism cards based on known Prism Pokemon
            # This is a fallback when visual detection fails
            prism_pokemon = ['gengar', 'tyranitar', 'celebi', 'entei', 'raikou', 'suicune', 
                           'ho-oh', 'lugia', 'crobat', 'houndoom', 'kabutops', 'steelix']
            card_name_en_lower = card_data.get('card_name_english', '').lower()
            
            # If it's a known Prism Pokemon, vintage (no modern set code), and no set name yet
            # Check: no set name AND (no card number OR card number doesn't have modern format)
            is_vintage = not card_number or '/' not in card_number
            if (any(pokemon in card_name_en_lower for pokemon in prism_pokemon) and 
                not set_name and 
                is_vintage):
                # Likely a Prism card
                set_name = 'Prism'
                card_data['set_name'] = 'Prism'
                if 'Prism' not in special_variants:
                    special_variants.append('Prism')

            
            # Map rarity to internal system
            rarity_mapping = {
                # Pokémon
                'common': 'Common',
                'uncommon': 'Uncommon',
                'rare': 'Rare',
                'holo rare': 'Rare',
                'reverse holo': 'Rare',
                'ultra rare': 'Ultra Rare',
                'secret rare': 'Ultra Rare',
                'rainbow rare': 'Ultra Rare',
                'hyper rare': 'Ultra Rare',
                # One Piece
                'c': 'Common',
                'uc': 'Uncommon',
                'r': 'Rare',
                'sr': 'Ultra Rare',
                'sar': 'Ultra Rare',
                'sec': 'Ultra Rare',
                'l': 'Ultra Rare',  # Leader cards
                # Magic
                'mythic rare': 'Ultra Rare',
                # Yu-Gi-Oh!
                'super rare': 'Epic',
                'starlight rare': 'Ultra Rare',
                # Vintage special variants
                'prism': 'Ultra Rare',
                'crystal': 'Ultra Rare',
                'shining': 'Ultra Rare',
                'gold star': 'Ultra Rare',
                '★': 'Rare',    # Single black star = Rare Holo (English) or Rare (Japanese)
                '★★': 'Ultra Rare',   # Double star = Ultra Rare / ex / V cards
                '★★★': 'Ultra Rare',  # Triple star = Secret Rare
                # Generic
                'epic': 'Epic',
            }
            
            # Normalize and map rarity
            extracted_rarity = card_data.get('rarity', 'Common')
            if extracted_rarity:
                normalized_rarity = extracted_rarity.lower().strip()
                mapped_rarity = rarity_mapping.get(normalized_rarity, 'Rare')  # Default to Rare if unknown
            else:
                mapped_rarity = 'Common'
            
            # Upgrade rarity if special variants detected
            if special_variants:
                special_variant_lower = [v.lower() for v in special_variants]
                if any(v in ['prism', 'crystal', 'shining', 'gold star'] for v in special_variant_lower):
                    mapped_rarity = 'Ultra Rare'
            
            # Build formatted card name based on card type
            card_name_jp = card_data.get('card_name_japanese', '')
            card_name_en = card_data.get('card_name_english', '')
            set_name = card_data.get('set_name', '')
            card_number = card_data.get('card_number', '')
            
            # Format the card name differently based on card type
            name_parts = []
            
            if card_type == 'Trainer':
                # Trainer cards: "Japanese (English) #CardNumber"
                if card_name_jp and card_name_en and card_name_jp != card_name_en:
                    name_parts.append(f"{card_name_jp} ({card_name_en})")
                elif card_name_jp:
                    name_parts.append(card_name_jp)
                elif card_name_en:
                    name_parts.append(card_name_en)
                
                # Add card number if available (no "- Trainer" label)
                if card_number:
                    formatted_number = card_number if card_number.startswith('#') else f"#{card_number}"
                    name_parts.append(formatted_number)
                
                formatted_card_name = ' '.join(name_parts) if name_parts else 'Unknown Trainer'
            
            else:
                # Pokemon/Energy cards
                if card_name_jp and card_name_en and card_name_jp != card_name_en:
                    name_parts.append(f"{card_name_jp} ({card_name_en})")
                elif card_name_jp:
                    name_parts.append(card_name_jp)
                elif card_name_en:
                    name_parts.append(card_name_en)
                
                # Add set name if available, otherwise use fallback for vintage cards
                if set_name:
                    name_parts.append(f"- {set_name}")
                elif card_data.get('year') and not re.match(r'^P-\d+$', card_number):
                    # Only label as "Vintage" if it's actually a vintage card
                    # Modern cards have "###/###" format; vintage cards have standalone numbers like "094"
                    is_vintage_number = '/' not in card_number if card_number else True
                    year = card_data['year']
                    is_vintage_year = int(year) < 2003 if year.isdigit() else False
                    if is_vintage_number and is_vintage_year:
                        name_parts.append(f"- Vintage {year}")

                elif special_variants:
                    # Special variant without set (e.g., Prism)
                    name_parts.append(f"- {special_variants[0]}")
                
                # Add card number if available
                if card_number:
                    formatted_number = card_number if card_number.startswith('#') else f"#{card_number}"
                    name_parts.append(formatted_number)
                
                formatted_card_name = ' '.join(name_parts) if name_parts else 'Unknown Card'
            
            # Build result with new fields
            result = {
                'card_name': formatted_card_name,
                'card_type': card_type,
                'set_name': set_name if set_name else '',  # Ensure empty string, not None
                'card_number': card_number if card_number else '',  # Ensure empty string, not None
                'rarity': mapped_rarity,
                'special_variants': special_variants,  # List of special variants
                'year': card_data.get('year', ''),
                'manufacturer': card_data.get('manufacturer', ''),
                'raw_rarity': extracted_rarity,  # Include original for debugging
                'card_name_japanese': card_name_jp,  # Keep for reference
                'card_name_english': card_name_en   # Keep for reference
            }

            
            safe_print(f"[APPRAISE_IMAGE] Extracted: {result}")
            return result
            
    except json.JSONDecodeError as e:
        safe_print(f"[APPRAISE_IMAGE] JSON parsing error: {e}")
        safe_print(f"[APPRAISE_IMAGE] Response was: {response_text}")
        return {'error': 'Failed to parse AI response. Please try again.'}
    except Exception as e:
        safe_print(f"[APPRAISE_IMAGE] Error: {e}")
        return {'error': f'Image appraisal failed: {str(e)}'}



async def get_market_value_jpy(
    card_name: str,
    rarity: str,
    set_name: str = "Unknown",
    card_number: str = "",
    variants: Optional[list] = None,
    force_refresh: bool = False
) -> Dict:
    """
    Get market value estimate in JPY for a trading card.
    
    Args:
        card_name: Name of the card
        rarity: Rarity level (Common, Rare, Epic, Ultra Rare, etc.)
        set_name: Card set name
        card_number: Card number (e.g., #001/024)
        variants: List of variants (e.g., ['1st Edition', 'Holographic', 'Japanese'])
        force_refresh: If True, bypass cache and fetch fresh data
    
    Returns:
        dict: Market value data including JPY amount and price comparison
    """
    # Create cache key from card details
    cache_key = f"{card_name}|{rarity}|{set_name}|{card_number}|{variants}"
    
    # Check cache first (unless force_refresh is True)
    if not force_refresh and cache_key in _appraisal_cache:
        cached_data, cached_time = _appraisal_cache[cache_key]
        if datetime.now() - cached_time < _cache_ttl:
            safe_print(f"[APPRAISE] Using cached result for '{card_name}'")
            return cached_data
        else:
            # Remove expired cache entry
            del _appraisal_cache[cache_key]
    
    if force_refresh:
        safe_print(f"[APPRAISE] Force refresh - bypassing cache for '{card_name}'")
    
    try:
        # Step 1: Estimate market value in USD
        market_usd = await estimate_market_value_usd(card_name, rarity, set_name, card_number, variants)
        
        if market_usd == 0:
            return {'error': 'Unable to estimate market value'}
        
        # Step 2: Convert USD to JPY using Frankfurter API
        exchange_rate = 153.7  # Fallback rate
        rate_date = "estimated"
        market_jpy = market_usd * exchange_rate # Initialize with fallback
        
        try:
            safe_print(f"[APPRAISE] Converting ${market_usd} USD to JPY...")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://api.frankfurter.app/latest",
                    params={
                        'from': 'USD',
                        'to': 'JPY',
                        'amount': market_usd
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    safe_print(f"[APPRAISE] Frankfurter API response: {data}")
                    market_jpy = data['rates']['JPY']
                    exchange_rate = market_jpy / market_usd
                    rate_date = data.get('date', 'today')
                    safe_print(f"[APPRAISE] Converted: ${market_usd} USD -> ¥{market_jpy} JPY (rate: {exchange_rate})")
                else:
                    # Use fallback rate if API returns non-200 status
                    safe_print(f"[APPRAISE] Currency API returned status {response.status_code}, using fallback rate: {exchange_rate}")
                    # market_jpy is already initialized with fallback
        except (httpx.TimeoutException, Exception) as e:
            # Use fallback rate if currency API fails or times out
            safe_print(f"[APPRAISE] Currency API timeout or error ({e}), using fallback rate: {exchange_rate}")
            # market_jpy is already initialized with fallback
        
        result = {
            'market_usd': round(market_usd, 2),
            'market_jpy': int(market_jpy),
            'exchange_rate': round(exchange_rate, 2),
            'rate_date': rate_date,
            'confidence': 'Medium'  # Mock confidence level
        }
        
        # Cache the successful result
        _appraisal_cache[cache_key] = (result, datetime.now())
        
        return result
    
    except Exception as e:
        safe_print(f"[APPRAISE] Unexpected error: {e}")
        return {'error': f'Appraisal failed: {str(e)}'}


async def estimate_market_value_usd(
    card_name: str,
    rarity: str,
    set_name: str = "Unknown",
    card_number: str = "",
    variants: Optional[list] = None
) -> float:
    """
    Estimate market value in USD using PriceCharting with Gemini filtering.
    
    Args:
        card_name: Name of the card
        rarity: Rarity level
        set_name: Card set name
        card_number: Card number
        variants: List of variants
    
    Returns:
        float: Estimated market value in USD
    """
    import httpx
    from bs4 import BeautifulSoup
    import re
    
    # Check if Japanese card
    is_japanese = variants and 'Japanese' in variants
    
    # Try PriceCharting API first (official, no blocking)
    price = await _try_pricecharting_api(card_name, set_name, card_number, is_japanese)
    if price:
        return price
    
    # Fallback to scraping if API not available or failed
    safe_print(f"[APPRAISE] API unavailable, trying web scraping...")
    price = await _try_pricecharting_scrape(card_name, set_name, card_number, is_japanese)
    if price:
        return price
    
    # Fallback to mock data if both API and scraping fail
    safe_print(f"[APPRAISE] PriceCharting failed for '{card_name}', using mock data")
    return _mock_estimate(card_name, rarity, set_name, variants)


def _try_pokemontcg_api(card_name: str, set_name: str, rarity: str, card_number: str = "", is_japanese: bool = False) -> Optional[float]:
    """Try to get price from PokémonTCG.io API."""
    try:
        import httpx
        
        search_name = card_name.split('(')[0].strip()
        
        # Build search query
        search_query = f'name:"{search_name}"'
        if set_name and set_name != "Unknown":
            search_query += f' set.name:"{set_name}"'
        if card_number:
            # Extract just the number part (e.g., "001" from "#001/024")
            num = card_number.replace('#', '').split('/')[0].strip()
            if num:
                search_query += f' number:{num}'
        
        url = "https://api.pokemontcg.io/v2/cards"
        params = {"q": search_query, "pageSize": 10}
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, params=params)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            cards = data.get('data', [])
            
            if not cards:
                return None
            
            # Find best match
            best_match = None
            for card in cards:
                card_set = card.get('set', {}).get('name', '')
                card_rarity = card.get('rarity', '')
                
                if set_name.lower() in card_set.lower() and rarity.lower() in card_rarity.lower():
                    best_match = card
                    break
            
            if not best_match:
                best_match = cards[0]
            
            # Extract price
            tcgplayer = best_match.get('tcgplayer', {})
            prices = tcgplayer.get('prices', {})
            
            for price_type in ['holofoil', 'normal', '1stEditionHolofoil', 'reverseHolofoil', 'unlimitedHolofoil']:
                if price_type in prices:
                    market_price = prices[price_type].get('market')
                    if market_price:
                        price = float(market_price)
                        safe_print(f"[APPRAISE] PokémonTCG.io: ${price} for '{search_name}'")
                        return price
            
            return None
                
    except httpx.TimeoutException:
        safe_print(f"[APPRAISE] PokémonTCG.io: Timeout (skipping)")
        return None
    except Exception as e:
        safe_print(f"[APPRAISE] PokémonTCG.io error: {e}")
        return None


async def _gemini_filter_cards(search_query: str, results: list[dict]) -> list[dict]:
    """
    Use Gemini AI to filter cards that match the search query.
    
    Args:
        search_query: The card we're searching for (e.g., "Pikachu sA #001/024")
        results: List of dicts with 'name' and 'price' keys from PriceCharting
    
    Returns:
        Filtered list of matching cards
    """
    try:
        import google.generativeai as genai
        import os
        import json
        import re
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            safe_print("[APPRAISE] No Gemini API key, using all results")
            return results  # Fallback to all results if no API key
        
        # Use lock to prevent concurrent Gemini API calls (rate limiting)
        async with _gemini_lock:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Build the prompt
            results_text = "\n".join([
                f"{i+1}. \"{r['name']}\" - ${r['price']}"
                for i, r in enumerate(results)
            ])
            
            prompt = f"""You are a trading card expert. I'm searching for: "{search_query}"

PriceCharting returned these results:
{results_text}

Analyze which cards match my search query. Follow these rules IN ORDER:

1. **Card Number Match (HIGHEST PRIORITY)**:
   - If the card number in the result matches the search query, it's likely a match
   - Card numbers might be formatted differently (#1 vs #001/024 vs OP13-001)

2. **Prefer REGULAR versions over special variants**:
   - PREFER cards WITHOUT brackets like [Ichiban Kuji], [Promo], [Alt Art], [Serial], [Parallel], etc.
   - These special variants are usually more expensive collector versions
   - ONLY include special variants if NO regular version exists

3. **Prefer ENGLISH versions over Japanese versions**:
   - PREFER cards WITHOUT "Japanese" in the title
   - English versions are typically cheaper and more common
   - ONLY include Japanese versions if NO English version exists

4. **Card Name Match**:
   - The base card name should match (e.g., "Luffy", "Shanks", "Pikachu")
   - Ignore differences in punctuation (e.g., "Monkey D Luffy" vs "Monkey.D.Luffy")

5. **Variant Indicators (ONLY for Pokémon)**:
   - For Pokémon cards, variants like sA, V, VMAX, VSTAR must match exactly
   - For One Piece cards, the base card is what matters

Examples:
- Search "Monkey D Luffy OP13-001"
  - BEST: "Monkey.D.Luffy OP13-001 One Piece Carrying on His Will" (English regular) ✓✓✓
  - OK: "Monkey.D.Luffy OP13-001 One Piece Japanese..." (Japanese regular) ✓
  - AVOID: "Monkey.D.Luffy [Ichiban Kuji] OP13-001" (special variant) ✗
- Search "Pikachu sA #001/024" 
  - MATCHES: "Pikachu sA #1" ✓ (same variant, compatible numbers)
  - REJECTS: "Pikachu V #001" ✗ (different Pokémon variant)

Return ONLY the indices of the BEST matching cards (English regular versions preferred) as a JSON array.
Prioritize: English regular > Japanese regular > English special > Japanese special
Example: [1, 3] or [2]

If no cards match, return an empty array: []
"""
            
            response = model.generate_content(prompt)
            response_text = response.text.strip()
        
        # Extract JSON from response (might have markdown code blocks)
        if "```" in response_text:
            # Extract from code block
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
        
        matching_indices = json.loads(response_text)
        
        if not matching_indices:
            safe_print(f"[APPRAISE] Gemini found no matching cards for '{search_query}'")
            return []
        
        # Convert 1-indexed to 0-indexed and filter results
        matching_results = [results[i-1] for i in matching_indices if 0 < i <= len(results)]
        
        safe_print(f"[APPRAISE] Gemini filtered {len(results)} results to {len(matching_results)} matches")
        return matching_results if matching_results else results
    
    except Exception as e:
        safe_print(f"[APPRAISE] Gemini filtering error: {e}, using all results")
        return results  # Fallback to all results


def _filter_by_language(results: List[dict], is_japanese: bool) -> List[dict]:
    """
    Filter PriceCharting results by language.
    
    Filter order:
    1. Check product title (name) for language keyword
    Logic:
    - Japanese card: search for 'japanese' in BOTH title AND console name.
      If found → keep those. If not found → keep only unlabeled results
      (no language keyword at all), since PriceCharting often has no label
      for Japanese-only sets (e.g. One Piece). Unlabeled = not English.
    - English card: exclude anything with 'japanese' in title OR console name.
      Unlabeled results are treated as English (PriceCharting default).

    Args:
        results: List of price results with 'name' and 'console_name' fields
        is_japanese: True for Japanese cards, False for English

    Returns:
        Filtered list, or original list if no language matches found
    """
    if not results:
        return results

    japanese_keywords = ['japanese', 'japan', 'jpn', '日本']
    english_keywords = ['english', 'eng']

    def has_japanese_label(r):
        """Check both title AND console name for Japanese keywords."""
        name = r['name'].lower()
        console = r.get('console_name', '').lower()
        return any(kw in name for kw in japanese_keywords) or any(kw in console for kw in japanese_keywords)

    def has_english_label(r):
        """Check both title AND console name for English keywords."""
        name = r['name'].lower()
        console = r.get('console_name', '').lower()
        return any(kw in name for kw in english_keywords) or any(kw in console for kw in english_keywords)

    def has_any_language_label(r):
        return has_japanese_label(r) or has_english_label(r)

    if is_japanese:
        # Step 1: Find results explicitly labeled Japanese (title OR console name)
        japanese_labeled = [r for r in results if has_japanese_label(r)]
        if japanese_labeled:
            safe_print(f"[PRICECHARTING] Language filter (Japanese): {len(japanese_labeled)} results labeled Japanese")
            return japanese_labeled

        # Step 2: No explicit Japanese label found.
        # Keep only unlabeled results (no language keyword in title or console).
        # Unlabeled in PriceCharting usually means it's the base/Japanese-only version.
        unlabeled = [r for r in results if not has_any_language_label(r)]
        if unlabeled:
            safe_print(f"[PRICECHARTING] Language filter (Japanese): no Japanese label found, keeping {len(unlabeled)} unlabeled results (assumed Japanese/base)")
            return unlabeled

        # Step 3: All results have language labels but none are Japanese — return all as fallback
        safe_print(f"[PRICECHARTING] Language filter (Japanese): no matching results, keeping all {len(results)} as fallback")
        return results

    else:
        # English card: exclude anything explicitly labeled Japanese (title OR console name).
        # Unlabeled results are treated as English (PriceCharting default).
        non_japanese = [r for r in results if not has_japanese_label(r)]
        if non_japanese:
            excluded = len(results) - len(non_japanese)
            if excluded > 0:
                safe_print(f"[PRICECHARTING] Language filter (English): excluded {excluded} Japanese-labeled results, {len(non_japanese)} remain")
            else:
                safe_print(f"[PRICECHARTING] Language filter (English): no Japanese labels found, keeping all {len(results)} results")
            return non_japanese

        # All results were Japanese-labeled — return all as fallback
        safe_print(f"[PRICECHARTING] Language filter (English): all results are Japanese-labeled, keeping all {len(results)} as fallback")
        return results


async def _try_pricecharting_api(card_name: str, set_name: str, card_number: str = "", is_japanese: bool = False) -> Optional[float]:
    """Try to get price from PriceCharting API (official, no scraping)."""
    try:
        import httpx
        import os
        import re
        from urllib.parse import quote_plus
        
        # Check if API key is configured
        api_key = os.getenv("PRICECHARTING_API_KEY")
        if not api_key:
            safe_print("[PRICECHARTING_API] No API key configured, skipping API")
            return None
        
        # Build search query - extract English name if Japanese name has parenthesized English
        search_name = card_name
        paren_match = re.search(r'\(([^)]+)\)', card_name)
        if paren_match:
            # Use the English name in parentheses (e.g., "ジュラキュール (Dracule Mihawk)" -> "Dracule Mihawk")
            search_name = paren_match.group(1).strip()
        else:
            search_name = card_name.split('(')[0].strip()
        
        query_parts = [search_name]
        
        if set_name and set_name != "Unknown":
            query_parts.append(set_name)
        
        if card_number:
            clean_card_number = card_number.replace('#', '')
            query_parts.append(clean_card_number)
        
        search_query = " ".join(query_parts)
        
        # API endpoint
        url = f"https://www.pricecharting.com/api/products?t={api_key}&q={quote_plus(search_query)}"
        
        safe_print(f"[PRICECHARTING_API] Search query: '{search_query}'")
        safe_print(f"[PRICECHARTING_API] Calling API...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            safe_print(f"[PRICECHARTING_API] Response status: {response.status_code}")
            
            if response.status_code != 200:
                safe_print(f"[PRICECHARTING_API] Non-200 status, falling back to scraping")
                return None
            
            data = response.json()
            
            if not data.get('products') or len(data['products']) == 0:
                safe_print(f"[PRICECHARTING_API] No products found")
                return None
            
            products = data['products']
            safe_print(f"[PRICECHARTING_API] Found {len(products)} products")
            
            # Collect all valid prices from all products
            valid_prices = []
            for product in products:
                product_name = product.get('product-name', 'Unknown')
                console_name = product.get('console-name', '')  # Set name from PriceCharting
                
                # Try to get price (prefer loose-price for single cards)
                price = None
                price_type = None
                
                if 'loose-price' in product and product['loose-price']:
                    try:
                        # API returns prices in cents, convert to dollars
                        price = float(product['loose-price']) / 100
                        price_type = "loose"
                    except (ValueError, TypeError):
                        pass
                
                if not price and 'cib-price' in product and product['cib-price']:
                    try:
                        # API returns prices in cents, convert to dollars
                        price = float(product['cib-price']) / 100
                        price_type = "complete"
                    except (ValueError, TypeError):
                        pass
                
                if not price and 'new-price' in product and product['new-price']:
                    try:
                        # API returns prices in cents, convert to dollars
                        price = float(product['new-price']) / 100
                        price_type = "new"
                    except (ValueError, TypeError):
                        pass
                
                if price and price > 0:
                    valid_prices.append({
                        'name': product_name,
                        'console_name': console_name,  # Store set name for language filtering
                        'price': price,
                        'type': price_type
                    })
                    safe_print(f"[PRICECHARTING_API]   - '{product_name}' | Set: '{console_name}' = ${price} ({price_type})")
            
            if not valid_prices:
                safe_print(f"[PRICECHARTING_API] No valid prices found")
                return None
            
            
            # Step 1: Filter by card name first
            filtered_prices = valid_prices
            
            # Extract just the card name, removing card number and set info
            # Examples: "Pikachu - 26 #26" → "Pikachu", "Charizard - 4 #4" → "Charizard"
            card_name_only = card_name.split('(')[0].strip()  # Remove Japanese name in parentheses
            card_name_only = re.sub(r'\s*-\s*\d+.*$', '', card_name_only)  # Remove " - 26 #26"
            card_name_only = re.sub(r'\s*#\d+.*$', '', card_name_only)  # Remove " #26"
            card_name_english = card_name_only.strip()
            
            if card_name_english:
                
                safe_print(f"[PRICECHARTING_API] Filtering by card name: '{card_name_english}'")
                
                name_matches = []
                for item in valid_prices:
                    # Check if card name appears in product name (case-insensitive)
                    if card_name_english.upper() in item['name'].upper():
                        name_matches.append(item)
                        safe_print(f"[PRICECHARTING_API]   ✓ Name match: '{item['name']}'")
                
                if name_matches:
                    safe_print(f"[PRICECHARTING_API] Filtered to {len(name_matches)} products matching card name")
                    filtered_prices = name_matches
                else:
                    safe_print(f"[PRICECHARTING_API] No card name matches found")
            
            # Step 2: Filter by set name (if provided)
            if set_name and set_name not in ["Unknown", ""]:
                safe_print(f"[PRICECHARTING_API] Filtering by set name: '{set_name}'")
                set_matches = []
                for item in filtered_prices:
                    # Check if set name appears in product name (case-insensitive)
                    if set_name.upper() in item['name'].upper():
                        set_matches.append(item)
                        safe_print(f"[PRICECHARTING_API]   ✓ Set match: '{item['name']}'")
                
                if set_matches:
                    safe_print(f"[PRICECHARTING_API] Filtered to {len(set_matches)} products matching set name")
                    filtered_prices = set_matches
                else:
                    safe_print(f"[PRICECHARTING_API] No set name matches found, keeping previous results")
            
            # Step 3: Filter by card number (if card number provided)
            if card_number:
                
                # Normalize the search card number: remove common separators and symbols
                # e.g., "#OP09-051" -> "OP09051", "001/024" -> "001024"
                search_normalized = re.sub(r'[#\-/\s]', '', card_number).upper()
                
                safe_print(f"[PRICECHARTING_API] Looking for card number: '{card_number}'")
                
                # Generate multiple search variations
                # e.g., "027/071" -> try "027/071", "027-071", "027071", "027", "27"
                variations = set()  # Use set to avoid duplicates
                
                # Original format
                variations.add(card_number.upper())
                
                # Normalized (no separators)
                normalized = re.sub(r'[#\-/\s]', '', card_number).upper()
                variations.add(normalized)
                
                # With dash instead of slash
                if '/' in card_number:
                    variations.add(card_number.replace('/', '-').upper())
                
                # Just the first number (before / or -)
                first_num = re.split(r'[/\-]', card_number)[0].strip('#').strip()
                variations.add(first_num.upper())
                
                # Without leading zeros (e.g., "027" -> "27")
                first_num_no_zeros = first_num.lstrip('0') or '0'
                variations.add(first_num_no_zeros.upper())
                
                safe_print(f"[PRICECHARTING_API] Trying variations: {list(variations)}")
                
                # Try to find products that contain any of these variations
                number_matches = []
                for item in filtered_prices:  # Search in filtered_prices, not valid_prices
                    product_name_upper = item['name'].upper()
                    
                    # Check if any variation appears in the product name
                    for variation in variations:
                        if variation in product_name_upper:
                            number_matches.append(item)
                            safe_print(f"[PRICECHARTING_API]   ✓ Number match ('{variation}'): '{item['name']}'")
                            break  # Don't check other variations for this item
                
                if number_matches:
                    safe_print(f"[PRICECHARTING_API] Filtered to {len(number_matches)} products matching card number")
                    filtered_prices = number_matches
                else:
                    safe_print(f"[PRICECHARTING_API] No card number matches, using all {len(valid_prices)} results")
            
            # Step 3: Filter by language (Japanese vs English)
            safe_print(f"[PRICECHARTING_API] Filtering by language: {'Japanese' if is_japanese else 'English'}")
            filtered_prices = _filter_by_language(filtered_prices, is_japanese)
            
            # Step 4: Use Gemini AI to filter results for the best match
            search_desc = f"{search_name}"
            if card_number:
                search_desc += f" {card_number}"
            if set_name and set_name != 'Unknown':
                search_desc += f" {set_name}"
            
            gemini_filtered = await _gemini_filter_cards(search_desc, filtered_prices)
            
            if gemini_filtered:
                # Use Gemini's best match (first result from filtered list)
                best = gemini_filtered[0]
                safe_print(f"[PRICECHARTING_API] Gemini selected: '{best['name']}' = ${best['price']} ({best.get('type', 'unknown')})")
                return best['price']
            else:
                # Gemini found no matches — select cheapest from filtered results as fallback
                cheapest = min(filtered_prices, key=lambda x: x['price'])
                safe_print(f"[PRICECHARTING_API] Gemini no match, fallback cheapest: '{cheapest['name']}' = ${cheapest['price']} ({cheapest['type']})")
                return cheapest['price']
    
    except Exception as e:
        safe_print(f"[PRICECHARTING_API] Error: {e}")
        return None


async def _try_pricecharting_scrape(card_name: str, set_name: str, card_number: str = "", is_japanese: bool = False) -> Optional[float]:
    """Try to scrape price from PriceCharting.com - SPECIFIC SEARCH ONLY."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        import re
        
        # Extract English name only (remove Japanese part)
        if '(' in card_name and ')' in card_name:
            # Format: "Japanese (English)" → extract "English"
            english_part = card_name.split('(')[1].split(')')[0].strip()
            search_name = english_part
        else:
            search_name = card_name.split('(')[0].strip()
        
        # Build SPECIFIC search query - must include card number
        # We want accurate pricing, not generic fallbacks
        query_parts = [search_name]
        
        if set_name and set_name not in ["Unknown", ""]:
            query_parts.append(set_name)
        
        # Require card number to make search specific
        if not card_number:
            safe_print(f"[APPRAISE] PriceCharting: Skipping - no card number")
            return None
        
        # Add # symbol to card number for PriceCharting
        if not card_number.startswith('#'):
            clean_card_number = f"#{card_number}"
        else:
            clean_card_number = card_number
        query_parts.append(clean_card_number)
        
        # Use proper URL encoding
        from urllib.parse import quote_plus
        search_query = " ".join(query_parts)
        encoded_query = quote_plus(search_query)
        url = f"https://www.pricecharting.com/search-products?q={encoded_query}&type=prices"
        
        safe_print(f"[PRICECHARTING] Search query: '{search_query}'")
        safe_print(f"[PRICECHARTING] URL: {url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            
            safe_print(f"[PRICECHARTING] Response status: {response.status_code}")
            safe_print(f"[PRICECHARTING] Response length: {len(response.text)} bytes")
            
            if response.status_code != 200:
                safe_print(f"[PRICECHARTING] Non-200 status, aborting")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract all card names and prices from search results
            results = []
            
            # Find all table rows in search results
            rows = soup.find_all('tr')
            safe_print(f"[PRICECHARTING] Found {len(rows)} table rows")
            
            for row in rows:
                # Find card name in <td class='title'>
                name_elem = row.find('td', class_='title')
                if not name_elem:
                    continue
                    
                card_title = name_elem.get_text(strip=True)
                
                # Find price in the same row (looking for used_price which is the main price)
                price_elem = row.find('td', class_='used_price')
                if not price_elem:
                    continue
                    
                price_text = price_elem.get_text(strip=True)
                match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                if match:
                    price = float(match.group(1).replace(',', ''))
                    if price > 0:
                        safe_print(f"[PRICECHARTING] Found result: '{card_title}' = ${price}")
                        results.append({"name": card_title, "price": price})
            
            
            if not results:
                safe_print(f"[APPRAISE] PriceCharting: No results found for '{search_name}'")
                safe_print(f"[APPRAISE] Checking for suggestion links...")
                
                # Look for suggestion links on the page
                suggestion_links = soup.find_all('a', href=True)
                
                for link in suggestion_links:
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True)
                    
                    # Only check game detail pages
                    if '/game/' not in href:
                        continue
                    
                    # Skip non-English pages (e.g., /de/, /fr/, /es/)
                    if '/de/' in href or '/fr/' in href or '/es/' in href or '/it/' in href:
                        continue
                    
                    # Create card number variations for matching
                    # e.g., #018/051 -> ['018051', '18051', '01851', '1851', '018', '18']
                    card_num_clean = card_number.replace('#', '').replace('-', '')
                    variations = [card_num_clean.replace('/', '').lower()]
                    
                    # Add main number (before slash)
                    if '/' in card_num_clean:
                        main_num = card_num_clean.split('/')[0]
                        variations.append(main_num.lower())
                        # Add version without leading zeros
                        if main_num.isdigit():
                            variations.append(str(int(main_num)))
                    
                    href_clean = href.lower().replace('-', '').replace('/', '')
                    
                    # Look for links that contain any variation of the card number
                    if any(var in href_clean for var in variations):
                        # Found a potential match, try to scrape the detail page
                        detail_url = href if href.startswith('http') else f"https://www.pricecharting.com{href}"
                        safe_print(f"[APPRAISE] Found suggestion: {link_text} -> {detail_url}")
                        
                        try:
                            detail_response = client.get(detail_url, headers=headers, timeout=10.0)
                            if detail_response.status_code == 200:
                                detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                                
                                # Look for "Ungraded" price in the price table
                                # The detail page has a table with "Ungraded" row
                                ungraded_row = detail_soup.find('td', string=re.compile(r'Ungraded', re.I))
                                if ungraded_row:
                                    # Find the price in the next cell
                                    price_cell = ungraded_row.find_next_sibling('td')
                                    if price_cell:
                                        price_text = price_cell.get_text(strip=True)
                                        price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                                        if price_match:
                                            price = float(price_match.group(1).replace(',', ''))
                                            if price > 0:
                                                safe_print(f"[APPRAISE] Detail page (Ungraded): ${price}")
                                                return price
                                
                                # Fallback: try to find "used-price" span
                                used_price_elem = detail_soup.find('span', id='used-price')
                                if used_price_elem:
                                    price_text = used_price_elem.get_text(strip=True)
                                    price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                                    if price_match:
                                        price = float(price_match.group(1).replace(',', ''))
                                        if price > 0:
                                            safe_print(f"[APPRAISE] Detail page (Used): ${price}")
                                            return price
                                            
                        except Exception as e:
                            safe_print(f"[APPRAISE] Error scraping detail page: {e}")
                            continue
                
                # No suggestions found or scraped
                return None
            
            safe_print(f"[APPRAISE] PriceCharting: Found {len(results)} total results")
            
            # Progressive filtering approach:
            # 1. Filter by card name
            # 2. Filter by set name (if provided)
            # 3. Filter by card number
            # 4. Use Gemini to filter variants
            # 5. Filter by Japanese language
            # 6. Select cheapest
            
            filtered_results = results
            
            # Step 1: Filter by card name (fuzzy match)
            name_matches = [r for r in filtered_results if search_name.lower() in r['name'].lower()]
            if name_matches:
                safe_print(f"[APPRAISE] Filtered by card name '{search_name}': {len(name_matches)} matches")
                filtered_results = name_matches
            else:
                safe_print(f"[APPRAISE] No card name matches for '{search_name}', keeping all results")
            
            # Step 2: Filter by set name (if provided)
            safe_print(f"[APPRAISE] Set name provided: '{set_name}'")
            if set_name and set_name not in ["Unknown", ""]:
                safe_print(f"[APPRAISE] Attempting to filter by set name '{set_name}'")
                set_matches = [r for r in filtered_results if set_name.lower() in r['name'].lower()]
                if set_matches:
                    safe_print(f"[APPRAISE] Filtered by set name '{set_name}': {len(set_matches)} matches")
                    filtered_results = set_matches
                else:
                    safe_print(f"[APPRAISE] No set name matches for '{set_name}', keeping previous results")
            else:
                safe_print(f"[APPRAISE] Skipping set name filter (set_name='{set_name}')")
            
            # Step 3: Filter by card number
            # Extract just the number part (e.g., "OP13-001" from "#OP13-001")
            clean_number = card_number.replace('#', '').strip()
            
            # Extract the main card number (before the slash if present)
            main_number = clean_number.split('/')[0] if '/' in clean_number else clean_number
            
            # Create variations to match (with and without leading zeros)
            number_variations = [main_number]
            
            # If it's a numeric card number, add version without leading zeros
            if main_number.isdigit():
                number_variations.append(str(int(main_number)))  # Remove leading zeros
            
            # Also try the full number with slash
            if '/' in clean_number:
                number_variations.append(clean_number)
            
            # Filter results that contain any variation of the card number
            number_matches = []
            for result in filtered_results:
                result_name = result['name']
                # Check if any variation appears in the result name
                for var in number_variations:
                    # If variation contains letters (e.g., OP13-001), match anywhere
                    if any(c.isalpha() for c in var):
                        if var in result_name:
                            number_matches.append(result)
                            break
                    # If purely numeric, require # or space separator
                    elif f"#{var}" in result_name or f" {var}/" in result_name or f" {var} " in result_name:
                        number_matches.append(result)
                        break
            
            if number_matches:
                safe_print(f"[APPRAISE] Filtered by card number {number_variations}: {len(number_matches)} matches")
                filtered_results = number_matches
            else:
                # Fallback: if no card number matches, use previous results (limit to 20)
                safe_print(f"[APPRAISE] No card number matches for {number_variations}, using previous results")
                filtered_results = filtered_results[:20] if len(filtered_results) > 20 else filtered_results
            
            # Step 4: Use Gemini to filter matching cards (variant filtering)
            import asyncio
            matching_results = await _gemini_filter_cards(search_query, filtered_results)
            
            if not matching_results:
                safe_print(f"[APPRAISE] PriceCharting: No matching cards after Gemini filtering")
                
                # Try to find suggestion links and scrape detail pages
                safe_print(f"[APPRAISE] Checking for suggestion links...")
                suggestion_links = soup.find_all('a', href=True)
                
                for link in suggestion_links[:10]:  # Check first 10 links
                    href = link.get('href', '')
                    link_text = link.get_text(strip=True)
                    
                    # Look for links that contain the card number
                    if clean_number.lower() in href.lower() or clean_number.lower() in link_text.lower():
                        # Found a potential match, try to scrape the detail page
                        detail_url = href if href.startswith('http') else f"https://www.pricecharting.com{href}"
                        safe_print(f"[APPRAISE] Found suggestion link: {link_text}")
                        
                        try:
                            detail_response = client.get(detail_url, headers=headers, timeout=10.0)
                            if detail_response.status_code == 200:
                                detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
                                
                                # Look for the "Used" price on detail page
                                used_price_elem = detail_soup.find('span', id='used-price')
                                if not used_price_elem:
                                    # Try alternative selectors
                                    used_price_elem = detail_soup.find('td', string=re.compile(r'Used', re.I))
                                    if used_price_elem:
                                        used_price_elem = used_price_elem.find_next('td')
                                
                                if used_price_elem:
                                    price_text = used_price_elem.get_text(strip=True)
                                    price_match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                                    if price_match:
                                        price = float(price_match.group(1).replace(',', ''))
                                        safe_print(f"[APPRAISE] Detail page price: ${price}")
                                        return price
                        except Exception as e:
                            safe_print(f"[APPRAISE] Error scraping detail page: {e}")
                            continue
                
                return None
            
            # Step 5: Filter by language
            safe_print(f"[APPRAISE] PriceCharting: Filtering by language: {'Japanese' if is_japanese else 'English'}")
            matching_results = _filter_by_language(matching_results, is_japanese)
            
            # Step 6: Return cheapest from matching results
            cheapest = min(matching_results, key=lambda x: x['price'])
            safe_print(f"[APPRAISE] PriceCharting: Selected '{cheapest['name']}' at ${cheapest['price']}")
            return cheapest['price']
                
                
    except httpx.TimeoutException:
        safe_print(f"[APPRAISE] PriceCharting: Timeout (skipping)")
        return None
    except Exception as e:
        safe_print(f"[APPRAISE] PriceCharting error: {e}")
        return None


def _try_ebay_scrape(card_name: str, set_name: str, card_number: str = "", is_japanese: bool = False) -> Optional[float]:
    """Try to scrape average sold price from eBay."""
    try:
        import httpx
        from bs4 import BeautifulSoup
        import re
        
        search_name = card_name.split('(')[0].strip()
        
        # Build SPECIFIC search query - must include card number
        query_parts = [search_name]
        
        if set_name and set_name != "Unknown":
            query_parts.append(set_name)
        
        # Require card number to make search specific
        if not card_number:
            safe_print(f"[APPRAISE] eBay: Skipping - no card number")
            return None
        
        query_parts.append(card_number)
        
        query_parts.append("pokemon card")
        
        # Use proper URL encoding
        from urllib.parse import quote_plus
        search_query = " ".join(query_parts)
        encoded_query = quote_plus(search_query)
        
        # Search for sold listings
        url = f"https://www.ebay.com/sch/i.html?_nkw={encoded_query}&LH_Sold=1&LH_Complete=1"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find sold prices
            prices = []
            price_elements = soup.find_all('span', class_='s-item__price')
            
            for elem in price_elements[:10]:  # Take first 10 results
                price_text = elem.get_text(strip=True)
                match = re.search(r'\$?([\d,]+\.?\d*)', price_text)
                if match:
                    price = float(match.group(1).replace(',', ''))
                    if price > 0 and price < 10000:  # Sanity check
                        prices.append(price)
            
            if prices:
                avg_price = sum(prices) / len(prices)
                safe_print(f"[APPRAISE] eBay (with number, avg of {len(prices)} sold): ${avg_price:.2f} for '{search_name}'")
                return round(avg_price, 2)
            
            return None
                
    except httpx.TimeoutException:
        safe_print(f"[APPRAISE] eBay: Timeout (skipping)")
        return None
    except Exception as e:
        safe_print(f"[APPRAISE] eBay error: {e}")
        return None



def _mock_estimate(
    card_name: str,
    rarity: str,
    set_name: str = "Unknown",
    variants: Optional[list] = None
) -> float:
    """
    Mock market value estimation as fallback.
    
    Args:
        card_name: Name of the card
        rarity: Rarity level
        set_name: Card set name
        variants: List of variants
    
    Returns:
        float: Estimated market value in USD
    """
    # Base values by rarity (mock data)
    base_values = {
        'Common': 0.50,
        'Uncommon': 1.50,
        'Rare': 5.00,
        'Epic': 15.00,
        'Ultra Rare': 50.00,
        'Holo Rare': 20.00,
        'Secret Rare': 100.00
    }
    
    base_value = base_values.get(rarity, 1.00)
    
    # Apply variant multipliers
    if variants:
        for variant in variants:
            if '1st Edition' in variant or 'First Edition' in variant:
                base_value *= 2.5
            if 'Holographic' in variant or 'Holo' in variant:
                base_value *= 1.8
            if 'Reverse Holo' in variant:
                base_value *= 1.3
            if 'Shadowless' in variant:
                base_value *= 3.0
    
    # Apply set multipliers (mock - popular sets are worth more)
    popular_sets = ['Base Set', 'Jungle', 'Fossil', 'Team Rocket', 'Neo Genesis']
    if any(s in set_name for s in popular_sets):
        base_value *= 1.5
    
    # Apply name-based multipliers (mock - popular cards)
    popular_names = ['Charizard', 'Pikachu', 'Mewtwo', 'Lugia', 'Rayquaza']
    if any(name in card_name for name in popular_names):
        base_value *= 3.0
    
    return round(base_value, 2)


async def compare_price_to_market(
    actual_price_jpy: float,
    market_value_jpy: float
) -> Dict:
    """
    Compare actual price to market value and provide insights.
    
    Args:
        actual_price_jpy: Your current selling price in JPY
        market_value_jpy: Estimated market value in JPY
    
    Returns:
        dict: Price comparison with percentage difference and recommendation
    """
    if market_value_jpy == 0:
        return {
            'difference_jpy': 0,
            'difference_pct': 0,
            'status': 'unknown',
            'recommendation': 'Unable to compare'
        }
    
    diff_jpy = actual_price_jpy - market_value_jpy
    diff_pct = (diff_jpy / market_value_jpy) * 100
    
    # Determine status
    if diff_pct < -15:
        status = 'underpriced'
        recommendation = 'Consider raising price'
    elif diff_pct > 15:
        status = 'overpriced'
        recommendation = 'Consider lowering price'
    else:
        status = 'fair'
        recommendation = 'Price is competitive'
    
    return {
        'difference_jpy': int(diff_jpy),
        'difference_pct': round(diff_pct, 1),
        'status': status,
        'recommendation': recommendation
    }
