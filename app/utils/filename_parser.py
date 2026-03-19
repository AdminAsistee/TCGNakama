"""
Filename Parser Utility
Parses structured batch filenames to extract Batch ID, Intake Date, and Rarity.

Expected filename structure:
    BATCH-1-2025-02-13-OP-SR 1.jpg
    └─────┘ └──────────┘    └┘
    Batch ID  Intake Date   Rarity abbreviation (last segment before trailing space+number)

If the filename does not match this structure, returns empty strings for batch_id
and intake_date, and None for rarity (caller should use appraise_card_from_image()
rarity as fallback — no additional Gemini call is made per RULE-015).
"""

import re
from pathlib import Path

# Canonical rarity map: filename abbreviation → internal value.
# Mirrors the rarity_mapping in app/services/appraisal.py (RULE-016).
_RARITY_MAP: dict[str, str] = {
    # One Piece / generic abbreviations
    "c":            "Common",
    "uc":           "Uncommon",
    "u":            "Uncommon",
    "r":            "Rare",
    "sr":           "Ultra Rare",
    "sar":          "Ultra Rare",
    "ssr":          "Ultra Rare",
    "sec":          "Ultra Rare",
    "ur":           "Ultra Rare",
    "l":            "Ultra Rare",    # Leader
    "hr":           "Ultra Rare",    # Hyper Rare
    "ar":           "Ultra Rare",    # Alt Rare
    "rr":           "Ultra Rare",    # Double Rare
    "pr":           "Rare",          # Promo
    # Pokémon text rarities
    "common":       "Common",
    "uncommon":     "Uncommon",
    "rare":         "Rare",
    "holo rare":    "Rare",
    "reverse holo": "Rare",
    "ultra rare":   "Ultra Rare",
    "secret rare":  "Ultra Rare",
    "rainbow rare": "Ultra Rare",
    "hyper rare":   "Ultra Rare",
    "mythic rare":  "Ultra Rare",
    "prism":        "Ultra Rare",
    "crystal":      "Ultra Rare",
    "shining":      "Ultra Rare",
    "gold star":    "Ultra Rare",
    # Yu-Gi-Oh!
    "super rare":   "Epic",
    "starlight rare": "Ultra Rare",
    # Star symbols
    "★":            "Rare",
    "★★":           "Ultra Rare",
    "★★★":          "Ultra Rare",
    # Generic
    "epic":         "Epic",
}

# Pattern: BATCH-<N>-<YYYY-MM-DD>-<rest>
# The <rest> part ends with an optional space+number (the card copy index).
# Rarity abbreviation is the LAST hyphen-separated token in <rest>, before the trailing space+number.
_BATCH_RE = re.compile(
    r"^(BATCH-\d+)"          # group 1: batch id  e.g. BATCH-1
    r"-(\d{4}-\d{2}-\d{2})"  # group 2: date      e.g. 2025-02-13
    r"-(.+)$",               # group 3: remainder  e.g. OP-SR 1
    re.IGNORECASE,
)


def parse_batch_filename(filename: str) -> dict:
    """
    Parse a structured batch filename and return batch metadata.

    Args:
        filename: The original upload filename (with or without extension).

    Returns:
        dict with keys:
            batch_id    (str)  – e.g. "BATCH-1", or ""
            intake_date (str)  – e.g. "2025-02-13", or ""
            rarity      (str|None) – canonical rarity value, or None if
                                     unstructured / unknown abbreviation
    """
    # Strip extension so it doesn't interfere with the regex
    stem = Path(filename).stem

    match = _BATCH_RE.match(stem)
    if not match:
        return {"batch_id": "", "intake_date": "", "sequence_index": "", "rarity": None}

    batch_id = match.group(1).upper()       # e.g. "BATCH-1"
    intake_date = match.group(2)             # e.g. "2025-02-13"
    remainder = match.group(3)               # e.g. "OP-SR 1"

    # Capture trailing copy-index (sequence number) before stripping it
    seq_match = re.search(r"\s+(\d+)$", remainder)
    sequence_index = seq_match.group(1) if seq_match else ""

    # Strip trailing space+number to isolate the rarity token
    remainder = re.sub(r"\s+\d+$", "", remainder).strip()

    # Rarity abbreviation is the last hyphen-separated token
    tokens = remainder.split("-")
    rarity_abbr = tokens[-1].strip() if tokens else ""

    # Look up canonical value
    rarity = _RARITY_MAP.get(rarity_abbr.lower())

    return {
        "batch_id": batch_id,
        "intake_date": intake_date,
        "sequence_index": sequence_index,
        "rarity": rarity,  # None means → use appraise_card_from_image() result
    }
