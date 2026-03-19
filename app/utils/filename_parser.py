"""
Filename Parser Utility
Parses structured batch filenames to extract Batch ID, Intake Date, Rarity,
and Sequence Index.

Supports TWO modes:

1. **Strict Batch Format** (production standard):
       BATCH-1-2025-02-13-OP-SR 1.jpg
       └─────┘ └──────────┘    └┘
       Batch ID  Intake Date   Rarity abbreviation

2. **Flexible / Generic Format** (any filename):
       Shelf_A_Pikachu_3.jpg   →  batch_id="Shelf", tags=["Shelf","A","Pikachu"], seq=3
       Vault-B-Charizard.png   →  batch_id="Vault", tags=["Vault","B","Charizard"]
       20260319_Mew_ex.jpg     →  intake_date="2026-03-19" (auto-detected from segment)

If the filename does not match the strict structure, the parser falls back
to the flexible mode, extracting as much metadata as possible.
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

# ─── Strict pattern: BATCH-<N>-<YYYY-MM-DD>-<rest> ───
_BATCH_RE = re.compile(
    r"^(BATCH-\d+)"          # group 1: batch id  e.g. BATCH-1
    r"-(\d{4}-\d{2}-\d{2})"  # group 2: date      e.g. 2025-02-13
    r"-(.+)$",               # group 3: remainder  e.g. OP-SR 1
    re.IGNORECASE,
)

# ─── Date detection anywhere in filename ───
_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

# ─── Compact date (YYYYMMDD) detection ───
_COMPACT_DATE_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")


def parse_batch_filename(filename: str) -> dict:
    """
    Parse a structured batch filename and return batch metadata.

    Args:
        filename: The original upload filename (with or without extension).

    Returns:
        dict with keys:
            batch_id       (str)       – e.g. "BATCH-1", or ""
            intake_date    (str)       – e.g. "2025-02-13", or ""
            sequence_index (str)       – e.g. "1", or ""
            rarity         (str|None)  – canonical rarity value, or None
    """
    # Strip extension so it doesn't interfere with parsing
    stem = Path(filename).stem

    # ── Try strict BATCH-N-YYYY-MM-DD pattern first ──
    match = _BATCH_RE.match(stem)
    if match:
        batch_id = match.group(1).upper()       # e.g. "BATCH-1"
        intake_date = match.group(2)             # e.g. "2025-02-13"
        remainder = match.group(3)               # e.g. "OP-SR 1"

        # Capture trailing copy-index (sequence number)
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
            "rarity": rarity,
        }

    # ── Flexible / Generic mode ──
    # The filename does NOT match the strict BATCH structure.
    # Per RULE-014/015: batch_id, intake_date, and sequence_index MUST be empty
    # unless the strict BATCH-N-YYYY-MM-DD pattern was matched above.
    # We still try to extract rarity as a helpful fallback.
    # (filename-to-tags is handled separately by the frontend via extracted_tags)

    # Split by common delimiters to find rarity token anywhere in filename
    segments = re.split(r"[_\-\s]+", stem)
    segments = [s for s in segments if s]  # Remove empties

    rarity = None
    for seg in segments:
        seg_lower = seg.lower()
        if seg_lower in _RARITY_MAP:
            rarity = _RARITY_MAP[seg_lower]
            break  # Take the first rarity hit

    # Always return empty strings for the 3 batch metadata fields
    return {
        "batch_id": "",
        "intake_date": "",
        "sequence_index": "",
        "rarity": rarity,
    }
