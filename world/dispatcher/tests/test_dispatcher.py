"""The dispatcher: one agent, two vans, two parcels on the courier's grid, and an aversion to two
vans on one cell (#567). What this world is held to is what was MEASURED on it:

- the two vans are ONE scope, joined through the parcels, since a parcel standing where either van
  could stand is a filling value of both vans' Pick (a-scope-is-a-predicate-on-a-key, the two-vans
  seam); so every world a want's search opens admits the other van's moves too, and each is weighed;
- two parcels astray are ONE want where a constraint can make their plans collide: the aversion reads
  `at` on vans joined on the cell, both vans can reach every cell of the one grid, so the derivation
  couples the two parcels into one cluster — one want about both, one search, the joint ten-step plan
  optimal for both by construction (one-mind-couples-the-wants-a-constraint-can-make-collide, #900).
  Its estimate is the desire's sum over both parcels, ten, which is what the plan costs; what the
  coupling costs is the product — 228 candidates against 50 for two wants apart, and a budget of 128
  cuts it short. Two parcels whose vans stand on DISJOINT grids are two wants as before, each named for
  its parcel and planned alone, since the aversion over what the vans can reach yields no row there;
- a want's estimate never overstates what its plan cost — the one promise an estimate makes, held
  here as a gate over the shipped world, the corridor, a van alone and a van parked in the way;
- THE BOUND (#902): the aversion is a state invariant, weighed in every possible world the search
  weighs, and a world that NEWLY enters the avoided state — a violation row with no equal in its
  parent's weighing — is refused, off the frontier and never an achiever. On the corridor the coupled
  search refuses 13 worlds and opens none holding two vans, and the joint plan it finds is walked
  with two vans on no cell at any act, promised now and not pinned as luck; a van parked across the
  other's only shortest path is not driven through, and the one mind holding both vans does better
  than the route round: it delivers with the parked van, or moves it aside;
- two vans on one cell at a PASS'S START are seen: the aversion — the avoided state itself, under
  `planning:unmetWhen`, judged as a met-test is since #892 — reads unmet with a witness per van and
  the cell as the offending value, its want is minted carrying the same select, and a one-step plan
  parts them; an invariant already unmet in the root bounds nothing, since repair removes a row and
  enters none. The two parcels' coupled want beside it is the product's price no budget here pays.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent import clock
from agent.ontology import STATE
from agent.planning.planner import Planner
from agent.runtime import UNFINISHED, Runtime, boot
from agent.store import graphs_of, rows

WORLD = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
D = "http://example.org/orexis/world/dispatcher#"
DESIRE = "http://example.org/orexis/planning#DesireGraph"   # planning's word; the Planner is all planning exports
#  THE ONE WANT THE TWO PARCELS ARE where the aversion couples them, named for both.
JOINT = "every_parcel_delivered.pursued.parcel_a.parcel_b"
#  WHAT THE COUPLED SEARCH NEEDS: 228 candidates on the shipped pose and 286 on the corridor, measured
#  (measure-the-search), so the default budget of 128 cuts it short and the tests state their own. The
#  bound took the corridor from 296 to 286 and the shipped pose nowhere, since no world of it collides;
#  neither fits 128, and the budgets stand.
BUDGET, CORRIDOR_BUDGET = 256, 512
#  THE AVERSION, the one state invariant this world's holder holds.
AVERSION = "no_cell_holds_two_vans"
#  THE DRIVE'S BAND, as the courier declares it (`domains/courier/actions.ttl`, #901): a drive lands
#  between half a minute and a minute after it is taken; a pick and a drop at once. The executor's
#  patience past the latest landing is its own default.
DRIVE_LEAST_S, DRIVE_MOST_S = 30, 60
PATIENCE_S = 60

_MEMBERS_Q = "SELECT ?m ?s WHERE { GRAPH ?g { ?m planning:inScope ?s } }"
_WANTS_Q = "SELECT ?w ?d WHERE { GRAPH ?g { ?w a planning:Want ; prov:wasDerivedFrom ?d } }"
_PLANS_Q = """
SELECT ?want ?outcome (COUNT(?step) AS ?steps) WHERE {
  GRAPH ?p { ?p a planning:Plan ; planning:outcome ?outcome ; planning:for ?want .
             OPTIONAL { ?step a execution:Step ; execution:partOf ?p } } }
GROUP BY ?want ?outcome"""
_STEPS_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?want ?a ?van ?parcel ?to WHERE {
  GRAPH ?p { ?p planning:for ?want . ?step a execution:Step ; execution:partOf ?p ; planning:fills ?a .
             OPTIONAL { ?step courier:van ?van } OPTIONAL { ?step courier:parcel ?parcel } OPTIONAL { ?step courier:to ?to } } }"""
