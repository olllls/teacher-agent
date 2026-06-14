import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.parser import ExcelParser, ExcelParseError
from backend.config import settings
from backend.database import get_db
from backend.models import ClassModel, StudentModel
from backend.schemas import UploadResponse, StudentData

router = APIRouter(prefix="/api/v1", tags=["upload"])


@router.post("/upload-excel", response_model=UploadResponse)
async def upload_excel(
    file: UploadFile = File(...),
    class_name: str = Form(...),
    grade: str = Form(""),
    semester: str = Form(...),
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
        name=class_name,
        grade=grade or None,
        semester=semester,
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
        class_name=class_name,
        total=len(all_students),
        preview=preview_students,
        columns=columns,
    )
