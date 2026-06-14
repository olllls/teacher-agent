from __future__ import annotations

import re
from dataclasses import dataclass, field

BUILTIN_WORDS: list[dict[str, str]] = [
    {"word": "差生", "severity": "block"},
    {"word": "笨", "severity": "block"},
    {"word": "蠢", "severity": "block"},
    {"word": "傻瓜", "severity": "block"},
    {"word": "废物", "severity": "block"},
    {"word": "没出息", "severity": "block"},
    {"word": "朽木", "severity": "block"},
    {"word": "智商低", "severity": "block"},
    {"word": "脑子不好", "severity": "block"},
    {"word": "无可救药", "severity": "block"},
    {"word": "没救了", "severity": "block"},
    {"word": "太差了", "severity": "warning"},
    {"word": "倒数", "severity": "warning"},
    {"word": "拖后腿", "severity": "warning"},
    {"word": "问题学生", "severity": "block"},
    {"word": "坏学生", "severity": "block"},
    {"word": "不听话", "severity": "warning"},
    {"word": "捣蛋鬼", "severity": "warning"},
    {"word": "讨厌", "severity": "warning"},
    {"word": "懒得管你", "severity": "block"},
    {"word": "随便你", "severity": "warning"},
    {"word": "放弃", "severity": "warning"},
    {"word": "真笨", "severity": "block"},
    {"word": "不认真", "severity": "warning"},
    {"word": "态度差", "severity": "warning"},
    {"word": "懒惰", "severity": "warning"},
    {"word": "消极", "severity": "warning"},
    {"word": "对抗", "severity": "warning"},
    {"word": "恶习", "severity": "warning"},
    {"word": "屡教不改", "severity": "warning"},
    {"word": "不求上进", "severity": "warning"},
    {"word": "教不会", "severity": "block"},
    {"word": "听不懂人话", "severity": "block"},
    {"word": "真差", "severity": "warning"},
    {"word": "很差", "severity": "warning"},
    {"word": "极差", "severity": "warning"},
    {"word": "糟糕", "severity": "warning"},
    {"word": "太糟糕", "severity": "warning"},
    {"word": "不行", "severity": "warning"},
    {"word": "太不行", "severity": "warning"},
    {"word": "没救了", "severity": "block"},
    {"word": "最差", "severity": "warning"},
    {"word": "全年级最差", "severity": "block"},
    {"word": "全班最差", "severity": "block"},
    {"word": "无可奉告", "severity": "warning"},
    {"word": "不配合", "severity": "warning"},
    {"word": "敷衍", "severity": "warning"},
    {"word": "混日子", "severity": "warning"},
    {"word": "混", "severity": "warning"},
    {"word": "作弊", "severity": "block"},
    {"word": "抄袭", "severity": "block"},
    {"word": "撒谎", "severity": "warning"},
    {"word": "偷懒", "severity": "warning"},
]


@dataclass
class SensitiveMatch:
    word: str
    severity: str
    position: int
    length: int


class SensitiveChecker:
    """敏感词检测器，支持内置词库和运行时扩展词库。"""

    def __init__(self, extra_words: list[dict[str, str]] | None = None):
        words = BUILTIN_WORDS[:]
        if extra_words:
            words.extend(extra_words)
        self._words = words
        # sort by length desc so longer matches take priority
        self._patterns: list[tuple[re.Pattern, str, str]] = []
        for w in words:
            escaped = re.escape(w["word"])
            pattern = re.compile(escaped)
            self._patterns.append((pattern, w["word"], w["severity"]))

    def check(self, text: str) -> list[SensitiveMatch]:
        matches: list[SensitiveMatch] = []
        seen: set[int] = set()

        for pattern, word, severity in self._patterns:
            for m in pattern.finditer(text):
                pos = m.start()
                if pos not in seen:
                    seen.add(pos)
                    matches.append(SensitiveMatch(
                        word=word,
                        severity=severity,
                        position=pos,
                        length=len(word),
                    ))

        matches.sort(key=lambda x: x.position)
        return matches

    def has_blocked(self, text: str) -> bool:
        return any(m.severity == "block" for m in self.check(text))

    def highlight(self, text: str) -> str:
        """用标记包裹敏感词（用于前端展示）。"""
        matches = self.check(text)
        if not matches:
            return text

        result = []
        last = 0
        for m in matches:
            if m.position < last:
                continue
            result.append(text[last:m.position])
            cls = "sensitive-block" if m.severity == "block" else "sensitive-warn"
            result.append(f'<span class="{cls}">{text[m.position:m.position + m.length]}</span>')
            last = m.position + m.length
        result.append(text[last:])
        return "".join(result)

    @classmethod
    def default(cls) -> SensitiveChecker:
        return cls()
