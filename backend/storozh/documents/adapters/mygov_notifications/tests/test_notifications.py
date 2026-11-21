from pathlib import Path

from storozh.documents.adapters.mygov_notifications.adapter import MyGovNotificationsAdapter, parse_list

HTML = (Path(__file__).parent / "fixtures" / "notifications.html").read_text(encoding="utf-8")


def test_parse_skips_login_events_and_keeps_titles():
    recs = parse_list(HTML)
    assert [r.data["title"] for r in recs] == [
        "На ваше имя зарегистрировано международное курьерское отправление", "Лист временной нетрудоспособности"]
    assert recs[0].data["time"] == "2026-11-20 09:15:30"


def test_normalize_drops_body_text_and_names():
    adapter = MyGovNotificationsAdapter()
    docs = [adapter.normalize(r) for r in parse_list(HTML)]
    assert docs[1].kind == "notification" and docs[1].issued_at.isoformat() == "2026-11-19"
    assert docs[0].uri.startswith("uz:mygov:notice:") and docs[0].uri != docs[1].uri
    assert "Иванов" not in "".join(d.model_dump_json() for d in docs)


def test_same_notification_same_uri():
    a, b = parse_list(HTML), parse_list(HTML)
    assert [r.external_id for r in a] == [r.external_id for r in b]
