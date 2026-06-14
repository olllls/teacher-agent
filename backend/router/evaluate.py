from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.evaluator import EvaluationService, EvaluationError
from backend.agent.sensitive import SensitiveChecker
from backend.database import async_session, get_db
from backend.models import EvaluationModel, StudentModel
from backend.schemas import (
    EvaluationResult,
    EvaluationUpdate,
    GenerateRequest,
    GenerateResponse,
    GenerateStatus,
)

router = APIRouter(prefix="/api/v1", tags=["evaluate"])

sensitive_checker = SensitiveChecker.default()


@dataclass
class TaskState:
    task_id: str
    class_id: int
    status: str  # processing / completed / failed
    total: int
    completed: int = 0
    results: list[EvaluationResult] = field(default_factory=list)
    error: str | None = None


_tasks: dict[str, TaskState] = {}


@router.post("/generate", response_model=GenerateResponse)
async def start_generate(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StudentModel).where(StudentModel.class_id == req.class_id)
    )
    students = result.scalars().all()
    if not students:
        raise HTTPException(status_code=404, detail="该班级没有学生数据")

    # Prevent duplicate generation for the same class
    for t in _tasks.values():
        if t.class_id == req.class_id and t.status == "processing":
            raise HTTPException(
                status_code=409,
                detail="该班级正在生成评语中，请等待完成",
            )

    task_id = f"gen-{uuid.uuid4().hex[:12]}"
    state = TaskState(
        task_id=task_id,
        class_id=req.class_id,
        status="processing",
        total=len(students),
    )
    _tasks[task_id] = state

    # Create own session for background task
    asyncio.create_task(_run_generation(task_id, students, req))

    return GenerateResponse(task_id=task_id, total=len(students))


@router.get("/generate/{task_id}", response_model=GenerateStatus)
async def get_generate_status(task_id: str):
    state = _tasks.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="任务不存在")
    return GenerateStatus(
        task_id=state.task_id,
        status=state.status,
        total=state.total,
        completed=state.completed,
        results=state.results,
    )


@router.put("/evaluations/{evaluation_id}")
async def update_evaluation(evaluation_id: int, body: EvaluationUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EvaluationModel).where(EvaluationModel.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="评语不存在")

    word_count = len(body.content.replace(" ", "").replace("\n", ""))
    matches = sensitive_checker.check(body.content)

    evaluation.content = body.content
    evaluation.word_count = word_count
    evaluation.status = "edited"
    evaluation.sensitive_hit = len(matches)
    await db.commit()

    return {"ok": True}


@router.get("/classes/{class_id}/evaluations")
async def get_class_evaluations(class_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            StudentModel.id,
            StudentModel.name,
            StudentModel.score,
            StudentModel.performance,
            StudentModel.homework,
            StudentModel.keywords,
            StudentModel.extra_info,
            EvaluationModel.id.label("eval_id"),
            EvaluationModel.content,
            EvaluationModel.sensitive_hit,
            EvaluationModel.status,
        )
        .outerjoin(EvaluationModel, EvaluationModel.student_id == StudentModel.id)
        .where(StudentModel.class_id == class_id)
        .order_by(StudentModel.id)
    )
    rows = result.all()

    results = []
    for row in rows:
        sensitive_words = []
        if row.content:
            sensitive_words = [m.word for m in sensitive_checker.check(row.content)]

        results.append({
            "student_id": row.id,
            "name": row.name,
            "score": row.score,
            "performance": row.performance,
            "homework": row.homework,
            "keywords": row.keywords,
            "extra_info": row.extra_info,
            "eval_id": row.eval_id,
            "content": row.content or "",
            "sensitive_hit": row.sensitive_hit or 0,
            "sensitive_words": sensitive_words,
            "status": row.status or "pending",
        })

    return {"students": results}


async def _run_generation(task_id: str, students: list[StudentModel], req: GenerateRequest):
    state = _tasks[task_id]
    evaluator = EvaluationService()

    try:
        student_ids = [s.id for s in students]
        async with async_session() as db:
            # Delete existing evaluations for these students (raw delete to avoid autoflush issues)
            await db.execute(
                EvaluationModel.__table__.delete().where(
                    EvaluationModel.student_id.in_(student_ids)
                )
            )

            for idx, student in enumerate(students):
                content = await evaluator.generate(
                    name=student.name,
                    score=student.score,
                    performance=student.performance,
                    homework=student.homework,
                    keywords=student.keywords,
                    extra_info=student.extra_info,
                    style=req.style,
                    custom_prompt=req.custom_prompt,
                    word_count=req.word_count,
                )

                word_count = len(content.replace(" ", "").replace("\n", ""))
                matches = sensitive_checker.check(content)
                sensitive_words_list = [m.word for m in matches]

                eval_model = EvaluationModel(
                    student_id=student.id,
                    content=content,
                    word_count=word_count,
                    status="approved",
                    sensitive_hit=len(matches),
                    raw_response=content,
                )
                db.add(eval_model)

                state.results.append(EvaluationResult(
                    student_id=student.id,
                    name=student.name,
                    score=student.score,
                    performance=student.performance,
                    homework=student.homework,
                    keywords=student.keywords,
                    content=content,
                    sensitive_hit=len(matches),
                    sensitive_words=sensitive_words_list,
                ))
                state.completed += 1

                # Incremental commit every 5 evaluations
                if (idx + 1) % 5 == 0:
                    await db.commit()

            await db.commit()

    except EvaluationError as e:
        state.status = "failed"
        state.error = str(e)
    except Exception as e:
        err_msg = f"生成过程异常: {e}"
        state.status = "failed"
        state.error = err_msg
        import sys
        print(f"[BG ERROR] {err_msg}", file=sys.stderr, flush=True)
    else:
        state.status = "completed"
    finally:
        await evaluator.close()
