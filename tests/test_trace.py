"""What the planner considered, and the guarantees that let it be written down at all.

The trace is the record's ONE sanctioned materialisation of a possible world — computed and
dropped is the rule, and a reader outside the process is the exception. Everything here holds it
to the four conditions that made the exception grantable: its own graph class, cleared at the
start of every pass, PROV to what generated it, never public and never in belief.

Written against `world/loner` for the reason `test_planning.py` is: the gardener owns its pump,
so its Actuate has an effect rule and there is something to simulate. Every plant in
`world/simulation` buys its water, and Acquire has no rule for a search to reason with.
"""

from __future__ import annotations

import re

from orexis_agent_progression.ontology import DELIBERATION_GRAPH
from orexis_agent_progression.store import bindings
from orexis_agent_deliberation import planner as search, trace
from orexis_agent_deliberation.planner import Planner

from conftest import build_agent, genesis_store

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
KERNEL = "http://example.org/orexis#"
LEDGER_NS = "http://example.org/orexis/progression#"   # the ledger's words (#529)
TRACE_NS = "http://example.org/orexis/deliberation#"   # the trace's words (#529)
#  zz states 0.1–0.3 and survives 0.02–0.45; the gardener aims at the centre.
WET, DRY = 0.42, 0.04


def _gardener(monkeypatch, moisture):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    st = genesis_store({("zz", MOISTURE): moisture}, world="loner")
    agent = build_agent("gardener", st, monkeypatch)
    desire = next(g for g in agent.pursuing()
                  if getattr(g, "observed_property", None) == MOISTURE)
    return agent, Planner(agent, agent.me), desire


def _trace(agent, query=None):
    """Everything in the trace graph, as (subject, predicate, object) rows."""
    return bindings((query or agent.beliefs.query_union)(f"""
SELECT ?s ?p ?o WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{ ?s ?p ?o }} }}"""))


def test_the_sovereign_can_ask_what_it_considered_and_why_it_declined(monkeypatch):
    """The question the issue exists for, asked the way `orexis-ask` would ask it.

    A gardener at 0.42 is above its region and holds one lever, a pump that raises moisture.
    The reflex would take it — direction matches sign, aim sits above the reading, both true of
    a drowning plant. The planner declines by building the world and finding it no better, and
    before this that decision was a single log line nobody outside the process could reach.
    """
    agent, planner, desire = _gardener(monkeypatch, WET)
    plan = planner.plan(desire)
    assert plan.outcome == search.NOT_BETTER

    rows = bindings(agent.beliefs.query_union(f"""
SELECT ?verdict ?means ?wouldReach ?standsAt WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{
  ?d a <{TRACE_NS}Deliberation> ; <{TRACE_NS}standsAt> ?standsAt ;
     <{TRACE_NS}considered> ?c .
  ?c <{TRACE_NS}wouldTake> ?means ; <{TRACE_NS}verdict> ?verdict .
  OPTIONAL {{ ?c <{TRACE_NS}wouldReach> ?wouldReach }} }} }}"""))

    assert rows, "a pass that decided something must be readable"
    #  BOTH levers appear, which is the debugging value rather than an accident of the fixture:
    #  a reader asking why nothing happened learns that looking was weighed too, and that the
    #  pump was tried and found wanting — not that the search never saw it.
    by_means = {r["means"].rsplit("#", 1)[-1]: r for r in rows}
    assert set(by_means) == {"Observing", "Dosing"}

    pump = by_means["Dosing"]
    assert pump["verdict"] == trace.WORSE
    #  The numbers are the point: a reader must be able to see that the world it would reach
    #  is no better than the one it is in, rather than take the verdict on trust.
    assert float(pump["wouldReach"]) >= float(pump["standsAt"])


