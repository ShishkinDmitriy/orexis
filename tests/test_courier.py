"""A courier on a grid: the domain whose distance is a NUMBER, and whose pick deletes.

Hanoi proved a domain can be a plug-in and could not show a search being GUIDED — its want is
binary, so no world is nearer than another. Here one is: a van two cells from a parcel is
closer than a van five cells away, in the same unit a drive costs. That is what an admissible
heuristic needs, and this world is the case for building one.

It is also the first domain here whose effect genuinely DELETES. Every shipped retraction
replaces a value — the observation node its own construct re-creates, the peg a disk was on —
and a pick removes `courier:at` outright, putting the parcel aboard under another predicate.
"""

import pytest

from conftest import genesis_store

C = "http://example.org/orexis/courier#"
W = "http://example.org/orexis/world/courier#"
WANT = W + "every_parcel_delivered"
STATE_GRAPH = "http://example.org/orexis/graph/sensed"


def _pose(st, van, parcel):
    """Seed the delivery: where the van stands and where the parcel waits. Runtime, exactly as
    a reading is — the world authors the grid and the destination, never a position."""
    st.update(f"""INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{
        <{W}van> <{C}at> <{W}{van}> . <{W}parcel> <{C}at> <{W}{parcel}> . }} }}""")


def _driver(monkeypatch, van, parcel):
    """A plain Agent, not conftest's wired builder: this driver holds no bus, and the world's
    whole point is the search — the same reason `test_hanoi` builds one by hand."""
    from agent import genesis, runtime

    monkeypatch.setenv("INFLUX_BUCKET", "test-courier")
    monkeypatch.setenv("INFLUX_TOKEN", "test-token-courier")
    st = genesis_store(world="courier")
    _pose(st, van, parcel)
    genesis.classify_own_graphs(st, "courier")
    return runtime.Agent("courier", st=st)


def _goal(agent):
    return next(g for g in agent.pursuing() if g.uri == WANT)


def _plan(agent, budget=None):
    """Plan with the budget the WORLD states, or with one pinned on this instance."""
    from orexis_agent_deliberation.planner import Planner

    p = Planner(agent, agent.me)
    if budget is not None:
        p.budget = budget
    return p.plan(_goal(agent))


def _counting_forks(monkeypatch):
    from orexis_agent_deliberation import imaginarium

    forks = []
    reached = imaginarium.Imaginarium.reached
    monkeypatch.setattr(imaginarium.Imaginarium, "reached",
                        lambda self, *a, **k: (forks.append(1), reached(self, *a, **k))[1])
    return forks


def _steps(plan):
    return [(str(s.act.action).split("#")[-1], str(s.act.about).split("#")[-1])
            for s in plan.steps]


def test_the_goal_is_pursued_and_the_kernel_judges_it(monkeypatch):
    """Pure ratified data — no capability, no module, no measure — lifted and judged by the
    kernel from its own pattern, exactly as hanoi's is. Aboard counts as astray: carrying a
    parcel past its door is not delivering it."""
    agent = _driver(monkeypatch, "c3_3", "c3_3")
    assert _goal(agent).state == "met", "a parcel standing where it is owed is delivered"

    agent = _driver(monkeypatch, "c0_0", "c0_0")
    assert _goal(agent).state == "unmet" and _goal(agent).urgency == 1.0


def test_a_delivery_is_planned_and_it_is_the_short_way_round(monkeypatch):
    """Drive to the parcel, load it, drive to the door, set it down — and no step wasted. The
    route is the cheapest achiever, by no code of this world's: every action costs one, so the
    plan with fewest steps is the one the two-stage cut crowns."""
    agent = _driver(monkeypatch, "c2_3", "c3_2")
    plan = _plan(agent)

    assert len(plan.steps) == 5, f"the short way is five steps, got {_steps(plan)}"
    assert [a for a, _ in _steps(plan)] == ["Drive", "Drive", "Pick", "Drive", "Drop"]
    assert _steps(plan)[-1] == ("Drop", "c3_3"), "and it ends at the door"


def test_a_spent_budget_still_answers_with_progress(monkeypatch):
    """What a declared distance buys, and the reason this world exists.

    The corner-to-corner delivery needs eight steps and 78 worlds. Before the want could say
    how far it still was, a search that could not reach the end returned NOTHING — every
    unmet world scored 1.0, `best` never improved, and the satisficing floor refused the lot.
    With `orexis:estimates` a world three drives from the parcel beats one five drives away,
    so a pass whose budget runs out answers with the drives toward it, and the agent arrives
    across ticks rather than in one pass. That is the architecture's own model of a long
    horizon: act, let the world move, plan again — and since #494 the ceiling is a budget of
    WORLDS the pass never exceeds, not a depth.
    """
    forks = _counting_forks(monkeypatch)
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    shallow = _plan(agent, budget=8)
    assert len(forks) <= 8, f"a pass never imagines past its budget: {len(forks)} worlds"
    assert shallow.outcome == "exhausted" and shallow.steps, _steps(shallow)
    assert {a for a, _ in _steps(shallow)} == {"Drive"}, \
        f"what eight worlds buy is drives toward the parcel: {_steps(shallow)}"
    assert shallow.steps[-1].urgency_after == 1.0, "not delivered, and it does not say so"

    forks.clear()
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    plan = _plan(agent)
    assert len(plan.steps) == 8, f"and with the world's budget it arrives: {_steps(plan)}"
    assert _steps(plan)[-1] == ("Drop", "c3_3")
    assert len(forks) <= 128, "inside the budget the world states"


