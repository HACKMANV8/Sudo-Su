from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


class Crawl4AIError(Exception):
    pass


class OfflineError(Crawl4AIError):
    pass


_PROFILE_SKIP_PATTERNS = (
    "linkedin.com/in/",
    "facebook.com/",
    "instagram.com/",
)


def _redact_pii(text: str) -> str:
    text = re.sub(r"[\w\.-]+@[\w\.-]+", "[REDACTED_EMAIL]", text)
    text = re.sub(r"\b\+?\d[\d\s\-]{7,}\b", "[REDACTED_PHONE]", text)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", text)
    return text


def _query_hash(query: str, options: Dict[str, Any]) -> str:
    payload = json.dumps({"q": query, "opts": options}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class Crawl4AIClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        cache_dir: str = "/tmp/openschema_crawl_cache",
        rate_limit_per_sec: float = 1.0,
        llm_client: Optional[Any] = None,
    ) -> None:
        self.api_key = api_key
        self.endpoint = endpoint or os.environ.get("CRAWL4AI_ENDPOINT", "https://api.crawl4ai.dev")
        self.cache_dir = cache_dir
        self.rate_limit_per_sec = rate_limit_per_sec
        self.llm_client = llm_client
        os.makedirs(self.cache_dir, exist_ok=True)

    def _cache_path(self, key: str) -> str:
        return os.path.join(self.cache_dir, f"{key}.json")

    def search_and_scrape(
        self,
        query: str,
        max_pages: int = 10,
        recency_days: Optional[int] = 365,
        cache_ttl_sec: int = 7 * 24 * 3600,
        bypass_cache: bool = False,
        allow_profiles: bool = False,
        mode: str = "scrape",
        seed: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        opts = {
            "max_pages": max_pages,
            "recency_days": recency_days,
            "allow_profiles": allow_profiles,
            "mode": mode,
        }
        key = _query_hash(query, opts)
        cache_path = self._cache_path(key)
        now = time.time()
        if not bypass_cache and os.path.exists(cache_path):
            if now - os.path.getmtime(cache_path) <= cache_ttl_sec:
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        cached = json.load(f)
                    log.info("Crawl4AI cache hit for %s", query)
                    return cached.get("pages", [])
                except Exception:
                    pass

        # cache-only mode: do not attempt network/llm
        if mode == "cache":
            return []

        rng = None
        if seed is not None:
            try:
                rng = __import__("numpy").random.default_rng(seed)  # type: ignore
            except Exception:
                rng = None

        pages: List[Dict[str, Any]] = []
        if mode == "llm":
            if not self.llm_client:
                # Simple deterministic stub
                words = ["electronics", "fashion", "grocery", "salary", "price", "discount"]
                sel = words[(seed or 0) % len(words)]
                txt = f"Query: {query}. Examples: {sel} 100 200 300 400. Category {sel}."
                pages = [{"url": "mock://llm", "title": f"LLM for {query}", "text": txt}]
            else:
                try:
                    prompt = f"Extract concise examples and numeric hints for: {query}."
                    resp = self.llm_client(prompt, temperature=0)
                    pages = [{"url": "mock://llm", "title": f"LLM for {query}", "text": str(resp)}]
                except Exception as e:
                    raise OfflineError(str(e))
        elif mode == "scrape":
            if not self.api_key:
                log.warning("Crawl4AI offline: missing API key")
                raise OfflineError("Crawl4AI API key missing")
            try:
                import requests  # type: ignore
                from bs4 import BeautifulSoup  # type: ignore
            except Exception as e:
                log.warning("Crawl4AI offline: scrape deps missing: %s", e)
                raise OfflineError("scrape deps missing")
            # Rate limit
            time.sleep(1.0 / max(self.rate_limit_per_sec, 1e-9))
            # Naive scrape: attempt query as URL if looks like URL else skip
            urls: List[str] = []
            if query.startswith("http://") or query.startswith("https://"):
                urls = [query]
            # Fetch limited pages
            for u in urls[:max_pages]:
                try:
                    if not allow_profiles and any(s in u for s in _PROFILE_SKIP_PATTERNS):
                        continue
                    r = requests.get(u, timeout=3)
                    if r.status_code != 200:
                        continue
                    soup = BeautifulSoup(r.text, "html.parser")
                    text = "\n".join(t.get_text(" ", strip=True) for t in soup.find_all(["p", "li", "span"]))
                    pages.append({"url": u, "title": soup.title.string if soup.title else "", "text": text})
                except Exception:
                    continue
        elif mode == "upload":
            # Upload mode expects content already cached externally; nothing to do here
            pages = []

        # Filter and redact
        filtered: List[Dict[str, Any]] = []
        for p in pages:
            url = p.get("url", "")
            if not allow_profiles and any(s in url for s in _PROFILE_SKIP_PATTERNS):
                continue
            txt = _redact_pii((p.get("text") or "")[:10000])
            filtered.append({"url": url, "title": p.get("title", ""), "text": txt})

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump({"pages": filtered}, f)
        except Exception:
            pass

        return filtered

    def extract_field_examples(self, pages: List[Dict[str, Any]], field_hint: str, max_examples: int = 50) -> List[str]:
        examples: List[str] = []
        hint = field_hint.lower()
        for p in pages:
            txt = p.get("text", "")
            lines = [l.strip() for l in txt.splitlines() if l.strip()]
            for line in lines:
                if hint in line.lower() or len(line.split()) <= 12:
                    s = _redact_pii(line)
                    if s not in examples:
                        examples.append(s)
                if len(examples) >= max_examples:
                    break
            if len(examples) >= max_examples:
                break
        return examples[:max_examples]

    def infer_numeric_distribution(self, pages: List[Dict[str, Any]], field_hint: str, min_samples: int = 5) -> Optional[Dict[str, Any]]:
        nums: List[float] = []
        pattern = re.compile(r"\$?\b(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\b")
        for p in pages:
            txt = p.get("text", "")
            # Loosen matching: always scan numbers when hint is numeric-like
            if field_hint.lower() in txt.lower() or True:
                for m in pattern.findall(txt):
                    try:
                        val = float(str(m).replace(",", ""))
                        # Filter unrealistic values if hint contains salary
                        if "salary" in field_hint.lower() and not (1000 <= val <= 1e7):
                            continue
                        nums.append(val)
                    except Exception:
                        pass
        if len(nums) < min_samples:
            return None
        arr = nums[:min(1000, len(nums))]
        return {
            "mean": float(sum(arr) / len(arr)),
            "std": float((sum((x - (sum(arr) / len(arr))) ** 2 for x in arr) / max(1, len(arr) - 1)) ** 0.5),
            "min": float(min(arr)),
            "max": float(max(arr)),
            "samples": int(len(arr)),
        }

    def infer_category_frequencies(
        self, pages: List[Dict[str, Any]], field_hint: str, categories: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        tokens: List[str] = []
        for p in pages:
            txt = p.get("text", "")
            if field_hint.lower() in txt.lower():
                for tok in re.findall(r"[A-Za-z][A-Za-z\-]{1,20}", txt):
                    tokens.append(tok.lower())
        if categories:
            counts = {c: 0 for c in categories}
            for t in tokens:
                for c in categories:
                    if c.lower() in t:
                        counts[c] += 1
            total = sum(counts.values())
            if total == 0:
                return None
            probs = [counts[c] / total for c in categories]
            return {"categories": categories, "probs": probs, "samples": total}
        return None


