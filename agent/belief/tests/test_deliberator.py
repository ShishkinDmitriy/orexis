"""The deliberator: a queue of what was written, a pass within a budget, and a cut continued.

Held over the `revise/` cases, since a pass is `revise` sequenced: what a source's revisions
are is the case's claim, and what is tested here is the sequencing — that a changed source is
revised and leaves the queue, that a budget cuts a pass and the next continues, that nothing
changed spends nothing, and that a cut survives a new deliberator over the same store.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from agent import clock
from agent.belief.deliberator import BUDGET, Deliberator
from agent.belief.fire import fire
from agent.belief.ontology import BUDGET_TERM, SETTLED, SUBJECT_BELIEF_GRAPH
from agent.store import entry, forget_graph, graphs_of, rows, update

CASES_DIR = Path(__file__).parent / "revise"
SENSED = "http://example.org/test#sensed"
_CONCLUDED_Q = "SELECT ?s ?p ?o WHERE { GRAPH $g { ?s ?p ?o } }"
_SETTLED_Q = "SELECT ?v WHERE { GRAPH ?c { $g $settled ?v } }"


def _settled(store) -> str | None:
    found = rows(store, _SETTLED_Q, (), g=SENSED + "/revisions", settled=SETTLED)
    return found[0]["v"] if found else None


def test_a_changed_source_is_revised_on_the_pass_and_leaves_the_queue(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_reading_below_its_range_is_concluded_below.trig")
    deliberator = Deliberator(store, snapshots.AGENT)
    deliberator.changed(SENSED)
    assert deliberator.pending == [SENSED]
    assert deliberator.deliberate() > 0
    assert deliberator.pending == []
    assert rows(store, _CONCLUDED_Q, (), g=SENSED + "/revisions")
    assert _settled(store) == "true"


def test_nothing_changed_spends_nothing(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_reading_below_its_range_is_concluded_below.trig")
    assert Deliberator(store, snapshots.AGENT).deliberate() == 0


def test_a_budget_cuts_the_pass_and_the_next_continues(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_chain_settles_in_a_later_round.trig")
    deliberator = Deliberator(store, snapshots.AGENT, budget=2)
    deliberator.changed(SENSED)
    assert deliberator.deliberate() == 2
    assert deliberator.pending == [SENSED] and _settled(store) == "false"
    deliberator.budget = 64
    assert deliberator.deliberate() > 0
    assert deliberator.pending == [] and _settled(store) == "true"
    assert {r["p"].rsplit("#", 1)[-1] for r in rows(store, _CONCLUDED_Q, (), g=SENSED + "/revisions")} == {"side", "isDry"}


def test_the_budget_is_the_agents_stance_where_its_self_graph_states_one(monkeypatch, snapshots):
    """`belief:budget 2` in the keeper's self graph (knowledge/domain/kernel/stance.md): a deliberator
    handed no budget spends two rule executions and the source stays queued, where the default would
    have settled it. With none stated, `BUDGET`; a caller sizing the pass says its own."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    assert Deliberator(snapshots.stand_in(CASES_DIR / "a_chain_settles_in_a_later_round.trig"), snapshots.AGENT).budget == BUDGET
    store = snapshots.stating(snapshots.stand_in(CASES_DIR / "a_chain_settles_in_a_later_round.trig"), {BUDGET_TERM: 2})
    assert Deliberator(store, snapshots.AGENT, budget=64).budget == 64
    deliberator = Deliberator(store, snapshots.AGENT)
    deliberator.changed(SENSED)
    assert deliberator.deliberate() == 2
    assert deliberator.pending == [SENSED] and _settled(store) == "false"


def test_a_cut_survives_a_new_deliberator_over_the_store(monkeypatch, snapshots):
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(CASES_DIR / "a_chain_settles_in_a_later_round.trig")
    first = Deliberator(store, snapshots.AGENT, budget=2)
    first.changed(SENSED)
    first.deliberate()
    second = Deliberator(store, snapshots.AGENT)
    assert second.pending == [SENSED], "the row said the rules did not settle"
    second.deliberate()
    assert second.pending == [] and _settled(store) == "true"


# --- an arrival is concluded on, then transitioned on (a-transition-changes-the-state-and-an-inference-only-concludes)

