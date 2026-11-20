"""mygov.notarial_history — История нотариальных действий по году; арифметическая капча."""

from storozh.documents.ports import BrowserSession, RawRecord
from storozh.shared.contracts import NormalizedDocument


class MyGovNotarialAdapter:
    source_id = "mygov.notarial_history"
    title = "my.gov.uz · история нотариальных действий"
    poll_interval_s = 600
    complete = True

    async def fetch(self, session: BrowserSession) -> list[RawRecord]:
        raise NotImplementedError("mygov.notarial_history.fetch: Разработчик 1")

    def normalize(self, raw: RawRecord) -> NormalizedDocument:
        raise NotImplementedError("mygov.notarial_history.normalize: Разработчик 1")
