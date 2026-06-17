import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.report import ReportCreate, ReportListResponse, ReportOut
from app.services.report_service import generate_report, get_report, list_reports

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportOut, status_code=201)
async def create_report(data: ReportCreate, db: AsyncSession = Depends(get_db)):
    return await generate_report(db, data)


@router.get("", response_model=ReportListResponse)
async def get_reports(db: AsyncSession = Depends(get_db)):
    items, total = await list_reports(db)
    return ReportListResponse(items=items, total=total)


@router.get("/{report_id}", response_model=ReportOut)
async def get_report_by_id(report_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await get_report(db, report_id)
