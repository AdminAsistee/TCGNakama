"""Shared pytest fixtures for TCGNakama tests."""
import pytest


@pytest.fixture
def sample_card():
    """Standard card dict matching Shopify product shape."""
    return {
        "id": "gid://shopify/Product/12345",
        "safe_id": "12345",
        "title": "リザードン (Charizard) - SV5M #001/024",
        "set": "SV5M",
        "set_name": "Cyber Judge",
        "rarity": "Ultra Rare",
        "price": 38000.0,
        "card_condition": "Near Mint",
        "package_type": "Raw",
        "totalInventory": 1,
        "variant_id": "gid://shopify/ProductVariant/99999",
    }


@pytest.fixture
def sample_pricecharting_results():
    """Sample PriceCharting API results with ambiguous variants."""
    return [
        {"product-name": "Charizard #001", "loose-price": "45.00"},
        {"product-name": "Charizard [Alt Art] #001", "loose-price": "120.00"},
        {"product-name": "Charizard [Promo] P-001", "loose-price": "25.00"},
    ]
