import json
import logging
import datetime
from typing import Optional, Any, Dict, List
from ..database import async_session
from ..models import MemoryEntry

logger = logging.getLogger(__name__)


class MemoryManager:
    def __init__(self):
        self.short_term: Dict[str, List[Dict]] = {}
        self.max_short_term = 50

    async def remember(self, agent_name: str, key: str, value: Any,
                       memory_type: str = "episodic", importance: float = 0.5):
        if isinstance(value, dict):
            value = {k: v for k, v in value.items()}

        mem_key = f"{agent_name}:{key}"
        if agent_name not in self.short_term:
            self.short_term[agent_name] = []
        self.short_term[agent_name].append({
            "key": key,
            "value": value,
            "memory_type": memory_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
        })
        if len(self.short_term[agent_name]) > self.max_short_term:
            self.short_term[agent_name].pop(0)

        try:
            async with async_session() as session:
                entry = MemoryEntry(
                    agent_name=agent_name,
                    key=key,
                    value=value if isinstance(value, dict) else {"data": str(value)},
                    memory_type=memory_type,
                    importance=importance,
                )
                session.add(entry)
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to persist memory: {e}")

    async def recall(self, agent_name: Optional[str] = None,
                     key: Optional[str] = None,
                     memory_type: Optional[str] = None,
                     limit: int = 20) -> List[Dict]:
        results = []

        if agent_name and agent_name in self.short_term:
            for mem in self.short_term[agent_name]:
                if key and mem["key"] != key:
                    continue
                if memory_type and mem["memory_type"] != memory_type:
                    continue
                results.append(mem)

        if len(results) < limit:
            try:
                async with async_session() as session:
                    from sqlalchemy import select
                    from sqlalchemy import and_
                    conditions = []
                    if agent_name:
                        conditions.append(MemoryEntry.agent_name == agent_name)
                    if key:
                        conditions.append(MemoryEntry.key == key)
                    if memory_type:
                        conditions.append(MemoryEntry.memory_type == memory_type)

                    query = select(MemoryEntry).where(
                        and_(*conditions) if conditions else True
                    ).order_by(MemoryEntry.created_at.desc()).limit(limit)

                    result = await session.execute(query)
                    for row in result.scalars().all():
                        results.append({
                            "key": row.key,
                            "value": row.value,
                            "memory_type": row.memory_type,
                            "importance": row.importance,
                            "created_at": row.created_at.isoformat() if row.created_at else None,
                        })
            except Exception as e:
                logger.warning(f"Failed to recall from DB: {e}")

        return results[:limit]

    async def forget(self, agent_name: Optional[str] = None, key: Optional[str] = None):
        if agent_name and agent_name in self.short_term:
            if key:
                self.short_term[agent_name] = [
                    m for m in self.short_term[agent_name] if m["key"] != key
                ]
            else:
                self.short_term[agent_name] = []

        try:
            async with async_session() as session:
                from sqlalchemy import delete
                conditions = []
                if agent_name:
                    conditions.append(MemoryEntry.agent_name == agent_name)
                if key:
                    conditions.append(MemoryEntry.key == key)
                query = delete(MemoryEntry).where(
                    and_(*conditions) if conditions else True
                )
                await session.execute(query)
                await session.commit()
        except Exception as e:
            logger.warning(f"Failed to forget from DB: {e}")

    async def get_context(self, agent_name: str, limit: int = 10) -> str:
        memories = await self.recall(agent_name=agent_name, limit=limit)
        if not memories:
            return ""
        context_parts = []
        for mem in memories:
            context_parts.append(f"[{mem['memory_type']}] {mem['key']}: {json.dumps(mem['value'], ensure_ascii=False)}")
        return "\n".join(context_parts)


memory_manager = MemoryManager()
