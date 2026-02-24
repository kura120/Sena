import asyncio
import os
from pathlib import Path
import pytest
from src.extensions.core import file_search


@pytest.mark.asyncio
async def test_file_search_by_name(tmp_path):
    # create files
    a = tmp_path / "hello_world.txt"
    a.write_text("this is a test file")
    b = tmp_path / "another.md"
    b.write_text("contains keyword: foobar")

    res = await file_search.execute({"query": "hello", "path": str(tmp_path), "max_results": 10})
    assert res["results"]
    assert any("hello_world.txt" in r["path"] or r["match_type"] == "filename" for r in res["results"]) 


@pytest.mark.asyncio
async def test_file_search_by_content(tmp_path):
    f = tmp_path / "content.txt"
    f.write_text("lorem foobar ipsum")
    res = await file_search.execute({"query": "foobar", "path": str(tmp_path), "max_results": 10})
    assert res["results"]
    assert any(r["match_type"] == "content" for r in res["results"]) 
