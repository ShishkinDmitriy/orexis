"""Execution's part: its executor, which adopts what planning publishes, ends an intention planning says
is reached before any step or blocked, and says by its own signal every intention that ends; linked, it
walks again when the deliberator says the present changed; once started, it walks every pass."""

from __future__ import annotations

from pathlib import Path

from agent import clock
from agent.lifecycle import Signal
from agent.execution.executor import Executor
from agent.belief.events import Revised
from agent.execution.create import create
from agent.ontology import STATE
from agent.store import entry, graphs_of, update

BENCH = Path(__file__).resolve().parents[2] / "planning" / "tests" / "bench"
PLAN, WANT = "urn:test:plan", "urn:test:want"


def _hand_down(store) -> None:
    """A plan of one step handed down, as planning would write it — by hand, since execution imports
    nothing of planning, its tests included."""
    update(store, f"""INSERT DATA {{
  GRAPH <{PLAN}> {{ <{PLAN}> <http://example.org/orexis/execution#pursues> <{WANT}> .
                   <{PLAN}.s1> a <http://example.org/orexis/execution#Step> ;
                               <http://example.org/orexis/execution#partOf> <{PLAN}> . }}
  {entry(store, PLAN, "http://example.org/orexis#PlanGraph", "http://example.org/orexis#Recorded")} }}""")


class _Belief:
    def __init__(self):
        self.deliberator = type("D", (), {"revised": Signal("revised")})()


def _part(monkeypatch, snapshots, stand_in_runtime):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(BENCH / "two_disk_hanoi.trig")
    runtime = stand_in_runtime(store, None, snapshots.NOW, agent_id=snapshots.AGENT)
    part = create(runtime)
    ended = []
    part.executor.intention_resolved.connect(lambda resolved: ended.append(resolved.outcome))
    return store, runtime, part, ended


def test_its_part_adopts_what_is_published_and_ends_what_was_reached_untaken(monkeypatch, snapshots, stand_in_runtime):
    store, runtime, part, ended = _part(monkeypatch, snapshots, stand_in_runtime)
    belief = _Belief()
    part.link({"execution": part, "belief": belief})
    part.start(runtime)
    assert [seconds for seconds, _ in runtime.timers] == [0], "a walk every pass"
    belief.deliberator.revised.emit(Revised(("urn:g",)))
    assert runtime.jobs == [], "a graph revised that is not the present — a prediction, a committed step — answers no step"
    (state,) = graphs_of(store, STATE)
    belief.deliberator.revised.emit(Revised((state,)))
    assert len(runtime.jobs) == 1, "the present changed, so a walk is queued"
    #  THE WALK A REVISION QUEUED IS THE DRAIN'S, and marks no lap: a lap is from the last mark, so
    #  the one it marked took the sensing and revision before it — the drain of two readings, 52 ms
    #  by hand — as `execute`, and the pass's `drain` read nought. The walk a pass asks for marks it.
    runtime.jobs.pop(0)()
    assert runtime.laps == [], "a walk run inside the drain is the drain's, not execution's"
    #  AN ARRIVAL OF NO KIND OF THIS PACKAGE'S — what a sensor said (#944) — changes the present by the
    #  transitions it triggers, and the deliberator says which state graphs they changed.
    belief.deliberator.revised.emit(Revised(("urn:g",), changed=("urn:test:state",)))
    assert len(runtime.jobs) == 1, "the transitions an arrival triggered changed the present, so a walk is queued"
    runtime.jobs.pop(0)()
    ((_, walk),) = runtime.timers
    walk()
    assert runtime.laps == ["execute"], "the walk a pass asks for is execution's lap"
    _hand_down(store)
    assert part.executor.adopt(PLAN, WANT) == [part.executor.graph]
    assert part.executor.walking() == [WANT]
    part.executor.end_for(WANT, "reached")
    assert part.executor.walking() == [] and ended == ["reached"], "reached before any step was taken: ended"


def test_its_part_ends_an_intention_whose_next_step_is_blocked(monkeypatch, snapshots, stand_in_runtime):
    store, runtime, part, ended = _part(monkeypatch, snapshots, stand_in_runtime)
    _hand_down(store)
    part.executor.adopt(PLAN, WANT)
    (standing,) = part.executor.standing()
    part.executor.end_at(standing.at, "failed")
    assert part.executor.walking() == [] and ended == ["failed"]


#  A DOSING ACTION WHOSE COMMAND IS SIZED FROM THE READING THE STEP NAMES, as the actuation domain's is.
T = "http://example.org/test#"
_DOSE = f"""INSERT DATA {{
  GRAPH <{T}actions> {{
    <{T}Dose> a orexis:Action ; orexis:takes <{T}valve> , <{T}reading> ;
      execution:implementation [ execution:operation [ a execution:Command ; sh:select \"\"\"SELECT ?actuator ?payload WHERE {{
          $reading sosa:hasSimpleResult ?value .
          BIND($valve AS ?actuator)
          BIND(CONCAT('{{"dose_ml": ', STR(xsd:integer(ROUND((0.45 - ?value) * 2000.0))), '}}') AS ?payload) }}\"\"\" ] ] . }}
  GRAPH <{PLAN}> {{ <{PLAN}> <http://example.org/orexis/execution#pursues> <{WANT}> .
                   <{PLAN}.s1> a <http://example.org/orexis/execution#Step> ;
                               <http://example.org/orexis/execution#partOf> <{PLAN}> ;
                               <http://example.org/orexis/planning#fills> <{T}Dose> ;
                               <{T}valve> <{T}pump> ; <{T}reading> <{T}soil> . }} }}"""


def _dosing(monkeypatch, snapshots, stand_in_runtime, reading: str | None):
    store, runtime, part, ended = _part(monkeypatch, snapshots, stand_in_runtime)
    runtime.me = T + "me"
    update(store, _DOSE)
    update(store, "INSERT DATA { "
           + entry(store, T + "actions", "http://example.org/orexis#ActionGraph", "http://example.org/orexis#Asserted")
           + entry(store, PLAN, "http://example.org/orexis#PlanGraph", "http://example.org/orexis#Recorded") + " }")
    if reading is not None:
        update(store, f"INSERT DATA {{ GRAPH <{T}sensed> {{ <{T}soil> sosa:hasSimpleResult {reading} }} "
               + entry(store, T + "sensed", "http://example.org/orexis#StateGraph", "http://example.org/orexis#Received")
               + " }")
    sent = []
    part.executor.commanded.connect(lambda c: sent.append((c.actuator, c.payload)) or [])
    part.executor.adopt(PLAN, WANT)
    part.executor.walk(snapshots.NOW)
    return sent, ended


def test_a_step_whose_command_answers_is_taken_and_sent(monkeypatch, snapshots, stand_in_runtime):
    sent, ended = _dosing(monkeypatch, snapshots, stand_in_runtime, "0.35")
    assert sent == [(T + "pump", {"dose_ml": 200})] and ended == ["done"]


def test_a_step_whose_command_answers_nothing_is_not_taken(monkeypatch, snapshots, stand_in_runtime, caplog):
    """#869: the reading the step names is not in the present — read past its period, say — so the
    command sizes nothing. Sending nothing and recording the step taken left the intention to wait out
    its patience as though the pump had run; the step is not taken, and the intention fails at once."""
    sent, ended = _dosing(monkeypatch, snapshots, stand_in_runtime, None)
    assert sent == [] and ended == ["failed"]
    assert "Dose" in caplog.text and "answered nothing" in caplog.text
