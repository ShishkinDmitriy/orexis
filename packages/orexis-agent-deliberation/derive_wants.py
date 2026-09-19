"""`derive_wants`: every desire judged, and the wants those judgments imply minted under them
(judge-desires-then-derive-wants). ONE FUNCTION, `derive_wants`, and one contract — after the
call the store says what every desire read and holds every want that follows from it.

It was two, `judge_desires` then `derive_wants`, and no caller ever took one without the
other: three call sites each wrote both lines and each could have written only the first. What
the split bought was a contract and a snapshot per half; what it cost was a seam a caller
could stop at. The judgment graph is untouched by the merge — it is written as it always
was, and `judgments.witnesses_of` reads it without deriving anything.

A FUNCTION OVER THE STORE: handed the engine, a `pyoxigraph.Store`, and nothing else. Which
graphs hold desires, which are predictions and which hold at an instant, the catalogue says;
who holds a desire, the desire's own graph says; what a met-test means, its shape says; the
scope graph says which results cluster, the graphs of wants say what already stands, and the
pick record says how long a plan is given after its instant. The present is the clock's, the
one read outside the store.

What was minted this time comes back for the caller that asked whether its own want was
re-minted. A caller holding a projection of the wants refreshes it on a non-empty answer —
announcing a write is the repository's contract, and a function that writes past it
leaves the refresh to whoever holds one.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, timedelta

import pyoxigraph as ox
import rdflib

from orexis_agent_progression import clock
from orexis_agent_progression.keeper import PATIENCE_S
from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.ontology import FORESEEN
from orexis_agent_progression.store import NAMESPACES, bind, graphs_holding, instant, rows

from .judgments import Witness, find_judgments, save_judgments
from .want import Want
from .wants import save_want

log = logging.getLogger("derive_wants")

DESIRE_GRAPH = OREXIS + "DesireGraph"
WANT_GRAPH = OREXIS + "WantGraph"
OREXIS_MET_WHEN = OREXIS + "metWhen"

#  EVERY DESIRE THE STORE HOLDS, who holds it and its met-test, from the graphs of desires
#  holding at the present — the roots graph states no period, the world's asserted graph
#  none, and a graph of desires with one is read while it holds. A desire, its holder and its
#  met-test are written together — one rule derives them, one file ratifies them — so the
#  pattern matches within one graph.
_ROOTS_Q = """
SELECT DISTINCT ?holder ?desire ?shape WHERE {
  GRAPH ?g { ?holder orexis:holds ?desire . ?desire a orexis:Desire .
             OPTIONAL { ?desire orexis:metWhen ?shape } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph .
               OPTIONAL { ?g dcterms:temporal ?period .
                          OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } }
               FILTER(!BOUND(?start) || $now >= ?start) FILTER(!BOUND(?end) || $now < ?end) } }
ORDER BY ?holder ?desire"""

#  WHEN THE HOLDER FORESEES: the start of every prediction of theirs, whatever its window —
#  the future states this judges at, given to it and never computed here (#643).
_STARTS_Q = """
SELECT DISTINCT ?start WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?start .
               OPTIONAL { ?g orexis:beliefsOf ?owner } FILTER(!BOUND(?owner) || ?owner = $holder) } }
ORDER BY ?start"""

#  WHERE THE SHAPES LIVE: every graph of desires and of wants, whatever its period — a root's
#  shape and its blank-node closure sit in a desire graph whole, a derived want's own in its
#  want graph, and the whole belief base parsed into rdflib cost half a second per shape (#711).
_SHAPE_GRAPHS_Q = """
SELECT DISTINCT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind . FILTER(isIRI(?g))
               VALUES ?kind { orexis:DesireGraph orexis:WantGraph } } }
