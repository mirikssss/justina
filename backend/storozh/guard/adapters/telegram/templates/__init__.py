"""Тексты бота по языкам. Набор ключей у uz и ru одинаковый (проверяет тест)."""

from types import ModuleType

from storozh.guard.adapters.telegram.templates import ru, uz

LANGS: dict[str, ModuleType] = {"uz": uz, "ru": ru}


def texts(lang: str | None) -> ModuleType:
    return LANGS.get(lang or "uz", uz)
