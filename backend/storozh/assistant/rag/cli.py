"""storozh rag ...: корпус lex.uz, индекс, поиск, вопрос агенту."""

import json

import typer

app = typer.Typer(no_args_is_help=True, help="RAG по lex.uz: ingest, index, search, ask")


@app.command()
def ingest(codes: list[str] = typer.Argument(None), refresh: bool = False):
    """Скачать и разобрать акты с lex.uz (по умолчанию все из sources.py)."""
    from storozh.assistant.rag.corpus import service

    print(json.dumps(service.ingest(codes or None, refresh=refresh), ensure_ascii=False, indent=1))


@app.command()
def index(codes: list[str] = typer.Argument(None), skip_embeddings: bool = False):
    """Нарезать статьи на чанки, посчитать tsvector и эмбеддинги."""
    from storozh.assistant.rag.retrieval import service

    print(service.reindex(codes or None, embeddings=not skip_embeddings))


@app.command()
def ensure(force: bool = typer.Option(False, help="перезагрузить корпус и индекс, даже если ничего не менялось")):
    """Автоиндексация при деплое: догрузить корпус и пересчитать индекс, только если изменился код или модель."""
    from storozh.assistant.rag.ensure import ensure as run

    print(json.dumps(run(force=force), ensure_ascii=False, indent=1, default=str))


@app.command()
def search(query: str, k: int = 8, rerank: bool = False):
    """Гибридный поиск по корпусу."""
    from storozh.assistant.rag.retrieval import service

    for h in service.search(query, k=k, rerank=rerank):
        print(f"[{h.score:.3f}] {h.code} ст.{h.number} {h.title}  ({', '.join(h.via)})\n    {h.url}")


@app.command()
def ask(question: str):
    """Ответ с цитатами (агент на Claude)."""
    from storozh.assistant.llm import service

    ans = service.answer(question)
    print(ans.text)
    for c in ans.citations:
        print(f"  - {c.code} ст.{c.number}: {c.url}")

