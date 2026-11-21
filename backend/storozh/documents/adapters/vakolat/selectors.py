"""Адреса и разбор публичного реестра Vakolat (NFR-D-07: всё, что может поменяться, — здесь).

Снято с живого https://vakolat.adliya.uz/search (21.11.2026):
- Страница — SPA; проверка идёт публичным JSON-запросом без подписи, куки и капчи:
  GET https://api-vakolat.adliya.uz/v1/front/mandate/number/{номер}
- Несуществующий номер: HTTP 422, {"status": {"code": "2013", "message": "Vakolat topilmadi"}, "error": {...}}.
- ФОРМАТ УСПЕШНОГО ОТВЕТА НЕ СНЯТ: не было ни одного настоящего номера. STATUS_KEYS и разбор в adapter.py — предположение,
  его надо сверить на живом ответе и поправить здесь.
- Неизвестно: совпадает ли «номер вакольата» с номером заявки на my.gov.uz; есть ли лимит частоты запросов.
"""

API_URL = "https://api-vakolat.adliya.uz/v1/front/mandate/number/{number}"
NOT_FOUND_CODE = "2013"
STATUS_KEYS = ("status", "state", "mandateStatus", "statusName")  # предположение, не проверено на живом ответе
