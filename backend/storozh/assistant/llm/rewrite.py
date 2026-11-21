"""Переписывание вопроса юридическими терминами (ru + uz). Отдельный вызов без инструментов (NFR-A-03)."""

import logging

from storozh.assistant.llm.port import LLM, LLMError

log = logging.getLogger(__name__)

SYSTEM = """Ты помогаешь искать нормы законодательства Узбекистана о нотариате, доверенностях \
(в том числе электронных: my.gov.uz, Vakolat.uz) и сделках с имуществом.
Перепиши вопрос гражданина в 3–4 коротких поисковых запроса юридическими терминами: \
минимум один на русском и минимум один на узбекском (латиница). Не отвечай на вопрос."""

SCHEMA = {
    "type": "object",
    "properties": {"queries": {"type": "array", "items": {"type": "string"}}},
    "required": ["queries"],
    "additionalProperties": False,
}


async def rewrite(llm: LLM, question: str, context: str = "") -> list[str]:
    """Запросы для поиска. При ошибке модели — исходный вопрос (поиск всё равно сработает)."""
    user = f"Документ: {context}\nВопрос: {question}" if context else f"Вопрос: {question}"
    try:
        out = await llm.complete_json(SYSTEM, user, SCHEMA, max_tokens=1024, timeout_s=15, effort="low",
                                    think=False)
        queries = [q for q in out.get("queries", []) if isinstance(q, str)][:4]
    except LLMError as e:
        log.warning("rewrite failed: %s", e)
        queries = []
    return [question, *queries]
