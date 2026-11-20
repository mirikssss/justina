"""vakolat.check — Статус известных доверенностей по номеру в публичном реестре — второй источник правды."""

from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared.contracts import NormalizedDocument


class VakolatAdapter:
    source_id = "vakolat.check"
    title = "Vakolat.uz · проверка доверенностей"
    poll_interval_s = 300
    complete = False

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        raise NotImplementedError("vakolat.check.fetch: Разработчик 1")

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        raise NotImplementedError("vakolat.check.normalize: Разработчик 1")