#  THE POSSIBLE WORLDS WEIGHED PER WANT — the figure measure-the-search tabulates; a candidate passed
#  over is weighed too and is not counted here.
_WEIGHED_Q = """
SELECT ?for (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?w .
    ?w a planning:PossibleGraph } }
GROUP BY ?for"""
#  WHAT A WANT'S SEARCH SPENT — every weighing but a ground's, a candidate passed over among them: the
#  unit the budget is stated in, and the runbook's "candidates".
_SPENT_Q = """
SELECT ?for (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?u .
    FILTER NOT EXISTS { ?u a planning:GroundGraph } } }
GROUP BY ?for"""
#  OF THOSE, THE ONES REACHED BY A MOVE OF EACH VAN: the candidate a world is `planning:by` fills the van.
_BY_VAN_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?for ?van (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?w .
    ?w a planning:PossibleGraph ; planning:by ?c . ?c courier:van ?van } }
GROUP BY ?for ?van"""
#  WHAT EACH WANT'S ESTIMATE READ IN THE PRESENT GROUND.
_REMAINING_Q = """
SELECT ?for ?left WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for ?for ; planning:weighs ?g ;
    planning:remaining ?left . ?g a planning:GroundGraph } }"""
#  WHAT EACH WANT'S PLAN SPENT — the cost the search found, which the estimate at the root may never exceed.
_COSTS_Q = """
SELECT ?want ?spent WHERE { GRAPH ?p { ?p a planning:Plan ; planning:for ?want ; planning:spent ?spent } }"""
_WORLDS_Q = "SELECT ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph } }"
#  WHAT A WANT'S SEARCH SAYS OF EACH POSSIBLE WORLD IT WEIGHED: refused by which invariant, open, opened,
#  met — the frontier's own rows (#902). A world the search passed over by hash has no row here.
_JUDGED_Q = """
SELECT ?w ?refused ?open ?expanded ?met WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:for $want ; planning:weighs ?w .
    ?w a planning:PossibleGraph .
    OPTIONAL { ?x planning:refused ?refused } OPTIONAL { ?x planning:open ?open }
    OPTIONAL { ?x planning:expanded ?expanded } OPTIONAL { ?x planning:met ?met } } }"""
#  TWO VANS ON ONE CELL, in one graph's facts: the vans' kinds are public and the world's facts its own.
_SHARED_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT DISTINCT ?cell WHERE { GRAPH $w { ?a courier:at ?cell . ?b courier:at ?cell }
                              GRAPH ?h { ?a a courier:Van . ?b a courier:Van } FILTER(?a != ?b) }"""
#  WHERE THINGS STAND, asked of what the agent BELIEVES by kind: a published plan's steps state the
#  positions they predict in graphs of their own (a-steps-prediction-is-two-graphs-it-names), and a
#  read over every graph took a van's predicted cell for its present one.
_AT_Q = """PREFIX courier: <http://example.org/orexis/courier#>
SELECT ?x ?cell WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?x courier:at ?cell } }"""
_ACTS_Q = "SELECT (COUNT(?a) AS ?n) WHERE { GRAPH ?g { ?a a execution:Act } }"
#  WHAT A DESIRE'S WEIGHING IN A GROUND SAYS IS IN TROUBLE, and where: each witness's instance and
#  the value that offended — for the aversion, the van and the cell it shares.
_WITNESSES_Q = """
SELECT ?x ?cell WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:Weighing ; planning:for $d ; planning:weighs ?g ; planning:violation ?v .
               ?g a planning:GroundGraph . ?v planning:instance ?x ; planning:offending ?cell } }"""
#  THE PLAN'S STEPS WITH THEIR INSTANTS, along the chain: when each may be taken, the earliest and the
#  latest its change lands — and the period of the world it reaches, off that world's row.
_PLACED_Q = """
SELECT ?step ?a ?nb ?la ?na ?ws ?we WHERE {
  GRAPH ?p { ?p a planning:Plan ; planning:for $want . ?step a execution:Step ; execution:partOf ?p ; planning:fills ?a ;
             planning:of ?by ; execution:notBefore ?nb ; execution:landsAt ?la . OPTIONAL { ?step execution:notAfter ?na } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w planning:by ?by ; dcterms:temporal ?period . ?period orexis:start ?ws ; orexis:end ?we } }
ORDER BY ?nb ?la"""
#  THE COMMITTED STEPS' WINDOWS in the beliefs, with the two lengths each states.
_WINDOWS_Q = """
SELECT ?g ?s ?e ?within ?by WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a execution:CommittedStepGraph ; dcterms:temporal ?p . ?p orexis:start ?s ; orexis:end ?e }
  GRAPH ?g { ?step execution:landsWithinS ?within ; execution:answeredWithinS ?by } }
ORDER BY ?s ?g"""
_INTENTIONS_Q = "SELECT (COUNT(?i) AS ?n) WHERE { GRAPH ?g { ?i a execution:Intention } }"
#  WHICH POLARITY a want carries its met-test under, and what it points at.
_POLARITY_Q = "SELECT ?p ?o WHERE { GRAPH ?g { $w ?p ?o FILTER(?p IN (planning:metWhen, planning:unmetWhen)) } }"
#  WHAT A WANT'S MET-TEST TARGETS — one node per instance a coupled want is about.
_TARGETS_Q = "SELECT ?t WHERE { GRAPH ?g { $w planning:metWhen ?m . ?m sh:targetNode ?t } }"

