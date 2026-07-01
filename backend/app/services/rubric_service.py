import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rubric import Rubric
from app.schemas.rubric import RubricCreate


async def create_rubric(db: AsyncSession, data: RubricCreate) -> Rubric:
    rubric = Rubric(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        criteria=[c.model_dump() for c in data.criteria],
    )
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    return rubric


async def get_rubric(db: AsyncSession, rubric_id: str) -> Rubric | None:
    return await db.get(Rubric, rubric_id)


async def list_rubrics(db: AsyncSession) -> list[Rubric]:
    result = await db.execute(select(Rubric).order_by(Rubric.created_at.desc()))
    return list(result.scalars().all())
