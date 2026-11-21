"""Набор проверки поиска (FR-A-10): доля попаданий ожидаемой статьи в top-k и MRR.

    make eval                                        # = uv run python -m storozh.assistant.eval.run
    uv run python -m storozh.assistant.eval.run --rerank
    uv run python -m storozh.assistant.eval.run --lang uz    # T10: только узбекские вопросы

T10: итог считается отдельно по uz и ru — средняя цифра прячет провал на одном языке.
"""

import sys
import time
from pathlib import Path

import yaml

from storozh.assistant.rag.retrieval.service import search

QUESTIONS = Path(__file__).with_name("questions.yaml")


def load() -> list[dict]:
    return yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))


def main(rerank: bool = False, k: int = 8, lang: str | None = None) -> float:
    rows = [r for r in load() if lang is None or r.get("lang") == lang]
    if not rows:
        print(f"нет вопросов для lang={lang}")
        return 0.0
    hit_k, mrr, t0 = 0, 0.0, time.time()
    by_lang: dict[str, list[int]] = {}  # lang -> [вопросов, попаданий]
    for r in rows:
        expect = {tuple(map(str, e)) for e in r["expect"]}
        got = [(h.code, h.number) for h in search(r["q"], k=k, rerank=rerank, expand=False)]
        rank = next((i + 1 for i, g in enumerate(got) if g in expect), None)
        hit_k += rank is not None
        mrr += 1 / rank if rank else 0
        stat = by_lang.setdefault(r.get("lang", "?"), [0, 0])
        stat[0] += 1
        stat[1] += rank is not None
        print(f"{'✓' if rank else '✗'} {rank or '-'}  {r['q'][:62]:62}  top: {got[:3]}")
    n = len(rows)
    share = hit_k / n
    print(f"\nдоля попаданий (top-{k}): {hit_k}/{n} = {share:.0%}   MRR: {mrr / n:.2f}   "
          f"({(time.time() - t0) / n:.1f} с/вопрос, rerank={rerank})")
    for lg, (total, hits) in sorted(by_lang.items()):
        print(f"  {lg}: {hits}/{total} = {hits / total:.0%}")
    return share


if __name__ == "__main__":
    args = sys.argv[1:]
    lang = args[args.index("--lang") + 1] if "--lang" in args else None
    main(rerank="--rerank" in args, lang=lang)