#  THE CORRIDOR: van A drives parcel A along the second row, van B drives parcel B down the third
#  column, and the two shortest chains meet at c2_1 — each van's third step.
CORRIDOR = {"world.ttl": [("courier:destination :c0_3", "courier:destination :c3_1"),
                          ("courier:destination :c3_3", "courier:destination :c2_0")],
            "state.ttl": [(":van_a courier:at :c0_0 .", ":van_a courier:at :c0_1 ."),
                          (":parcel_a courier:at :c0_1 .", ":parcel_a courier:at :c1_1 ."),
                          (":van_b courier:at :c3_0 .", ":van_b courier:at :c2_3 ."),
                          (":parcel_b courier:at :c3_1 .", ":parcel_b courier:at :c2_2 .")]}
#  ONE VAN AND ITS PARCEL ALONE, either half of the shipped delivery.
HALF_A = {"world.ttl": [(':van_b a courier:Van ; rdfs:label "van B" .', ""),
                        (':parcel_b a courier:Parcel ; courier:destination :c3_3 ;\n    rdfs:label "the parcel owed at the top of the last column" .', "")],
          "state.ttl": [(":van_b courier:at :c3_0 .", ""), (":parcel_b courier:at :c3_1 .", "")]}
HALF_B = {"world.ttl": [(':van_a a courier:Van ; rdfs:label "van A" .', ""),
                        (':parcel_a a courier:Parcel ; courier:destination :c0_3 ;\n    rdfs:label "the parcel owed at the top of the first column" .', "")],
          "state.ttl": [(":van_a courier:at :c0_0 .", ""), (":parcel_a courier:at :c0_1 .", "")]}
#  BOTH VANS ON ONE CELL as the world is posed.
TOGETHER = {"state.ttl": [(":van_b courier:at :c3_0 .", ":van_b courier:at :c0_0 .")]}
#  VAN B PARKED ACROSS THE ONLY SHORTEST PATH: van A at c0_1, parcel A at c1_1 owed at c3_1 — two drives
#  through c2_1, four round it — and van B standing on c2_1 with no parcel of its own.
PARKED = {"world.ttl": [("courier:destination :c0_3", "courier:destination :c3_1"),
                        (':parcel_b a courier:Parcel ; courier:destination :c3_3 ;\n    rdfs:label "the parcel owed at the top of the last column" .', "")],
          "state.ttl": [(":van_a courier:at :c0_0 .", ":van_a courier:at :c0_1 ."),
                        (":parcel_a courier:at :c0_1 .", ":parcel_a courier:at :c1_1 ."),
                        (":van_b courier:at :c3_0 .", ":van_b courier:at :c2_1 ."),
                        (":parcel_b courier:at :c3_1 .", "")]}
#  THE SAME WITH PARCEL A ALREADY ABOARD VAN A at c1_1, so only van A can deliver it.
CARRYING = {"world.ttl": PARKED["world.ttl"],
            "state.ttl": [(":van_a courier:at :c0_0 .", ":van_a courier:at :c1_1 ."),
                          (":parcel_a courier:at :c0_1 .", ":parcel_a courier:carriedBy :van_a ."),
                          (":van_b courier:at :c3_0 .", ":van_b courier:at :c2_1 ."),
                          (":parcel_b courier:at :c3_1 .", "")]}
#  TWO GRIDS A CONTINENT APART: van B and parcel B on a second 4x4 at x 10 to 13, no cell of which is
#  one apart from any of the first, so no drive crosses and no cell can ever hold both vans.
DISJOINT = {"world.ttl": [(":c3_3 a courier:Cell ; courier:x 3 ; courier:y 3 .",
                           ":c3_3 a courier:Cell ; courier:x 3 ; courier:y 3 .\n"
                           + "\n".join(f":g{x}_{y} a courier:Cell ; courier:x {x} ; courier:y {y} ."
                                       for x in range(10, 14) for y in range(4))),
                          ("courier:destination :c3_3", "courier:destination :g10_3")],
            "state.ttl": [(":van_b courier:at :c3_0 .", ":van_b courier:at :g10_0 ."),
                          (":parcel_b courier:at :c3_1 .", ":parcel_b courier:at :g10_1 .")]}


def _local(iri: str | None) -> str | None:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1] if iri else None


def _dt(instant: str) -> datetime:
    return datetime.fromisoformat(instant)


def variant(tmp_path: Path, name: str, edits: dict) -> Path:
    """The dispatcher with its documents rewritten — a copy, since a world imports its domains by the tree's shape."""
    world = tmp_path / name / "world" / "dispatcher"
    shutil.copytree(WORLD, world, ignore=shutil.ignore_patterns("tests", "secrets", "__pycache__"))
    (tmp_path / name / "domains").symlink_to(WORLD.parents[1] / "domains")
    for file, pairs in edits.items():
        text = (world / file).read_text()
        for old, new in pairs:
            assert old in text, f"{file} no longer says {old!r}"
            text = text.replace(old, new)
        (world / file).write_text(text)
    return world


