"""Гибридный поиск: точные ссылки + полнотекст + вектора -> RRF -> cross-encoder rerank -> граф ссылок."""

from collections import defaultdict
from dataclasses import dataclass, field

from storozh.assistant.rag.corpus import service as corpus
from storozh.assistant.rag.db import connection
from storozh.assistant.rag.retrieval import embeddings
from storozh.assistant.rag.retrieval.query import ParsedQuery, parse
from storozh.shared.config import settings

RRF_K = 60
# Вес каждого сигнала в RRF (подобрано на eval/golden.jsonl)
RRF_WEIGHTS = {"dense": 1.0, "lexical": 0.5}
# Полнотекст шумный на бытовых формулировках: доверяем только его верхушке
RRF_DEPTH = {"lexical": 3}
CANDIDATES = 50
RERANK_TOP = 24

Key = tuple[str, str]  # (code, number) — статья независимо от языка


@dataclass
class Hit:
    code: str
    number: str
    title: str
    lang: str
    text: str
    url: str
    article_id: int
    path: list[str]
    act_id: int = 0  # id акта на lex.uz (языковой версии)
    score: float = 0.0
    via: set[str] = field(default_factory=set)
    related: list["Hit"] = field(default_factory=list)

    @property
    def act_title(self) -> str:
        src = corpus.BY_CODE[self.code]
        return src.name_uz if self.lang == "uz" else src.name_ru

    @property
    def article(self) -> str:
        """Подпись для ссылки: «ст. 31», «п. 16 прил. 4» (FR-A-02)."""
        return corpus.BY_CODE[self.code].article_label(self.number, self.lang)


def _lexical(pq: ParsedQuery) -> list[Key]:
    tq = pq.tsquery
    if not tq:
        return []
    cfg, q = tq
    with connection() as conn:
        rows = conn.execute(
            f"""SELECT a.code, a.number, ts_rank_cd(c.tsv, q) AS r
                FROM chunks c JOIN articles a ON a.id = c.article_id,
                     to_tsquery(%s::regconfig, %s) q
                WHERE c.lang = %s AND c.tsv @@ q {'AND a.code = ANY(%s)' if pq.codes else ''}
                ORDER BY r DESC LIMIT %s""",
            [cfg, q, pq.lang] + ([pq.codes] if pq.codes else []) + [CANDIDATES],
        ).fetchall()
    return [(r["code"], r["number"]) for r in rows]


def _dense(pq: ParsedQuery) -> list[Key]:
    vec = embeddings.embed_query(pq.text)
    with connection() as conn:
        conn.execute("SET LOCAL hnsw.ef_search = 100")
        rows = conn.execute(
            f"""SELECT a.code, a.number FROM chunks c JOIN articles a ON a.id = c.article_id
                WHERE c.embedding IS NOT NULL {'AND a.code = ANY(%s)' if pq.codes else ''}
                ORDER BY c.embedding <=> %s::vector LIMIT %s""",
            ([pq.codes] if pq.codes else []) + [vec, CANDIDATES],
        ).fetchall()
    return [(r["code"], r["number"]) for r in rows]


def _rrf(rankings: dict[str, list[Key]]) -> tuple[dict[Key, float], dict[Key, set[str]]]:
    scores: dict[Key, float] = defaultdict(float)
    via: dict[Key, set[str]] = defaultdict(set)
    for name, keys in rankings.items():
        seen = set()
        for rank, key in enumerate(keys):
            if key in seen:  # несколько чанков одной статьи — считаем лучший
                continue
            seen.add(key)
            if len(seen) > RRF_DEPTH.get(name, len(keys)):
                break
            scores[key] += RRF_WEIGHTS.get(name, 1.0) / (RRF_K + rank + 1)
            via[key].add(name)
    return scores, via


def _pick_lang(rows: list[dict], lang: str) -> dict[Key, dict]:
    """Для каждой статьи берём версию на языке запроса (иначе любую)."""
    out: dict[Key, dict] = {}
    for r in rows:
        k = (r["code"], r["number"])
        if k not in out or r["lang"] == lang:
            out[k] = r
    return out


def _to_hit(a: dict, score: float = 0.0, via: set[str] | None = None) -> Hit:
    return Hit(
        code=a["code"], number=a["number"], title=a["title"], lang=a["lang"], text=a["body"],
        url=corpus.article_url(a), article_id=a["id"], path=a["path"], act_id=a["lex_id"], score=score,
        via=via or set(),
    )


def search(query: str, k: int = 8, rerank: bool | None = None, expand: bool = True, codes: list[str] | None = None,
           kinds: list | None = None) -> list[Hit]:
    """codes — явные акты; kinds — типы документа (FR-A-03), из них выводятся акты."""
    pq = parse(query)
    codes = codes or corpus.codes_for_kinds(kinds)
    if codes:
        pq.codes = codes
    if rerank is None:
        rerank = settings.rerank_enabled
    rankings = {"lexical": _lexical(pq), "dense": _dense(pq)}
    scores, via = _rrf(rankings)

    for key in pq.exact_keys:  # точное попадание всегда наверху
        scores[key] = scores.get(key, 0) + 10.0
        via[key].add("exact")

    ranked = sorted(scores, key=scores.get, reverse=True)[: RERANK_TOP if rerank else k]
    arts = _pick_lang(corpus.articles_by_keys(ranked), pq.lang)
    ranked = [key for key in ranked if key in arts]

    if rerank and ranked:
        passages = [f"{arts[key]['title']}\n{arts[key]['body'][:1500]}" for key in ranked]
        rr = embeddings.rerank(query, passages)
        for key, s in zip(ranked, rr):
            scores[key] = s + (10.0 if "exact" in via[key] else 0.0)
        ranked.sort(key=scores.get, reverse=True)

    hits = [_to_hit(arts[key], scores[key], via[key]) for key in ranked[:k]]

    if expand and hits:
        by_src = defaultdict(list)
        for r in corpus.referenced_articles([h.article_id for h in hits]):
            by_src[r["src_article_id"]].append(r)
        for h in hits:
            h.related = [_to_hit(r, via={"ref"}) for r in by_src.get(h.article_id, [])][:5]
    return hits
