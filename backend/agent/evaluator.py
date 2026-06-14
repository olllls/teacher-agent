from __future__ import annotations

import asyncio
import re

import httpx

from backend.config import settings

STYLES = {
    "encourage": "以鼓励为主，语气温暖亲切",
    "moderate": "客观中肯，既肯定优点也指出不足",
    "strict": "严格要求，高标准，语气正式",
}

PROMPT_TEMPLATE = """你是一位有丰富教学经验的班主任，{style_desc}。
请为以下学生撰写期末评语，字数控制在 {min_words}-{max_words} 字之间。

学生信息：
- 姓名：{name}
- 期末成绩（百分制）：{score}
- 课堂表现：{performance}
- 作业情况：{homework}

要求：
1. 先肯定学生的优点和进步，再委婉指出需要改进的地方
2. 结合具体的课堂表现或作业情况来佐证评价
3. 提出下学期可操作的改进建议，让学生知道怎么做
4. 语气真诚温暖，用"你"来称呼学生
5. 不得出现歧视性、贬低性词汇
6. 请直接输出评语正文，不要加标题和署名"""


class EvaluationError(Exception):
    pass


class EvaluationService:

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=settings.deepseek_base_url,
                timeout=60.0,
            )
        return self._client

    async def generate(
        self,
        name: str,
        score: float | None = None,
        performance: str | None = None,
        homework: str | None = None,
        style: str = "encourage",
        custom_prompt: str | None = None,
        word_count: str = "100-150",
    ) -> str:
        style_desc = STYLES.get(style, STYLES["encourage"])
        match = re.match(r"(\d+)-(\d+)", word_count)
        min_words, max_words = (match.group(1), match.group(2)) if match else ("100", "150")

        if custom_prompt:
            style_desc = f"{style_desc}，{custom_prompt}"

        score_str = f"{score}分" if score is not None else "未知"
        performance_str = performance or "未记录"
        homework_str = homework or "未记录"

        prompt = PROMPT_TEMPLATE.format(
            style_desc=style_desc,
            min_words=min_words,
            max_words=max_words,
            name=name,
            score=score_str,
            performance=performance_str,
            homework=homework_str,
        )

        return await self._call_deepseek(prompt)

    async def _call_deepseek(self, prompt: str) -> str:
        if not settings.deepseek_api_key:
            raise EvaluationError("DeepSeek API Key 未配置，请在设置页面填写")

        client = await self._get_client()

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                resp = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                    json={
                        "model": settings.deepseek_model,
                        "messages": [
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0.7,
                        "max_tokens": 500,
                    },
                )

                if resp.status_code == 401:
                    raise EvaluationError("DeepSeek API Key 无效，请检查设置")
                if resp.status_code == 429:
                    await asyncio.sleep(2 ** attempt)
                    continue
                if resp.status_code >= 500:
                    await asyncio.sleep(2 ** attempt)
                    continue

                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()
                return content

            except httpx.TimeoutException:
                last_error = EvaluationError("DeepSeek API 请求超时")
                await asyncio.sleep(2 ** attempt)

            except httpx.RequestError as e:
                last_error = EvaluationError(f"网络请求失败: {e}")
                await asyncio.sleep(2 ** attempt)

            except (KeyError, IndexError, ValueError) as e:
                raise EvaluationError(f"API 返回格式异常: {e}")

        raise EvaluationError(f"生成失败（已重试 3 次）: {last_error}")

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
