from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StudentData(BaseModel):
    name: str
    score: Optional[str] = None
    performance: Optional[str] = None
    homework: Optional[str] = None
    extra_info: Optional[str] = None


class UploadResponse(BaseModel):
    class_id: int
    class_name: str
    total: int
    preview: list[StudentData]
    columns: list[str]


class GenerateRequest(BaseModel):
    class_id: int
    style: str = "encourage"
    custom_prompt: Optional[str] = None
    word_count: str = "100-150"


class EvaluationResult(BaseModel):
    student_id: int
    name: str
    score: Optional[str] = None
    performance: Optional[str] = None
    homework: Optional[str] = None
    content: str
    sensitive_hit: int = 0
    sensitive_words: list[str] = []


class GenerateResponse(BaseModel):
    task_id: str
    total: int
    status: str = "processing"


class GenerateStatus(BaseModel):
    task_id: str
    status: str
    total: int
    completed: int
    results: list[EvaluationResult] = []


class EvaluationUpdate(BaseModel):
    content: str


class ClassInfo(BaseModel):
    id: int
    name: str
    grade: Optional[str] = None
    semester: str
    style: str
    student_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class SensitiveWordCreate(BaseModel):
    word: str
    severity: str = "warning"


class SensitiveWordOut(BaseModel):
    id: int
    word: str
    severity: str
    is_system: bool

    class Config:
        from_attributes = True


class ConfigUpdate(BaseModel):
    value: str