class _Clock:
    """One timeline: every read moves it on by a second, as a running agent's clock does."""

    def __init__(self, at):
        self.at = at

    def __call__(self):
        self.at += timedelta(seconds=1)
        return self.at


def _pass(world: Path, budget: int = BUDGET):
    """One pass of the Planner over the booted world, from the present. The one imaginarium."""
    planner = Planner(boot(world, "dispatcher"), "dispatcher", budget=budget)
    planner.plan(NOW)
    (im,) = planner.imaginaria.values()
    return im


def _wants(im) -> dict[str, str]:
    return {_local(r["w"]): _local(r["d"]) for r in rows(im, _WANTS_Q, ())}


def _plans(im) -> dict[str, tuple[str, int]]:
    return {_local(r["want"]): (_local(r["outcome"]), int(r["steps"])) for r in rows(im, _PLANS_Q, ())}


def _steps(im) -> dict[str, set[tuple]]:
    out: dict[str, set] = {}
    for r in rows(im, _STEPS_Q, ()):
        out.setdefault(_local(r["want"]), set()).add((_local(r["a"]), _local(r.get("van")), _local(r.get("parcel")), _local(r.get("to"))))
    return out


def _weighed(im) -> dict[str, int]:
    return {_local(r["for"]): int(r["n"]) for r in rows(im, _WEIGHED_Q, ())}


def _spent(im) -> dict[str, int]:
    return {_local(r["for"]): int(r["n"]) for r in rows(im, _SPENT_Q, ())}


def _by_van(im) -> dict[str, dict[str, int]]:
    out: dict[str, dict] = {}
    for r in rows(im, _BY_VAN_Q, ()):
        out.setdefault(_local(r["for"]), {})[_local(r["van"])] = int(r["n"])
    return out


def _remaining(im) -> dict[str, float]:
    return {_local(r["for"]): float(r["left"]) for r in rows(im, _REMAINING_Q, ())}


def _costs(im) -> dict[str, float]:
    return {_local(r["want"]): float(r["spent"]) for r in rows(im, _COSTS_Q, ())}


def _targets(im, want: str) -> set[str]:
    return {_local(r["t"]) for r in rows(im, _TARGETS_Q, (), w=D + want)}


def _shared(store, graphs) -> dict[str, list[str]]:
    """Per graph among `graphs`, the cells two vans stand on in it — only those holding one."""
    found = {_local(g): sorted(_local(r["cell"]) for r in rows(store, _SHARED_Q, (), w=g)) for g in graphs}
    return {g: cells for g, cells in found.items() if cells}


def _refused(im) -> dict[str, int]:
    """Per want, how many of its weighings an invariant refused."""
    out: dict[str, int] = {}
    for want in {_local(r["w"]) for r in rows(im, _WANTS_Q, ())}:
        out[want] = sum(1 for r in rows(im, _JUDGED_Q, (), want=D + want) if r.get("refused"))
    return {w: n for w, n in out.items() if n}


def _bounded(im, want: str) -> None:
    """THE BOUND'S PROMISE, asserted of one want's search: no world holding two vans on a cell was
    opened, is open, or is an achiever — every such world the search made was refused by the
    aversion, or passed over by hash as a repeat of one, and a refused weighing is neither open nor
    expanded. The loop is held to judging at least one world."""
    judged = {r["w"]: r for r in rows(im, _JUDGED_Q, (), want=D + want)}
    assert judged
    colliding = {g for g in (r["w"] for r in rows(im, _WORLDS_Q, ())) if rows(im, _SHARED_Q, (), w=g)}
    for w in colliding:
        row = judged.get(w)
        assert row is None or (_local(row.get("refused")) == AVERSION and not row.get("open") and not row.get("expanded")), \
            f"a world holding two vans was neither refused nor passed over: {_local(w)} {row}"
    for w, row in judged.items():
        if row.get("refused"):
            assert w in colliding, f"refused, and holding no two vans: {_local(w)}"
            assert not row.get("open") and not row.get("expanded"), f"refused and still on the frontier: {_local(w)}"


def _at(store) -> dict[str, str]:
    return {_local(r["x"]): _local(r["cell"]) for r in rows(store, _AT_Q, ()) if r["x"].startswith(D)}


def _run(world: Path, passes: int = 40, budget: int = BUDGET):
    """The runtime over the booted world, pass after pass with the clock moved on by a drive's least
    landing between passes, until no intention stands or `passes` are spent; every step taken traced
    as (step, van A's cell, van B's cell, the cells two vans share) read off the beliefs the moment it
    was taken. A DRIVE LANDS HALF A MINUTE AFTER IT IS TAKEN (#901), so a plan of drives is walked
    across as many passes as it has drives, each pass taking the head that has landed."""
    time = _Clock(NOW)
    clock.now = time
    beliefs = boot(world, "dispatcher")
    runtime = Runtime(beliefs, "dispatcher", budget=budget)
    executor = runtime.parts["execution"].executor
    trace: list[tuple] = []

    def traced(event):
        at = _at(beliefs)
        trace.append((_local(event.step), at.get("van_a"), at.get("van_b"), _shared(beliefs, graphs_of(beliefs, STATE))))
        return []
    executor.step_taken.connect(traced)
    outcome = runtime.run(passes=1, poll_s=0)
    for _ in range(passes - 1):
        if outcome != UNFINISHED or not executor.standing():
            break
        time.at += timedelta(seconds=DRIVE_LEAST_S)
        outcome = runtime.run(passes=1, poll_s=0)
    return runtime, outcome, trace


