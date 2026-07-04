import uuid
from sqlalchemy import String, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date
from app.db.base import Base

class Company(Base):
    __tablename__ = "companies"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    cin: Mapped[str] = mapped_column(String(21), unique=True, index=True, nullable=True)
    gstin: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=True)
    registration_status: Mapped[str] = mapped_column(String(50), nullable=True)
    incorporation_date: Mapped[date] = mapped_column(Date, nullable=True)
    registered_address: Mapped[str] = mapped_column(String(1000), nullable=True)
    directors: Mapped[str] = mapped_column(String(2000), nullable=True)  # Stored as a JSON or comma-separated string
    last_filing_date: Mapped[date] = mapped_column(Date, nullable=True)
    
    # Combined Phase 2 Cache Indicators
    domain: Mapped[str] = mapped_column(String(255), nullable=True)
    domain_created_at: Mapped[date] = mapped_column(Date, nullable=True)
    glassdoor_rating: Mapped[float] = mapped_column(nullable=True)
    glassdoor_review_count: Mapped[int] = mapped_column(nullable=True)
    trustpilot_rating: Mapped[float] = mapped_column(nullable=True)
    google_search_footprint: Mapped[str] = mapped_column(String(50), nullable=True)
    
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