ORDER BY ?g"""


#  WHAT A DESIRE SAYS, from the graphs of desires and wants asked by class: what it is about,
#  what it points at, its label and its met-test. The OBJECT'S TYPE matters — a blank node
#  cannot be pointed at from another graph — so the caller reads the engine's own terms.
_SAID_Q = """
SELECT ?p ?o WHERE {
  GRAPH ?g { $root ?p ?o
    FILTER(?p IN (orexis:metWhen, orexis:unmetWhen, orexis:estimates, orexis:about, rdfs:label)) }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { orexis:DesireGraph orexis:WantGraph } } }"""

#  DOES THE MET-TEST NAME ITS ONE NODE (`sh:targetNode`)?
_TARGETS_ONE_Q = """
ASK { GRAPH ?g { $root orexis:metWhen ?s . ?s sh:targetNode ?n }
      GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph } }"""

#  HOW LONG A PLAN IS GIVEN after the instant its want must hold at — the keeper's pick, from
#  the record where review writes it. Progression's word, which this layer reads downward.
_PATIENCE_Q = """
SELECT ?s WHERE {
  GRAPH ?g { $holder $patience ?s }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:PickRecordGraph } } LIMIT 1"""

#  WHAT ALREADY STANDS under one desire: every want derived from it that was minted here and
#  whose graph still holds. A want IS its graph (#645), so which family it is in and whether it
#  holds are the graph's questions, asked of the catalogue in the text as `Wants` asks them.
_STANDING_Q = """
SELECT ?w ?holdsAt WHERE {
  GRAPH ?g { ?w a orexis:Want ; prov:wasDerivedFrom $root .
             OPTIONAL { ?w orexis:holdsAt ?holdsAt } }
  GRAPH ?cat {
    ?cat a orexis:CatalogueGraph . ?g a deliberation:PursuedGraph .
    OPTIONAL { ?g dcterms:temporal ?period .
               OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } } }
  FILTER(!BOUND(?start) || ?start <= $now) FILTER(!BOUND(?end) || ?end > $now) }
