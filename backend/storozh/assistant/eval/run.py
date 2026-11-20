"""Мини-eval поиска: recall@k и MRR по golden.jsonl. Запуск: uv run python -m storozh.assistant.eval.run [--rerank]"""

import json
import sys
import time
from pathlib import Path

from storozh.assistant.rag.retrieval.service import search


def main(rerank: bool = True, k: int = 5) -> None:
    rows = [json.loads(line) for line in Path(__file__).with_name("golden.jsonl").read_text().splitlines() if line]
    hit_k, mrr, t0 = 0, 0.0, time.time()
    for r in rows:
        expect = {tuple(e) for e in r["expect"]}
        got = [(h.code, h.number) for h in search(r["q"], k=k, rerank=rerank, expand=False)]
        rank = next((i + 1 for i, g in enumerate(got) if g in expect), None)
        hit_k += rank is not None
        mrr += 1 / rank if rank else 0
        print(f"{'✓' if rank else '✗'} {rank or '-'}  {r['q'][:60]:60}  top: {got[:3]}")
    n = len(rows)
    print(f"\nrecall@{k}: {hit_k / n:.2f}   MRR: {mrr / n:.2f}   ({(time.time() - t0) / n:.1f}s/запрос, rerank={rerank})")


if __name__ == "__main__":
    main(rerank="--rerank" in sys.argv)
