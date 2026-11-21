from storozh.assistant.rag.corpus.parser import parse_bilingual
from storozh.assistant.rag.corpus.text import detect_lang, to_uz_latin, uz_terms
from storozh.assistant.rag.retrieval.query import parse

PAGE = """<html><body>
<div class="lang1"><div id="divCont">
 <div class="ACT_TITLE"><div id="1">ГРАЖДАНСКИЙ КОДЕКС</div></div>
 <div class="TEXT_HEADER_DEFAULT"><div id="2">РАЗДЕЛ I<br/>ОБЩИЕ ПОЛОЖЕНИЯ</div></div>
 <div class="TEXT_HEADER_DEFAULT"><div id="3">ГЛАВА 1<br/>ЗАКОНОДАТЕЛЬСТВО</div></div>
 <div class="CLAUSE_DEFAULT"><div id="10"><strong>Статья 12<sup>1</sup>. Название</strong></div></div>
 <div class="ACT_TEXT"><div id="11">Текст со <a href="/ru/docs/111181#10">ссылкой</a>.</div></div>
 <div class="CHANGES_ORIGINS"><label></label><div id="12">(в редакции Закона)</div></div>
</div></div>
<div class="lang2"><div id="divCont">
 <div class="TEXT_HEADER_DEFAULT"><div id="-2">I BOʻLIM<br/>UMUMIY QOIDALAR</div></div>
 <div class="CLAUSE_DEFAULT"><div id="-10">12<sup>1</sup>-modda. Nomi</div></div>
 <div class="ACT_TEXT"><div id="-11">Matn <a href="/ru/docs/-111189#-10">havola</a>.</div></div>
</div></div></body></html>"""


def test_parse_bilingual():
    docs = parse_bilingual(PAGE, 111181)
    ru, uz = docs["ru"], docs["uz"]
    a = ru.articles[0]
    assert (a.number, a.title) == ("12-1", "Название")
    assert a.path == ["РАЗДЕЛ I. ОБЩИЕ ПОЛОЖЕНИЯ", "ГЛАВА 1. ЗАКОНОДАТЕЛЬСТВО"]
    assert a.refs[0].lex_id == 111181 and a.refs[0].elem_id == 10
    assert a.amendments == ["(в редакции Закона)"]
    assert uz.articles[0].number == "12-1"
    assert uz.lex_id == -111189


def test_text_utils():
    assert detect_lang("Сколько дней отпуска?") == "ru"
    assert detect_lang("Меҳнат таътили қанча?") == "uz"
    assert detect_lang("Mehnat ta'tili qancha?") == "uz"
    assert to_uz_latin("ўғил") == "o'g'il"
    assert uz_terms("shartnomaning") == ["shartn"]


def test_exact_ref():
    assert parse("статья 150 ГК").exact_keys == [("gk1", "150"), ("gk2", "150")]
    assert parse("31-modda notariat to'g'risida").exact_keys == [("notary", "31")]
    assert parse("статья 31 закона о нотариате").exact_keys == [("notary", "31")]


ITEMS_PAGE = """<html><body><div class="lang2"><div id="divCont">
 <div class="ACT_TITLE"><div id="1">Reglamentni tasdiqlash toʻgʻrisida</div></div>
 <div class="ACT_TEXT"><div id="2">1. Reglament tasdiqlansin.</div></div>
 <div class="APPL_BANNER_LANDSCAPE_TITLE"><div id="3">Vazirlar Mahkamasining 726-son qaroriga 4-ILOVA</div></div>
 <div class="ACT_TITLE_APPL"><div id="4">Ishonchnomalarni tasdiqlashning</div></div>
 <div class="ACT_FORM"><div id="5">MAʼMURIY REGLAMENTI</div></div>
 <div class="TEXT_HEADER_DEFAULT"><div id="6">1-bob. Umumiy qoidalar</div></div>
 <div class="ACT_TEXT"><div id="7">19. Ishonchli vakilning ishtiroki talab etilmaydi.</div></div>
 <div class="ACT_TEXT"><div id="8">Davomi.</div></div>
 <div class="APPL_BANNER_LANDSCAPE_TITLE"><div id="9">Ishonchnomalarni tasdiqlash reglamentiga ILOVA</div></div>
 <div class="ACT_TEXT"><div id="10">1. Sxema bandi — tashlab yuboriladi.</div></div>
</div></div></body></html>"""


def test_parse_items_with_appendices():
    doc = parse_bilingual(ITEMS_PAGE, 5118081)["uz"]
    assert [a.number for a in doc.articles] == ["1", "4-19"]
    item = doc.articles[1]
    assert item.path == ["Ishonchnomalarni tasdiqlashning maʼmuriy reglamenti", "1-bob. Umumiy qoidalar"]
    assert item.body.endswith("Davomi.")


def test_article_label():
    from storozh.assistant.rag.corpus.sources import BY_CODE

    assert BY_CODE["reg726"].article_label("4-19") == "п. 19 прил. 4"
    assert BY_CODE["notary"].article_label("31", "uz") == "31-modda"
