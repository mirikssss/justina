"""mygov.car_poa — Электронные доверенности на авто, выданные человеком и ему."""

from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared.contracts import NormalizedDocument


class MyGovCarPoaAdapter:
    source_id = "mygov.car_poa"
    poll_interval_s = 20
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        raise NotImplementedError("mygov.car_poa.fetch: Разработчик 1")

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        raise NotImplementedError("mygov.car_poa.normalize: Разработчик 1")
