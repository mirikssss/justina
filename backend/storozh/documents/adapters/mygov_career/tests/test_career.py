from pathlib import Path

from storozh.documents.adapters.mygov_career.adapter import MyGovCareerAdapter, parse_list

HTML = (Path(__file__).parent / "fixtures" / "career.html").read_text(encoding="utf-8")


def test_parse_rows():
    recs = parse_list(HTML)
    assert len(recs) == 3 and len({r.external_id for r in recs}) == 3
    assert recs[0].data["ended"] == "До сих пор" and recs[2].data["position"] == "Стажер"


def test_ongoing_is_active_and_ended_is_completed():
    docs = [MyGovCareerAdapter().normalize(r) for r in parse_list(HTML)]
    assert docs[0].status == "active" and docs[0].valid_until is None
    assert docs[1].status == "completed" and docs[1].valid_until.isoformat() == "2026-09-27"
    assert docs[0].kind == "labor_contract" and docs[0].owner_role == "employee"
    assert docs[0].uri.startswith("uz:mehnat:contract:") and docs[0].issued_at.isoformat() == "2026-09-28"
    assert docs[0].parties[1].role == "employer"


def test_ending_a_job_keeps_uri_and_flips_status():
    ended = HTML.replace("<td>До сих пор</td>", "<td>2026-11-20</td>")
    before, after = parse_list(HTML)[0], parse_list(ended)[0]
    a = MyGovCareerAdapter()
    assert before.external_id == after.external_id
    assert a.normalize(before).status == "active" and a.normalize(after).status == "completed"
