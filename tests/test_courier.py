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
    genesis.classify_kernel_graphs(st, "courier")
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
    return [(str(s.action).split("#")[-1], str(s.about).split("#")[-1])
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
    assert plan.urgency_after == 0.0 and plan.steps[-1].urgency_after == 0.0, \
        "a compiled want nobody measures is binary: the delivered world scores 0, not the " \
        "not-knowing 1.0 the fallback gave it before #499"


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
    assert "FILTER NOT EXISTS" in p._compiled.unmet and "?this a courier:Parcel" in p._compiled.unmet, \
        "the shape compiled to a select over every parcel, in the prefixed names it was written in"
    assert _goal(agent).state == "unmet", "and the shape is judged by its compiled select"


def test_two_domains_in_one_world_and_a_delivery_pass_moves_no_disk(monkeypatch):
    """The plug-in claim's other half (#488): two domains sharing one agent. Hanoi's disks
    are declared into the courier's world and posed on a peg, so Move rows appear on the
    van's menu beside Drive; a delivery pass reads what the delivered shape reads — where
    things are and where they are owed — finds Move writes only what a disk rests on, and
    never simulates a move: the same 78 forks and the same eight steps as with no disk in
    the world, and the trace names every Move row as irrelevant rather than losing it."""
    from orexis_agent_deliberation import trace
    from orexis_agent_deliberation.planner import Planner
    from orexis_agent_progression.store import bindings

    HANOI = "http://example.org/orexis/hanoi#"
    forks = _counting_forks(monkeypatch)
    agent = _driver(monkeypatch, "c0_0", "c1_2")
    agent.beliefs.update(f"""INSERT DATA {{
        GRAPH <http://example.org/orexis/graph/world> {{
            <urn:disk_1> a <{HANOI}Disk> ; <{HANOI}size> 1 .
            <urn:disk_2> a <{HANOI}Disk> ; <{HANOI}size> 2 . }}
        GRAPH <{STATE_GRAPH}> {{
            <urn:disk_2> <{HANOI}on> <{HANOI}PegA> . <urn:disk_1> <{HANOI}on> <urn:disk_2> . }} }}""")
    agent.desires.rebuild()
    p = Planner(agent, agent.me)
    plan = p.plan(_goal(agent))
    assert len(plan.steps) == 8 and _steps(plan)[-1] == ("Drop", "c3_3"), _steps(plan)
    assert {a for a, _ in _steps(plan)} <= {"Drive", "Pick", "Drop"}
    assert len(forks) == 78, f"{len(forks)} forks: 78 with no disk in the world"
    assert HANOI + "Move" not in p._compiled.relevant
    rows = bindings(agent.beliefs.query_union(f"""SELECT (COUNT(?c) AS ?n) WHERE {{
        ?c <http://example.org/orexis/deliberation#wouldTake> <{HANOI}Move> ;
           <http://example.org/orexis/deliberation#verdict> "{trace.IRRELEVANT}" }}"""))
    assert int(rows[0]["n"]) > 0, "Move rows were on the menu, and the trace says so"


def test_an_irrelevant_lever_is_never_even_asked(monkeypatch):
    """#504: relevance stopped the search SIMULATING a foreign row; the menu still ran
    every action's precondition at every node and threw the rows away. Now a lever outside
    the relevant set is asked ONCE, at the root, so the trace can say truthfully that it was
    there — and never again at any of the 78 nodes. Move is in the vocabulary whether or not a
    disk is in the world, so both passes ask it exactly once and make exactly the same number
    of queries; what differs is that with a disk the root ask yields rows, and the trace names
    them."""
    from orexis_agent_deliberation import imaginarium, trace
    from orexis_agent_deliberation.planner import Planner
    from orexis_agent_progression.store import bindings

    HANOI = "http://example.org/orexis/hanoi#"
    asked = []
    query = imaginarium.Imaginarium.query
    monkeypatch.setattr(imaginarium.Imaginarium, "query",
                        lambda self, sparql, *a, **k: (asked.append(sparql), query(self, sparql, *a, **k))[1])
    #  The menu asks through the rules' door since a round became a graph with a period
    #  (#620): counted the same, since what is counted is the precondition text being run.
    query_at = imaginarium.Imaginarium.query_at
    monkeypatch.setattr(imaginarium.Imaginarium, "query_at",
                        lambda self, sparql, *a, **k: (asked.append(sparql), query_at(self, sparql, *a, **k))[1])

    def pass_with(disks):
        agent = _driver(monkeypatch, "c0_0", "c1_2")
        if disks:
            agent.beliefs.update(f"""INSERT DATA {{
                GRAPH <http://example.org/orexis/graph/world> {{
                    <urn:disk_1> a <{HANOI}Disk> ; <{HANOI}size> 1 . }}
                GRAPH <{STATE_GRAPH}> {{ <urn:disk_1> <{HANOI}on> <{HANOI}PegA> . }} }}""")
            agent.desires.rebuild()
        asked.clear()
        plan = Planner(agent, agent.me).plan(_goal(agent))
        assert len(plan.steps) == 8, _steps(plan)
        return agent, len(asked), sum(1 for q in asked if "hanoi:size" in q or f"{HANOI}size" in q)

    _, without, _ = pass_with(False)
    agent, with_disks, move_asked = pass_with(True)
    assert move_asked == 1, \
        "Move's precondition — the only text reading hanoi:size — ran once, at the root"
    assert with_disks == without, \
        f"{with_disks} queries with a disk in the world, {without} without: none per node"
    rows = bindings(agent.beliefs.query_union(f"""SELECT (COUNT(?c) AS ?n) WHERE {{
        ?c <http://example.org/orexis/deliberation#wouldTake> <{HANOI}Move> ;
           <http://example.org/orexis/deliberation#verdict> "{trace.IRRELEVANT}" }}"""))
    assert int(rows[0]["n"]) == 2, "one disk on a peg, two pegs to move it to: two rows, at the root"


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


# --- a surprise drops the tail and a new plan is made (#510) ------------------

def test_a_parcel_moved_under_a_standing_plan_drops_the_tail_and_replans(monkeypatch):
    """#510's surprise: the van sets off toward the parcel with the whole delivery in the
    ledger; the parcel is moved while it drives. The first drive still answers as predicted
    — the van is where it said — but the next step cannot be taken and lapses, which drops
    the tail, tells deliberation, and the next pursue searches again from the new world."""
    from datetime import datetime, timedelta, timezone
    from orexis_agent_deliberation import planner, pursuit

    agent = _driver(monkeypatch, "c0_0", "c1_2")
    searches = []
    real = planner.Planner.plan
    monkeypatch.setattr(planner.Planner, "plan", lambda self, d, **kw: (searches.append(1), real(self, d, **kw))[1])
    keeper = agent.keeper
    uri = pursuit.pursue(agent, _goal(agent))
    assert uri is not None and len(searches) == 1
    first = keeper.standing(want=WANT)[0].step
    assert keeper.in_progress(WANT) is not None, "the whole delivery stands as one plan"
    assert keeper.expect(uri, "driving — show me",
                         not_after=datetime.now(timezone.utc) + timedelta(hours=1))
    # the parcel is moved while the van drives: the world differs from the plan's tail
    agent.beliefs.update(f"""DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ <{W}parcel> <{C}at> <{W}c1_2> . }} }}""")
    agent.beliefs.update(f"""INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{W}parcel> <{C}at> <{W}c2_2> . }} }}""")
    assert keeper.standing(want=WANT)[0].step.predicts == first.predicts, \
        "the drive itself is not answered by that"
    adds, retracts = first.predicts                       # the drive lands as predicted
    for f in retracts:
        agent.beliefs.update(f"DELETE DATA {{ GRAPH <{STATE_GRAPH}> {{ <{f[0]}> <{f[1]}> <{f[2]}> . }} }}")
    for f in adds:
        agent.beliefs.update(f"INSERT DATA {{ GRAPH <{STATE_GRAPH}> {{ <{f[0]}> <{f[1]}> <{f[2]}> . }} }}")
    second = keeper.standing(want=WANT)[0].step
    assert second.predicts != first.predicts, "advanced to the next step on the drive's own answer"
    failed = agent.deliberator._plans_failed
    keeper.lapse(uri)                    # the next step could not be taken; its deadline passes
    assert agent.deliberator._plans_failed == failed + 1
    assert keeper.standing(want=WANT) == [] and keeper.in_progress(WANT) is None, "the tail is dropped"
    again = pursuit.pursue(agent, _goal(agent))
    assert again is not None and again != uri and len(searches) == 2, "a new plan from the new world"