TICKS = Path(__file__).parent / "worlds" / "a_counter_and_its_ticks.trig"
T = "http://example.org/test#"

#  WHAT THE COUNTER IS HELD TO, in every subject belief graph whatever its period, by local name.
_COUNTER_Q = "SELECT ?p ?o WHERE { <http://example.org/test#counter> ?p ?o FILTER(?p != rdf:type) }"


def _tick(store, name: str, start, *, loud: bool = True) -> str:
    """A tick arrived: its own graph, received and the keeper's, holding twenty minutes from `start`."""
    graph = T + name
    update(store, f"""INSERT DATA {{
  GRAPH <{graph}> {{ <{T}{name}_t> a <{T}Tick> {'; <' + T + 'loud> true' if loud else ''} }}
  {entry(store, graph, T + "TickGraph", "http://example.org/orexis#Received", T + "keeper", start, start + timedelta(minutes=20))} }}""")
    return graph


def _counter(store) -> dict[str, str]:
    return {r["p"].rsplit("#", 1)[-1]: r["o"].rsplit("#", 1)[-1]
            for r in rows(store, _COUNTER_Q, graphs_of(store, SUBJECT_BELIEF_GRAPH))}


def _row_settled(store, graph: str) -> str | None:
    found = rows(store, _SETTLED_Q, (), g=graph + "/revisions", settled=SETTLED)
    return found[0]["v"] if found else None


def test_an_arrival_is_revised_before_its_transitions_run_and_both_are_spent_from_one_budget(monkeypatch, snapshots):
    """The count reads `:ticked`, which only revision concludes: fired on the tick unrevised it counts
    nothing, and taken by the deliberator — revised, then transitioned on — it counts one. The pass
    spends both from one budget: two executions revising, three transitioning."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(TICKS)
    early = _tick(store, "early", snapshots.NOW)
    fire(store, early)
    assert "count" not in _counter(store), "nothing the transition reads is concluded yet"
    store = snapshots.stand_in(TICKS)
    deliberator = Deliberator(store, snapshots.AGENT)
    deliberator.changed(_tick(store, "first", snapshots.NOW))
    assert deliberator.deliberate() == 5
    assert _counter(store) == {"count": "1", "echo": "1", "last": "first_t"}
    assert deliberator.pending == []


def test_arrivals_are_transitioned_on_in_turn_whatever_the_budget_cuts(monkeypatch, snapshots):
    """A loud tick then a quiet one, with a source's share of the pass cut to one execution: the loud
    tick's revision is cut, the quiet one's settles in that pass — and its transitions WAIT, its row
    saying so, since the loud tick came first. The next pass finishes the loud tick and transitions on
    both in the order they arrived: the last tick taken is the quiet one, never overwritten by the one
    before it finished late."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    monkeypatch.setattr("agent.belief.deliberator.PER_SOURCE", 1)
    store = snapshots.stand_in(TICKS)
    deliberator = Deliberator(store, snapshots.AGENT, budget=50)
    loud = _tick(store, "loud", snapshots.NOW)
    quiet = _tick(store, "quiet", snapshots.NOW + timedelta(minutes=1), loud=False)
    deliberator.changed(loud)
    deliberator.changed(quiet)
    deliberator.deliberate()
    assert deliberator.pending == [loud, quiet]
    assert _counter(store) == {}, "nothing transitioned while the first arrival is cut"
    assert _row_settled(store, loud) == "false"
    deliberator.deliberate()
    assert deliberator.pending == []
    assert _counter(store) == {"count": "1", "echo": "1", "last": "quiet_t"}
    assert _row_settled(store, loud) == "true"
    held = {g.rsplit("#", 1)[-1]: sorted(r["p"].rsplit("#", 1)[-1] for r in rows(store, _COUNTER_Q, [g]))
            for g in graphs_of(store, SUBJECT_BELIEF_GRAPH)}
    assert held == {"loud/believed": ["count"], "quiet/believed": ["echo", "last"]}, \
        "what the quiet tick replaced was taken out where the loud one put it; the count, which it does not touch, stands there"


