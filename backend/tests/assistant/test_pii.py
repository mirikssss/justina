from storozh.assistant.pii import contains_hard_pii, mask


def test_masks_identifiers_and_names():
    text = ("Доверитель Каримов Азиз Ахмедович, ПИНФЛ 31234567890123, паспорт AA 1234567, тел. +998 90 123-45-67, "
            "авто 01 A 123 BC. Поверенный Karimov A.A. Повторно: Каримов Азиз Ахмедович.")
    m = mask(text)
    for secret in ("31234567890123", "1234567", "123-45-67", "01 A 123 BC", "Каримов Азиз", "Karimov A.A"):
        assert secret not in m.text, secret
    assert m.text.count("[NAME_1]") == 2  # одно значение — одна метка
    assert "[PINFL_1]" in m.text and "[PASSPORT_1]" in m.text and "[PHONE_1]" in m.text and "[PLATE_1]" in m.text
    assert m.unmask(m.text) == text
    assert not contains_hard_pii(m.text)


def test_uzbek_names_and_known_parties():
    m = mask("Ishonch bildiruvchi Toshmatov Sardor Baxtiyor o'g'li va Dilnoza", names=["Dilnoza"])
    assert "Toshmatov" not in m.text and "Dilnoza" not in m.text


def test_keeps_legal_text():
    text = "Согласно статье 31 Закона «О нотариате» нотариус откладывает действие на 10 дней. Документ № 2026-114."
    assert mask(text).text == text
    assert contains_hard_pii("ПИНФЛ 31234567890123")
