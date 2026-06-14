from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd

from backend.schemas import StudentData

REQUIRED_COLUMNS = ["姓名"]
COLUMN_ALIASES = {
    "学生姓名": "姓名",
    "名字": "姓名",
    "学生": "姓名",
    "分数": "成绩",
    "得分": "成绩",
    "期末成绩": "成绩",
    "考试成绩": "成绩",
    "等级": "成绩",
    "等第": "成绩",
    "评价": "成绩",
    "课堂表现": "课堂表现",
    "上课表现": "课堂表现",
    "课上表现": "课堂表现",
    "纪律": "课堂表现",
    "课堂": "课堂表现",
    "作业": "作业情况",
    "作业情况": "作业情况",
    "作业完成": "作业情况",
    "作业完成情况": "作业情况",
    "作业质量": "作业情况",
    "关键词": "关键词",
    "标签": "关键词",
    "特点": "关键词",
    "关键字": "关键词",
}


class ExcelParseError(Exception):
    pass


class ExcelParser:
    @staticmethod
    def parse(file_path: str | Path) -> tuple[list[StudentData], list[str]]:
        path = Path(file_path)
        if not path.exists():
            raise ExcelParseError(f"文件不存在: {file_path}")
        if path.suffix not in (".xlsx", ".xls"):
            raise ExcelParseError(f"不支持的文件格式: {path.suffix}，仅支持 .xlsx / .xls")

        df = pd.read_excel(path, dtype=str)
        if df.empty:
            raise ExcelParseError("Excel 文件为空")

        df = ExcelParser._normalize_columns(df)
        ExcelParser._validate_columns(df)

        df = df.where(pd.notna(df), None)
        students = []
        for _, row in df.iterrows():
            students.append(
                StudentData(
                    name=str(row["姓名"]).strip(),
                    score=str(row["成绩"]).strip() if row.get("成绩") is not None else None,
                    performance=str(row["课堂表现"]).strip() if row.get("课堂表现") is not None else None,
                    homework=str(row["作业情况"]).strip() if row.get("作业情况") is not None else None,
                    keywords=str(row["关键词"]).strip() if row.get("关键词") is not None else None,
                )
            )

        return students, list(df.columns)

    @staticmethod
    def parse_preview(file_path: str | Path, rows: int = 5) -> tuple[list[StudentData], list[str]]:
        path = Path(file_path)
        if not path.exists():
            raise ExcelParseError(f"文件不存在: {file_path}")

        df = pd.read_excel(path, dtype=str, nrows=rows)
        if df.empty:
            raise ExcelParseError("Excel 文件为空")

        df = ExcelParser._normalize_columns(df)
        ExcelParser._validate_columns(df)

        df = df.where(pd.notna(df), None)
        students = []
        for _, row in df.iterrows():
            students.append(
                StudentData(
                    name=str(row["姓名"]).strip(),
                    score=str(row["成绩"]).strip() if row.get("成绩") is not None else None,
                    performance=str(row["课堂表现"]).strip() if row.get("课堂表现") is not None else None,
                    homework=str(row["作业情况"]).strip() if row.get("作业情况") is not None else None,
                    keywords=str(row["关键词"]).strip() if row.get("关键词") is not None else None,
                )
            )

        return students, list(df.columns)

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        renamed = {}
        for col in df.columns:
            col_stripped = str(col).strip()
            if col_stripped in COLUMN_ALIASES:
                renamed[col] = COLUMN_ALIASES[col_stripped]
        return df.rename(columns=renamed)

    @staticmethod
    def _validate_columns(df: pd.DataFrame) -> None:
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            raise ExcelParseError(
                f"缺少必要列: {', '.join(missing)}。"
                f"需要的列: {', '.join(REQUIRED_COLUMNS)}"
            )