ORDER BY ?w"""


def derive_wants(store: ox.Store) -> list[str]:
    """Mint a want under every desire for every cluster of its judgments' results that has
    none, and return what was minted, reading the judgments this function wrote with one
    select and nothing in hand (judge-desires-then-derive-wants). Run whenever a pass stands on a root or on any want
    under it, and by a package that has just written an instance, since a claim arriving
    should be a want arriving and not a want on the next tick. A package that calls this
    mints nothing; it says an instance is there and this does the rest
    (one-road-derives-every-want).

    THE MINTING IS THE DECOMPOSITION OF THE JUDGMENTS AND NOTHING ELSE. `_judge` above judges each
    desire at the present and at every instant a prediction reaches, and writes what it read;
    this turns those judgments into wants, and asks no question the judgments do not answer.
    A FORESIGHT once stood here — a per-agent pick that discarded a foreseen failure further
    out than N seconds — and it is gone: the judgments already say which instants fail and
    when, and how far ahead the agent sees is said by the drifts, each declaring the horizons
    it predicts at. A second number gating the first was an on/off switch wearing a horizon's
    name, and no shipped world set it.

    The instant is EACH CLUSTER'S OWN. A desire unmet at the present derives wants with none.
    One met at the present derives them at the instants it is judged unmet — and two debts
    cross at two deadlines, so the second is not filtered away by the first's; each cluster
    holds at its earliest result. A desire met at every instant judged derives NOTHING: there
    is nothing to pursue, and a want about everything the desire is about is minted only for a
    desire unmet at the present with no result, which is what every want once was.

    WHOSE, FROM THE JUDGMENT: each judgment graph says whose it is, so the wants a holder's
    judgments imply are written to graphs that holder owns. One agent, one volume, so the
    holder is the agent.
    """
    now = clock.now()
    _judge(store, now)
    minted: list[str] = []
    for holder, judged in sorted(find_judgments(store).items()):
        by_desire: dict[str, list[dict]] = {}
        for row in judged:
            by_desire.setdefault(row["desire"], []).append(row)
        for root, judgments in sorted(by_desire.items()):
            minted += _derive_under(store, holder, root, judgments, now)
    return minted


def _judge(store: ox.Store, now: datetime) -> None:
    """Judge every desire the store holds at the present and at every instant its holder
    foresees, and write the judgments — this function's first half, and the only thing here that
    reads a PREDICTION. After it the store says what each desire's met-test read: met or
    unmet, and where unmet the results, one `deliberation:Judgment` per desire per instant in
    the holder's judgment graph, replaced whole. Nothing is kept in hand; the derivation below
    reads the graph, as every other reader of what a desire read does.

    The desires and who holds them are asked of the graphs of desires, the instants of the
    predictions' periods, the dataset at each instant of the catalogue — the texts above, each
    naming what it reads. One agent, one volume, so the holder is the agent; a store holding
    several agents' desires is judged for each, over what each holds and what nobody does.

    ONE SELECT PER DESIRE PER INSTANT, and not one union of them: the compiler measured a
    single UNION of every shape at thirteen times the cost of the selects asked one by one,
    so this iterates where the contract is the whole. The foreseen instants are every
    prediction's start, where the dataset holds the prediction beside the present (#643).
    A desire whose met-test the compiler refuses is not judged, and the log says so: it was
    judged by the choir once, and a function over the store has no choir to ask — nor a
    shipped desire whose met-test is refused.
    """
    now = clock.now()
    shapes = shapes_in(store)
    by_holder: dict[str, list[tuple[str, str | None]]] = {}
    for row in store.query(bind(_ROOTS_Q, now=instant(now)), prefixes=NAMESPACES):
        by_holder.setdefault(row["holder"].value, []).append(
            (row["desire"].value, row["shape"].value if row["shape"] is not None else None))
    for holder, roots in by_holder.items():
        starts = _starts(store, holder)
        judged: list[tuple[str, datetime | None, bool, list[dict]]] = []
        for root, shape in roots:
            select = _compiled(shapes, shape, root)
            if select is None:
                continue
            for at in [None, *starts]:
                rows = _violations(store, select, holder, at or now, now)
                if rows is None:
                    log.error("%s: could not be judged at %s", root.rsplit("#", 1)[-1], at or "now")
                    continue
                judged.append((root, at, not rows, rows))
        save_judgments(store, holder, judged)



def _derive_under(store: ox.Store, holder: str, root: str, judged: list[dict],
                  now: datetime) -> list[str]:
    """The wants one desire's judgments imply, minted where none stands. `judged` are the
    judgment graph's rows: one per result, a met judgment's row naming no focus."""
    present = [r for r in judged if not r.get("at")]
    if not present:
        return []
    unmet_now = present[0]["met"] != "true"
    if unmet_now:
        found = [Witness(instance=r["focus"], constraint=r["k"], about=r.get("about"), at=now)
                 for r in present if r.get("focus")]
    else:
        #  MET NOW, AND JUDGED UNMET LATER: each (instance, constraint) at the FIRST instant
        #  it fails. Every instant here is one the judging was asked about, which is every
        #  instant a prediction reaches — so what bounds the lookahead is what the drifts
        #  predict, and nothing filters them again.
        seen: dict[tuple[str, str], Witness] = {}
        for r in sorted((r for r in judged if r.get("at") and r["met"] != "true" and r.get("focus")),
                        key=lambda r: r["at"]):
            seen.setdefault((r["focus"], r["k"]), Witness(
                instance=r["focus"], constraint=r["k"], about=r.get("about"),
                at=datetime.fromisoformat(r["at"])))
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
    #  from the present. The instant was this function's reading of the predictions; the present
    #  outranks it, as it does everywhere else here.
    #  STANDING IS BY NAME, and the name is the cluster's: what it is about, and which instance
    #  where the desire ranges over several (`name_of`). Two tanks low about their level are
    #  two clusters and two names; keyed by what they were about alone, the second read the
    #  first as standing, and by construction the second mint had overwritten the first.
    standing = {r["w"]: r.get("holdsAt") for r in rows(store, _STANDING_Q, (), root=root,
                                                      now=instant(now))}
    said = _said(store, root)
    minted = []
    for cluster in _clusters(store, found) or [[]]:
        about = tuple(sorted({w.about for w in cluster if w.about}))
        instances = {w.instance for w in cluster}
        instance = next(iter(instances)) if len(instances) == 1 else None
        child = name_of(store, root, said, about, instance)
        if child in standing and not (unmet_now and standing[child]):
            continue
        if child in standing:
            log.info("%s: what was foreseen at %s has arrived", child.rsplit("#", 1)[-1],
                     standing[child])
        at = None if unmet_now else min((w.at for w in cluster), default=None)
        child = mint(store, holder, root, said, holds_at=at, about=about, instance=instance)
        if child is not None:
            minted.append(child)
    return minted


def _clusters(store: ox.Store, witnesses: list) -> list[list]:
    """The witnesses grouped by SCOPE — which of them some action can move together — so a
    want is minted per group. Two in one scope are one want and one cone; two in different
    scopes are two, planned apart and concatenated, which is the mechanism `scope.md` says the
    concept exists for. A witness naming no property, or one no scope holds, joins every group
    it could belong to, which with one scope is the one group.

    THE SCOPES ARE READ, NEVER COMPUTED: `scope_actions` wrote them (scope-actions),
    and a store holding no scope graph is refused rather than clustered as one scope — the
    loud direction, since one want about everything is what a missing partition would have
    quietly minted.

    Measured on every shipped world: one scope, so one group. The code path is the same the
    day a world splits, and a scope is over PREDICATES — two debts to two hosts are one scope,
    correctly, since they may draw from one vessel."""
    if not witnesses:
        return []
    from .scopes import find_scopes
    scopes = find_scopes(store)
    if scopes is None:
        raise RuntimeError("the store holds no scope graph — scope_actions has not run")
    groups: dict = {}
    loose = []
    for w in witnesses:
        scope = scopes.get(w.about) if w.about else None
        key = (scope, w.instance) if scope is not None or w.about == w.instance else None
        (groups.setdefault(key, []) if key is not None else loose).append(w)
    if not groups:
        return [loose]
    for w in loose:
        for group in groups.values():
            group.append(w)
    return list(groups.values())


def _said(store: ox.Store, root: str) -> list[tuple[str, object]]:
    """What the desire says, as `(predicate, the engine's own term)` — the TYPE is load-bearing,
    since a blank node has no name another graph could point at."""
    solutions = store.query(bind(_SAID_Q, root=root), prefixes=NAMESPACES)
    return sorted(((str(s["p"].value), s["o"]) for s in solutions), key=lambda pair: (pair[0], str(pair[1])))


def _abouts(said) -> tuple:
    return tuple(sorted(str(o.value) for p, o in said if p.endswith("#about")))


def _tail(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def name_of(store: ox.Store, root: str, said, about: tuple, instance: str | None) -> str:
    """The name of the want minted under `root` for one cluster of its witnesses: the root's,
    suffixed, so a second episode of the same cluster pursues the same node and everything
    keyed by it — the planner, a remembered plan, the trace, the keeper — finds what it kept.

    NAMED FOR WHAT IT IS ABOUT where that is NARROWER than the desire, so two wants under one
    desire — soil now, air later — are two nodes; and for the desire alone where it is not,
    which is every want there once was: a desire about one property mints
    `<desire>.pursued` exactly as it always did. AND FOR THE INSTANCE where the desire ranges
    over several — its shape targets a class, or whatever bears a property, rather than one
    node — since two tanks low about their level are two clusters, two plans, and would be one
    name otherwise (found by the cases in `tests/derive_wants/`); a desire whose shape names
    its one node (`sh:targetNode`, sensing's and the greenhouse's) keeps its names, and an
    instance the want is already about (a debt, `orexis:about sh:this`) is not said twice.
    """
    tails = [_tail(a) for a in about] if about and set(about) != set(_abouts(said)) else []
    if instance is not None and instance not in about and not _targets_one_node(store, root):
        tails.insert(0, _tail(instance))
    return root + ".pursued" + "".join(f".{t}" for t in tails)


def _targets_one_node(store: ox.Store, root: str) -> bool:
    """Does the root's met-test name the one node it is about (`sh:targetNode`)?"""
    return store.query(bind(_TARGETS_ONE_Q, root=root), prefixes=NAMESPACES)


