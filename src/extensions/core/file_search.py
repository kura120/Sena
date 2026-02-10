"""Core extension: file_search

Search files in the repository for filenames or content matching a query.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

EXTENSION_METADATA = {
    "name": "file_search",
    "description": "Search repository files by name or content and return matched paths and snippets.",
    "version": "1.0.0",
    "core": True,
}


async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """Execute file search.

    params:
      - query: string to search for (required)
      - path: base path to search (optional, defaults to repo root)
      - max_results: integer limit (optional, default 20)
    """
    query = params.get("query")
    if not query:
        return {"error": "query parameter is required"}

    base = Path(params.get("path") or Path(__file__).parent.parent.parent)
    max_results = int(params.get("max_results", 20))

    results: List[Dict[str, Any]] = []

    # Search filenames first
    for fp in base.rglob("*"):
        if len(results) >= max_results:
            break
        try:
            if query.lower() in fp.name.lower():
                results.append({"path": str(fp), "match_type": "filename", "snippet": fp.name})
                continue
        except Exception:
            continue

    # If not enough results, search file contents (text files)
    if len(results) < max_results:
        for fp in base.rglob("**/*"):
            if len(results) >= max_results:
                break
            if fp.is_dir():
                continue
            try:
                # Try to read as text
                text = fp.read_text(errors="ignore")
            except Exception:
                continue
            if query.lower() in text.lower():
                idx = text.lower().find(query.lower())
                start = max(0, idx - 80)
                end = min(len(text), idx + len(query) + 80)
                snippet = text[start:end].replace("\n", " ")
                results.append({"path": str(fp), "match_type": "content", "snippet": snippet})

    return {"query": query, "base": str(base), "results": results}
