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
    # Split by common delimiters: underscore, hyphen, space
    segments = re.split(r"[_\-\s]+", stem)
    segments = [s for s in segments if s]  # Remove empties

    if not segments:
        return {"batch_id": "", "intake_date": "", "sequence_index": "", "rarity": None}

    batch_id = ""
    intake_date = ""
    sequence_index = ""
    rarity = None

    # 1. Try to detect a date (YYYY-MM-DD) in the original stem
    date_match = _DATE_RE.search(stem)
    if date_match:
        y, m, d = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))
        if 1990 <= y <= 2099 and 1 <= m <= 12 and 1 <= d <= 31:
            intake_date = f"{y:04d}-{m:02d}-{d:02d}"

    # 2. Check segments for compact date (YYYYMMDD) if no date found yet
    if not intake_date:
        for seg in segments:
            cm = _COMPACT_DATE_RE.match(seg)
            if cm:
                y, m, d = int(cm.group(1)), int(cm.group(2)), int(cm.group(3))
                if 1990 <= y <= 2099 and 1 <= m <= 12 and 1 <= d <= 31:
                    intake_date = f"{y:04d}-{m:02d}-{d:02d}"
                    break

    # 3. Sequence index: if the LAST segment is purely numeric, treat as sequence
    if segments and segments[-1].isdigit():
        sequence_index = segments[-1]
        segments = segments[:-1]  # Remove it from consideration

    # 4. Rarity: check if last remaining segment is a known rarity abbreviation
    if segments:
        last_lower = segments[-1].lower()
        if last_lower in _RARITY_MAP:
            rarity = _RARITY_MAP[last_lower]
            segments = segments[:-1]

    # 5. Batch ID: use the first segment as the batch identifier
    if segments:
        batch_id = segments[0]

    return {
        "batch_id": batch_id,
        "intake_date": intake_date,
        "sequence_index": sequence_index,
        "rarity": rarity,
    }
