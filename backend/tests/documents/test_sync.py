import uuid

from storozh.documents.demo import _poa
from storozh.documents.sync import build_snapshots


def test_snapshots_grouped_per_source_incomplete_and_for_remote_citizen():
    poa = _poa("active").model_dump(mode="json")
    other = {**poa, "uri": "uz:notarius:poa:2026-0000002", "source": "mygov.requests"}
    rows = [{"source": "mygov.car_poa", "payload": poa}, {"source": "mygov.requests", "payload": other}]
    remote = uuid.uuid4()
    snaps = build_snapshots(rows, remote)
    assert {s.source for s in snaps} == {"mygov.car_poa", "mygov.requests"}
    assert all(s.citizen_id == remote and s.complete is False and s.raw == {} for s in snaps)
    assert sum(len(s.documents) for s in snaps) == 2