def mint(store: ox.Store, holder: str, root: str, said=None, holds_at: datetime | None = None,
         about: tuple = (), instance: str | None = None) -> str | None:
    """Derive the want pursued under `root` and write it to the pursued graph, named by
    `name_of`. None, and the root stays the goal, where the root states its met-test inline:
    a blank node has no name another graph could point at, and copying it would make a second
    owner of the claim."""
    said = _said(store, root) if said is None else said
    desire_abouts = _abouts(said)
    abouts = about or desire_abouts
    child = name_of(store, root, said, about, instance)
    points = []
    met_test = None
    for p, o in said:
        if isinstance(o, ox.BlankNode):
            log.warning("%s states its %s inline; it is pursued itself", root.rsplit("#", 1)[-1],
                        p.rsplit("#", 1)[-1])
            return None
        #  WHAT IT IS ABOUT is the witnesses' where the shape named them per block, and the
        #  desire's whole where it did not; the avoided state and the estimate are pointed at
        #  as ever, and the met-test is carried, instantiated, below. The label is read here
        #  too and is not a point: a want's is made from it.
        if p.endswith("#about") or p.endswith("#label"):
            continue
        if p == OREXIS_MET_WHEN:
            met_test = str(o.value)
            continue
        points.append((p, str(o.value)))
    #  THE MET-TEST IS THE DESIRE'S INSTANTIATED AT THE WITNESS: carved from where the root's
    #  shape lives and narrowed to this cluster — the instance as its target, the blocks about
    #  what the want is about — and written into the want's own graph under its own name, so
    #  the want is judged on its instance and a plan for one tank is not refused for another's.
    shape_lines: tuple = ()
    if met_test is not None:
        own = child + ".met"
        shape_lines = narrowed(store, met_test, own, instance, abouts)
        points.append((OREXIS_MET_WHEN, own))

    labels = [str(o.value) for p, o in said if p.endswith("#label")]
    label = "pursued: " + (labels[0] if labels else root.rsplit("#", 1)[-1])
    #  AT AN INSTANT (#619): bound `orexis:At`, holding at the crossing, its room opening now.
    if holds_at is not None:
        label = f"foreseen: {label[len('pursued: '):]} at {holds_at.isoformat(timespec='minutes')}"
    #  IT HOLDS FROM ITS DERIVATION to the instant it must hold at plus the patience its plan
    #  is given after it — the last step is placed AT the instant and its verdict comes after —
    #  and is open for a want met at its plan's end (#645).
    #  THE WANT, AND THE REPOSITORY WRITES IT (#677). What is derived is decided here — the
    #  binding, the label, what it points at — and where a want is kept, how its graph is
    #  classified and what period it holds during are `wants.py`'s, whether a collection or
    #  this function asks for the write.
    ends = None
    if holds_at is not None:
        ends = (holds_at + timedelta(seconds=_patience(store, holder))).isoformat()
    save_want(store, _local(holder), Want(
        uri=child, holder=holder, desire=root, label=label, ends=ends,
        holds_at=holds_at.isoformat() if holds_at is not None else None,
        derived_at=clock.now().isoformat() if holds_at is not None else None,
        about=abouts, points=tuple(points), shape=shape_lines))
    log.info("%s reads unmet: pursuing %s", root.rsplit("#", 1)[-1], child.rsplit("#", 1)[-1])
    return child