@pytest.fixture
def ticking(monkeypatch):
    monkeypatch.setattr(clock, "now", lambda: NOW)


def test_the_boot_says_what_each_graph_is_and_two_vans_are_one_scope(ticking):
    """One scope, and both vans in it with both parcels: nothing van A does reads a fact of van B, but a
    parcel is a filling value of either van's Pick, so the parcels join the vans — by key as by predicate."""
    beliefs = boot(WORLD, "dispatcher")
    assert len(graphs_of(beliefs, DESIRE)) == 1 and len(graphs_of(beliefs, STATE)) == 1
    assert _at(beliefs) == {"van_a": "c0_0", "parcel_a": "c0_1", "van_b": "c3_0", "parcel_b": "c3_1"}
    members: dict[str, set] = {}
    for r in rows(beliefs, _MEMBERS_Q, ()):
        members.setdefault(_local(r["m"]), set()).add(r["s"])
    scopes = {s for ss in members.values() for s in ss}
    assert len(scopes) == 1, f"two vans in one courier vocabulary are one scope: {scopes}"
    assert {"van_a", "van_b", "parcel_a", "parcel_b", "Drive", "Pick", "Drop", "at", "carriedBy"} <= set(members)


def test_apart_two_parcels_the_aversion_can_make_collide_are_one_want_and_one_ten_step_plan(ticking, tmp_path):
    """ONE want about both parcels, targeting both, and one plan of ten steps over both vans, both
    delivered in one pass. The aversion reads `at` on vans joined on the cell and either van can reach
    every cell of the one grid from where it stands, so a plan for either parcel can collide with a plan
    for the other, and the derivation couples the two (one-mind-couples-the-wants-a-constraint-can-make-collide).
    THE ESTIMATE IS THE DESIRE'S SUM OVER BOTH: in the present ground it reads ten, the five each van alone
    reads added, which is the joint plan's own cost — the A* key the coupled search wants, admissible and
    tight. WHAT THE COUPLING COSTS IS THE PRODUCT: 228 candidates weighed, 148 of them worlds, against 50
    for two wants apart and 13 for a van alone, every interleaving of the two chains standing at ten on
    the frontier and opened in turn; at the default budget of 128 the search is cut short and the passes
    after would finish it, so this world's tests state 256 (measure-the-search). Apart, no world the
    search visits holds two vans on a cell, so the bound (#902) refuses nothing and the count is what it
    was before it — the aversion is weighed in every world the search weighs, 148, and reads met in all.
    AND TWO PARCELS ON DISJOINT GRIDS ARE TWO WANTS exactly as before: the aversion over what the vans
    can reach yields no row, nothing couples them, and each is planned alone at 23 weighings with its
    own estimate, five."""
    cut = _pass(WORLD, budget=128)
    assert _plans(cut) == {JOINT: ("Exhausted", 0)} and _spent(cut)[JOINT] == 128, \
        "the default budget cuts the coupled search short; the passes after finish it"
    im = _pass(WORLD)
    assert _wants(im) == {JOINT: "every_parcel_delivered"}
    assert _targets(im, JOINT) == {"parcel_a", "parcel_b"}, "a coupled want's met-test targets each instance"
    plans, steps = _plans(im), _steps(im)
    assert plans == {JOINT: ("Satisfied", 10)}
    assert {van for _, van, _, _ in steps[JOINT] if van} == {"van_a", "van_b"}
    assert {parcel for _, _, parcel, _ in steps[JOINT] if parcel} == {"parcel_a", "parcel_b"}
    assert _shared(im, [r["w"] for r in rows(im, _WORLDS_Q, ())]) == {}, "apart, no world the search visits holds two vans on a cell"
    paid, left, spent = _weighed(im), _remaining(im), _spent(im)
    halves_paid, halves_left = {}, {}
    for name, edits in (("a", HALF_A), ("b", HALF_B)):
        half = _pass(variant(tmp_path, name, edits), budget=128)
        (want,) = _plans(half)
        assert _plans(half)[want] == ("Satisfied", 5)
        halves_paid[want] = _weighed(half)[want]
        halves_left[want] = _remaining(half)[want]
    assert left[JOINT] == sum(halves_left.values()) == 10.0, f"the coupled want's estimate is the sum of its instances': {left} against {halves_left}"
    assert halves_paid == {"every_parcel_delivered.pursued.parcel_a": 13, "every_parcel_delivered.pursued.parcel_b": 13}
    assert (spent[JOINT], paid[JOINT]) == (228, 148), f"the product's price, measured: {spent} candidates, {paid} worlds"
    assert _refused(im) == {} and paid[AVERSION] == 148, "the invariant weighed in every world, refusing none: " + str(paid)
    runtime, outcome, trace = _run(WORLD)
    assert outcome == UNFINISHED and len(trace) == 10, "a desire holds the agent, and the one plan is walked, a drive a pass"
    assert _at(runtime.beliefs) == {"van_a": "c0_3", "parcel_a": "c0_3", "van_b": "c3_3", "parcel_b": "c3_3"}
    executor = runtime.parts["execution"].executor
    assert int(rows(executor.intentions, _INTENTIONS_Q, ())[0]["n"]) == 1 and executor.walking() == [], \
        "one plan, one intention, done: the cluster left once parcel A was delivered is the coupled want's, not a second want's"
    apart = _pass(variant(tmp_path, "disjoint", DISJOINT), budget=128)
    assert _wants(apart) == {"every_parcel_delivered.pursued.parcel_a": "every_parcel_delivered",
                             "every_parcel_delivered.pursued.parcel_b": "every_parcel_delivered"}
    assert _plans(apart) == {"every_parcel_delivered.pursued.parcel_a": ("Satisfied", 5),
                             "every_parcel_delivered.pursued.parcel_b": ("Satisfied", 5)}
    assert _weighed(apart) == {"every_parcel_delivered.pursued.parcel_a": 23, "every_parcel_delivered.pursued.parcel_b": 23, AVERSION: 42}, \
        "the aversion reads `at`, which the drive writes, so it is weighed in every world though no world of two grids can enter it: " + str(_weighed(apart))
    assert _refused(apart) == {}
    assert _remaining(apart) == {"every_parcel_delivered.pursued.parcel_a": 5.0, "every_parcel_delivered.pursued.parcel_b": 5.0}


