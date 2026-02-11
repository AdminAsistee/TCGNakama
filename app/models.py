"""
Database models for TCG Nakama.
"""
from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.database import Base


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
