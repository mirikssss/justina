from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from storozh.guard.domain.actions import (
    MAX_ATTEMPTS,
    Confirm,
    can_transition,
    code_matches,
    hash_code,
    judge_confirm,
    new_code,
)
from storozh.guard.domain.actions import ActionStatus as S

NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)
LATER = NOW + timedelta(minutes=2)
KEY = b"k" * 32


def test_forward_only():
    assert can_transition(S.proposed, S.awaiting_confirmation)
    assert not can_transition(S.awaiting_confirmation, S.proposed)
    assert not can_transition(S.proposed, S.executing)
    assert not can_transition(S.verifying, S.executing)


def test_fail_from_anywhere_but_terminal():
    assert can_transition(S.executing, S.failed)
    assert not can_transition(S.done, S.failed)
    assert not can_transition(S.expired, S.awaiting_confirmation)


def test_only_unconfirmed_action_can_expire():
    assert can_transition(S.awaiting_confirmation, S.expired)
    assert not can_transition(S.executing, S.expired)


def test_code_is_six_digits_and_stored_as_keyed_hash():
    codes = {new_code() for _ in range(200)}
    assert all(len(c) == 6 and c.isdigit() for c in codes) and len(codes) > 150
    a = uuid4()
    h = hash_code(KEY, a, "123456")
    assert "123456" not in h and code_matches(KEY, a, "123456", h)
    assert not code_matches(KEY, a, "123457", h)
    assert not code_matches(KEY, uuid4(), "123456", h)  # код привязан к действию
    assert not code_matches(b"x" * 32, a, "123456", h)  # без ключа не проверить
    assert not code_matches(KEY, a, "123456", None)


def test_correct_code_accepted_and_repeat_confirm_is_noop():
    assert judge_confirm(S.awaiting_confirmation, 0, LATER, NOW, True) == Confirm.accept
    for st in (S.confirmed, S.executing, S.verifying, S.done):
        assert judge_confirm(st, 0, LATER, NOW, True) == Confirm.already


def test_fourth_attempt_rejected():
    assert judge_confirm(S.awaiting_confirmation, 0, LATER, NOW, False) == Confirm.wrong
    assert judge_confirm(S.awaiting_confirmation, 1, LATER, NOW, False) == Confirm.wrong
    assert judge_confirm(S.awaiting_confirmation, 2, LATER, NOW, False) == Confirm.exhausted  # 3-я неверная
    # 4-я попытка, даже с верным кодом — отказ
    assert judge_confirm(S.expired, MAX_ATTEMPTS, LATER, NOW, True) == Confirm.exhausted
    assert judge_confirm(S.awaiting_confirmation, MAX_ATTEMPTS, LATER, NOW, True) == Confirm.exhausted


@pytest.mark.parametrize("expires", [NOW, NOW - timedelta(seconds=1), None])
def test_expired_code_rejected_even_if_correct(expires):
    assert judge_confirm(S.awaiting_confirmation, 0, expires, NOW, True) == Confirm.timeout
    assert judge_confirm(S.expired, 0, expires, NOW, True) == Confirm.timeout


def test_failed_action_cannot_be_confirmed():
    assert judge_confirm(S.failed, 0, LATER, NOW, True) == Confirm.closed