def test_corridor_the_coupled_search_refuses_the_worlds_holding_two_vans_and_the_joint_plan_shares_no_cell(ticking, tmp_path):
    """One want, one plan of ten steps over both vans, 286 candidates. The search REACHES worlds holding
    two vans on one cell — a van driven onto the cell the other stands on — and the bound (#902) refuses
    every one: the aversion, weighed in each of the 210 possible worlds the want is weighed in, carries
    a violation row there its parent's weighing does not, so the world is off the frontier and never an
    achiever, `planning:refused` naming the aversion. Thirteen are refused; three more worlds holding
    two vans were forked and passed over by hash as repeats of a refused one, which is what `take`
    leaves and `weigh` says. No world opened, open or met holds two vans. The plan is the one the
    search found before the bound — the colliding interleavings were never on the shortest path, so the
    bound cost it ten candidates and no steps — and WALKED, one head at a time, it puts both vans on no
    cell at any act: promised by the bound now, where before it was pinned as what happened to be true.
    Before the coupling each plan drove its van through `c2_1` at its third step and the two were walked
    in lockstep, both on the cell for one act (measure-the-search)."""
    corridor = variant(tmp_path, "corridor", CORRIDOR)
    im = _pass(corridor, budget=CORRIDOR_BUDGET)
    plans, steps = _plans(im), _steps(im)
    assert _wants(im) == {JOINT: "every_parcel_delivered"}
    assert plans == {JOINT: ("Satisfied", 10)}
    assert _spent(im)[JOINT] == 286, f"measured: {_spent(im)}"
    assert _weighed(im) == {JOINT: 210, AVERSION: 210}, "the invariant is weighed in every world the want is: " + str(_weighed(im))
    assert ("Drive", "van_a", None, "c2_1") in steps[JOINT] and ("Drive", "van_b", None, "c2_1") in steps[JOINT], \
        "both chains still cross the shared cell, one van at a time"
    held = _shared(im, [r["w"] for r in rows(im, _WORLDS_Q, ())])
    assert len(held) == 16 and {cell for cells in held.values() for cell in cells} == {"c1_1", "c2_0", "c2_1", "c2_2", "c3_1"}, \
        f"worlds the coupled search reached with two vans on one cell: {held}"
    assert _refused(im) == {JOINT: 13}, f"refused by the aversion, measured: {_refused(im)}"
    _bounded(im, JOINT)
    runtime, outcome, trace = _run(corridor, budget=CORRIDOR_BUDGET)
    assert outcome == UNFINISHED and len(trace) == 10
    met = [(step, shared) for step, _, _, shared in trace if shared]
    assert met == [], f"walked, the joint plan puts two vans on no cell at any act — the bound's promise: {trace}"
    assert _at(runtime.beliefs) == {"van_a": "c3_1", "parcel_a": "c3_1", "van_b": "c2_0", "parcel_b": "c2_0"}


