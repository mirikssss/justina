"""Маскирование персональных данных до отправки в модель. Метки обратимы только на нашей стороне."""

from dataclasses import dataclass, field


@dataclass
class Masked:
    text: str
    mapping: dict[str, str] = field(default_factory=dict)  # метка -> исходное значение


def mask(text: str) -> Masked:
    """ПИНФЛ (14 цифр), паспорт, телефон +998, госномер, ФИО -> <PINFL_1>, <PHONE_1>, ..."""
    raise NotImplementedError("assistant.pii.mask: Разработчик 3")
