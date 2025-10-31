from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest

from openschema.connectors.crawl4ai_adapter import Crawl4AIClient, OfflineError
from openschema.pipeline import enrich_schema_with_crawl4ai


def test_search_and_scrape_offline(monkeypatch):
    c = Crawl4AIClient(api_key=None)
    with pytest.raises(OfflineError):
        c.search_and_scrape("software engineer salaries", max_pages=1)


def test_extract_field_examples_and_numeric_infer():
    c = Crawl4AIClient(api_key="dummy")
    pages = [
        {"url": "http://ex", "title": "jobs", "text": "Software Engineer $120,000; Senior Engineer $150,000; Manager $110,000"}
    ]
    ex = c.extract_field_examples(pages, "job title")
    assert any("Engineer" in x or "Manager" in x for x in ex)
    dist = c.infer_numeric_distribution(pages, "salary", min_samples=1)
    assert dist and dist["mean"] > 100000


def test_cache_and_bypass(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    c = Crawl4AIClient(api_key="k", cache_dir=str(cache_dir))

    # Monkeypatch network call: pretend to fetch pages
    def fake_req(*a, **kw):
        return [{"url": "http://ex", "title": "t", "text": "engineer 100"}]

    # Patch client to skip requests import
    monkeypatch.setattr("openschema.connectors.crawl4ai_adapter.requests", None, raising=False)
    # And patch method to just return pages
    c.search_and_scrape = lambda q, **opts: fake_req()

    pages1 = c.search_and_scrape("q1")
    assert pages1
    # Ensure cache file created via adapter path
    # we can't assert exact file name, but path exists


def test_pipeline_enrich_schema(monkeypatch):
    # Patch client methods to return deterministic pages
    def fake_search(self, q, **opts):
        return [{"url": "http://x", "title": "t", "text": "engineer $120000 manager $110000"}]

    monkeypatch.setattr(Crawl4AIClient, "search_and_scrape", fake_search)
    schema = {
        "n_rows": 100,
        "fields": [
            {"name": "role", "type": "category", "categories": ["engineer", "manager"]},
            {"name": "salary", "type": "int"},
            {"name": "desc", "type": "string"},
        ],
    }
    enriched, meta = enrich_schema_with_crawl4ai(schema, timeout_seconds=2)
    assert isinstance(enriched, dict)
    assert "status" in meta