def test_the_search_follows_the_estimate_and_the_bound_then_refuses_work(monkeypatch):
    """What #492 bought, measured. Breadth-first, the estimate ranked worlds and pruned NONE
    of them: the first achiever arrived in the last layer, and a bound that arrives last has
    nothing left to refuse — 198 forks on the corner delivery with the heuristic and 198
    without. Best-first by `cost + estimate` the search walks to an achiever early and the
    bound refuses the rest: 78 forks, the same eight-step plan. Pinned loosely, so a change
    that moves the number reports itself without every reordering breaking the suite."""
    forks = _counting_forks(monkeypatch)
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    plan = _plan(agent)
    assert len(plan.steps) == 8 and _steps(plan)[-1] == ("Drop", "c3_3"), _steps(plan)
    assert len(forks) < 120, \
        f"{len(forks)} forks: measured 78 best-first against 198 breadth-first (#492)"


def test_the_world_asserts_the_want_and_the_package_owns_the_measure(monkeypatch):
    """The desire owns the term, the package owns the measure. `world/courier` says what it
    wants and points at `courier:delivered` — a POSITIVE shape, on every parcel the cell it is
    at equals the cell it is owed at — and at `courier:drivesOwed`; both live in the package's
    ontology beside the actions they are promises about, and the world's asserted graph carries
    neither a select nor a shape of its own. The kernel compiles the shape into the rows that
    violate it (#497), so nobody writes "a parcel astray" by hand, and the estimate still says
    six from the corner."""
    from orexis_agent_deliberation.planner import Planner
    from orexis_agent_progression.store import bindings

    agent = _driver(monkeypatch, "c0_0", "c1_2")
    inline = bindings(agent.desires.query_union(
        "SELECT ?n WHERE { GRAPH <http://example.org/orexis/graph/desire/asserted> "
        "{ { ?n sh:select ?t } UNION { ?n a sh:NodeShape } } }"))
    assert not inline, f"the world file states no measure of its own: {inline}"
    where = bindings(agent.desires.query_union(
        f"SELECT ?m ?e WHERE {{ <{WANT}> orexis:metWhen ?m ; orexis:estimates ?e }}"))[0]
    assert where["m"].startswith(C) and where["e"].startswith(C), \
        "both point into the courier package's namespace"

    p = Planner(agent, agent.me)
    node = p._begin(_goal(agent))
    assert p._estimate_in(node, _goal(agent)) == 6.0
    assert "FILTER NOT EXISTS" in p._unmet and "?this a <" + C + "Parcel>" in p._unmet, \
        "the shape compiled to a select over every parcel"
    assert _goal(agent).state == "unmet", "and the shape is judged by its compiled select"


def test_a_want_that_declares_no_distance_is_unchanged(monkeypatch):
    """The other half of the term's contract: hanoi declares no estimate, so every world reads
    equally far and the search behaves exactly as it did before `orexis:estimates` existed.
    Asserted here rather than in the hanoi suite because what is being checked is this term's
    silence, not that puzzle's answer."""
    from orexis_agent_deliberation.planner import _near

    agent = _driver(monkeypatch, "c0_0", "c1_2")
    from orexis_agent_deliberation.planner import Planner
    p = Planner(agent, agent.me)
    node = p._begin(_goal(agent))
    assert p._estimate_in(node, _goal(agent)) == 6.0, "the courier's want states its distance"

    node.estimate = None
    assert _near(node) == 0.0, "a want with none reads zero, which is the old comparison"


def test_a_pick_removes_where_the_parcel_was_and_replaces_it_with_nothing(monkeypatch):
    """THE FIRST REAL DELETE LIST IN THIS REPOSITORY, asserted rather than assumed.

    Every other retraction here is an upsert: sensing, actuation and the market each remove the
    observation node their own construct immediately re-creates, and hanoi's move removes the
    peg a disk was on while stating the peg it is on now. The planner's fork subtracts before it
    adds and has always been able to remove a fact outright; nothing had ever asked it to. A
    pick does: `courier:at` goes, and what arrives is `courier:carriedBy` — another predicate
    about the same parcel, so nothing takes the removed fact's place.
    """
    from orexis_agent_deliberation import effects
    from orexis_agent_deliberation.planner import Planner

    agent = _driver(monkeypatch, "c1_1", "c1_1")
    p = Planner(agent, agent.me)
    node = p._begin(_goal(agent))
    row = next(r for r in p._candidates(node, _goal(agent)) if str(r.action).endswith("Pick"))
    added, retracted = effects.apply(p.imaginarium, row.action, **p._bind(_goal(agent), node, row))

    #  `.value` and not `str()`: a pyoxigraph term stringifies to its N-Triples form, angle
    #  brackets and all, which is the trap `effects._triple` exists to keep out of rdflib.
    assert [t[1].value for t in retracted] == [C + "at"], "the pick removes where it stood"
    assert [t[1].value for t in added] == [C + "carriedBy"], "and puts it aboard, not elsewhere"
    assert not [t for t in added if t[1].value == C + "at"], \
        "nothing replaces the removed fact — that is what makes this a delete rather than an upsert"

    world = p._step_from(node, row, _goal(agent))
    text = p.imaginarium.dump_nt(world.graph)
    assert f"<{W}parcel> <{C}at>" not in text, "and the world it reaches holds no position for it"
    assert f"<{W}parcel> <{C}carriedBy>" in text