def _patience(store: ox.Store, holder: str) -> float:
    """The seconds a plan is given after the instant its want must hold at — the keeper's pick,
    or none where the holder states none."""
    found = rows(store, _PATIENCE_Q, (), holder=holder, patience=PATIENCE_S)
    return float(found[0]["s"]) if found and found[0].get("s") else 0.0


def _local(holder: str) -> str:
    """The holder's local name — what a graph this function writes is called, for eyes."""
    return holder.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def shapes_in(store: ox.Store) -> rdflib.Graph:
    """Every graph of desires and of wants, parsed once — where a root's shape lives with its
    blank-node closure, and a derived want's own. N-Triples, since it concatenates and rdflib
    parses it in a fraction of Turtle's time; the engine's blank-node labels are its own, so
    two graphs' nodes never collide in one text."""
    out = io.BytesIO()
    for row in store.query(_SHAPE_GRAPHS_Q, prefixes=NAMESPACES):
        store.dump(output=out, format=ox.RdfFormat.N_TRIPLES, from_graph=row["g"])
    shapes = rdflib.Graph()
    if out.tell():
        shapes.parse(data=out.getvalue().decode(), format="nt")
    return shapes


def _compiled(shapes: rdflib.Graph, shape: str | None, root: str) -> str | None:
    """`shape` compiled to its report select out of `shapes`, or None — and a word in the log
    — where the root states none or the compiler refuses it."""
    from orexis_agent_progression.violation import Unsupported, report_select

    if shape is None:
        return None
    try:
        return report_select(shapes.cbd(rdflib.URIRef(shape)), rdflib.URIRef(shape))
    except Unsupported as exc:
        log.warning("%s: its met-test cannot be compiled, so it is not judged: %s",
                    root.rsplit("#", 1)[-1], exc)
        return None


