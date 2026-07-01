import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trace import Trace
from app.schemas.trace import TraceCreate


async def create_trace(db: AsyncSession, data: TraceCreate) -> Trace:
    trace = Trace(
        id=str(uuid.uuid4()),
        input=data.input.model_dump(),
        expected=data.expected.model_dump() if data.expected else None,
        spans=[s.model_dump(mode="json") for s in data.spans],
        metadata_=data.metadata,
    )
    db.add(trace)
    await db.commit()
    await db.refresh(trace)
    return trace


async def get_trace(db: AsyncSession, trace_id: str) -> Trace | None:
    return await db.get(Trace, trace_id)


async def get_traces(db: AsyncSession, trace_ids: list[str]) -> list[Trace]:
    result = await db.execute(select(Trace).where(Trace.id.in_(trace_ids)))
    return list(result.scalars().all())
