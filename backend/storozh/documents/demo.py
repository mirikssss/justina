"""Демо-данные для разработки фронта и правил без живого кабинета: python -m storozh documents seed.

Идут через тот же ingest_snapshot, что и живые снимки, поэтому события document.* настоящие.
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from storozh.shared.contracts import NormalizedDocument, SourceSnapshot

POA_NUMBER = "2026-0001234"


def _poa(status: str) -> NormalizedDocument:
    today = date.today()
    return NormalizedDocument.model_validate({
        "uri": f"uz:notarius:poa:{POA_NUMBER}", "kind": "poa_car", "source": "mygov.car_poa",
        "title": "Avtomobilni boshqarish uchun e-ishonchnoma", "status": status, "owner_role": "principal",
        "parties": [{"role": "principal", "name_masked": "Вы"}, {"role": "agent", "name_masked": "Б***р К."}],
        "object": {"type": "vehicle", "id_masked": "01 *** BC", "label": "Chevrolet Cobalt"},
        "issued_at": today.isoformat(), "valid_until": (today + timedelta(days=30)).isoformat(),
        "issuer": {"type": "mygov", "name": "my.gov.uz"}, "fields": {"number_masked": "2026-****234"},
        "source_ref": {"external_id": POA_NUMBER},
    })


def _notarial() -> list[NormalizedDocument]:
    base = {"source": "mygov.notarial_history", "issuer": {"type": "notary", "name": "Toshkent sh., Yunusobod tumani notariusi"}}
    return [NormalizedDocument.model_validate({**base, **d}) for d in [
        {"uri": "uz:notarius:act:2025-0457812", "kind": "notarial_act", "title": "Kvartira oldi-sotdi shartnomasi",
         "status": "completed", "owner_role": "party", "issued_at": "2025-03-14",
         "parties": [{"role": "party", "name_masked": "Вы"}, {"role": "seller", "name_masked": "Д***р Р."}],
         "object": {"type": "real_estate", "id_masked": "10:05:***:17", "label": "Kvartira, Yunusobod"},
         "fields": {"number_masked": "2025-****812"}, "source_ref": {"external_id": "2025-0457812"}},
        {"uri": "uz:notarius:poa:2024-0119305", "kind": "poa_notarial", "title": "Notarial ishonchnoma",
         "status": "expired", "owner_role": "agent", "issued_at": "2024-06-02", "valid_until": "2025-06-02",
         "parties": [{"role": "principal", "name_masked": "Н***а А."}, {"role": "agent", "name_masked": "Вы"}],
         "fields": {"number_masked": "2024-****305"}, "source_ref": {"external_id": "2024-0119305"}},
    ]]


def snapshots(citizen_id: UUID, step: str) -> list[SourceSnapshot]:
    """step: base — история + активная доверенность; new_poa — только история (затем добавится доверенность);
    revoke — доверенность отозвана."""
    now = datetime.now(UTC)

    def snap(source: str, docs: list[NormalizedDocument]) -> SourceSnapshot:
        return SourceSnapshot(snapshot_id=uuid.uuid4(), citizen_id=citizen_id, source=source, fetched_at=now,
                              complete=True, documents=docs)

    out = [snap("mygov.notarial_history", _notarial())]
    if step in ("base", "poa"):
        out.append(snap("mygov.car_poa", [_poa("active")]))
    elif step == "revoke":
        out.append(snap("mygov.car_poa", [_poa("revoked")]))
    return out
