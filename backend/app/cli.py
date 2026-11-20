import json
import logging

import typer

app = typer.Typer(no_args_is_help=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@app.command()
def ingest(codes: list[str] = typer.Argument(None), refresh: bool = False):
    """Скачать и разобрать акты с lex.uz (по умолчанию все из sources.py)."""
    from app.modules.corpus import service

    print(json.dumps(service.ingest(codes or None, refresh=refresh), ensure_ascii=False, indent=1))


@app.command()
def index(codes: list[str] = typer.Argument(None), skip_embeddings: bool = False):
    """Нарезать статьи на чанки, посчитать tsvector и эмбеддинги."""
    from app.modules.retrieval import service

    print(service.reindex(codes or None, embeddings=not skip_embeddings))


@app.command()
def search(query: str, k: int = 8, rerank: bool = False):
    """Гибридный поиск по корпусу."""
    from app.modules.retrieval import service

    for h in service.search(query, k=k, rerank=rerank):
        print(f"[{h.score:.3f}] {h.code} ст.{h.number} {h.title}  ({', '.join(h.via)})\n    {h.url}")


@app.command()
def ask(question: str):
    """Ответ с цитатами (агент на Claude)."""
    from app.modules.reasoning import service

    ans = service.answer(question)
    print(ans.text)
    for c in ans.citations:
        print(f"  - {c.code} ст.{c.number}: {c.url}")


if __name__ == "__main__":
    app()
