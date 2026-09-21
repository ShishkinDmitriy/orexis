"""What is pursued is derived from an Always want (#618) — the record
an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it, held to the code.

A desire is never handed to the search. The deliberator mints the want derived under it the
first time the desire reads unmet, the container presents that want in the desire's place with
the desire's own measure, and it is withdrawn when its plan finishes or when it reads met with
nothing standing for it. Every shipped world plans exactly as it did: the planner is untouched
and is handed the same shape under another name, which is the measurement the issue asks for
and the suite's fork and step pins already carry.
"""
from __future__ import annotations

from orexis_agent_deliberation import pursuit
from orexis_agent_progression.ontology import STATE_GRAPH
from orexis_agent_progression.store import bindings
from conftest import build_agent, genesis_store, write_reading
from orexis_agent_progression.ontology import PUBLIC
from orexis_agent_progression.ontology import WANT
from orexis_agent_deliberation.derive_wants import graph_of
from orexis_agent_deliberation.forget_wants import forget_wants

MOISTURE = "http://example.org/orexis/water#SoilMoisture"
DOSING = "http://example.org/orexis/actuation#Dosing"
DRY, CONTENT = 0.04, 0.20
MET_WHEN = "http://example.org/orexis#metWhen"
DERIVED_FROM = "http://www.w3.org/ns/prov#wasDerivedFrom"


def _gardener(monkeypatch, moisture):
    monkeypatch.setenv("OREXIS_WORLD", "loner")
    return build_agent("gardener", genesis_store({("zz", MOISTURE): moisture}, world="loner"),
                       monkeypatch)


def _stake(agent):
    """The want about moisture the container presents — the desire, or what is derived under it."""
    return next(d for d in agent.considering()
                if getattr(d, "observed_property", None) == MOISTURE and not d.is_epistemic)


def _said_of(agent, want):
    return {(r["p"], r["o"]) for r in bindings(agent.desires.query(
        f"SELECT ?p ?o WHERE {{ <{want}> ?p ?o }}"))}


def test_a_root_is_never_handed_to_the_search_and_what_is_pursued_is_derived_under_it(monkeypatch):
    """The claim itself. Bone dry, the desire reads unmet; deciding about it mints the want
    derived under it and plans THAT — the same dose, since the derived want points at the
    desire's own met-test — and from then on the container presents the derived want in the
    desire's place, carrying the desire's measure and naming the desire."""
    agent = _gardener(monkeypatch, DRY)
    desire = _stake(agent)
    assert desire.desire is None and not desire.is_met

    plan = agent.deliberator.decide(desire)
    assert [s.action for s in plan.steps] == [DOSING], "the derived want plans what the desire would have"

    child = _stake(agent)
    assert child.uri == desire.uri + ".pursued" and child.desire == desire.uri
    assert child.observed_property == MOISTURE, \
        "the derived want is presented with the desire's own row"
    assert all(d.uri != desire.uri for d in agent.considering()), \
        "while a derived want stands, the desire is presented as it and never beside it"
    assert set(agent.deliberator._planners) == {child.uri}, \
        "the search was handed the derived want and never the desire"

    said = _said_of(agent, child.uri)
    assert (DERIVED_FROM, desire.uri) in said
    #  THE MET-TEST IS CARRIED, INSTANTIATED — the desire's shape at this want's witness, under
    #  the want's own name: the same node targeted (the desire names its one node), the block
    #  about its property, so the want is judged on its own instance. It was pointed at
    #  before, one owner, and every want under a desire over several instances read unmet
    #  for any of them.
    from orexis_agent_progression.store import bindings
    [own] = [o for p, o in said if p == MET_WHEN]
    assert own == child.uri + ".met", "its own shape, named for the want"
    root_met = next(o for p, o in _said_of(agent, desire.uri) if p == MET_WHEN)
    rows = bindings(agent.beliefs.query_union(f"""SELECT ?target ?about WHERE {{
        <{own}> sh:targetNode ?target ; sh:property ?b . ?b orexis:about ?about }}"""))
    [same] = bindings(agent.beliefs.query_union(
        f"SELECT ?target WHERE {{ <{root_met}> sh:targetNode ?target }}"))
    assert rows and {r["target"] for r in rows} == {same["target"]} \
        and {r["about"] for r in rows} == {MOISTURE}, \
        "the desire's own target and the blocks about this property, and nothing else"


def test_a_met_root_derives_nothing_and_no_pass_runs(monkeypatch):
    """A desire inside its region is nothing to pursue: no want is derived, no planner is built,
    and the container keeps presenting the desire itself."""
    agent = _gardener(monkeypatch, CONTENT)
    desire = _stake(agent)
    assert desire.is_met
    assert agent.deliberator.decide(desire) is None
    assert pursuit.child_of(agent, desire.uri) is None
    assert not agent.deliberator._planners, "no pass ran for a met desire"
    assert _stake(agent).uri == desire.uri