@pytest.mark.parametrize("name, edits, steps, spent, refused, by, at", [
    ("parked", PARKED, 5, 56, 7, {"van_b"}, {"van_a": "c0_1", "van_b": "c3_1", "parcel_a": "c3_1"}),
    ("carrying", CARRYING, 4, 66, 5, {"van_a", "van_b"}, {"van_a": "c3_1", "van_b": "c2_0", "parcel_a": "c3_1"}),
])
def test_a_van_parked_across_the_only_shortest_path_is_not_driven_through(ticking, tmp_path, name, edits, steps, spent, refused, by, at):
    """Van B stands on `c2_1` with nothing to do, parcel A is owed at `c3_1` from `c1_1`, and the only
    two-drive route runs through B. Before the bound the search drove through — five steps, eleven of
    66 worlds holding two vans, judged by nobody, and the walk put both vans on `c2_1` for an act
    (measure-the-search). With it, every world that puts van A on B's cell is refused, and the ONE MIND
    holding both vans does better than the seven-step route round the record expected: PARKED, with
    the parcel on the ground beside van B, it delivers with van B itself in five steps and van A
    never moves; CARRYING, with the parcel already aboard van A so only A can deliver it, it moves
    van B aside first and drives A through — four steps, where the route round is five. In neither
    does an opened world hold two vans, and walked, the vans share no cell at any act."""
    world = variant(tmp_path, name, edits)
    im = _pass(world, budget=128)
    want = "every_parcel_delivered.pursued.parcel_a"
    assert _wants(im) == {want: "every_parcel_delivered"}
    assert _plans(im) == {want: ("Satisfied", steps)}
    assert {van for _, van, _, _ in _steps(im)[want] if van} == by, _steps(im)[want]
    assert (_spent(im)[want], _refused(im)) == (spent, {want: refused}), f"measured: {_spent(im)} {_refused(im)}"
    _bounded(im, want)
    runtime, outcome, trace = _run(world, budget=128)
    assert outcome == UNFINISHED and len(trace) == steps
    assert [(step, shared) for step, _, _, shared in trace if shared] == [], f"two vans on one cell at an act: {trace}"
    assert _at(runtime.beliefs) == at


@pytest.mark.parametrize("name, edits, budget, tight", [("apart", {}, BUDGET, True), ("corridor", CORRIDOR, CORRIDOR_BUDGET, True),
                                                        ("half_a", HALF_A, 128, True), ("parked", PARKED, 128, True),
                                                        ("carrying", CARRYING, 128, False)])
def test_a_wants_estimate_at_the_present_never_exceeds_what_its_plan_cost(ticking, tmp_path, name, edits, budget, tight):
    """THE ONE PROMISE AN ESTIMATE MAKES, as a gate: what a want's estimate read in the present ground
    (`planning:remaining` on the ground's weighing) is at most what the plan the search found spent
    (`planning:spent` on the plan). An estimate that overstates lets a pass end with a dearer plan
    than exists, and until #898 nothing in the suite held one to it — the courier's comment said it
    and eyes checked. Every want with a plan here is judged, and the loop is held to judging at least
    one, since an empty frontier would pass an `all` over nothing. Mostly the figure is TIGHT — ten
    against ten for the coupled want, five against five for a van alone: the drive, the pick, the two
    drives and the drop of each parcel are each certain, and the estimate counts each once. NOT WHERE
    THE BOUND COSTS A STEP THE WANT DOES NOT OWE: with the parcel aboard van A and van B parked on the
    only short route, the estimate reads three — two drives and the drop — and the plan costs four,
    since moving van B aside is a step of the aversion's and not the parcel's; admissible, loose by
    one, which is the slack the invariant makes and the search pays for with its frontier (#902)."""
    im = _pass(variant(tmp_path, name, edits) if edits else WORLD, budget=budget)
    left, costs = _remaining(im), _costs(im)
    judged = {w: (left[w], costs[w]) for w in costs if w in left}
    assert judged and set(judged) == {w for w, (outcome, _) in _plans(im).items() if outcome == "Satisfied"}, \
        f"every want the search found a plan for has an estimate at the present: {left} against {costs}"
    assert all(estimate <= cost for estimate, cost in judged.values()), \
        f"an estimate never overstates what the plan cost: {judged}"
    assert all((estimate == cost) == tight for estimate, cost in judged.values()), \
        f"{'tight, each certain step counted once' if tight else 'loose by the step the bound costs'}: {judged}"


