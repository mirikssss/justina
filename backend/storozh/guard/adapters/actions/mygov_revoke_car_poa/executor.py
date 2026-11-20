"""Аннулирование e-доверенности на авто в my.gov.uz (Playwright).

После execute: documents.public.request_refresh и ожидание document.status_changed -> revoked (до 120 с).
Повтор допускается только до шага отправки формы.
"""

from storozh.documents.public import BrowserSession
from storozh.guard.ports import ActionRequest, ActionResult


class RevokeCarPoaExecutor:
    action_type = "revoke_car_poa"

    async def execute(self, req: ActionRequest, session: BrowserSession) -> ActionResult:
        raise NotImplementedError("revoke_car_poa: Разработчик 2")