def _state_of(agent, uri: str) -> str | None:
    """Where a want has got to (`orexis:state`), or None where it is not there at all.

    A want is ONE-SHOT and its stages are written on it by whoever decides each — so a plan
    finishing leaves the want `orexis:Done` and the collector takes it on the next pass.
    Deciding and clearing are two acts; asserting on the stage is asserting on the first."""
    from orexis_agent_progression.store import bindings
    rows = bindings(agent.beliefs.query(
        f"SELECT ?s WHERE {{ GRAPH ?g {{ <{uri}> orexis:state ?s }} }}", ()))
    return rows[0]["s"].rsplit("#", 1)[-1] if rows else None


def test_the_derived_want_is_withdrawn_when_its_plan_finishes_and_derived_again_while_unmet(monkeypatch):
    """A plan that finished leaves the want it served DONE, the collector takes it, and a desire
    still unmet derives it again on the next decision — under the same name, so everything keyed
    by it finds what it kept."""
    agent = _gardener(monkeypatch, DRY)
    desire = _stake(agent)
    agent.deliberator.decide(desire)
    child = pursuit.child_of(agent, desire.uri)
    assert child is not None

    agent.deliberator.on_plan_finished("urn:orexis:test:intention", DOSING, child)
    assert _state_of(agent, child) == "Done", "the plan finished, so the want is finished"
    #  AND THE COLLECTOR TAKES IT. Not where it was finished: deciding that something is done
    #  and clearing it away are two acts (`forget_wants`, garbage collection on the pass).
    assert forget_wants(agent.beliefs.engine) == [child]
    assert pursuit.child_of(agent, desire.uri) is None
    assert _stake(agent).uri == desire.uri, "with nothing derived under it, the desire is presented again"

    agent.deliberator.decide(desire)
    assert pursuit.child_of(agent, desire.uri) == child, "still dry: derived again, same node"


def test_a_derived_want_that_reads_met_with_nothing_standing_is_withdrawn(monkeypatch):
    """The world moved on its own — rain, a neighbour's hose — and the desire reads met with no
    plan standing for the derived want: deciding about it withdraws it and plans nothing."""
    agent = _gardener(monkeypatch, DRY)
    desire = _stake(agent)
    agent.deliberator.decide(desire)
    child = _stake(agent)
    assert child.desire == desire.uri

    write_reading(agent, CONTENT)
    now = _stake(agent)
    assert now.uri == child.uri and now.is_met, "still presented until withdrawn, and measured met"
    assert agent.deliberator.decide(now) is None
    assert pursuit.child_of(agent, desire.uri) is None
    assert _stake(agent).uri == desire.uri


def test_the_derived_want_borrows_the_roots_verdict(monkeypatch):
    """An at-end want has no room of its own; the one derived under a desire reads the desire's.
    Both were asked of the MEASURE, which is gone — what they must still agree about is the
    verdict, which is the thing anything ever branched on."""
    agent = _gardener(monkeypatch, DRY)
    desire = _stake(agent)
    agent.deliberator.decide(desire)
    child = _stake(agent)
    assert child.state == desire.state == "unmet"


def test_a_mark_by_either_name_pursues_the_same_want(monkeypatch):
    """A reading's actor marks the want it means, and it may hold the desire's name from before
    the derived want stood: the derivation meets the same want by either name, and the
    intention it adopts names the derived want."""
    agent = _gardener(monkeypatch, DRY)
    desire = _stake(agent)
    uri = pursuit.pursue_for(agent, desire.uri)
    assert uri is not None, "the search proposed nothing"
    child = pursuit.child_of(agent, desire.uri)
    assert child is not None
    assert {s.want for s in agent.keeper.standing(want=child)} == {child}, \
        "the intention pursues the derived want, never the desire"
    assert [s.uri for s in agent.keeper.standing(want=desire.uri)] == \
        [s.uri for s in agent.keeper.standing(want=child)], \
        "the ledger answers by either name: the desire's, and the derived want's"
    assert pursuit.pursue_for(agent, child) == uri, "in progress: absorbed, not re-decided"


def test_the_pursued_graph_is_this_agents_own_and_recorded(monkeypatch):
    """Classified by the DERIVATION when it mints the want — each want a graph of its own since
    #645, on BOTH axes where it is written and never by its name — so the sweep, the ask
    channel and the imaginarium's copy of the records all see it.

    Two axes, because a graph of wants the derivation wrote and a graph of wants a world
    ratified differ in who wrote them and in nothing else. It was one class,
    `deliberation:PursuedGraph`, and the cost was that no read could ask for the world's wants
    at all — so the kernel judged those a second time instead of reading them."""
    agent = _gardener(monkeypatch, DRY)
    desire = _stake(agent)
    agent.deliberator.decide(desire)
    child = _stake(agent)
    graph = graph_of(agent.id, child.uri)
    assert graph in agent.beliefs.graphs_of(WANT), "the derivation classified what it wrote"
    assert bindings(agent.beliefs.query(
        f"SELECT ?a WHERE {{ GRAPH <{agent.beliefs.catalogue}> {{ "
        f"<{graph}> orexis:arrivedBy ?a }} }}", ()))[0]["a"].endswith("#Derived"), \
        "and said on the other axis that the derivation, not a world, put the rows there"