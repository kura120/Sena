import pytest
import asyncio
from types import SimpleNamespace

import src.extensions.core.web_search as web_search


class DummyResponse:
    def __init__(self, text):
        self.text = text


class DummyClient:
    def __init__(self, text):
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, data=None):
        return DummyResponse(self._text)


@pytest.mark.asyncio
async def test_web_search_parsing(monkeypatch):
    html = '<html><body><a href="https://example.com">Example Domain</a></body></html>'

    def fake_client(*args, **kwargs):
        return DummyClient(html)

    monkeypatch.setattr(web_search, "httpx", SimpleNamespace(AsyncClient=fake_client))

    res = await web_search.execute({"query": "example", "limit": 5})
    assert res["results"]
    assert any(r["url"].startswith("https://") for r in res["results"]) 