def test_a_lever_taken_says_so_and_names_the_thing_that_would_act(monkeypatch):
    """PROV to what generated it, which the record asks for by name. A trace that said only
    `Actuate` would not answer "through which valve" — and an agent with two pumps is the case
    where that question stops being rhetorical."""
    agent, planner, desire = _gardener(monkeypatch, DRY)
    plan = planner.plan(desire)
    assert plan.steps, "dry, with a pump: there is a plan"

    rows = bindings(agent.beliefs.query_union(f"""
SELECT ?means ?via ?depth ?verdict WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{
  ?d <{TRACE_NS}chose> ?c .
  ?c <{TRACE_NS}wouldTake> ?means ; <{LEDGER_NS}through> ?via ;
     <{TRACE_NS}atDepth> ?depth ; <{TRACE_NS}verdict> ?verdict }} }}"""))
    assert len(rows) == 1, "one chosen candidate, named once"
    assert rows[0]["means"].endswith("Dosing")
    assert rows[0]["via"].endswith("pump"), "the lever itself, not just the kind of move"
    assert int(rows[0]["depth"]) == 0
    assert rows[0]["verdict"] in (trace.MET, trace.BETTER)


def test_the_graph_holds_one_pass_and_not_two(monkeypatch):
    """The condition the exception was granted on. A trace that accumulates is a conclusion
    sitting beside beliefs it can contradict, which is the whole reason possible worlds are
    computed and dropped — so planning the same desire twice must REPLACE, not add.

    Asserted on the candidates and not only on the pass node, because the failure that would
    actually happen is orphans: the pass node is one subject and overwriting it is easy, while
    the candidates hang off it and would be left behind by a clear that only took the head.
    """
    agent, planner, desire = _gardener(monkeypatch, DRY)
    planner.plan(desire)
    after_one = _trace(agent)
    planner.plan(desire)
    after_two = _trace(agent)

    passes = [r for r in after_two if r["o"] == f"{TRACE_NS}Deliberation"]
    assert len(passes) == 1, "a second pass replaced the first"
    #  Since #553 the second pass RESUMES the first's frontier and weighs new worlds, so the
    #  two traces need not be the same size; what must hold is that nothing of the first
    #  outlives it: every candidate in the graph hangs off the one pass that is there.
    considered = {r["o"] for r in after_two if r["p"] == f"{TRACE_NS}considered"}
    candidates = {r["s"] for r in after_two if r["o"] == f"{TRACE_NS}Candidate"}
    assert candidates and candidates <= considered, \
        "an orphan is a trace outliving its pass"
    assert after_one, "the first pass wrote a trace to be replaced"


def test_a_restart_does_not_inherit_the_last_process_s_thinking(monkeypatch):
    """One lifecycle up from the rule above. A trace describes a pass over a world, and the
    world moved while the agent was not running — so a decision about readings nobody has taken
    since must not survive a boot.

    This is also what the node IRI has to be deterministic FOR: minted with `hash()` it would
    differ per interpreter, the clear would match nothing, and every restart would orphan a
    trace instead of replacing it.
    """
    agent, planner, desire = _gardener(monkeypatch, DRY)
    planner.plan(desire)
    assert _trace(agent), "a pass was recorded"

    reborn = build_agent("gardener", agent.beliefs, monkeypatch)
    deliberation = next(m for m in reborn.modules if m.name == "deliberation")
    deliberation.start()
    assert _trace(reborn) == [], "a new process starts with no opinion about the old world"


def test_what_it_weighed_is_private(monkeypatch):
    """Which levers an agent considered and rejected is a disclosure nobody decided to make.

    Two checks and they fail differently: the graph must not be an instance of the class the
    default union is built from, and — the one that would actually bite — an ordinary
    `store.query` must not see it. The second is what a rival's query would be.
    """
    agent, planner, desire = _gardener(monkeypatch, DRY)
    planner.plan(desire)

    assert DELIBERATION_GRAPH not in agent.beliefs.public_graphs()
    assert bindings(agent.beliefs.query(
        f"SELECT ?s WHERE {{ ?s a <{TRACE_NS}Deliberation> }}")) == [], \
        "a public query must not reach what an agent thought about doing"
    assert _trace(agent, agent.beliefs.query_union), \
        "and the sovereign, who asks over the union, must"


def test_the_verdicts_reach_the_series_so_a_dashboard_can_watch(monkeypatch):
    """The aggregate half. One case in detail is the ask channel's job; how often an agent
    finds nothing worth doing is a shape you only see over time, and a number nobody graphs is
    a number nobody notices.

    Six fields because a planner has six answers where returning a move or None had two — and
    the pair that matters most is `no candidate` against `exhausted`, since one says equip me
    and the other says my doses are too coarse. Counted from the TRACE rather than tallied in
    the module, so the figure a dashboard shows and the answer `orexis-ask` gives cannot drift.
    """
    agent, _, _ = _gardener(monkeypatch, WET)
    deliberation = next(m for m in agent.modules if m.name == "deliberation")

    _, _, fields = next(row for row in deliberation.series()
                        if row[0] == "agent_deliberation")
    assert set(fields) == {"satisfied", "improved", "no_candidate",
                           "exhausted", "not_better", "refused"}
    assert fields["not_better"] == 1.0, "the drowning plant's verdict, counted"
    assert sum(fields.values()) >= 1.0


