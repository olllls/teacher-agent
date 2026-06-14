from __future__ import annotations

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models import EvaluationModel, ClassModel, StudentModel

router = APIRouter(prefix="/api/v1", tags=["export"])


class ExportRequest(BaseModel):
    class_id: int


@router.post("/export-excel")
async def export_excel(req: ExportRequest, db: AsyncSession = Depends(get_db)):
    class_result = await db.execute(
        select(ClassModel).where(ClassModel.id == req.class_id)
    )
    class_ = class_result.scalar_one_or_none()
    if not class_:
        raise HTTPException(status_code=404, detail="班级不存在")

    result = await db.execute(
        select(
            StudentModel.name,
            StudentModel.score,
            StudentModel.performance,
            StudentModel.homework,
            StudentModel.keywords,
            EvaluationModel.content,
        )
        .outerjoin(EvaluationModel, EvaluationModel.student_id == StudentModel.id)
        .where(StudentModel.class_id == req.class_id)
        .order_by(StudentModel.id)
    )
    rows = result.all()

    import pandas as pd

    data = []
    for row in rows:
        data.append({
            "姓名": row.name,
            "成绩": row.score if row.score is not None else "",
            "课堂表现": row.performance or "",
            "作业情况": row.homework or "",
            "关键词": row.keywords or "",
            "评语": row.content or "",
        })

    if not data:
        raise HTTPException(status_code=400, detail="没有可导出的数据")

    df = pd.DataFrame(data)
    filename = f"评语_{class_.name}_{class_.semester}_{uuid.uuid4().hex[:8]}.xlsx"
    filepath = os.path.join(settings.export_dir, filename)
    df.to_excel(filepath, index=False, engine="openpyxl")

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
