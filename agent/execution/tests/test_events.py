"""What the executor says of a step: taken when its act is recorded, and landed or failed at the
verdict — each an event in the journal, carrying the act, the step as its plan states it and the want
its intention pursues — and nothing made where nobody hears."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pyoxigraph as ox
import pytest

from agent import clock
from agent.execution.events import StepAnswered, StepTaken
from agent.execution.executor import DEFAULT_PATIENCE_S, Executor
from agent.journal import Journal, mint
from agent.store import put_graph, update

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
T = "http://example.org/test#"
FILLS = "http://example.org/orexis/planning#fills"      # the layer above's word, which this one repeats
PLAN, WANT, MOVE = T + "plan", T + "want_disk_1", T + "Move"
STATE, DISK, ON, PEG_A, PEG_B = T + "sensed", T + "disk_1", T + "on", T + "PegA", T + "PegB"


@pytest.fixture(autouse=True)
def stopped_clock(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


class _Heard:
    """The step events an executor says, kept in a journal as the history part keeps them; `rows` reads them back."""

    def __init__(self, x: Executor):
        self.journal = Journal()
        for signal in (x.step_taken, x.step_answered, x.intention_resolved):
            signal.connect(self._kept)

    def _kept(self, event):
        node = mint()
        self.journal.record(node, event.statements(node), event.at)

    def rows(self) -> list[dict]:
        """Each step event, in time order: its kind, its instant, the act's `taken`, the verdict's `landed`, the action
        the step fills, the values it takes and the want its intention pursues."""
        out = []
        for r in self.journal.store.query(f"""
PREFIX execution: <http://example.org/orexis/execution#> PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?kind ?at ?taken ?landed ?action ?disk ?to ?want ?incident WHERE {{ GRAPH ?e {{
  ?e a ?kind ; prov:atTime ?at ; execution:act ?act . ?act execution:of ?step ; execution:taken ?taken .
  ?step <{FILLS}> ?action ; <{T}disk> ?disk ; <{T}to> ?to . ?i execution:pursues ?want
  OPTIONAL {{ ?e execution:landed ?landed }}
  BIND(EXISTS {{ ?e a execution:StepFailed }} AS ?incident)
  FILTER(?kind IN (execution:StepTaken, execution:StepAnswered)) }} }} ORDER BY ?at ?kind"""):
            out.append({k: (r[k].value if r[k] is not None else None) for k in
                        ("kind", "at", "taken", "landed", "action", "disk", "to", "want", "incident")})
        return out


def _executor(beliefs, take) -> tuple[Executor, _Heard]:
    """An executor whose step events are heard, and the journal they are kept in."""
    x = Executor(beliefs, "keeper", ox.Store(), take=take)
    return x, _Heard(x)


def _said(row: dict) -> tuple:
    return (row["kind"].rsplit("#", 1)[-1], row["taken"], row["landed"], row["incident"])


def _beliefs(on: str) -> ox.Store:
    """The disk's one reading, and an action `Move` that takes a disk and a peg."""
    st = ox.Store()
    put_graph(st, T + "world", f"""
@prefix orexis: <http://example.org/orexis#> .
GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{on}> }}
GRAPH <{T}actions> {{ <{MOVE}> a orexis:Action ; orexis:takes <{T}disk> , <{T}to> }}
GRAPH <{T}catalogue> {{
  <{T}catalogue> a orexis:CatalogueGraph .
  <{STATE}> a orexis:BeliefGraph . <{T}actions> a orexis:ActionGraph }}""", dataset=True)
    return st


def _plan() -> ox.Store:
    """One step filling `Move` with disk_1 and peg B, predicting the disk on B in the two graphs a
    step names, landing at NOW."""
    st = ox.Store()
    update(st, f"""INSERT DATA {{ GRAPH <{PLAN}> {{
  <{PLAN}.0> a execution:Step ; execution:partOf <{PLAN}> ; <{FILLS}> <{MOVE}> ;
             <{T}disk> <{DISK}> ; <{T}to> <{PEG_B}> ; <{T}spent> 1 ;
             execution:adds <{PLAN}.0.adds> ; execution:retracts <{PLAN}.0.retracts> ;
             execution:landsAt "{NOW.isoformat()}"^^xsd:dateTime }}
  GRAPH <{PLAN}.0.adds> {{ <{DISK}> <{ON}> <{PEG_B}> }}
  GRAPH <{PLAN}.0.retracts> {{ <{DISK}> <{ON}> <{PEG_A}> }} }}""")
    return st


def test_a_step_taken_carries_its_act_its_step_as_the_plan_states_it_and_its_want():
    """The journal is read without the beliefs: what the step fills and the values it takes, in the domain's words,
    are copied from the plan, and the want from the intention."""
    x, heard = _executor(_beliefs(PEG_A), lambda said, intention: None)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    (taken,) = heard.rows()
    assert {k: taken[k] for k in ("action", "disk", "to", "want", "taken")} == {
        "action": MOVE, "disk": DISK, "to": PEG_B, "want": WANT, "taken": "true"}
    assert datetime.fromisoformat(taken["at"]) == NOW


def test_a_step_taken_and_answered_is_a_taken_point_and_a_landed_one():
    beliefs = _beliefs(PEG_A)
    x, heard = _executor(beliefs, lambda said, intention: None)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    assert [_said(r) for r in heard.rows()] == [("StepTaken", "true", None, "false")]
    update(beliefs, f"DELETE DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_A}> }} }} ; "
                    f"INSERT DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_B}> }} }}")
    later = NOW + timedelta(minutes=1)
    x.tick(later)
    assert [_said(r) for r in heard.rows()] == [("StepTaken", "true", None, "false"), ("StepAnswered", "true", "true", "false")]
    assert datetime.fromisoformat(heard.rows()[1]["at"]) == later


def test_a_step_the_world_does_not_answer_by_the_patience_has_failed_and_is_an_incident():
    x, heard = _executor(_beliefs(PEG_A), lambda said, intention: None)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S - 1))
    assert [_said(r) for r in heard.rows()] == [("StepTaken", "true", None, "false")], "waiting is no verdict"
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S))
    assert [_said(r) for r in heard.rows()] == [("StepTaken", "true", None, "false"), ("StepAnswered", "true", "false", "true")]


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
    x, heard = _executor(_beliefs(PEG_A), refuse)
    x.commit(_plan(), PLAN, WANT)
    x.tick(NOW)
    x.drain()
    x.tick(NOW + timedelta(seconds=DEFAULT_PATIENCE_S))
    assert [_said(r) for r in heard.rows()] == [("StepTaken", "false", None, "false")]
    failed = list(heard.journal.store.query("""
PREFIX execution: <http://example.org/orexis/execution#>
SELECT ?outcome WHERE { ?e a execution:IntentionResolved, execution:IntentionFailed ; execution:intention ?i .
                        ?i execution:outcome ?outcome }""", use_default_graph_as_union=True))
    assert [r["outcome"].value for r in failed] == ["failed"], "the intention it failed is an IntentionFailed, a class beneath orexis:Incident"


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
