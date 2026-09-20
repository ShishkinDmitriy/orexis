"""`derive_wants`: every desire judged, and a want minted for every cluster of what its
met-test reads unmet (judge-desires-then-derive-wants). ONE FUNCTION and one contract — after
the call the store holds every want its desires imply, and NOTHING STANDS BETWEEN A DESIRE AND
A WANT.

There was a third thing once, a `deliberation:Judgment`: what a met-test read, per desire per
instant, written to a working graph and read back by the minting and by whoever wanted a
crossing. It is gone, and everything it carried a want carries — which instance is in trouble,
what the trouble is about, which way it broke (`orexis:violationIs`) and the instant it must
hold at. What a met-test reads is a WITNESS, computed where it is needed and stored nowhere
(`judging.py`): the answer is about a situation, and the situation has moved by the next pass.

A FUNCTION OVER THE STORE: handed the engine, a `pyoxigraph.Store`, and nothing else. The
judging says what each desire reads and whose it is, the scope graph says which witnesses
cluster, the graphs of desires say what a desire is about and what its met-test is, the graphs
of wants say what already stands, and the pick record says how long a plan is given after its
instant. The present is the clock's, the one read outside the store.

What was minted this time comes back for the caller that asked whether its own want was
re-minted. A caller holding a projection of the wants refreshes it on a non-empty answer —
announcing a write is the repository's contract, and a function that writes past it leaves the
refresh to whoever holds one.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pyoxigraph as ox

from orexis_agent_progression import clock
from orexis_agent_progression.keeper import PATIENCE_S
from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.store import NAMESPACES, bind, instant, rows

from .judging import Witness, desires_in, read_ahead, read_now, shapes_in
from .want import Want
from .wants import save_want

log = logging.getLogger("derive_wants")

DESIRE_GRAPH = OREXIS + "DesireGraph"
WANT_GRAPH = OREXIS + "WantGraph"
OREXIS_MET_WHEN = OREXIS + "metWhen"

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

#  WHAT ALREADY STANDS under one desire: every want derived from it that the road minted and
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
    """Mint a want under every desire for every cluster of what its met-test reads unmet, and
    return what was minted. Run whenever a pass stands on a desire or on any want under it,
    and by a package that has just written an instance, since a claim arriving should be a
    want arriving and not a want on the next tick. A package that calls this mints nothing; it
    says an instance is there and this does the rest (one-road-derives-every-want).

    IT IS THE DECOMPOSITION OF WHAT THE MET-TESTS READ. A desire is judged at the present and,
    where it reads met there, at every instant a prediction reaches; what comes back is
    witnesses, and a want is minted per cluster of them. Nothing is written between the two.

    The instant is EACH CLUSTER'S OWN. A desire unmet at the present derives wants with none.
    One met at the present derives them at the instants it reads unmet — and two debts cross
    at two deadlines, so the second is not filtered away by the first's; each cluster holds at
    its earliest witness. A desire met at every instant read derives NOTHING: there is nothing
    to pursue, and a want about everything the desire is about is minted only for a desire
    unmet at the present with no witness, which is what every want once was.

    WHOSE, FROM THE DESIRE: the graph a desire lives in says who holds it, so the wants it
    implies are written to graphs that holder owns. One agent, one volume, so the holder is
    the agent; a store holding several agents' desires derives for each.
    """
    now = clock.now()
    shapes = shapes_in(store)
    minted: list[str] = []
    for holder, desire, shape in desires_in(store, now):
        #  WHAT IT READS NOW, and what it reads ahead only where now is met: a desire in
        #  trouble already is pursued as it stands, and a crossing is a thing in the future.
        present = read_now(store, shapes, holder, desire, shape, now)
        if present is None:
            continue
        unmet_now = bool(present)
        found = present if unmet_now else read_ahead(store, shapes, holder, desire, shape, now)
        if not found:
            continue
        minted += _derive_under(store, holder, desire, found, unmet_now, now)
    return minted


def _derive_under(store: ox.Store, holder: str, root: str, found: list[Witness],
                  unmet_now: bool, now: datetime) -> list[str]:
    """The wants one desire's witnesses imply, minted where none stands. `found` is what its
    met-test read: at the present where it is unmet now, and otherwise each witness at the
    earliest foreseen instant it reads unmet."""
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
        #  ONE SIDE OR NONE: the witnesses of a cluster agree where the same block found them
        #  all, and two sides in one cluster is a want about two troubles, which says neither.
        sides = {w.side for w in cluster if w.side}
        child = mint(store, holder, root, said, holds_at=at, about=about, instance=instance,
                     side=next(iter(sides)) if len(sides) == 1 else None)
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
    which is every want there was before the road: a desire about one property mints
    `<desire>.pursued` exactly as it always did. AND FOR THE INSTANCE where the desire ranges
    over several — its shape targets a class, or whatever bears a property, rather than one
    node — since two tanks low about their level are two clusters, two plans, and would be one
    name otherwise (found by the road's own table, `tests/road/`); a desire whose shape names
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
         about: tuple = (), instance: str | None = None, side: str | None = None) -> str | None:
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
    #  this road asks for the write.
    ends = None
    if holds_at is not None:
        ends = (holds_at + timedelta(seconds=_patience(store, holder))).isoformat()
    save_want(store, _local(holder), Want(
        uri=child, holder=holder, desire=root, label=label, ends=ends,
        holds_at=holds_at.isoformat() if holds_at is not None else None,
        derived_at=clock.now().isoformat() if holds_at is not None else None,
        about=abouts, points=tuple(points), shape=shape_lines, side=side))
    log.info("%s reads unmet: pursuing %s", root.rsplit("#", 1)[-1], child.rsplit("#", 1)[-1])
    return child


def _patience(store: ox.Store, holder: str) -> float:
    """The seconds a plan is given after the instant its want must hold at — the keeper's pick,
    or none where the holder states none."""
    found = rows(store, _PATIENCE_Q, (), holder=holder, patience=PATIENCE_S)
    return float(found[0]["s"]) if found and found[0].get("s") else 0.0


def _local(holder: str) -> str:
    """The holder's local name — what a graph this road writes is called, for eyes."""
    return holder.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


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