def _starts(store: ox.Store, holder: str) -> list[datetime]:
    return [datetime.fromisoformat(row["start"].value)
            for row in store.query(bind(_STARTS_Q, holder=holder), prefixes=NAMESPACES)]


def _violations(store: ox.Store, select: str, holder: str, at: datetime,
                now: datetime) -> list[dict] | None:
    """The select's rows over the graphs `holder`'s desire is judged over at `at`, each a
    dict of the engine's own terms by variable name, one per distinct row — two predictions
    holding at one instant give one node two offending values, and both are told. None where
    the engine refuses the text."""
    graphs = [ox.NamedNode(g) for g in graphs_holding(store, FORESEEN, holder=holder, at=at, now=now)]
    try:
        answer = store.query(select, prefixes=NAMESPACES, default_graph=graphs)
        names = [v.value for v in answer.variables]
        rows: dict[tuple, dict] = {}
        for solution in answer:
            row = {name: solution[name] for name in names if solution[name] is not None}
            rows.setdefault(tuple(sorted((k, str(v)) for k, v in row.items())), row)
    except Exception as exc:                                        # noqa: BLE001
        log.error("the met-test could not be read at %s: %s", at, exc)
        return None
    return [rows[key] for key in sorted(rows)]

def narrowed(store: ox.Store, shape: str, own: str, instance: str | None, abouts: tuple) -> tuple[str, ...]:
    """The desire's met-test as THIS want's: the same shape under the want's own name, its
    target the one instance the want is about where the cluster had one, and only the property
    blocks and `sh:sparql` constraints about what the want is about — the universal instantiated
    at its witness (a-desire-is-universal-and-a-want-is-existential). A block or constraint
    saying nothing about what it is about is kept, as is one about `sh:this`, which is the
    instance. The triples, as N-Triples lines the write puts into the want's graph.

    Carved from the graphs of desires and wants, asked by classification, where a root's shape
    lives; a shape that names its one node (`sh:targetNode`) narrows to the same node, so
    sensing's wants and the greenhouse's keep their target and lose only the blocks they are
    not about.
    """
    from rdflib import Graph, URIRef
    from rdflib.namespace import SH

    about_p = URIRef(OREXIS + "about")
    targets = {SH.targetNode, SH.targetClass, SH.targetSubjectsOf, SH.targetObjectsOf, SH.target}
    #  From the graphs that hold desires and wants, asked by class, as `unmet_select_of` carves (#711).
    cbd = shapes_in(store).cbd(URIRef(shape))
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
