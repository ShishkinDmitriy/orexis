"""What the executor says of a step: taken when its act is recorded, and landed or failed at the
verdict — each history measured `Step`, tagged with the action, the want and the values the action
takes — and nothing made where nobody hears."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.events import MEASUREMENT, StepAnswered, StepTaken
from agent.execution.executor import DEFAULT_PATIENCE_S, Executor
from agent.hash_named_graph import facts_of
from agent.store import put_graph, update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T = "http://example.org/test#"
FILLS = "http://example.org/orexis/planning#fills"      # the layer above's word, which this one repeats
PLAN, WANT, MOVE = T + "plan", T + "want_disk_1", T + "Move"
STATE, DISK, ON, PEG_A, PEG_B = T + "sensed", T + "disk_1", T + "on", T + "PegA", T + "PegB"


@pytest.fixture(autouse=True)
def stopped_clock(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


def _executor(beliefs, take) -> tuple[Executor, list]:
    """An executor whose step events are heard, and the points they answer as they are said."""
    x = Executor(beliefs, "keeper", ox.Store(), take=take)
    history = []
    x.step_taken.connect(lambda event: history.append(event.point()))
    x.step_answered.connect(lambda event: history.append(event.point()))
    return x, history


def _beliefs(on: str) -> ox.Store:
    """The disk's one reading, and an action `Move` that takes a disk and a peg."""
    st = ox.Store()
    put_graph(st, T + "world", f"""
@prefix orexis: <http://example.org/orexis#> .
GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{on}> }}
GRAPH <{T}actions> {{ <{MOVE}> a orexis:Action ; orexis:takes <{T}disk> , <{T}to> }}
GRAPH <{T}catalogue> {{
  <{T}catalogue> a orexis:CatalogueGraph .
  <{STATE}> a orexis:StateGraph . <{T}actions> a orexis:ActionGraph }}""", dataset=True)
    return st


def _plan() -> ox.Store:
    """One step filling `Move` with disk_1 and peg B, predicting the disk on B, landing at NOW."""
    (before,) = facts_of(_beliefs(PEG_A), STATE)
    (after,) = facts_of(_beliefs(PEG_B), STATE)
    predicts = json.dumps({"adds": [after], "retracts": [before]})
    st = ox.Store()
    update(st, f"""INSERT DATA {{ GRAPH <{PLAN}> {{
  <{PLAN}.0> a execution:Step ; execution:partOf <{PLAN}> ; <{FILLS}> <{MOVE}> ;
             <{T}disk> <{DISK}> ; <{T}to> <{PEG_B}> ; <{T}spent> 1 ;
             execution:predicts {json.dumps(predicts)} ; execution:landsAt "{NOW.isoformat()}"^^xsd:dateTime }} }}""")
    return st


TAGS = {"action": "Move", "want": "want_disk_1", "disk": "disk_1", "to": "PegB"}


def test_a_step_is_tagged_with_its_action_its_want_and_the_values_the_action_takes():
    """What the step says beyond the parameters its action takes — here a figure the search wrote —
    is not a value of the step and is not tagged."""
    x, history = _executor(_beliefs(PEG_A), lambda said, intention: None)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    assert history == [{"measurement": MEASUREMENT, "tags": TAGS, "fields": {"taken": True}, "time": NOW}]
    assert MEASUREMENT == "Step"


def test_a_step_taken_and_answered_is_a_taken_point_and_a_landed_one():
    beliefs = _beliefs(PEG_A)
    x, history = _executor(beliefs, lambda said, intention: None)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    assert history == [{"measurement": "Step", "tags": TAGS, "fields": {"taken": True}, "time": NOW}]
    update(beliefs, f"DELETE DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_A}> }} }} ; "
                    f"INSERT DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_B}> }} }}")
    later = NOW + timedelta(minutes=1)
    x.tick(later)
    assert history[1:] == [{"measurement": "Step", "tags": TAGS, "fields": {"landed": True}, "time": later}]


def test_a_step_the_world_does_not_answer_by_the_patience_has_failed():
    x, history = _executor(_beliefs(PEG_A), lambda said, intention: None)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S - 1))
    assert [p["fields"] for p in history] == [{"taken": True}], "waiting is no verdict"
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S))
    assert [p["fields"] for p in history] == [{"taken": True}, {"landed": False}]


def test_a_verdict_says_how_late_the_world_answered_and_whether_the_patience_ran_out():
    heard = []
    x = Executor(_beliefs(PEG_A), "keeper", ox.Store(), take=lambda said, intention: None)
    x.step_answered.connect(heard.append)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S))
    (verdict,) = heard
    assert isinstance(verdict, StepAnswered)
    assert (verdict.landed, verdict.timed_out, verdict.late_s, verdict.action) == (False, True, DEFAULT_PATIENCE_S, "Move")


def test_a_step_that_could_not_be_taken_says_so_and_has_no_verdict():
    def refuse(said, intention):
        raise RuntimeError("no valve answers")
    x, history = _executor(_beliefs(PEG_A), refuse)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S))
    assert [p["fields"] for p in history] == [{"taken": False}]


def test_nobody_hearing_is_no_event_made(monkeypatch):
    """Where nobody hears a step, the executor reads nothing to say one — hanoi's mover takes
    thousands of steps in a bench and writes no series."""
    def made(*args, **kw):
        raise AssertionError("an event was made with nobody to hear it")
    monkeypatch.setattr(StepTaken, "__init__", made)
    x = Executor(_beliefs(PEG_A), "keeper", ox.Store(), take=lambda said, intention: None)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    assert x.drain() == 1
