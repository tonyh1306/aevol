from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.trace import TraceCreate, TraceResponse
from app.services import trace_service

router = APIRouter(prefix="/traces", tags=["traces"])


@router.post("", response_model=TraceResponse, status_code=201)
async def create_trace(data: TraceCreate, db: AsyncSession = Depends(get_db)):
    return await trace_service.create_trace(db, data)


@router.get("/{trace_id}", response_model=TraceResponse)
async def get_trace(trace_id: str, db: AsyncSession = Depends(get_db)):
    trace = await trace_service.get_trace(db, trace_id)
    if not trace:
        raise HTTPException(404, "trace not found")
    return trace
