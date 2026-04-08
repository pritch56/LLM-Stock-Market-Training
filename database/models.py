from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, Text, DateTime, ForeignKey, CheckConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True)
    published_time = Column(DateTime(timezone=True))
    article_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    impacts = relationship("CompanyImpact", back_populates="article")


class CompanyImpact(Base):
    __tablename__ = "company_impacts"

    id = Column(Integer, primary_key=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    company_name = Column(Text, nullable=False)
    ticker = Column(Text)
    impact_rating = Column(Integer, nullable=False)
    reasoning = Column(Text)

    __table_args__ = (
        CheckConstraint("impact_rating >= 1 AND impact_rating <= 10", name="ck_impact_rating_range"),
    )

    article = relationship("Article", back_populates="impacts")