def test_a_drive_lands_within_its_band_and_the_steps_and_worlds_advance_along_the_path(ticking):
    """THE COURIER'S LANDING BAND (#901), probed on the plan it places and not only on the outcome,
    since a `landsAfter` text that will not parse is read as nought and the walk would still deliver.
    Each step of the joint plan opens where the step before it lands — `execution:notBefore` is the
    previous `landsAt` — a drive lands half a minute after it opens at the earliest and a minute after
    the plan's latest so far at the latest, and a pick or a drop lands at once; so the six drives land
    at six distinct instants, the plan's last step lands no earlier than three minutes after the root
    and no later than six, and every possible world holds over the period its step's two ends say,
    where before the band every world and step stood at the pass's one instant
    (a-landing-is-a-band-and-a-world-holds-over-a-period). ADOPTED, each committed step is believed
    from its opening to its latest landing plus the patience — a drive's window two minutes and more,
    no longer the patience alone — with `landsWithinS` the band's least and `answeredWithinS` the window's
    whole length. The band shifts instants and not the frontier's order: the candidates, the weighings
    and the steps are the figures `test_apart` pins, unchanged."""
    im = _pass(WORLD)
    placed = rows(im, _PLACED_Q, (), want=D + JOINT)
    assert len(placed) == 10
    least = {"Drive": DRIVE_LEAST_S, "Pick": 0, "Drop": 0}
    most = {"Drive": DRIVE_MOST_S, "Pick": 0, "Drop": 0}
    opens, latest = NOW, NOW
    landings = []
    for r in placed:
        action, nb, la, na = _local(r["a"]), _dt(r["nb"]), _dt(r["la"]), _dt(r["na"])
        assert nb == opens, f"a step opens where the one before it lands: {action} {nb} against {opens}"
        assert la == nb + timedelta(seconds=least[action]) and na == latest + timedelta(seconds=most[action]), \
            f"the band, summed along the path: {action} opens {nb}, lands {la}, latest {na}"
        assert (_dt(r["ws"]), _dt(r["we"])) == (la, na), "the world a step reaches holds over the period the step's two ends say"
        if action == "Drive":
            landings.append(la)
        opens, latest = la, na
    assert len(landings) == len(set(landings)) == 6, f"six drives, six distinct landings: {landings}"
    assert (opens, latest) == (NOW + timedelta(minutes=3), NOW + timedelta(minutes=6)), "the plan's last step lands between three and six minutes out"
    runtime, outcome, trace = _run(WORLD, passes=1)
    assert outcome == UNFINISHED and len(trace) == 1, "one pass takes the first drive, which has not landed when the pass ends"
    windows = rows(runtime.beliefs, _WINDOWS_Q, ())
    assert len(windows) == 10, "every step of the adopted plan is a belief over its window"
    for w in windows:
        length, within, by = (_dt(w["e"]) - _dt(w["s"])).total_seconds(), float(w["within"]), float(w["by"])
        assert within in (0.0, float(DRIVE_LEAST_S)) and by == length and length > PATIENCE_S, f"a window is its step's band plus the patience: {w}"
    assert sum(1 for w in windows if float(w["within"]) == DRIVE_LEAST_S) == 6 and len({w["s"] for w in windows}) == 7, \
        "six drives land within the least; a pick or a drop opens where its drive landed"


def test_two_vans_on_one_cell_at_a_pass_start_mint_the_aversions_want_and_a_drive_parts_them(ticking, tmp_path):
    """The aversion, the avoided state under `planning:unmetWhen` (#892): both vans on c0_0 as posed, it
    reads unmet with a witness per van, each offending with c0_0, one want is minted under it — about
    both, targeting both, carrying the same select under the same term — and a one-step plan, a
    drive, satisfies it; run, the vans stand apart. AN INVARIANT UNMET IN THE ROOT BOUNDS NOTHING (#902):
    the aversion's own search refuses no world, since every child either keeps the root's two rows or
    removes them, and a repair enters no state. BESIDE IT THE TWO PARCELS ARE ONE COUPLED WANT, and
    from one cell the joint delivery is thirteen steps whose product no budget tried pays — Exhausted
    at 128 here and at 512, measured — which is the record's seam on the product's budget and the
    trigger for its fallback, not this test's to settle; the bound refuses seven of its 128 candidates,
    the worlds that part the vans and bring them together again on another cell, and the aversion's
    want is found beside it in 4 weighings as before."""
    together = variant(tmp_path, "together", TOGETHER)
    im = _pass(together, budget=128)
    assert {(_local(r["x"]), _local(r["cell"])) for r in rows(im, _WITNESSES_Q, (), d=D + "no_cell_holds_two_vans")} == \
        {("van_a", "c0_0"), ("van_b", "c0_0")}, "the avoided state is judged in the present: a row per van, the cell offending"
    assert _wants(im) == {"no_cell_holds_two_vans.pursued": "no_cell_holds_two_vans", JOINT: "every_parcel_delivered"}
    assert [(_local(r["p"]), _local(r["o"])) for r in rows(im, _POLARITY_Q, (), w=D + "no_cell_holds_two_vans.pursued")] == \
        [("unmetWhen", "no_cell_holds_two_vans.pursued.avoided")]
    assert _plans(im)["no_cell_holds_two_vans.pursued"] == ("Satisfied", 1)
    assert _plans(im)[JOINT] == ("Exhausted", 0), "the product's budget: the record's seam, pinned"
    assert {a for a, *_ in _steps(im)["no_cell_holds_two_vans.pursued"]} == {"Drive"}
    assert _weighed(im)["no_cell_holds_two_vans.pursued"] == 4, "what the met-test form cost, measured: " + str(_weighed(im))
    assert _refused(im) == {JOINT: 7}, "the aversion's own want is refused nothing; the joint want, the worlds that meet again: " + str(_refused(im))
    runtime, outcome, trace = _run(together, budget=128)
    at = _at(runtime.beliefs)
    assert at["van_a"] != at["van_b"], at
