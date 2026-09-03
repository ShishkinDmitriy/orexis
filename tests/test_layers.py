"""The arrows between the kernel's layers at RUN time, where `test_layering.py` holds them at
import time: what progression has to say to deliberation crosses as an EVENT through the
choir, and what deliberation decides crosses back as ONE item on the reactive loop. Each was
broken once and seen to fail before it was trusted (#452)."""

from __future__ import annotations

import threading
from dataclasses import replace

import pytest

from orexis_capability_market.terms import ACQUIRING, TENDERING
from orexis_agent_progression.ontology import PLAN_FAILED, PLAN_FINISHED, STEP_DONE
from orexis_agent_reactive.loop import loop

from conftest import MOISTURE, build_agent, genesis_store, open_round_for, reading_of, stake_of, write_reading, predicted_reading


@pytest.fixture
def thirsty(monkeypatch):
    return build_agent("fern", genesis_store({"fern": 0.30}), monkeypatch)


def test_the_three_events_are_points_deliberation_fills(thirsty):
    """A term nobody reads is annotation: every event progression tells has a listener above."""
    for point in (STEP_DONE, PLAN_FINISHED, PLAN_FAILED):
        assert thirsty.deliberator.answer(point) is not None, point


def test_an_unmet_expectation_is_told_upward_and_marks_the_want(thirsty):
    """The keeper judges the step's RESULT against the baseline the actor handed in; what to do
    about a plan that failed is deliberation's, and it hears it as an event rather than the
    ledger importing the search."""
    keeper, want = thirsty.keeper, stake_of(thirsty).uri
    uri = keeper.adopt(TENDERING, want, "a dose that will not land")
    before = dict(failed=thirsty.deliberator._plans_failed,
                  finished=thirsty.deliberator._plans_finished)
    assert keeper.expect(uri, "watching", baseline=reading_of(thirsty, MOISTURE),
                         predicts=predicted_reading(thirsty.me.acts_for, MOISTURE, 0.31))
    write_reading(thirsty, 0.29, MOISTURE)                           # fell — not an answer
    #  The deadline passes — fired here as the keeper's scheduler would (#516), on this
    #  thread, so the event it tells upward has landed when the next line asserts.
    keeper.lapse(uri)
    assert thirsty.deliberator._plans_failed == before["failed"] + 1
    assert thirsty.deliberator._plans_finished == before["finished"]
    assert want in thirsty.reviser._pending, "a failed plan is a want marked for re-planning"


def test_a_met_expectation_is_counted_and_not_re_planned(thirsty):
    keeper, want = thirsty.keeper, stake_of(thirsty).uri
    uri = keeper.adopt(TENDERING, want, "a dose that lands")
    assert keeper.expect(uri, "watching", baseline=reading_of(thirsty, MOISTURE),
                         predicts=predicted_reading(thirsty.me.acts_for, MOISTURE, 0.31))
    write_reading(thirsty, 0.31, MOISTURE)
    assert thirsty.deliberator._plans_finished == 1
    assert want not in thirsty.reviser._pending, \
        "a finished plan re-planned itself and raced the next offer (see on_plan_finished)"


def test_a_plans_head_is_committed_and_taken_as_one_item_on_the_loop(thirsty, monkeypatch):
    """Only the RESULT of a search crosses onto the executing thread: the search ran here, on the
    test's thread, and the ledger write and the take ran on the loop, together."""
    from orexis_agent_deliberation import pursuit

    on: list[threading.Thread] = []
    keeper = thirsty.keeper
    real_adopt = keeper.adopt

    def adopt_here(*a, **kw):
        on.append(threading.current_thread())
        return real_adopt(*a, **kw)

    monkeypatch.setattr(keeper, "adopt", adopt_here)
    monkeypatch.setattr(thirsty, "tell", lambda point, *a, **kw: on.append(threading.current_thread())
                        if point == STEP_DONE else None)
    open_round_for(thirsty, "fern")                       # something to buy in, so a plan
    assert pursuit.pursue(thirsty, stake_of(thirsty)) is not None, "the search proposed nothing"
    assert on, "neither the commit nor the take ran"
    assert all(t is not threading.current_thread() for t in on), \
        "the commit or the take ran on the searcher's thread instead of the loop"
    assert len({t.name for t in on}) == 1 and on[0].name == loop().name
