from storozh.assistant.rag.retrieval.chunking import chunk_article


def words(s: str) -> int:  # подставной счётчик: токен = слово
    return len(s.split())


def article(body: str, lang: str = "ru") -> dict:
    return {"id": 1, "lang": lang, "number": "31", "title": "Сроки", "path": ["Глава 4"], "doc_title": "О нотариате",
            "body": body}


def test_short_article_is_one_chunk():
    chunks = chunk_article(article("Первая часть.\nВторая часть."), count=words, budget=100)
    assert len(chunks) == 1 and chunks[0].part == 0
    assert chunks[0].content.startswith("О нотариате\nГлава 4\nСтатья 31. Сроки")


def test_long_article_split_by_paragraphs_within_budget():
    paras = [f"Часть {i} " + "слово " * 30 for i in range(1, 6)]
    chunks = chunk_article(article("\n".join(paras)), count=words, budget=80)
    assert len(chunks) > 1
    assert all(words(c.content) <= 80 for c in chunks)              # каждый кусок влезает в окно модели
    assert all("Статья 31. Сроки (ч." in c.content for c in chunks)  # заголовок в каждом куске
    joined = " ".join(c.content for c in chunks)
    assert all(p.split()[1] in joined for p in paras)               # ни одна часть не потерялась


def test_oversized_paragraph_split_by_sentences():
    para = " ".join(f"Предложение {i} " + "x " * 20 + "конец." for i in range(6))
    chunks = chunk_article(article(para, lang="uz"), count=words, budget=60)
    assert len(chunks) > 1 and all(words(c.content) <= 60 for c in chunks)
    assert "(1-qism)" in chunks[0].content
