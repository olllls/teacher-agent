import io
import os
import uuid
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.parser import ExcelParser, ExcelParseError
from backend.config import settings
from backend.database import get_db
from backend.models import ClassModel, StudentModel
from backend.schemas import UploadResponse

router = APIRouter(prefix="/api/v1", tags=["upload"])


@router.get("/template")
async def download_template():
    df = pd.DataFrame({
        "姓名": ["例：张三"],
        "成绩": ["优秀"],
    })
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=template.xlsx; filename*=utf-8''%E8%AF%84%E8%AF%AD%E6%A8%A1%E6%9D%BF.xlsx"},
    )


@router.post("/upload-excel", response_model=UploadResponse)
async def upload_excel(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls 格式")

    content = await file.read()
    if len(content) > settings.max_upload_size:
        raise HTTPException(status_code=400, detail="文件大小超过 10MB 限制")

    filename = f"{uuid.uuid4().hex}_{file.filename}"
    filepath = os.path.join(settings.upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    try:
        preview_students, columns = ExcelParser.parse_preview(filepath)
        all_students, _ = ExcelParser.parse(filepath)
    except ExcelParseError as e:
        os.remove(filepath)
        raise HTTPException(status_code=400, detail=str(e))

    class_ = ClassModel(
        name=f"班级_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        semester=datetime.now().strftime('%Y-%m'),
        style=settings.default_style,
        created_at=datetime.now(),
    )
    db.add(class_)
    await db.flush()

    for s in all_students:
        student = StudentModel(
            class_id=class_.id,
            name=s.name,
            score=s.score,
            performance=s.performance,
            homework=s.homework,
        )
        db.add(student)

    await db.commit()

    return UploadResponse(
        class_id=class_.id,
        class_name=class_.name,
        total=len(all_students),
        preview=preview_students,
        columns=columns,
    )
