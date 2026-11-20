"""Агент-юрист: Claude сам ищет нормы через инструменты, отвечает со ссылками [[code:number]],
после чего мы проверяем, что каждая ссылка реально была найдена в корпусе."""

import json
import re
from dataclasses import dataclass, field

import anthropic

from storozh.assistant.rag.corpus.service import BY_CODE, SOURCES, article_url, articles_by_keys
from storozh.assistant.rag.retrieval.service import search
from storozh.shared.config import settings

MAX_TURNS = 8
_CITE = re.compile(r"\[\[([a-z0-9]+):([\d-]+)\]\]")

SYSTEM = f"""Ты — юридический помощник для граждан Республики Узбекистан. Отвечаешь на языке вопроса \
(русский или узбекский), простыми словами, без канцелярита.

Опирайся только на тексты норм, полученные через инструменты search_law и get_article. Обычно нужно \
2–4 поиска с разными формулировками (бытовые слова → юридические термины, на русском и узбекском). \
Если вопрос касается процедуры, найди и порядок, и сроки, и компетентный орган.

Каждое утверждение о праве подкрепляй ссылкой вида [[код:номер]], например [[gk1:386]]. \
Ссылаться можно только на статьи, которые ты получил из инструментов. Если нужной нормы в корпусе \
нет — честно скажи об этом и посоветуй обратиться за бесплатной юридической помощью.

Структура ответа: коротко суть → что говорит закон → что делать по шагам (куда, какие документы, сроки).

Доступные коды актов: {", ".join(f"{s.code} — {s.name_ru}" for s in SOURCES)}."""

TOOLS = [
    {
        "name": "search_law",
        "description": "Гибридный поиск статей кодексов Узбекистана (ru/uz). Возвращает статьи с текстом, "
        "путём (раздел/глава) и ссылками на связанные статьи. Формулируй запрос юридическими терминами.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Поисковый запрос на русском или узбекском"},
                "codes": {
                    "type": "array",
                    "items": {"type": "string", "enum": [s.code for s in SOURCES]},
                    "description": "Ограничить поиск этими актами (пустой список — искать везде)",
                },
            },
            "required": ["query", "codes"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_article",
        "description": "Полный текст конкретной статьи по коду акта и номеру (например gk1, 386).",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "enum": [s.code for s in SOURCES]},
                "number": {"type": "string"},
            },
            "required": ["code", "number"],
            "additionalProperties": False,
        },
    },
]


@dataclass
class Citation:
    code: str
    number: str
    title: str
    url: str


@dataclass
class Answer:
    text: str
    citations: list[Citation] = field(default_factory=list)
    unverified: list[str] = field(default_factory=list)
    tool_calls: int = 0
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)  # input/output/cache_read/cache_write токены за все шаги


class _Session:
    """Запоминает, какие статьи агент реально видел — только на них разрешено ссылаться."""

    def __init__(self, lang: str):
        self.lang = lang
        self.seen: dict[tuple[str, str], dict] = {}

    def _remember(self, code: str, number: str, title: str, url: str) -> None:
        self.seen[(code, number)] = {"title": title, "url": url}

    def search_law(self, query: str, codes: list[str]) -> str:
        hits = search(query, k=6, codes=codes or None)
        out = []
        for h in hits:
            self._remember(h.code, h.number, h.title, h.url)
            out.append({
                "cite": f"[[{h.code}:{h.number}]]",
                "act": BY_CODE[h.code].name_ru,
                "title": h.title,
                "path": " > ".join(h.path),
                "text": h.text[:2500],
                "related": [f"[[{r.code}:{r.number}]] {r.title}" for r in h.related],
            })
        return json.dumps(out, ensure_ascii=False)

    def get_article(self, code: str, number: str) -> str:
        rows = articles_by_keys([(code, number)])
        if not rows:
            raise LookupError(f"Статья {code}:{number} не найдена в корпусе")
        a = next((r for r in rows if r["lang"] == self.lang), rows[0])
        self._remember(code, number, a["title"], article_url(a))
        return json.dumps(
            {"cite": f"[[{code}:{number}]]", "title": a["title"], "path": " > ".join(a["path"]), "text": a["body"]},
            ensure_ascii=False,
        )

    def run(self, name: str, args: dict) -> str:
        if name == "search_law":
            return self.search_law(args["query"], args.get("codes") or [])
        if name == "get_article":
            return self.get_article(args["code"], args["number"])
        raise ValueError(f"unknown tool {name}")


def _verify(text: str, session: _Session) -> Answer:
    cites, bad = {}, []
    for code, number in _CITE.findall(text):
        meta = session.seen.get((code, number))
        if meta:
            cites[(code, number)] = Citation(code, number, meta["title"], meta["url"])
        else:
            bad.append(f"{code}:{number}")
    # Неподтверждённые ссылки вырезаем из текста, чтобы пользователь не увидел выдуманную норму.
    clean = _CITE.sub(lambda m: m.group(0) if (m.group(1), m.group(2)) in cites else "", text)
    return Answer(text=clean, citations=list(cites.values()), unverified=bad)


# Модели с серверным fallback при отказе (safety refusal). Haiku 5.5 и 4.x — без него.
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}


def _request_kwargs(model: str, effort: str) -> dict:
    kw: dict = {"thinking": {"type": "adaptive"}, "output_config": {"effort": effort}}
    if model in _FALLBACK_MODELS:
        kw |= {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    return kw


def _add_usage(acc: dict[str, int], u) -> None:
    for key, attr in (("input", "input_tokens"), ("output", "output_tokens"),
                      ("cache_read", "cache_read_input_tokens"), ("cache_write", "cache_creation_input_tokens")):
        acc[key] = acc.get(key, 0) + (getattr(u, attr, 0) or 0)


def answer(question: str, lang: str, model: str | None = None, effort: str = "medium") -> Answer:
    model = model or settings.llm_model
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    session = _Session(lang)
    messages: list = [{"role": "user", "content": question}]
    calls, usage = 0, {}
    kwargs = _request_kwargs(model, effort)

    for _ in range(MAX_TURNS):
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            system=SYSTEM,
            tools=TOOLS,
            cache_control={"type": "ephemeral"},  # история шагов агента переиспользуется из кэша
            messages=messages,
            **kwargs,
        )
        _add_usage(usage, response.usage)
        if response.stop_reason == "refusal":
            return Answer(text="Не могу ответить на этот запрос.", model=model, usage=usage, tool_calls=calls)
        if response.stop_reason != "tool_use":
            text = "".join(b.text for b in response.content if b.type == "text")
            ans = _verify(text, session)
            ans.tool_calls, ans.model, ans.usage = calls, model, usage
            return ans

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            calls += 1
            try:
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": session.run(block.name, block.input)})
            except Exception as e:  # ошибка инструмента -> модель может переформулировать
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"Ошибка: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})

    return Answer(text="Не удалось собрать ответ за отведённое число шагов.", tool_calls=calls, model=model, usage=usage)
