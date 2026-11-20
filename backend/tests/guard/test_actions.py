from storozh.guard.domain.actions import ActionStatus as S
from storozh.guard.domain.actions import can_transition


def test_forward_only():
    assert can_transition(S.proposed, S.awaiting_confirmation)
    assert not can_transition(S.awaiting_confirmation, S.proposed)
    assert not can_transition(S.proposed, S.executing)


def test_fail_from_anywhere_but_terminal():
    assert can_transition(S.executing, S.failed)
    assert not can_transition(S.done, S.failed)
