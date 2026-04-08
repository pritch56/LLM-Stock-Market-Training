import logging
from datetime import datetime
from typing import Optional

from database.db import get_session
from database.models import Article, CompanyImpact

logger = logging.getLogger(__name__)


def insert_article(article_text: str, published_time: Optional[datetime] = None) -> int:
    with get_session() as session:
        article = Article(
            article_text=article_text,
            published_time=published_time,
        )
        session.add(article)
        session.flush()
        return article.id


def insert_company_impacts(article_id: int, companies: list[dict]) -> int:
    inserted = 0
    with get_session() as session:
        for company in companies:
            impact = CompanyImpact(
                article_id=article_id,
                company_name=company["company_name"],
                ticker=company.get("ticker"),
                impact_rating=company["impact_rating"],
                reasoning=company.get("reasoning"),
            )
            session.add(impact)
            inserted += 1
    logger.info("Inserted %d company impacts for article %d", inserted, article_id)
    return inserted
