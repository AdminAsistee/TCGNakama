from typing import TypedDict, List, Optional
from enum import Enum

class CardCondition(str, Enum):
    MINT = "Mint"
    NEAR_MINT = "Near Mint"
    LIGHTLY_PLAYED = "Lightly Played"
    MODERATELY_PLAYED = "Moderately Played"
    HEAVILY_PLAYED = "Heavily Played"
    DAMAGED = "Damaged"

class TCGGame(str, Enum):
    POKEMON = "Pokémon"
    ONE_PIECE = "One Piece"
    MAGIC = "Magic: The Gathering"
    YU_GI_OH = "Yu-Gi-Oh!"

class CardMetadata(TypedDict):
    """Structured ontology for TCG Card data."""
    card_name: str
    card_number: str
    set_name: str
    full_set_name: str
    rarity: str
    condition: CardCondition
    game: TCGGame
    storage_location: str  # e.g., "Box A", "Vault 1"
    buy_price_jpy: float
    market_price_jpy: Optional[float]
    tags: List[str]

class ProductOntology:
    """
    Mapping system to bridge Shopify API data with internal business logic.
    Ensures consistent naming and data types across the platform.
    """
    
    @staticmethod
    def extract_location_from_filename(filename: str) -> str:
        """
        Standardized logic for extracting storage location.
        Assumption: Location is usually the first part before a dash or underscore.
        Example: 'BoxA-001-Pikachu.jpg' -> 'BoxA'
        """
        import re
        # Look for patterns like 'Box123', 'VaultA', 'Binder_1'
        match = re.match(r'^([a-zA-Z0-9]+)[\-_]', filename)
        if match:
            return match.group(1)
        return "Unknown"

    @staticmethod
    def format_shopify_tags(metadata: CardMetadata) -> List[str]:
        """Convert ontological metadata into Shopify-compatible tags."""
        tags = [
            f"Set: {metadata['set_name']}",
            f"Number: {metadata['card_number']}",
            f"Rarity: {metadata['rarity']}",
            f"Card: {metadata['condition']}",
            f"Location: {metadata['storage_location']}",
        ]
        return tags + metadata.get('tags', [])
