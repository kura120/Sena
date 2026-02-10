"""Core extension: web_search

Simple web search using DuckDuckGo HTML endpoint and lightweight parsing.
Note: This is a pragmatic V1 implementation that does not require API keys.
"""

from __future__ import annotations

from typing import Any, Dict, List
import re

import httpx

EXTENSION_METADATA = {
    "name": "web_search",
    "description": "Perform a simple web search and return titles and URLs.",
    "version": "1.0.0",
    "core": True,
}


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    query = params.get("query")
    if not query:
        return {"error": "query parameter is required"}

    limit = int(params.get("limit", 10))
    url = "https://html.duckduckgo.com/html/"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(url, data={"q": query})
            html = resp.text
        except Exception as e:
            return {"error": f"search request failed: {e}"}

    # Very small parser: find <a href="...">text</a>
    pattern = re.compile(r"<a[^>]+href=\"(?P<href>https?://[^\" ]+)\"[^>]*>(?P<title>.*?)</a>", re.IGNORECASE | re.DOTALL)
    matches = pattern.finditer(html)

    results: List[Dict[str, Any]] = []
    for m in matches:
        if len(results) >= limit:
            break
        href = m.group("href")
        title_raw = m.group("title")
        # remove tags
        title = re.sub(r"<.*?>", "", title_raw).strip()
        results.append({"title": title, "url": href})

    return {"query": query, "engine": "duckduckgo_html", "results": results}
