import logging
from typing import List
from fastapi import APIRouter, HTTPException

from ..schemas import MemorySearch
from ..memory.manager import memory_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.post("/search", response_model=dict)
async def search_memory(request: MemorySearch):
    try:
        results = await memory_manager.recall(
            agent_name=request.agent_name,
            key=request.key,
            memory_type=request.memory_type,
            limit=request.limit,
        )
        return {"results": results, "total": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/forget", response_model=dict)
async def forget_memory(agent_name: str = None, key: str = None):
    try:
        await memory_manager.forget(agent_name=agent_name, key=key)
        return {"status": "forgotten"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=dict)
async def memory_stats():
    return {
        "status": "active",
        "short_term_slots": memory_manager.max_short_term,
    }
