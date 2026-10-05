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
  here as a gate over the shipped world, the corridor and a van alone;
- on a corridor, the one coupled search visits worlds holding two vans on one cell and nothing refuses
  them, since the bound (#902) is not built: the aversion, a desire, is weighed in no possible world,
  and the joint plan found is pinned as it is, collision and all, so the bound's arrival is seen here;
- two vans on one cell at a PASS'S START are seen: the aversion — the avoided state itself, under
  `planning:unmetWhen`, judged as a met-test is since #892 — reads unmet with a witness per van and
  the cell as the offending value, its want is minted carrying the same select, and a one-step plan
  parts them; the two parcels' coupled want beside it is the product's price no budget here pays.
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
#  WHAT THE COUPLED SEARCH NEEDS: 228 candidates on the shipped pose and 296 on the corridor, measured
#  (measure-the-search), so the default budget of 128 cuts it short and the tests state their own.
BUDGET, CORRIDOR_BUDGET = 256, 512

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


def _at(store) -> dict[str, str]:
    return {_local(r["x"]): _local(r["cell"]) for r in rows(store, _AT_Q, ()) if r["x"].startswith(D)}


def _run(world: Path, passes: int = 1, budget: int = BUDGET):
    """The runtime over the booted world for `passes`, every step taken traced as (step, van A's cell,
    van B's cell, the cells two vans share) read off the beliefs the moment it was taken."""
    time = _Clock(NOW)
    clock.now = time
    beliefs = boot(world, "dispatcher")
    runtime = Runtime(beliefs, "dispatcher", budget=budget)
    runtime.time = time
    executor = runtime.parts["execution"].executor
    trace: list[tuple] = []

    def traced(event):
        at = _at(beliefs)
        trace.append((_local(event.step), at.get("van_a"), at.get("van_b"), _shared(beliefs, graphs_of(beliefs, STATE))))
        return []
    executor.step_taken.connect(traced)
    outcome = runtime.run(passes=passes, poll_s=0)
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
    search visits holds two vans on a cell. AND TWO PARCELS ON DISJOINT GRIDS ARE TWO WANTS exactly as
    before: the aversion over what the vans can reach yields no row, nothing couples them, and each is
    planned alone at 23 weighings with its own estimate, five."""
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
    runtime, outcome, trace = _run(WORLD)
    assert outcome == UNFINISHED and len(trace) == 10, "a desire holds the agent, and the one plan is walked in one pass"
    assert _at(runtime.beliefs) == {"van_a": "c0_3", "parcel_a": "c0_3", "van_b": "c3_3", "parcel_b": "c3_3"}
    apart = _pass(variant(tmp_path, "disjoint", DISJOINT), budget=128)
    assert _wants(apart) == {"every_parcel_delivered.pursued.parcel_a": "every_parcel_delivered",
                             "every_parcel_delivered.pursued.parcel_b": "every_parcel_delivered"}
    assert _plans(apart) == {"every_parcel_delivered.pursued.parcel_a": ("Satisfied", 5),
                             "every_parcel_delivered.pursued.parcel_b": ("Satisfied", 5)}
    assert _weighed(apart) == {"every_parcel_delivered.pursued.parcel_a": 23, "every_parcel_delivered.pursued.parcel_b": 23}
    assert _remaining(apart) == {"every_parcel_delivered.pursued.parcel_a": 5.0, "every_parcel_delivered.pursued.parcel_b": 5.0}


def test_corridor_the_coupled_search_finds_the_joint_plan_and_nothing_yet_refuses_the_worlds_holding_two_vans(ticking, tmp_path):
    """One want, one plan of ten steps over both vans, 296 candidates. The search VISITS worlds holding
    two vans on one cell — a van driven onto the cell the other stands on — and refuses none of them,
    because the bound (#902) is not built: the aversion is a desire, weighed in grounds alone and in no
    possible world. Pinned as it is now, so the bound's arrival is seen here: how many such worlds the
    search visits, and whether the plan found, walked one head at a time, puts both vans on `c2_1` for
    an act. Before the coupling each plan drove its van through `c2_1` at its third step and the two were
    walked in lockstep, both on the cell for one act (measure-the-search)."""
    corridor = variant(tmp_path, "corridor", CORRIDOR)
    im = _pass(corridor, budget=CORRIDOR_BUDGET)
    plans, steps = _plans(im), _steps(im)
    assert _wants(im) == {JOINT: "every_parcel_delivered"}
    assert plans == {JOINT: ("Satisfied", 10)}
    assert _spent(im)[JOINT] == 296, f"measured: {_spent(im)}"
    assert ("Drive", "van_a", None, "c2_1") in steps[JOINT] and ("Drive", "van_b", None, "c2_1") in steps[JOINT], \
        "both chains still cross the shared cell"
    held = _shared(im, [r["w"] for r in rows(im, _WORLDS_Q, ())])
    assert len(held) == 18 and {cell for cells in held.values() for cell in cells} == {"c1_1", "c2_0", "c2_1", "c2_2", "c3_1"}, \
        f"worlds the coupled search visits with two vans on one cell, refused by nothing yet: {held}"
    assert "no_cell_holds_two_vans" not in _weighed(im), "the aversion, a desire, is weighed in no possible world"
    runtime, outcome, trace = _run(corridor, budget=CORRIDOR_BUDGET)
    assert outcome == UNFINISHED and len(trace) == 10
    met = [(step, shared) for step, _, _, shared in trace if shared]
    assert met == [], f"the plan found happens to move the vans one at a time past c2_1; pinned, not promised: {trace}"
    assert _at(runtime.beliefs) == {"van_a": "c3_1", "parcel_a": "c3_1", "van_b": "c2_0", "parcel_b": "c2_0"}


@pytest.mark.parametrize("name, edits, budget", [("apart", {}, BUDGET), ("corridor", CORRIDOR, CORRIDOR_BUDGET), ("half_a", HALF_A, 128)])
def test_a_wants_estimate_at_the_present_never_exceeds_what_its_plan_cost(ticking, tmp_path, name, edits, budget):
    """THE ONE PROMISE AN ESTIMATE MAKES, as a gate: what a want's estimate read in the present ground
    (`planning:remaining` on the ground's weighing) is at most what the plan the search found spent
    (`planning:spent` on the plan). An estimate that overstates lets a pass end with a dearer plan
    than exists, and until #898 nothing in the suite held one to it — the courier's comment said it
    and eyes checked. Every want with a plan here is judged, and the loop is held to judging at least
    one, since an empty frontier would pass an `all` over nothing. Here the figure is TIGHT — ten against
    ten for the coupled want, five against five for a van alone: the drive, the pick, the two drives and
    the drop of each parcel are each certain, and the estimate counts each once."""
    im = _pass(variant(tmp_path, name, edits) if edits else WORLD, budget=budget)
    left, costs = _remaining(im), _costs(im)
    judged = {w: (left[w], costs[w]) for w in costs if w in left}
    assert judged and set(judged) == {w for w, (outcome, _) in _plans(im).items() if outcome == "Satisfied"}, \
        f"every want the search found a plan for has an estimate at the present: {left} against {costs}"
    assert all(estimate <= cost for estimate, cost in judged.values()), \
        f"an estimate never overstates what the plan cost: {judged}"
    assert all(estimate == cost for estimate, cost in judged.values()), \
        f"and here it is tight, each certain step counted once: {judged}"


def test_two_vans_on_one_cell_at_a_pass_start_mint_the_aversions_want_and_a_drive_parts_them(ticking, tmp_path):
    """The aversion, the avoided state under `planning:unmetWhen` (#892): both vans on c0_0 as posed, it
    reads unmet with a witness per van, each offending with c0_0, one want is minted under it — about
    both, targeting both, carrying the same select under the same term — and a one-step plan, a
    drive, satisfies it; run, the vans stand apart. BESIDE IT THE TWO PARCELS ARE ONE COUPLED WANT, and
    from one cell the joint delivery is thirteen steps whose product no budget tried pays — Exhausted
    at 128 here and at 512 in 32 seconds, measured — which is the record's seam on the product's budget
    and the trigger for its fallback, not this test's to settle; the aversion's want is found beside it
    in 4 weighings as before."""
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
    runtime, outcome, trace = _run(together, budget=128)
    at = _at(runtime.beliefs)
    assert at["van_a"] != at["van_b"], at