def test_an_arrival_that_fires_nothing_holds_no_turn(monkeypatch, snapshots):
    """A graph of a kind no transition declares, cut in its revision, changes no state whenever it is
    done, so the tick queued after it is transitioned on in the same pass — where waiting on it, a
    prediction rewritten and cut every pass would hold every reading's transitions for ever."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    monkeypatch.setattr("agent.belief.deliberator.PER_SOURCE", 1)
    store = snapshots.stand_in(TICKS)
    note = T + "note"
    update(store, f"""INSERT DATA {{ GRAPH <{note}> {{ <{T}note_t> a <{T}Tick> ; <{T}loud> true }}
  {entry(store, note, "http://example.org/orexis#StateGraph", "http://example.org/orexis#Received", T + "keeper")} }}""")
    deliberator = Deliberator(store, snapshots.AGENT, budget=50)
    deliberator.changed(note)
    deliberator.changed(_tick(store, "quiet", snapshots.NOW, loud=False))
    deliberator.deliberate()
    assert deliberator.pending == [note], "the note is cut, and the tick done"
    assert _counter(store) == {"last": "quiet_t"}


def test_a_graph_written_again_is_a_new_arrival_at_the_end_of_the_queue(monkeypatch, snapshots):
    """A loud tick is cut, a quiet one arrives after it, and then the loud tick's graph is written again
    with a later tick — as a message's latest reading reuses its graph's name. The rewritten graph is a
    new arrival and takes its turn after the quiet one: the last tick taken is the later loud one, where
    left in its old place it would have been taken first and the quiet one would have overwritten it."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    monkeypatch.setattr("agent.belief.deliberator.PER_SOURCE", 1)
    store = snapshots.stand_in(TICKS)
    deliberator = Deliberator(store, snapshots.AGENT, budget=50)
    deliberator.changed(_tick(store, "loud", snapshots.NOW))
    deliberator.changed(_tick(store, "quiet", snapshots.NOW + timedelta(minutes=1), loud=False))
    deliberator.deliberate()
    forget_graph(store, T + "loud")
    deliberator.changed(_tick(store, "loud", snapshots.NOW + timedelta(minutes=2)))
    assert deliberator.pending == [T + "quiet", T + "loud"]
    for _ in range(5):
        deliberator.deliberate()
    assert deliberator.pending == []
    assert _counter(store)["last"] == "loud_t"
    (held,) = rows(store, "SELECT ?s WHERE { GRAPH ?c { $g dcterms:temporal/orexis:start ?s } }", (), g=T + "loud/believed")
    assert held["s"].startswith("2026-01-01T12:02"), "the later loud tick's period"


def test_transitions_a_budget_left_waiting_survive_a_new_deliberator(monkeypatch, snapshots):
    """A budget of two revises the tick and leaves nothing to transition with: its row says it is not
    done, a deliberator made over the store again takes it up, and the state is the one an uncut pass
    leaves — counted once."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(TICKS)
    tick = _tick(store, "first", snapshots.NOW)
    first = Deliberator(store, snapshots.AGENT, budget=2)
    first.changed(tick)
    assert first.deliberate() == 2
    assert first.pending == [tick] and _counter(store) == {}
    assert _row_settled(store, tick) == "false"
    second = Deliberator(store, snapshots.AGENT)
    assert second.pending == [tick], "the row said the arrival was not done"
    second.deliberate()
    assert second.pending == [] and _row_settled(store, tick) == "true"
    assert _counter(store) == {"count": "1", "echo": "1", "last": "first_t"}


def test_a_cut_between_orders_is_continued_from_the_order_it_stopped_at(monkeypatch, snapshots):
    """Three executions a pass: the first revises the tick (two) and begins its first order of
    transitions (two more, applied whole); the second applies the second order alone. Counted once."""
    monkeypatch.setattr(clock, "now", lambda: snapshots.NOW)
    store = snapshots.stand_in(TICKS)
    deliberator = Deliberator(store, snapshots.AGENT, budget=3)
    deliberator.changed(_tick(store, "first", snapshots.NOW))
    assert deliberator.deliberate() == 4
    assert _counter(store) == {"count": "1", "last": "first_t"}
    assert deliberator.deliberate() == 1
    assert deliberator.pending == []
    assert _counter(store) == {"count": "1", "echo": "1", "last": "first_t"}
