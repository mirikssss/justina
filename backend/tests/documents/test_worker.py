from storozh.documents.worker import next_delay


def test_backoff_doubles_up_to_ten_minutes():
    assert [next_delay(20, n) for n in (1, 2, 3)] == [20, 40, 80]
    assert next_delay(20, 20) == 600


def test_jitter_within_three_seconds():
    assert all(17 <= next_delay(20, 0) <= 23 for _ in range(200))
