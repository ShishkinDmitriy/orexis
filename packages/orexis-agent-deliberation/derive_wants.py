"""`derive_wants`: the wants every desire's judgments imply, minted under their desires — the
second of the road's two functions (judge-desires-then-derive-wants), reading the judgment
graph with one select and nothing in hand — and the minting beside it: which results cluster
into one want (a scope), what the want is named, the desire's met-test narrowed to the want's,
and how far ahead a desire foresees.

After the call, every want the store's judgments imply stands in the store; what was minted
this time comes back for the caller that asked whether its own want was re-minted.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from orexis_agent_progression import clock
from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.store import bindings

from .judge_desires import Witness
from .judgments import find_judgments
from .want import Want

log = logging.getLogger("derive_wants")


def derive_wants(agent) -> list[str]:
    """Mint a want under every desire for every cluster of its judgments' results that has
    none, and return what was minted — the second of the road's two functions, reading the
    judgments `judge_desires` wrote with one select and nothing in hand
    (judge-desires-then-derive-wants). Run whenever a pass stands on a root or on any want
    under it, and by a package that has just written an instance, since a claim arriving
    should be a want arriving and not a want on the next tick. A package that calls this
    mints nothing; it says an instance is there and the road does the rest
    (one-road-derives-every-want).

    The instant is EACH CLUSTER'S OWN. A desire unmet at the present derives wants with none.
    One met at the present derives them at the instants it foresees unmet — and two debts
    cross at two deadlines, so the second is not filtered away by the first's; each cluster
    holds at its earliest result, and one past the foresight is not derived. A desire met at
    the present with nothing foreseen derives NOTHING: there is nothing to pursue, and a want
    about everything the desire is about is minted only for a desire unmet at the present
    with no result — a met-test the compiler refused, judged by the choir — which is what
    every want was before the road.
    """
    by_desire: dict[str, list[dict]] = {}
    for row in find_judgments(agent.beliefs):
        by_desire.setdefault(row["desire"], []).append(row)
    minted: list[str] = []
    for root, rows in sorted(by_desire.items()):
        minted += _derive_under(agent, root, rows)
    return minted


def _derive_under(agent, root: str, rows: list[dict]) -> list[str]:
    """The wants one desire's judgments imply, minted where none stands. `rows` are the
    judgment graph's: one per result, a met judgment's row naming no focus."""
    now = clock.now()
    present = [r for r in rows if not r.get("at")]
    if not present:
        return []
    if present[0]["met"] != "true":
        unmet_now, ahead = True, None
        found = [Witness(instance=r["focus"], constraint=r["k"], about=r.get("about"), at=now)
                 for r in present if r.get("focus")]
    else:
        unmet_now, ahead = False, foresees_of(agent, root)
        if ahead is None:
            return []
        seen: dict[tuple[str, str], Witness] = {}
        for r in sorted((r for r in rows if r.get("at") and r["met"] != "true" and r.get("focus")),
                        key=lambda r: r["at"]):
            at = datetime.fromisoformat(r["at"])
            if (at - now).total_seconds() > ahead:
                continue
            seen.setdefault((r["focus"], r["k"]), Witness(
                instance=r["focus"], constraint=r["k"], about=r.get("about"), at=at))
        found = sorted(seen.values(), key=lambda w: (w.at, w.instance, w.constraint))
        if not found:
            return []
    #  ONE WANT PER SCOPE OF WHAT IS IN TROUBLE, and per INSTANCE: the results clustered by
    #  which of them some action can move together, and a want minted per cluster about
    #  exactly those, holding at the earliest instant among them. Every shipped world is one
    #  scope, so two properties of one bed are one want; two debts are two instances and two
    #  wants. A cluster that already has its want — `about` for `about` — is left standing.
    #
    #  UNLESS WHAT WAS FORESEEN HAS ARRIVED. A want minted at a foreseen instant says "hold
    #  at T", and a plan for it is placed to land at T (#619). A cluster unmet NOW whose want
    #  still says T — the holder asked before the claim lapsed, the pot crossed before the
    #  drift said it would — is re-minted with no instant, under the same name, so the
    #  trace, a remembered plan and the keeper meet the want they kept and a plan is found
    #  from the present. The instant was the road's reading of the predictions; the present
    #  outranks it, as it does everywhere else here.
    #  STANDING IS BY NAME, and the name is the cluster's: what it is about, and which instance
    #  where the desire ranges over several (`name_of`). Two tanks low about their level are
    #  two clusters and two names; keyed by what they were about alone, the second read the
    #  first as standing, and by construction the second mint had overwritten the first.
    standing = {w.uri: w for w in agent.wants.find_all_by_desire(root)}
    minted = []
    for cluster in _clusters(agent, found) or [[]]:
        about = tuple(sorted({w.about for w in cluster if w.about}))
        instances = {w.instance for w in cluster}
        instance = next(iter(instances)) if len(instances) == 1 else None
        child = name_of(agent, root, about, instance)
        stood = standing.get(child)
        if stood is not None and not (unmet_now and stood.holds_at):
            continue
        if stood is not None:
            log.info("%s: what was foreseen at %s has arrived", stood.uri.rsplit("#", 1)[-1],
                     stood.holds_at)
        instant = min((w.at for w in cluster), default=None) if ahead is not None else None
        child = mint(agent, root, holds_at=instant, about=about, instance=instance)
        if child is not None:
            minted.append(child)
    return minted


def _clusters(agent, witnesses: list) -> list[list]:
    """The witnesses grouped by SCOPE — which of them some action can move together — so a
    want is minted per group. Two in one scope are one want and one cone; two in different
    scopes are two, planned apart and concatenated, which is the mechanism `scope.md` says the
    concept exists for. A witness naming no property joins every group it could belong to, which
    with one scope is the one group.

    Measured on every shipped world: one scope, so one group. The code path is the same the
    day a world splits, and a scope is over PREDICATES — two debts to two hosts are one scope,
    correctly, since they may draw from one vessel."""
    if not witnesses:
        return []
    from . import relevance
    parts = agent.beliefs.remember("deliberation:scopes", lambda: relevance.scopes(
        relevance.actions_of(agent.beliefs.query), relevance.rule_edges()))
    def scope_of(about):
        return next((i for i, part in enumerate(parts) if about in part), None)
    groups: dict = {}
    loose = []
    for w in witnesses:
        #  KEYED BY INSTANCE TOO: a desire whose shape targets the agent has one instance and
        #  one group per scope; one whose shape targets each debt has one group per debt, so
        #  a Serving step can name its claim. A witness about the instance itself — the block
        #  said `sh:this` — is its own group by construction.
        scope = scope_of(w.about) if w.about else None
        key = (scope, w.instance) if scope is not None or w.about == w.instance else None
        (groups.setdefault(key, []) if key is not None else loose).append(w)
    if not groups:
        return [loose]
    for w in loose:
        for group in groups.values():
            group.append(w)
    return list(groups.values())


def foresees_of(agent, root: str) -> float | None:
    """How far ahead this root derives a want from a prediction, in seconds, or None.

    ASKED OF THE CHOIR (#644): a root authored at genesis states no foresight, because the
    belief that says how far the agent looks ahead is a pick, and a root is not a function of
    the agent's state — whoever holds that belief answers `orexis:foresight` at the moment a
    child is derived, so a re-pick reaches the next derivation with no rebuild. An asserted want
    may still state `orexis:foresees`, read where no voice answers."""
    from orexis_agent_progression.ontology import FORESIGHT

    for answer in agent.ask(FORESIGHT, root):
        if answer is not None:
            return float(answer)
    rows = bindings(agent.desires.query_union(
        f"SELECT ?f WHERE {{ <{root}> orexis:foresees ?f }} LIMIT 1"))
    return float(rows[0]["f"]) if rows else None


def _tail(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def name_of(agent, root: str, about: tuple, instance: str | None) -> str:
    """The name of the want minted under `root` for one cluster of its witnesses: the root's,
    suffixed, so a second episode of the same cluster pursues the same node and everything
    keyed by it — the planner, a remembered plan, the trace, the keeper — finds what it kept.

    NAMED FOR WHAT IT IS ABOUT where that is NARROWER than the desire, so two wants under one
    desire — soil now, air later — are two nodes; and for the desire alone where it is not,
    which is every want there was before the road: a desire about one property mints
    `<desire>.pursued` exactly as it always did. AND FOR THE INSTANCE where the desire ranges
    over several — its shape targets a class, or whatever bears a property, rather than one
    node — since two tanks low about their level are two clusters, two plans, and would be one
    name otherwise (found by the road's own table, `tests/road/`); a desire whose shape names
    its one node (`sh:targetNode`, sensing's and the greenhouse's) keeps its names, and an
    instance the want is already about (a debt, `orexis:about sh:this`) is not said twice.
    """
    desire_abouts = tuple(sorted(
        r["a"] for r in bindings(agent.desires.query_union(
            f"SELECT ?a WHERE {{ <{root}> orexis:about ?a }}"))))
    tails = [_tail(a) for a in about] if about and set(about) != set(desire_abouts) else []
    if instance is not None and instance not in about and not _targets_one_node(agent, root):
        tails.insert(0, _tail(instance))
    return root + ".pursued" + "".join(f".{t}" for t in tails)


def _targets_one_node(agent, root: str) -> bool:
    """Does the root's met-test name the one node it is about (`sh:targetNode`)? Cached per
    root on the agent: a root never changes while the agent runs."""
    cache = agent.__dict__.setdefault("_root_targets_one", {})
    if root not in cache:
        cache[root] = bool(bindings(agent.desires.query_union(
            f"SELECT ?n WHERE {{ <{root}> orexis:metWhen ?s . ?s sh:targetNode ?n }} LIMIT 1")))
    return cache[root]


def mint(agent, root: str, holds_at: datetime | None = None, about: tuple = (),
         instance: str | None = None) -> str | None:
    """Derive the want pursued under `root` and write it to the pursued graph, named by
    `name_of`. None, and the root stays the goal, where the root states its met-test inline:
    a blank node has no name another graph could point at, and copying it would make a second
    owner of the claim."""
    desire_abouts = tuple(sorted(
        r["a"] for r in bindings(agent.desires.query_union(
            f"SELECT ?a WHERE {{ <{root}> orexis:about ?a }}"))))
    abouts = about or desire_abouts
    child = name_of(agent, root, about, instance)
    points_said = []
    #  The raw SPARQL-JSON rows, because the TYPE of the object matters here and
    #  `bindings` flattens it away: a blank node cannot be pointed at from another graph.
    said = agent.desires.query_union(f"""
SELECT ?p ?o WHERE {{ <{root}> ?p ?o .
  FILTER(?p IN (orexis:metWhen, orexis:unmetWhen, orexis:estimates, orexis:about)) }}""")
    met_test = None
    for sol in said.get("results", {}).get("bindings", []):
        if sol["o"]["type"] == "bnode":
            log.warning("%s states its %s inline; it is pursued itself", root.rsplit("#", 1)[-1],
                        sol["p"]["value"].rsplit("#", 1)[-1])
            return None
        #  WHAT IT IS ABOUT is the witnesses' where the shape named them per block, and the
        #  desire's whole where it did not; the avoided state and the estimate are pointed at
        #  as ever, and the met-test is carried, instantiated, below.
        if sol["p"]["value"].endswith("#about"):
            continue
        if sol["p"]["value"].endswith("#metWhen"):
            met_test = sol["o"]["value"]
            continue
        points_said.append(sol)
    #  THE MET-TEST IS THE DESIRE'S INSTANTIATED AT THE WITNESS: carved from where the root's
    #  shape lives and narrowed to this cluster — the instance as its target, the blocks about
    #  what the want is about — and written into the want's own graph under its own name, so
    #  the want is judged on its instance and a plan for one tank is not refused for another's.
    shape_lines: tuple = ()
    points = [(sol["p"]["value"], sol["o"]["value"]) for sol in points_said]
    if met_test is not None:
        own = child + ".met"
        shape_lines = narrowed(agent, met_test, own, instance, abouts)
        points.append((OREXIS_MET_WHEN, own))

    labels = bindings(agent.desires.query_union(
        f"SELECT ?l WHERE {{ <{root}> rdfs:label ?l }} LIMIT 1"))
    label = "pursued: " + (labels[0]["l"] if labels else root.rsplit("#", 1)[-1])
    #  AT AN INSTANT (#619): bound `orexis:At`, holding at the crossing, its room opening now.
    if holds_at is not None:
        label = f"foreseen: {label[len('pursued: '):]} at {holds_at.isoformat(timespec='minutes')}"
    #  IT HOLDS FROM ITS DERIVATION to the instant it must hold at plus the patience its plan
    #  is given after it — the last step is placed AT the instant and its verdict comes after —
    #  and is open for a want met at its plan's end (#645).
    #  THE WANT, AND THE REPOSITORY WRITES IT (#677). What is derived is decided here — the
    #  binding, the label, what it points at — and where a want is kept, how its graph is
    #  classified and what period it holds during are `Wants`'.
    ends = None
    if holds_at is not None:
        patience = float(getattr(getattr(agent.keeper, "beliefs", None), "patience_s", 0) or 0)
        ends = (holds_at + timedelta(seconds=patience)).isoformat()
    agent.wants.save(agent.id, Want(
        uri=child, holder=agent.me.uri, desire=root, label=label, ends=ends,
        holds_at=holds_at.isoformat() if holds_at is not None else None,
        derived_at=clock.now().isoformat() if holds_at is not None else None,
        about=abouts, points=tuple(points), shape=shape_lines))
    log.info("%s reads unmet: pursuing %s", root.rsplit("#", 1)[-1], child.rsplit("#", 1)[-1])
    return child


OREXIS_MET_WHEN = "http://example.org/orexis#metWhen"


def narrowed(agent, shape: str, own: str, instance: str | None, abouts: tuple) -> tuple[str, ...]:
    """The desire's met-test as THIS want's: the same shape under the want's own name, its
    target the one instance the want is about where the cluster had one, and only the property
    blocks and `sh:sparql` constraints about what the want is about — the universal instantiated
    at its witness (a-desire-is-universal-and-a-want-is-existential). A block or constraint
    saying nothing about what it is about is kept, as is one about `sh:this`, which is the
    instance. The triples, as N-Triples lines the collection writes into the want's graph.

    Carved from public knowledge and the agent's own graphs, asked by classification, where a
    root's shape lives; a shape that names its one node (`sh:targetNode`) narrows to the same
    node, so sensing's wants and the greenhouse's keep their target and lose only the blocks
    they are not about.
    """
    from rdflib import Graph, URIRef
    from rdflib.namespace import SH

    from .conformance import graph_from

    about_p = URIRef("http://example.org/orexis#about")
    targets = {SH.targetNode, SH.targetClass, SH.targetSubjectsOf, SH.targetObjectsOf, SH.target}
    #  From the graphs that hold desires and wants, asked by class, as `unmet_select_of` carves (#711).
    cbd = graph_from(agent.beliefs, *agent.beliefs.graphs_of(OREXIS + "DesireGraph", OREXIS + "WantGraph")).cbd(URIRef(shape))
    keep = {URIRef(a) for a in abouts}
    out, dropped = Graph(), Graph()
    for p, o in cbd.predicate_objects(URIRef(shape)):
        if p in targets and instance is not None:
            continue
        if p in (SH.property, SH.sparql):
            about = cbd.value(o, about_p)
            if about == SH.this:
                about = URIRef(instance) if instance is not None else None
            if keep and about is not None and about not in keep:
                dropped += cbd.cbd(o)
                continue
        out.add((URIRef(own), p, o))
    if instance is not None:
        out.add((URIRef(own), SH.targetNode, URIRef(instance)))
    for s, p, o in cbd:
        if s != URIRef(shape) and (s, p, o) not in dropped:
            out.add((s, p, o))
    return tuple(line for line in out.serialize(format="nt").splitlines() if line.strip())
