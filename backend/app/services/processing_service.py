import re
import unicodedata
from typing import Any

from app.core.supabase import get_supabase_client


class ProcessingService:
    def __init__(self) -> None:
        self.db = get_supabase_client()

    def clean(self, text: str) -> str:
        text = unicodedata.normalize("NFKC", text or "")
        text = re.sub(r"(?is)<(script|style|nav|footer|aside|form).*?</\1>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def process(self, result: dict[str, Any]) -> dict[str, Any]:
        cleaned = self.clean(str(result.get("content") or ""))
        article_id = result.get("article_id") or result.get("id")
        if not article_id:
            raise ValueError("Processed article is missing article_id")
        row = {"article_id": str(article_id), "cleaned_text": cleaned,
               "original_text": result.get("content"), "ai_ready_content": cleaned,
               "language": "en", "word_count": len(cleaned.split()), "status_id": None,
               "metadata": {"source_id": result.get("source_id"), "domain_id": result.get("domain_id"),
                            "subdomain_ids": result.get("subdomain_ids", []), "title": result.get("title"),
                            "author": result.get("author"), "publish_date": result.get("published_at"),
                            "last_updated_date": (result.get("crawl_metadata") or {}).get("last_updated_date") or result.get("last_updated_at"), "source_url": result.get("url"),
                            "kpi": result.get("kpi", {}), "matching": result.get("matching", {})}}
        saved = self.db.table("processed_content").upsert(row, on_conflict="article_id").execute().data or []
        self.db.table("crawled_articles").update({"is_processed": True}).eq("id", str(article_id)).execute()
        return saved[0] if saved else row
