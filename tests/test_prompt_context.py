"""Verify prompt_context module returns correct grounding context for every role."""
from app.prompt_context import get_context


def test_all_roles_return_content():
    """Every defined role must return non-trivial context containing the domain identifier."""
    for role in ["appraisal", "set_resolver", "blog", "price_filter", "price_tracker", "showcase", "ui"]:
        ctx = get_context(role)
        assert isinstance(ctx, str), f"Context for '{role}' is not a string"
        assert len(ctx) > 50, f"Context for '{role}' is too short ({len(ctx)} chars)"
        assert "TCGNakama" in ctx, f"Context for '{role}' missing domain identifier"


def test_unknown_role_returns_domain_context():
    """Unknown roles should still get the shared domain context (graceful fallback)."""
    ctx = get_context("unknown_role")
    assert "TCGNakama" in ctx
    assert "JPY" in ctx


def test_appraisal_includes_rarity_mapping():
    """Appraisal context must include the rarity tier mapping."""
    ctx = get_context("appraisal")
    assert "Ultra Rare" in ctx
    assert "Common" in ctx
    assert "SR" in ctx


def test_blog_includes_design_context():
    """Blog context must include design tokens for brand tone consistency."""
    ctx = get_context("blog")
    assert "#FFD700" in ctx or "gold" in ctx.lower()
    assert "Vault" in ctx or "vault" in ctx


def test_price_includes_variant_guidance():
    """Price context must include PriceCharting variant awareness."""
    ctx = get_context("price_filter")
    assert "regular" in ctx.lower() or "Regular" in ctx


def test_ui_role_includes_design_context():
    """UI role must have both domain and design context."""
    ctx = get_context("ui")
    assert "TCGNakama" in ctx
    assert "#0B1120" in ctx or "Background" in ctx
