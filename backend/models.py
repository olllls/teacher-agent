from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Float
from sqlalchemy.orm import relationship

from backend.database import Base


class ClassModel(Base):
    __tablename__ = "classes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, comment="班级名称")
    grade = Column(String(50), comment="年级")
    semester = Column(String(50), nullable=False, comment="学期")
    style = Column(String(50), default="encourage", comment="评语风格")
    custom_prompt = Column(Text, comment="自定义提示词")
    source_file = Column(String(500), comment="上传的源文件路径")
    created_at = Column(DateTime, default=datetime.now)

    students = relationship("StudentModel", back_populates="class_", cascade="all, delete-orphan")


class StudentModel(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=False)
    name = Column(String(50), nullable=False)
    score = Column(String(50), comment="成绩")
    performance = Column(Text, comment="课堂表现")
    homework = Column(Text, comment="作业情况")
    keywords = Column(String(200), comment="关键词")
    extra_info = Column(Text, comment="其他信息(JSON)")

    class_ = relationship("ClassModel", back_populates="students")
    evaluation = relationship("EvaluationModel", back_populates="student", uselist=False, cascade="all, delete-orphan")


class EvaluationModel(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False, unique=True)
    content = Column(Text, nullable=False, comment="评语内容")
    word_count = Column(Integer, comment="字数")
    status = Column(String(20), default="pending", comment="pending/approved/edited")
    sensitive_hit = Column(Integer, default=0, comment="敏感词命中数")
    raw_response = Column(Text, comment="AI原始返回")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    student = relationship("StudentModel", back_populates="evaluation")


class SensitiveWordModel(Base):
    __tablename__ = "sensitive_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(100), nullable=False, unique=True)
    severity = Column(String(20), default="warning", comment="warning/block")
    is_system = Column(Integer, default=0, comment="是否系统内置")
    created_at = Column(DateTime, default=datetime.now)


class ConfigModel(Base):
    __tablename__ = "config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
