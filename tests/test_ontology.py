"""Validate ontology module enums and helpers haven't drifted from the documented ontology."""
from app.ontology import CardCondition, TCGGame, ProductOntology


def test_card_conditions_exist():
    """All documented conditions must exist as enum values."""
    assert hasattr(CardCondition, "NEAR_MINT")
    assert hasattr(CardCondition, "DAMAGED")
    assert hasattr(CardCondition, "LIGHTLY_PLAYED")


def test_tcg_games_exist():
    """All documented TCG games must exist as enum values."""
    assert hasattr(TCGGame, "POKEMON")
    assert hasattr(TCGGame, "ONE_PIECE")
    assert hasattr(TCGGame, "MAGIC")
    assert hasattr(TCGGame, "YU_GI_OH")


def test_product_ontology_has_location_extractor():
    """ProductOntology must have the static method for extracting storage location."""
    assert hasattr(ProductOntology, "extract_location_from_filename")


def test_product_ontology_has_tag_formatter():
    """ProductOntology must have the static method for Shopify tag formatting."""
    assert hasattr(ProductOntology, "format_shopify_tags")
