"""Маскирование персональных данных до отправки в модель."""

from storozh.assistant.pii.scrub import Masked, mask

__all__ = ["Masked", "mask"]
