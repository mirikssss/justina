"""Набор проверки поиска (FR-A-10): доля попаданий ожидаемой статьи в top-k и MRR.

    make eval                                        # = uv run python -m storozh.assistant.eval.run
    uv run python -m storozh.assistant.eval.run --rerank
"""

import sys
import time
from pathlib import Path

import yaml

from storozh.assistant.rag.retrieval.service import search

QUESTIONS = Path(__file__).with_name("questions.yaml")


def load() -> list[dict]:
    return yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))


def main(rerank: bool = False, k: int = 8) -> float:
    rows = load()
    hit_k, mrr, t0 = 0, 0.0, time.time()
    for r in rows:
        expect = {tuple(map(str, e)) for e in r["expect"]}
        got = [(h.code, h.number) for h in search(r["q"], k=k, rerank=rerank, expand=False)]
        rank = next((i + 1 for i, g in enumerate(got) if g in expect), None)
        hit_k += rank is not None
        mrr += 1 / rank if rank else 0
        print(f"{'✓' if rank else '✗'} {rank or '-'}  {r['q'][:62]:62}  top: {got[:3]}")
    n = len(rows)
    share = hit_k / n
    print(f"\nдоля попаданий (top-{k}): {hit_k}/{n} = {share:.0%}   MRR: {mrr / n:.2f}   "
          f"({(time.time() - t0) / n:.1f} с/вопрос, rerank={rerank})")
    return share


if __name__ == "__main__":
    main(rerank="--rerank" in sys.argv)
