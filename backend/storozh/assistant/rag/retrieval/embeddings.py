"""Эмбеддинги и reranker. Локально (CPU), без ключей. Модели грузятся лениво."""

from functools import lru_cache

from storozh.shared.config import settings

RERANK_MODEL = "BAAI/bge-reranker-v2-m3"


@lru_cache(maxsize=1)
def _encoder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model, device="cpu")


@lru_cache(maxsize=1)
def _reranker():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(RERANK_MODEL, device="cpu", max_length=512)


def _prefix(kind: str) -> str:
    # e5-модели обучены с префиксами query:/passage:, bge-m3 — без них
    return f"{kind}: " if "e5" in settings.embedding_model else ""


def embed(texts: list[str], show_progress: bool = False, kind: str = "passage") -> list[list[float]]:
    vecs = _encoder().encode(
        [_prefix(kind) + t for t in texts],
        batch_size=settings.embedding_batch,
        normalize_embeddings=True,
        show_progress_bar=show_progress,
    )
    return [v.tolist() for v in vecs]


def embed_query(text: str) -> list[float]:
    return embed([text], kind="query")[0]


def rerank(query: str, passages: list[str]) -> list[float]:
    if not passages:
        return []
    return [float(s) for s in _reranker().predict([(query, p) for p in passages], batch_size=8)]


# Чанк не должен быть длиннее окна модели: всё, что дальше, модель эмбеддингов просто не читает.
_PASSAGE_RESERVE = 16  # префикс «passage: » и служебные токены
_CHUNK_CAP = 1024  # у BGE-M3 окно 8192, но статья длиннее ~1000 токенов лучше делится на части


def count_tokens(text: str) -> int:
    """Сколько токенов займёт текст как passage (с префиксом модели, если он нужен)."""
    tok = _encoder().tokenizer
    return len(tok(_prefix("passage") + text, add_special_tokens=True)["input_ids"])


def chunk_token_budget() -> int:
    return min(_encoder().max_seq_length - _PASSAGE_RESERVE, _CHUNK_CAP)
