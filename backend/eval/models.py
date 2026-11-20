"""Сравнение моделей Claude на агенте /ask: качество ответа vs цена.

  uv run python -m eval.models run --models claude-haiku-5-5 --n 2       # калибровка цены
  uv run python -m eval.models run --budget 1.2                           # все модели, лимит $ на модель
  uv run python -m eval.models judge                                      # оценка ответов судьёй
  uv run python -m eval.models report

Результаты кэшируются в eval/results/<model>.jsonl — повторный запуск не платит дважды.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic
import typer

from app.core.config import settings
from app.modules.corpus.service import articles_by_keys
from app.modules.corpus.text import detect_lang
from app.modules.reasoning.service import answer

app = typer.Typer()
HERE = Path(__file__).parent
RESULTS = HERE / "results"
JUDGE_MODEL = "claude-opus-5-5"

# $ за 1M токенов: input, output, cache read, cache write (5-мин кэш = 1.25 × input)
PRICES = {
    "claude-opus-5-5": (4.0, 20.0, 0.20, 5.0),
    "claude-sonnet-5-5": (2.0, 10.0, 0.10, 2.5),
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
    "claude-opus-4-7": (5.0, 25.0, 0.50, 6.25),
    "claude-sonnet-4-6": (3.0, 15.0, 0.30, 3.75),
}
DEFAULT_MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5", "claude-sonnet-4-6", "claude-opus-4-7"]


def cost(model: str, u: dict) -> float:
    pi, po, pr, pw = PRICES[model]
    return (u.get("input", 0) * pi + u.get("output", 0) * po + u.get("cache_read", 0) * pr
            + u.get("cache_write", 0) * pw) / 1e6


def golden() -> list[dict]:
    return [json.loads(x) for x in (HERE / "golden.jsonl").read_text().splitlines() if x]


def load(model: str) -> dict[str, dict]:
    path = RESULTS / f"{model}.jsonl"
    if not path.exists():
        return {}
    return {r["q"]: r for r in map(json.loads, path.read_text().splitlines()) if r}


def save(model: str, rows: dict[str, dict]) -> None:
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{model}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows.values()))


def _one(model: str, effort: str, g: dict) -> dict:
    t0 = time.time()
    a = answer(g["q"], model=model, effort=effort)
    expect = {tuple(e) for e in g["expect"]}
    cited = [(c.code, c.number) for c in a.citations]
    return {
        "q": g["q"], "expect": g["expect"], "model": model, "effort": effort,
        "answer": a.text, "cited": cited, "unverified": a.unverified,
        "cite_hit": any(c in expect for c in cited),
        "lang_ok": detect_lang(a.text) == detect_lang(g["q"]),
        "tool_calls": a.tool_calls, "usage": a.usage, "cost": cost(model, a.usage),
        "latency": round(time.time() - t0, 1),
    }


@app.command()
def run(models: list[str] = typer.Option(DEFAULT_MODELS), n: int = 100, effort: str = "medium",
        budget: float = 1.2, workers: int = 3):
    """Прогнать агента. budget — потолок $ на одну модель (останавливается, когда превышен)."""
    qs = golden()[:n]
    from app.modules.retrieval.service import search
    search("прогрев модели эмбеддингов")  # загрузить модель до запуска потоков
    for model in models:
        rows = load(model)
        todo = [g for g in qs if g["q"] not in rows]
        spent = sum(r["cost"] for r in rows.values())
        print(f"\n== {model}: готово {len(rows)}, осталось {len(todo)}, потрачено ${spent:.3f}")
        with ThreadPoolExecutor(workers) as pool:
            for i in range(0, len(todo), workers):
                if spent >= budget:
                    print(f"   стоп: бюджет ${budget} исчерпан")
                    break
                for r in pool.map(lambda g: _one(model, effort, g), todo[i:i + workers]):
                    rows[r["q"]] = r
                    spent += r["cost"]
                    print(f"   {'✓' if r['cite_hit'] else '✗'} ${r['cost']:.4f} {r['latency']:5.1f}s "
                          f"tools={r['tool_calls']} {r['q'][:50]}")
                save(model, rows)
        print(f"   итого ${spent:.3f}")


JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "correct": {"type": "integer", "description": "0 — ошибка по существу, 1 — частично, 2 — верно"},
        "complete": {"type": "integer", "description": "0 — не отвечает на вопрос, 1 — неполно, 2 — полно (суть + что делать)"},
        "clear": {"type": "integer", "description": "0 — непонятно, 1 — сносно, 2 — понятно простому человеку"},
        "comment": {"type": "string"},
    },
    "required": ["correct", "complete", "clear", "comment"],
    "additionalProperties": False,
}

JUDGE_PROMPT = """Ты проверяешь ответ юридического помощника гражданам Узбекистана.

