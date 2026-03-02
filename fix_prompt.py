path = r'app\services\appraisal.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

lf = '\n'

# Fix 1: vintage set detection (5-space indent)
old1 = (f'     * CRITICAL: If you see a rainbow/prismatic holographic effect on the card, use "Prism" as the set name{lf}'
        f'     * Otherwise return "" if no set code found')
new1 = (f'     * Look for a set symbol/icon near the card number to identify the set{lf}'
        f'     * Japanese Base Set: gold border, card number in "No.XXX" format, no set symbol -> set_name = "Base Set"{lf}'
        f'     * Japanese Jungle: set symbol is a leaf -> set_name = "Jungle"{lf}'
        f'     * Japanese Fossil: set symbol is a fossil -> set_name = "Fossil"{lf}'
        f'     * If no set code or symbol found, return "" -- do NOT guess "Prism" just because the art is holographic')

# Fix 2: Prism Cards section (5-space indent)
old2 = (f'   - **Prism Cards** - Look for MULTIPLE indicators:{lf}'
        f'     * VISUAL: Rainbow/prismatic holographic pattern across the ENTIRE card surface{lf}'
        f'     * The card background, borders, and text areas shimmer with rainbow colors{lf}'
        f'     * NOT just the artwork - the WHOLE card has a rainbow sheen{lf}'
        f'     * Common Prism cards: Gengar, Tyranitar, Celebi, Entei, Raikou, Suicune{lf}'
        f"     * If the card is Gengar and looks vintage (pre-2003), it's VERY LIKELY Prism{lf}"
        f'     * If you see ANY rainbow holographic effect, return "Prism"')
new2 = (f'   - **Holo Rare** (NOT a special variant -- this is just the standard holo rarity):{lf}'
        f'     * Sparkly/foil artwork ONLY inside the art box{lf}'
        f'     * Card borders, text boxes, and background are NORMAL (not rainbow){lf}'
        f'     * Very common in Base Set, Jungle, Fossil, and many other sets{lf}'
        f'     * Do NOT call this "Prism" -- it is just a Holo Rare card{lf}'
        f'   - **Prism Star** (Sun & Moon era, 2017-2019 ONLY):{lf}'
        f'     * Has "Prism Star" IN THE CARD NAME itself (e.g., "Gengar Prism Star"){lf}'
        f'     * Rainbow holographic effect across the ENTIRE card -- borders, text boxes, AND art{lf}'
        f'     * Only appears in Sun & Moon sets (SM era){lf}'
        f'     * If you do NOT see "Prism Star" in the name, it is NOT a Prism Star card')

# Fix 3: rarity rule
old3 = '   - IMPORTANT: If you detect Prism variant (see #7), the rarity is ALWAYS "Ultra Rare" or "★"'
new3 = '   - IMPORTANT: If you detect Prism Star variant (see #7), the rarity is ALWAYS "Ultra Rare"'

# Fix 4: IMPORTANT RULES section
old4 = ('- CRITICAL: For vintage Gengar cards, check VERY CAREFULLY for rainbow holographic effects (Prism)\n'
        '- If Prism variant detected, set rarity to "Ultra Rare" and set_name to "Prism"')
new4 = ('- CRITICAL: Do NOT confuse Holo Rare (sparkly art only) with Prism Star. A vintage Gengar with sparkly art is a Holo Rare from Base Set, NOT a Prism card.\n'
        '- If Prism Star variant detected ("Prism Star" in card name), set rarity to "Ultra Rare" and set_name to "Prism"\n'
        '- For Japanese Base Set cards (gold border, No.XXX number, no set symbol): set_name = "Base Set"')

applied = []
for i, (old, new) in enumerate([(old1, new1), (old2, new2), (old3, new3), (old4, new4)], 1):
    if old in content:
        content = content.replace(old, new)
        applied.append(f'Fix {i} applied')
    else:
        applied.append(f'Fix {i} NOT FOUND')

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

for msg in applied:
    print(msg)
print('Done')
