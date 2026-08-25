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

from agent.ontology import DELIBERATION_GRAPH
from agent.store import bindings
from agent import planner as search, trace
from agent.planner import Planner

from conftest import build_agent, genesis_store

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
KERNEL = "http://example.org/orexis#"
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
  ?d a <{KERNEL}Deliberation> ; <{KERNEL}standsAt> ?standsAt ;
     <{KERNEL}considered> ?c .
  ?c <{KERNEL}wouldTake> ?means ; <{KERNEL}verdict> ?verdict .
  OPTIONAL {{ ?c <{KERNEL}wouldReach> ?wouldReach }} }} }}"""))

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
  ?d <{KERNEL}chose> ?c .
  ?c <{KERNEL}wouldTake> ?means ; <{KERNEL}through> ?via ;
     <{KERNEL}atDepth> ?depth ; <{KERNEL}verdict> ?verdict }} }}"""))
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

    passes = [r for r in after_two if r["o"] == f"{KERNEL}Deliberation"]
    assert len(passes) == 1, "a second pass replaced the first"
    assert len(after_two) == len(after_one), \
        "and took its candidates with it — an orphan is a trace outliving its pass"


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
        f"SELECT ?s WHERE {{ ?s a <{KERNEL}Deliberation> }}")) == [], \
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