# --- the select a want was judged by is shown, never stored (#502) ----------------------------

def _judged(agent):
    """(road, text) off the one deliberation node — text None where the road is not a text."""
    rows = bindings(agent.beliefs.query_union(f"""
SELECT ?road ?text WHERE {{ GRAPH <{DELIBERATION_GRAPH}> {{
  ?d a <{TRACE_NS}Deliberation> ; <{TRACE_NS}judgedThrough> ?road .
  OPTIONAL {{ ?d <{TRACE_NS}judgedBy> ?text }} }} }}"""))
    assert len(rows) == 1, "one pass, one road"
    return rows[0]["road"], rows[0].get("text")


def test_a_shape_want_shows_the_select_it_was_judged_by_and_the_shape_stays_clean(monkeypatch):
    """The courier's want is a shape the kernel compiles (#497); the text lived nowhere. Now
    the trace shows the very select the pass ran — equal to what the compiler says of the
    shape today, so a reader can re-run it — while the shape itself carries no `sh:sparql`:
    written there it would be a second constraint the judge conjoins and reports twice."""
    from rdflib import URIRef
    from test_courier import _driver, _goal
    from orexis_agent_deliberation.conformance import graph_from
    from orexis_agent_progression.violation import unmet_select

    agent = _driver(monkeypatch, "b1", "a1")
    want = _goal(agent)
    Planner(agent, agent.me).plan(want)

    road, text = _judged(agent)
    assert road == trace.COMPILED
    public = graph_from(agent.beliefs, *agent.beliefs.public_graphs())
    shape = public.value(URIRef(want.uri), URIRef(f"{KERNEL}metWhen"))
    #  MODULO VARIABLE NUMBERING. The compiler names variables in the order it meets the
    #  shape's blank nodes, and rdflib hands a cbd's blank nodes in an order that differs
    #  from graph to graph and run to run — the pass's `?v0` was the recompile's `?v1`, one
    #  run in three under `-n0` and every run under xdist, with the text otherwise identical.
    #  What the claim needs is the same select, not the same spelling of its variables.
    same = lambda select: re.sub(r"\?v\d+", lambda m: "?v", select)
    assert same(text) == same(unmet_select(public.cbd(shape), shape)), \
        "the trace must show the select the pass actually ran, not a paraphrase of it"
    assert "SELECT" in text
    #  Never written INTO the shape, in any store the agent holds.
    for query in (agent.beliefs.query_union, agent.desires.query_union):
        assert not bindings(query(
            f"SELECT ?c WHERE {{ <{shape}> sh:sparql ?c }}")), \
            "the compiled select is an explanation in the trace, never a constraint on the shape"


def test_a_derived_want_is_judged_by_its_compiled_shape_and_measured_apart(monkeypatch):
    """Two questions, two roads, and the trace names the one it answers. The gardener's
    moisture want is a shape the deduction emits, so whether a world MEETS it is the compiled
    select — shown here — while how FAR a world is from it is sensing's measure, which is
    `deliberation:wouldReach` on every candidate and no text at all."""
    agent, planner, desire = _gardener(monkeypatch, WET)
    planner.plan(desire)
    road, text = _judged(agent)
    assert road == trace.COMPILED and text is not None and "SELECT" in text


def test_an_authored_pattern_is_shown_as_the_pattern(tmp_path, monkeypatch):
    """An aversion authored as a pattern (#468) is judged by that pattern, and the trace shows
    the text the author wrote and names the road."""
    from test_avoidance import MARKER, STATE_GRAPH, _avoidance_row, _gardener as _avoider

    agent, st = _avoider(tmp_path, monkeypatch)
    st.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ {MARKER} }} }}")
    Planner(agent, agent.me).plan(_avoidance_row(agent))
    road, text = _judged(agent)
    assert road == trace.AUTHORED
    assert text is not None and MARKER.split()[0] in text