Вопрос: {q}

Эталонные статьи закона (ответ может опираться и на другие статьи, если они уместны):
{refs}

Ответ помощника:
<answer>
{answer}
</answer>

Оцени ответ по шкалам correct, complete, clear (0–2) и кратко объясни в comment (1–2 предложения, по-русски).
Ссылки вида [[gk1:150]] — нормальный формат цитирования, не снижай за них."""


@app.command()
def judge(models: list[str] = typer.Option(DEFAULT_MODELS)):
    """Оценить сохранённые ответы судьёй (Claude Opus 5.5, effort low)."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    total = 0.0

    def grade(r: dict) -> dict:
        keys = [tuple(e) for e in r["expect"]]
        lang = detect_lang(r["q"])
        arts = articles_by_keys(keys)
        refs = "\n\n".join(f"[[{a['code']}:{a['number']}]] {a['title']}\n{a['body'][:2000]}"
                           for a in arts if a["lang"] == lang) or "(нет)"
        resp = client.messages.create(
            model=JUDGE_MODEL, max_tokens=4000,
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
            messages=[{"role": "user", "content": JUDGE_PROMPT.format(q=r["q"], refs=refs, answer=r["answer"])}],
        )
        if resp.stop_reason == "refusal":
            return {"error": "refusal", "cost": 0.0}
        u = {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens}
        out = json.loads(next(b.text for b in resp.content if b.type == "text"))
        out["cost"] = cost(JUDGE_MODEL, u)
        return out

    for model in models:
        rows = load(model)
        todo = [r for r in rows.values() if "judge" not in r]
        with ThreadPoolExecutor(4) as pool:
            for r, j in zip(todo, pool.map(grade, todo)):
                r["judge"] = j
                total += j.get("cost", 0)
        save(model, rows)
        print(f"{model}: оценено {len(todo)}")
    print(f"судья потратил ${total:.3f}")


@app.command()
def report():
    print(f"{'модель':20} {'n':>3} {'качество':>8} {'верно':>6} {'цит.ok':>6} {'выдум':>5} {'язык':>5} "
          f"{'$/вопр':>7} {'сек':>5} {'шаги':>4}")
    for model in DEFAULT_MODELS:
        rows = list(load(model).values())
        if not rows:
            continue
        n = len(rows)
        judged = [r["judge"] for r in rows if "judge" in r and "correct" in r["judge"]]
        quality = sum(j["correct"] + j["complete"] + j["clear"] for j in judged) / (6 * len(judged)) if judged else 0
        correct = sum(j["correct"] == 2 for j in judged) / len(judged) if judged else 0
        print(f"{model:20} {n:>3} {quality:>8.0%} {correct:>6.0%} {sum(r['cite_hit'] for r in rows) / n:>6.0%} "
              f"{sum(len(r['unverified']) for r in rows):>5} {sum(r['lang_ok'] for r in rows) / n:>5.0%} "
              f"{sum(r['cost'] for r in rows) / n:>7.4f} {sum(r['latency'] for r in rows) / n:>5.1f} "
              f"{sum(r['tool_calls'] for r in rows) / n:>4.1f}")
    print("\nкачество = (correct+complete+clear)/6 по судье; верно = доля correct=2; "
          "цит.ok = процитирована эталонная статья; выдум = вырезанных ссылок")


if __name__ == "__main__":
    app()
