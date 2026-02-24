# src/api/routes/memory.py
"""Memory API routes for memory management."""

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.deps import get_memory_manager
from src.memory.manager import MemoryManager
from src.utils.logger import logger

router = APIRouter(prefix="/memory", tags=["Memory"])


def _enrich_memory(item: dict[str, Any]) -> dict[str, Any]:
    """Flatten metadata fields (context, origin) to the top level for the UI."""
    meta = item.get("metadata") or {}
    return {
        **item,
        "context": meta.get("context", ""),
        "origin": meta.get("origin", meta.get("source", "unknown")),
    }


@router.get(
    "/recent",
    response_model=dict[str, Any],
    summary="Get recent memories",
    description="Fetch recent long-term memories",
)
async def get_recent_memories(
    limit: int = Query(20, ge=1, le=100),
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Fetch recent memories."""
    try:
        results = await memory_mgr.recent_memories(limit=limit)
        enriched = [_enrich_memory(r) for r in results]
        return {
            "status": "success",
            "results": enriched,
            "count": len(enriched),
        }
    except Exception as e:
        logger.error(f"Recent memories error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/stats",
    response_model=dict[str, Any],
    summary="Get memory statistics",
    description="Get statistics about short and long-term memory",
)
async def get_memory_stats(
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Get memory system statistics."""
    try:
        stats = await memory_mgr.get_memory_stats()
        retrieval_stats = await memory_mgr.get_retrieval_stats()

        return {
            "status": "success",
            "memory": stats,
            "retrieval": retrieval_stats,
        }
    except Exception as e:
        logger.error(f"Memory stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/search",
    response_model=dict[str, Any],
    summary="Search memories",
    description="Search through stored memories by query",
)
async def search_memories(
    query: str = Query(..., min_length=1),
    k: int = Query(5, ge=1, le=50),
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Search through stored memories."""
    try:
        results = await memory_mgr.recall(query=query, k=k)
        enriched = [_enrich_memory(r) for r in results]

        return {
            "status": "success",
            "query": query,
            "results": enriched,
            "count": len(enriched),
        }
    except Exception as e:
        logger.error(f"Memory search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/add",
    response_model=dict[str, Any],
    summary="Add a memory",
    description="Store a new memory in long-term storage",
)
async def add_memory(
    request: dict[str, Any],
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Add a new long-term memory."""
    try:
        if "content" not in request or not request["content"].strip():
            raise HTTPException(status_code=400, detail="Content cannot be empty")

        result = await memory_mgr.remember(content=request["content"], metadata=request.get("metadata", {}))

        return {
            "status": "success",
            "memory_id": result.get("memory_id"),
            "message": "Memory added successfully",
            "result": result,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put(
    "/edit",
    response_model=dict[str, Any],
    summary="Edit a memory",
    description="Update an existing memory",
)
async def edit_memory(
    request: dict[str, Any],
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Edit an existing memory."""
    try:
        if "memory_id" not in request:
            raise HTTPException(status_code=400, detail="memory_id is required")

        memory_id = request["memory_id"]

        success = await memory_mgr.long_term.update(
            memory_id=memory_id,
            content=request.get("content"),
            metadata=request.get("metadata"),
        )

        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")

        return {
            "status": "success",
            "memory_id": memory_id,
            "message": "Memory updated successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Edit memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{memory_id}",
    response_model=dict[str, Any],
    summary="Delete a memory",
    description="Delete a memory by ID",
)
async def delete_memory(
    memory_id: int,
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Delete a memory by ID."""
    try:
        success = await memory_mgr.forget_memory(memory_id)

        if not success:
            raise HTTPException(status_code=404, detail="Memory not found")

        return {
            "status": "success",
            "memory_id": memory_id,
            "message": "Memory deleted successfully",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/context",
    response_model=dict[str, Any],
    summary="Get current context",
    description="Get the current conversation context from short-term memory",
)
async def get_context(
    limit: int = Query(10, ge=1, le=50),
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Get current conversation context."""
    try:
        context = await memory_mgr.get_conversation_context(limit=limit)

        return {
            "status": "success",
            "context": context,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Get context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/clear",
    response_model=dict[str, Any],
    summary="Clear context",
    description="Clear the short-term memory buffer",
)
async def clear_context(
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Clear short-term memory context."""
    try:
        cleared = await memory_mgr.clear_context()

        return {
            "status": "success",
            "items_cleared": cleared,
            "message": "Context cleared successfully",
        }
    except Exception as e:
        logger.error(f"Clear context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/short-term",
    response_model=dict[str, Any],
    summary="Get short-term (in-session) memories",
    description="Fetch all items currently held in the short-term conversation buffer",
)
async def get_short_term_memories(
    memory_mgr: MemoryManager = Depends(get_memory_manager),
) -> dict[str, Any]:
    """Return the contents of the short-term in-memory buffer."""
    try:
        items = await memory_mgr.short_term.get_all()
        results = [
            {
                "id": item.id,
                "content": item.content,
                "role": item.role,
                "timestamp": item.timestamp.isoformat(),
                "expires_at": item.expires_at.isoformat() if item.expires_at else None,
                "metadata": item.metadata or {},
                "context": (item.metadata or {}).get("context", "In-session conversation"),
                "origin": (item.metadata or {}).get("origin", item.role),
            }
            for item in items
        ]
        return {
            "status": "success",
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        logger.error(f"Short-term memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
