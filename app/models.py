"""
Database models for TCG Nakama.
"""
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, DateTime, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum
from app.database import Base


class BlogCategory(str, enum.Enum):
    pokemon    = "pokemon"
    onepiece   = "onepiece"
    mtg        = "mtg"
    anime      = "anime"
    news       = "news"
    tips       = "tips"


class Banner(Base):
    """Homepage carousel banner model."""
    __tablename__ = "banners"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(100))
    subtitle: Mapped[str] = mapped_column(String(200))
    cta_label: Mapped[str] = mapped_column(String(50))
    cta_link: Mapped[str] = mapped_column(String(200))
    image_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gradient: Mapped[str] = mapped_column(String(100))
    display_order: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert banner to dictionary for template rendering."""
        # Handle image path - if it's a local file, prefix with /static/
        image_url = None
        if self.image_path:
            if self.image_path.startswith(('http://', 'https://')):
                # External URL, use as-is
                image_url = self.image_path
            elif self.image_path.startswith('/static/'):
                # Already has /static/ prefix, use as-is
                image_url = self.image_path
            else:
                # Local file without /static/, add prefix
                image_url = f"/static/{self.image_path.lstrip('/')}"
        
        return {
            "id": self.id,
            "title": self.title,
            "subtitle": self.subtitle,
            "cta_label": self.cta_label,
            "cta_link": self.cta_link,
            "image": image_url,
            "gradient": self.gradient,
            "display_order": self.display_order,
            "is_active": self.is_active,
        }


class PriceSnapshot(Base):
    """Historical price data from PriceCharting for gainers/trending."""
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[str] = mapped_column(String(100), index=True)
    product_title: Mapped[str] = mapped_column(String(300))
    market_usd: Mapped[float] = mapped_column(Float)
    market_jpy: Mapped[int] = mapped_column(Integer)
    exchange_rate: Mapped[float] = mapped_column(Float)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SystemSetting(Base):
    """Key-value store for admin-configurable settings."""
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))


class PageSpeedAudit(Base):
    """PageSpeed Insights audit results."""
    __tablename__ = "pagespeed_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(500))
    strategy: Mapped[str] = mapped_column(String(10))  # "mobile" or "desktop"
    performance_score: Mapped[int] = mapped_column(Integer)
    accessibility_score: Mapped[int] = mapped_column(Integer)
    best_practices_score: Mapped[int] = mapped_column(Integer)
    seo_score: Mapped[int] = mapped_column(Integer)
    opportunities_json: Mapped[str] = mapped_column(Text, default="{}")
    full_response_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class BlogPost(Base):
    """AI-generated blog posts for SEO and community engagement."""
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    meta_description: Mapped[str] = mapped_column(String(500))
    content_html: Mapped[str] = mapped_column(Text)          # Rendered HTML
    content_markdown: Mapped[str] = mapped_column(Text)      # Raw Markdown source
    category: Mapped[str] = mapped_column(String(50), index=True, default="news")
    tags: Mapped[str] = mapped_column(String(500), default="")  # comma-separated
    og_image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    facebook_post_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def excerpt(self) -> str:
        """First 200 characters of plain text for blog list cards."""
        import re
        plain = re.sub(r'<[^>]+>', '', self.content_html or '')
        return plain[:200].strip() + ('...' if len(plain) > 200 else '')

    @property
    def tags_list(self) -> list:
        return [t.strip() for t in (self.tags or '').split(',') if t.strip()]


# ── Seller Onboarding Models ────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    admin  = "admin"
    seller = "seller"


class SellerStatus(str, enum.Enum):
    pending   = "pending"
    approved  = "approved"
    rejected  = "rejected"
    suspended = "suspended"


class User(Base):
    """Platform user — admin or seller."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    password_salt: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(20), default="seller")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    seller_profile: Mapped["SellerProfile | None"] = relationship(
        "SellerProfile", back_populates="user", uselist=False
    )


class SellerProfile(Base):
    """Seller store profile — linked 1:1 to User."""
    __tablename__ = "seller_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, index=True)
    store_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="seller_profile")


class SupportTicket(Base):
    """Seller support / contact form submissions."""
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    seller_email: Mapped[str] = mapped_column(String(255), index=True)
    seller_name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)  # open, replied, closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

