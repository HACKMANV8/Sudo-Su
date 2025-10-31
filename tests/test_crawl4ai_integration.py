from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from openschema.pipeline import run_pipeline_from_schema
from openschema.connectors import crawl4ai_adapter as c4a


def test_crawl4ai_merge_priors(monkeypatch, tmp_path):
    # Mock pages
    pages = [{
        "url": "mock://page",
        "title": "Salary and Departments",
        "text": "salary 1000 2000 3000 4000 5000 department sales sales hr eng sales",
    }]

    def mock_search(self, query, **kwargs):
        return pages

    monkeypatch.setattr(c4a.Crawl4AIClient, "search_and_scrape", mock_search)

    schema = {
        "name": "test",
        "fields": [
            {"name": "salary", "type": "float", "min": 0.0, "max": 1e9},
            {"name": "dept", "type": "category", "categories": ["sales", "hr", "eng"], "probs": [0.34, 0.33, 0.33]},
        ],
        "n_rows": 100,
    }
    res = run_pipeline_from_schema(schema, use_crawl4ai=True, crawl_mode="llm", crawl_timeout=5)
    assert res["ok"]
    gen = res["schema"]
    fields = {f["name"]: f for f in gen["fields"]}
    # Numeric priors merged
    assert "mean" in fields["salary"] and fields["salary"]["mean"] > 0
    # Category probs merged (samples >=5)
    assert fields["dept"].get("probs") is not None
    # Metadata contains crawl report
    meta = res["generation_report"].get("crawl4ai", {})
    assert meta.get("used") is True
    assert meta.get("cache_key") is not None


def test_crawl4ai_cache_key_stable(monkeypatch, tmp_path):
    # Same mock ensures deterministic key
    pages = [{"url": "mock://p", "title": "T", "text": "price 10 20 30 40 50 category electronics electronics"}]

    def mock_search(self, query, **kwargs):
        return pages

    monkeypatch.setattr(c4a.Crawl4AIClient, "search_and_scrape", mock_search)
    schema = {"name": "t", "fields": [{"name": "price", "type": "float"}], "n_rows": 10}
    r1 = run_pipeline_from_schema(schema, use_crawl4ai=True, crawl_mode="cache")
    r2 = run_pipeline_from_schema(schema, use_crawl4ai=True, crawl_mode="cache")
    k1 = r1["generation_report"].get("crawl4ai", {}).get("cache_key")
    k2 = r2["generation_report"].get("crawl4ai", {}).get("cache_key")
    assert k1 == k2 and k1 is not None


