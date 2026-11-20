import pytest

from storozh.documents.adapters.mygov_notarial.captcha import solve_text


@pytest.mark.parametrize(("expr", "want"), [("3 + 4", 7), ("12-5=", 7), ("6 x 7 = ?", 42)])
def test_solve_text(expr: str, want: int):
    assert solve_text(expr) == want
