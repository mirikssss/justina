import pytest

from storozh.shared import uri


def test_roundtrip():
    s = uri.build("notarius", "poa", "2026-0001234")
    assert s == "uz:notarius:poa:2026-0001234"
    assert str(uri.parse(s)) == s


@pytest.mark.parametrize("bad", ["", "uz:notarius:poa:", "ru:notarius:poa:1", "uz:unknown:poa:1", "uz:notarius:xxx:1"])
def test_rejects(bad: str):
    with pytest.raises(ValueError):
        uri.parse(bad)
