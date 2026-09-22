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


def _region_want(agent):
    """The want derived under the moisture desire, or None where nothing is wanted.

    BY WHAT IT IS ABOUT. It filtered the container's merged list on `observed_property` — a
    field the kernel carried so sensing could read it back — and on `is_epistemic`; a region
    want is about its PROPERTY and a freshness want about its instrument, so one test does
    both. None is a real answer now: a reading in region leaves the desire met, the derivation
    mints nothing, and there is no want.
    """
    return next((w for w in agent.wants() if MOISTURE in w.about), None)


def _desire(agent) -> str:
    """The standing moisture desire — the node wants are derived UNDER, which is what these
    tests are about. The collection used to present it wherever no want stood, so a test could
    reach it through the same call; a desire is not a want and `wants()` holds none."""
    return next(r["d"] for r in bindings(agent.desires.query(
        "SELECT ?d WHERE { ?me orexis:holds ?d . ?d a orexis:Desire }"))
        if r["d"].endswith("SoilMoisture"))


def _said_of(agent, want):
    return {(r["p"], r["o"]) for r in bindings(agent.desires.query(
        f"SELECT ?p ?o WHERE {{ <{want}> ?p ?o }}"))}


def test_a_root_is_never_handed_to_the_search_and_what_is_pursued_is_derived_under_it(monkeypatch):
    """The claim itself. Bone dry, the desire reads unmet; deciding about it mints the want
    derived under it and plans THAT — the same dose, since the derived want points at the
    desire's own met-test — and from then on the container presents the derived want in the
    desire's place, carrying the desire's measure and naming the desire."""
    agent = _gardener(monkeypatch, DRY)
    desire = _desire(agent)
    #  THE WANT IS THERE ALREADY, because a started agent derives (`pursuit.derived`, at boot
    #  and in the fixture). It used to appear at the first DECISION, and until then the
    #  collection presented the desire in its place — which is what made a desire look like
    #  something a search could be handed.
    child = _region_want(agent)
    assert child is not None and child.uri == desire + ".pursued" and child.desire == desire

    plan = agent.deliberator.decide(child)
    assert [s.action for s in plan.steps] == [DOSING], "the derived want plans what the desire would have"

    assert MOISTURE in child.about, "the want says what it is about, and the kernel names no property"
    assert all(w.uri != desire for w in agent.wants()), \
        "a desire is not a want, and `wants()` holds none"
    assert set(agent.deliberator._planners) == {child.uri}, \
        "the search was handed the derived want and never the desire"

    said = _said_of(agent, child.uri)
    assert (DERIVED_FROM, desire) in said
    #  THE MET-TEST IS CARRIED, INSTANTIATED — the desire's shape at this want's witness, under
    #  the want's own name: the same node targeted (the desire names its one node), the block
    #  about its property, so the want is judged on its own instance. It was pointed at
    #  before, one owner, and every want under a desire over several instances read unmet
    #  for any of them.
    from orexis_agent_progression.store import bindings
    [own] = [o for p, o in said if p == MET_WHEN]
    assert own == child.uri + ".met", "its own shape, named for the want"
    root_met = next(o for p, o in _said_of(agent, desire) if p == MET_WHEN)
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
    desire = _desire(agent)
    #  NO WANT AT ALL, which is what "met" looks like now. It asserted `desire.is_met` on a row
    #  the collection judged at read time and presented in the want's place; a met desire
    #  derives nothing, so there is nothing to read a verdict off and nothing to pursue.
    assert _region_want(agent) is None, "in region: nothing is wanted"
    assert pursuit.child_of(agent, desire) is None
    assert not agent.deliberator._planners, "no pass ran for a met desire"


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
    desire = _desire(agent)
    child = pursuit.child_of(agent, desire)
    assert child is not None

    agent.deliberator.on_plan_finished("urn:orexis:test:intention", DOSING, child)
    assert _state_of(agent, child) == "Done", "the plan finished, so the want is finished"
    #  AND THE COLLECTOR TAKES IT. Not where it was finished: deciding that something is done
    #  and clearing it away are two acts (`forget_wants`, garbage collection on the pass).
    assert forget_wants(agent.beliefs.engine) == [child]
    assert pursuit.child_of(agent, desire) is None and _region_want(agent) is None, \
        "collected: nothing stands under the desire and nothing is in the store"

    pursuit.derived(agent)
    assert pursuit.child_of(agent, desire) == child, "still dry: derived again, same node"


def test_withdrawal_is_the_derivations_and_never_a_decisions(monkeypatch):
    """Who takes a want away: the derivation, from the same rows that minted it.

    A READING IN REGION IS NOT ENOUGH ON ITS OWN, which is the half worth pinning: the
    derivation reads the present AND every foreseen instant, so a plant watered into its range
    that a drift predicts drying again still wants something. `test_a_met_root_derives_nothing`
    has the case where nothing is foreseen either.
    """
    agent = _gardener(monkeypatch, DRY)
    desire = _desire(agent)
    child = _region_want(agent)
    assert child is not None and child.desire == desire

    write_reading(agent, CONTENT, MOISTURE)
    kept = _region_want(agent)
    assert kept is not None and kept.uri == child.uri, \
        "in region now, and a drift foresees the crossing: still wanted, same node"

    #  AND WHEN IT IS TAKEN, IT IS TAKEN BY THE DERIVATION. Not by a reader asking about it:
    #  the same rows that minted it withdraw it, and `forget_wants` collects what is finished.
    assert pursuit.child_of(agent, desire) == child.uri


def test_the_derived_want_borrows_the_roots_verdict(monkeypatch):
    """An at-end want has no room of its own; the one derived under a desire reads the desire's.
    Both were asked of the MEASURE, which is gone — what they must still agree about is the
    verdict, which is the thing anything ever branched on."""
    agent = _gardener(monkeypatch, DRY)
    #  ONE VERDICT, AND IT IS EXISTENCE. Both rows carried a `state` the container computed at
    #  read time and the test held them to each other; a want is in the store because its
    #  desire read unmet, so there is one answer and no second reader to disagree with it.
    assert _region_want(agent) is not None, "dry: the derivation minted the want"
    agent.deliberator.decide(_region_want(agent))
    assert _region_want(agent) is not None, "and deciding about it does not settle it"


def test_a_mark_by_either_name_pursues_the_same_want(monkeypatch):
    """A reading's actor marks the want it means, and it may hold the desire's name from before
    the derived want stood: the derivation meets the same want by either name, and the
    intention it adopts names the derived want."""
    agent = _gardener(monkeypatch, DRY)
    desire = _desire(agent)
    uri = pursuit.pursue_for(agent, desire)
    assert uri is not None, "the search proposed nothing"
    child = pursuit.child_of(agent, desire)
    assert child is not None
    assert {s.want for s in agent.keeper.standing(want=child)} == {child}, \
        "the intention pursues the derived want, never the desire"
    assert [s.uri for s in agent.keeper.standing(want=desire)] == \
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
    desire = _region_want(agent)
    agent.deliberator.decide(desire)
    child = _region_want(agent)
    graph = graph_of(agent.id, child.uri)
    assert graph in agent.beliefs.graphs_of(WANT), "the derivation classified what it wrote"
    assert bindings(agent.beliefs.query(
        f"SELECT ?a WHERE {{ GRAPH <{agent.beliefs.catalogue}> {{ "
        f"<{graph}> orexis:arrivedBy ?a }} }}", ()))[0]["a"].endswith("#Derived"), \
        "and said on the other axis that the derivation, not a world, put the rows there"