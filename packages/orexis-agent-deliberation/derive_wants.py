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

import json
import logging
from datetime import datetime, timedelta

import pyoxigraph as ox

from orexis_agent_progression import clock
from orexis_agent_progression.keeper import PATIENCE_S
from orexis_agent_progression.ontology import OREXIS
from orexis_agent_progression.store import NAMESPACES, bind, instant, rows

from .judging import Witness, desires_in, read_ahead, read_now, shapes_in
from .ontology import pursued_graph
from .want import Want

log = logging.getLogger("derive_wants")

DESIRE_GRAPH = OREXIS + "DesireGraph"
WANT_GRAPH = OREXIS + "WantGraph"
OREXIS_MET_WHEN = OREXIS + "metWhen"

#  WHAT A DESIRE SAYS, from the graphs of desires and wants asked by class: what it is about,
#  what it points at, its label and its met-test. The OBJECT'S TYPE matters — a blank node
#  cannot be pointed at from another graph — so the caller reads the engine's own terms.
_SAID_Q = """
SELECT ?p ?o WHERE {
  GRAPH ?g { $desire ?p ?o
    FILTER(?p IN (orexis:metWhen, orexis:unmetWhen, orexis:estimates, orexis:about, rdfs:label)) }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { orexis:DesireGraph orexis:WantGraph } } }"""

#  DOES THE MET-TEST NAME ITS ONE NODE (`sh:targetNode`)?
_TARGETS_ONE_Q = """
ASK { GRAPH ?g { $desire orexis:metWhen ?s . ?s sh:targetNode ?n }
      GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph } }"""

#  HOW LONG A PLAN IS GIVEN after the instant its want must hold at — the keeper's pick, from
#  the record where review writes it. Progression's word, which this layer reads downward.
_PATIENCE_Q = """
SELECT ?s WHERE {
  GRAPH ?g { $holder $patience ?s }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:PickRecordGraph } } LIMIT 1"""

#  WHAT ALREADY STANDS under one desire: every want derived from it that the derivation minted and
#  whose graph still holds. A want IS its graph (#645), so which family it is in and whether it
#  holds are the graph's questions, asked of the catalogue in the text as `find_wants` asks them.
#  A WANT A PLAN STANDS FOR is not withdrawn, however its desire now reads: the keeper is
#  walking it, and dropping the want under a running plan would leave the plan pursuing
#  nothing. `orexis:pursues` is the ledger's link and `orexis:resolvedAt` is how it ends —
#  progression's words, read downward, which is the direction a layer may read.
_PURSUED_Q = """
SELECT ?w WHERE {
  GRAPH ?g { ?i orexis:pursues ?w . FILTER NOT EXISTS { ?i orexis:resolvedAt ?done } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a progression:IntentionGraph } }"""


_STANDING_Q = """
SELECT ?w ?holdsAt WHERE {
  GRAPH ?g { ?w a orexis:Want ; prov:wasDerivedFrom $desire .
             OPTIONAL { ?w orexis:holdsAt ?holdsAt } }
  GRAPH ?cat {
    ?cat a orexis:CatalogueGraph . ?g a deliberation:PursuedGraph .
    OPTIONAL { ?g dcterms:temporal ?period .
               OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } } }
  FILTER(!BOUND(?start) || ?start <= $now) FILTER(!BOUND(?end) || ?end > $now) }
ORDER BY ?w"""


def derive_wants(store: ox.Store) -> list[str]:
    """Mint a want under every desire for every cluster of what its met-test reads unmet,
    withdraw every want those rows no longer imply, and return what changed either way. Run whenever a pass stands on a desire or on any want under it,
    and by a package that has just written an instance, since a claim arriving should be a
    want arriving and not a want on the next tick. A package that calls this mints nothing; it
    says an instance is there and this does the rest (one-function-mints-every-want).

    IT IS THE DECOMPOSITION OF WHAT THE MET-TESTS READ. A desire is judged at the present and,
    where it reads met there, at every instant a prediction reaches; what comes back is
    witnesses, and a want is minted per cluster of them. Nothing is written between the two.

    AND THE DECOMPOSITION IS THE WHOLE OF WHAT SHOULD STAND, which is why the same rows
    withdraw. A want exists because its desire read unmet; a want those rows no longer produce
    is met, and dropping it here is free, where asking its own met-test about it again was a
    second evaluation of what this function had just concluded. What it returns is therefore
    every want that CHANGED — minted or withdrawn — since a caller that refreshes a projection
    on a mint must refresh it on a withdrawal too.

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
    changed: list[str] = []
    for holder, desire, shape in desires_in(store, now):
        #  WHAT IT READS NOW, and what it reads ahead only where now is met: a desire in
        #  trouble already is pursued as it stands, and a crossing is a thing in the future.
        present = read_now(store, shapes, holder, desire, shape, now)
        if present is None:
            #  NOT JUDGED IS NOT MET. A desire whose met-test could not be run says nothing
            #  about its wants, and withdrawing on silence would drop a want on a bad shape.
            continue
        unmet_now = bool(present)
        found = present if unmet_now else read_ahead(store, shapes, holder, desire, shape, now)
        changed += _derive_under(store, holder, desire, found, unmet_now, now)
        changed += _withdraw_under(store, shapes, holder, desire, shape, found, unmet_now, now)
    return changed


def _derive_under(store: ox.Store, holder: str, desire: str, found: list[Witness],
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
    #  from the present. The instant was the derivation's reading of the predictions; the present
    #  outranks it, as it does everywhere else here.
    #  STANDING IS BY NAME, and the name is the cluster's: what it is about, and which instance
    #  where the desire ranges over several (`name_of`). Two tanks low about their level are
    #  two clusters and two names; keyed by what they were about alone, the second read the
    #  first as standing, and by construction the second mint had overwritten the first.
    standing = {r["w"]: r.get("holdsAt") for r in rows(store, _STANDING_Q, (), desire=desire,
                                                      now=instant(now))}
    said = _said(store, desire)
    #  THE FALLBACK IS FOR A DESIRE UNMET NOW AND NOTHING ELSE: one want about everything the
    #  desire is about, for a desire whose select yields no rows. A desire that reads MET now
    #  and foresees nothing must reach the same loop with NO clusters, so that what stands
    #  under it is withdrawn — which is why this is a condition and no longer `or [[]]`.
    clusters = _clusters(store, found)
    if not clusters and unmet_now:
        clusters = [[]]
    minted = []
    for cluster in clusters:
        about = tuple(sorted({w.about for w in cluster if w.about}))
        instances = {w.instance for w in cluster}
        instance = next(iter(instances)) if len(instances) == 1 else None
        child = name_of(store, desire, said, about, instance)
        if child in standing and not (unmet_now and standing[child]):
            continue
        if child in standing:
            log.info("%s: what was foreseen at %s has arrived", child.rsplit("#", 1)[-1],
                     standing[child])
        at = None if unmet_now else min((w.at for w in cluster), default=None)
        #  ONE SIDE OR NONE: the witnesses of a cluster agree where the same block found them
        #  all, and two sides in one cluster is a want about two troubles, which says neither.
        sides = {w.side for w in cluster if w.side}
        child = mint(store, holder, desire, said, holds_at=at, about=about, instance=instance,
                     side=next(iter(sides)) if len(sides) == 1 else None)
        if child is not None:
            minted.append(child)
    return minted


def _named(store: ox.Store, desire: str, said, found: list[Witness]) -> set[str]:
    """The names the clusters of `found` come to — what minting would call them.

    One namer for both halves: `_derive_under` mints under these names and `_withdraw_under`
    keeps what is under them, so the two can never disagree about which want a cluster is.
    """
    out = set()
    for cluster in _clusters(store, found):
        about = tuple(sorted({w.about for w in cluster if w.about}))
        instances = {w.instance for w in cluster}
        out.add(name_of(store, desire, said, about,
                        next(iter(instances)) if len(instances) == 1 else None))
    return out


def _withdraw_under(store: ox.Store, shapes, holder: str, desire: str, shape: str,
                    found: list[Witness], unmet_now: bool, now: datetime) -> list[str]:
    """Drop every want under this desire that its met-test no longer implies, and return them.

    A WANT EXISTS BECAUSE ITS DESIRE READ UNMET, so a want the decomposition no longer
    produces is met, and the rows that say so are the ones this pass already read. Nothing
    re-runs a met-test to find out whether a want is met: asking twice is what this removes.

    AGAINST THE WHOLE DECOMPOSITION, present AND foreseen, which is the correction the suite
    made: `found` is the present alone where the desire is unmet now, since a crossing is not
    minted for while there is trouble already — so a want minted at a foreseen instant is
    absent from it and would be withdrawn the moment any OTHER instance went unmet now. A
    presented debt did exactly that to an unpresented one. The foreseen half is read only
    where something would otherwise be dropped, so a pass that withdraws nothing pays nothing.

    A want a plan is WALKING is kept whatever its desire reads — see `_PURSUED_Q`. A want IS
    its graph (#645), so withdrawing is `forget_want` and there is nothing left behind.
    """
    standing = {r["w"] for r in rows(store, _STANDING_Q, (), desire=desire, now=instant(now))}
    if not standing:
        return []
    said = _said(store, desire)
    wanted = _named(store, desire, said, found)
    stale = standing - wanted
    if not stale:
        return []
    if unmet_now:
        stale -= _named(store, desire, said,
                        read_ahead(store, shapes, holder, desire, shape, now))
    pursued = {r["w"] for r in rows(store, _PURSUED_Q, ())} if stale else set()
    gone = []
    for want in sorted(stale - pursued):
        forget_want(store, _local(holder), want)
        log.info("%s withdrawn: its desire no longer reads it unmet", want.rsplit("#", 1)[-1])
        gone.append(want)
    return gone


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


def _said(store: ox.Store, desire: str) -> list[tuple[str, object]]:
    """What the desire says, as `(predicate, the engine's own term)` — the TYPE is load-bearing,
    since a blank node has no name another graph could point at."""
    solutions = store.query(bind(_SAID_Q, desire=desire), prefixes=NAMESPACES)
    return sorted(((str(s["p"].value), s["o"]) for s in solutions), key=lambda pair: (pair[0], str(pair[1])))


def _abouts(said) -> tuple:
    return tuple(sorted(str(o.value) for p, o in said if p.endswith("#about")))


def _tail(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def name_of(store: ox.Store, desire: str, said, about: tuple, instance: str | None) -> str:
    """The name of the want minted under `desire` for one cluster of its witnesses: the desire's,
    suffixed, so a second episode of the same cluster pursues the same node and everything
    keyed by it — the planner, a remembered plan, the trace, the keeper — finds what it kept.

    NAMED FOR WHAT IT IS ABOUT where that is NARROWER than the desire, so two wants under one
    desire — soil now, air later — are two nodes; and for the desire alone where it is not,
    which is every want there was before this: a desire about one property mints
    `<desire>.pursued` exactly as it always did. AND FOR THE INSTANCE where the desire ranges
    over several — its shape targets a class, or whatever bears a property, rather than one
    node — since two tanks low about their level are two clusters, two plans, and would be one
    name otherwise (found by the derivation's own table, `tests/derive_wants/`); a desire whose shape names
    its one node (`sh:targetNode`, sensing's and the greenhouse's) keeps its names, and an
    instance the want is already about (a debt, `orexis:about sh:this`) is not said twice.
    """
    tails = [_tail(a) for a in about] if about and set(about) != set(_abouts(said)) else []
    if instance is not None and instance not in about and not _targets_one_node(store, desire):
        tails.insert(0, _tail(instance))
    return desire + ".pursued" + "".join(f".{t}" for t in tails)


def _targets_one_node(store: ox.Store, desire: str) -> bool:
    """Does the desire's met-test name the one node it is about (`sh:targetNode`)?"""
    return store.query(bind(_TARGETS_ONE_Q, desire=desire), prefixes=NAMESPACES)


# --- what a want IS on disk, and how one goes -------------------------------------------
#
#  THE DERIVATION OWNS ITS OWN WRITES. These were module functions in `wants.py` beside the
#  collection, so the one function that mints wants had to reach into a repository to put one
#  down. A want's graph, what the catalogue says of it and the period it holds during are
#  decided where the want is decided; `wants.py` reads them back and names none of it.


def _moment(value) -> str:
    """One instant as the store keeps it. A string is passed through: a caller that already
    has the literal has nothing to convert."""
    return value if isinstance(value, str) else value.isoformat()


def graph_of(agent_id: str, uri: str) -> str:
    """The graph one DERIVED want lives in. Named for the want so a second episode of the same
    desire reuses it, and everything keyed by the want finds what it kept."""
    return f"{pursued_graph(agent_id)}/{uri.rsplit('#', 1)[-1]}"


def _forget(graph: str) -> str:
    """The update that removes one want — its graph, and everything the catalogue says of it.

    Shared, because there are two ways a want goes and they must leave the same nothing:
    `save_want` replaces one whole and puts it back, and `forget_want` does not. A want IS
    its graph (#645), so there is no second place to tidy — but the catalogue's account of
    that graph is not in it, and a row left pointing at an empty graph is litter every
    reader asking by class would still be handed.
    """
    return f"""DROP SILENT GRAPH <{graph}> ;
DELETE {{ GRAPH ?cat {{ <{graph}> ?p ?o . ?period ?pp ?po }} }}
WHERE  {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . <{graph}> ?p ?o .
          OPTIONAL {{ <{graph}> dcterms:temporal ?period . ?period ?pp ?po }} }} }}"""


def forget_want(engine, agent_id: str, uri: str) -> None:
    """Remove one derived want over the ENGINE, for a caller that holds no collection.

    `Wants.delete_by_uri` was the collection's door and announced itself; this is the
    derivation's, which announces nothing and whose caller says what changed — the same
    asymmetry `save_want` had beside `Wants.save`, and both doors are gone.
    """
    engine.update(_forget(graph_of(agent_id, uri)), prefixes=NAMESPACES)


def save_want(engine, agent_id: str, want: Want) -> None:
    """Write one derived want over the ENGINE: its graph, replaced whole, and the catalogue's
    account of that graph — its family, how it arrived, whose it is and the period it holds
    during — in one update, so a want and what is said about it land together or not at all.

    THE KNOWLEDGE STAYS IN THIS FILE, which is the point of it being here (#677): the derivation
    decides what a want IS — its name, its label, what it points at, when it must hold — and
    where a want is kept is this module's, whether the collection below or the derivation asks. The
    catalogue is found by its own row and every kind the vocabulary puts a pursued graph
    beneath is written from one `rdfs:subClassOf` step, the closure being materialised at
    genesis (one-graph-both-engines-read).
    """
    graph = graph_of(agent_id, want.uri)
    points = " ".join(f"<{want.uri}> <{p}> <{o}> ." for p, o in want.points)
    shape = "\n  ".join(want.shape)
    #  INSTANTS CROSS HERE AND NOWHERE ELSE. A want carries them as instants, because what
    #  reads them — the keeper placing a step, the container measuring the room left — works in
    #  instants; the store keeps them as `xsd:dateTime` literals. This is the boundary, so it
    #  is where the two forms meet, one line each way (`_moment` below, and `_instant` on read).
    timed = (f' ; orexis:holdsAt "{_moment(want.holds_at)}"^^xsd:dateTime'
             f' ; prov:generatedAtTime "{_moment(want.derived_at)}"^^xsd:dateTime'
             if want.holds_at is not None else "")
    about = "".join(f" ; orexis:about <{a}>" for a in want.about)
    #  WHICH WAY IT BROKE, where the met-test's block said so (`orexis:violationIs`).
    side = f" ; orexis:violationIs <{want.side}>" if want.side else ""
    period = f' ; orexis:start "{clock.now().isoformat()}"^^xsd:dateTime' + (
        f' ; orexis:end "{_moment(want.ends)}"^^xsd:dateTime' if want.ends else "")
    engine.update(_forget(graph) + f""" ;
INSERT {{
  GRAPH <{graph}> {{
  <{want.holder}> orexis:holds <{want.uri}> .
  <{want.uri}> a orexis:Want{timed}{about}{side} ;
      prov:wasDerivedFrom <{want.desire}> ;
      rdfs:label {json.dumps(want.label)} .
  {points}
  {shape} }}
  GRAPH ?cat {{ <{graph}> a deliberation:PursuedGraph ; orexis:arrivedBy orexis:Recorded ;
      orexis:beliefsOf <{want.holder}> ;
      dcterms:temporal [ a dcterms:PeriodOfTime{period} ] . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ deliberation:PursuedGraph rdfs:subClassOf ?kind }} }}""",
                  prefixes=NAMESPACES)


def mint(store: ox.Store, holder: str, desire: str, said=None, holds_at: datetime | None = None,
         about: tuple = (), instance: str | None = None, side: str | None = None) -> str | None:
    """Derive the want pursued under `desire` and write it to the pursued graph, named by
    `name_of`. None, and the desire stays the goal, where the desire states its met-test inline:
    a blank node has no name another graph could point at, and copying it would make a second
    owner of the claim."""
    said = _said(store, desire) if said is None else said
    desire_abouts = _abouts(said)
    abouts = about or desire_abouts
    child = name_of(store, desire, said, about, instance)
    points = []
    met_test = None
    for p, o in said:
        if isinstance(o, ox.BlankNode):
            log.warning("%s states its %s inline; it is pursued itself", desire.rsplit("#", 1)[-1],
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
    #  THE MET-TEST IS THE DESIRE'S INSTANTIATED AT THE WITNESS: carved from where the desire's
    #  shape lives and narrowed to this cluster — the instance as its target, the blocks about
    #  what the want is about — and written into the want's own graph under its own name, so
    #  the want is judged on its instance and a plan for one tank is not refused for another's.
    shape_lines: tuple = ()
    if met_test is not None:
        own = child + ".met"
        shape_lines = narrowed(store, met_test, own, instance, abouts)
        points.append((OREXIS_MET_WHEN, own))

    labels = [str(o.value) for p, o in said if p.endswith("#label")]
    label = "pursued: " + (labels[0] if labels else desire.rsplit("#", 1)[-1])
    #  AT AN INSTANT (#619): bound `orexis:At`, holding at the crossing, its room opening now.
    if holds_at is not None:
        label = f"foreseen: {label[len('pursued: '):]} at {holds_at.isoformat(timespec='minutes')}"
    #  IT HOLDS FROM ITS DERIVATION to the instant it must hold at plus the patience its plan
    #  is given after it — the last step is placed AT the instant and its verdict comes after —
    #  and is open for a want met at its plan's end (#645).
    #  THE WANT, AND THE REPOSITORY WRITES IT (#677). What is derived is decided here — the
    #  binding, the label, what it points at — and where a want is kept, how its graph is
    #  classified and what period it holds during are `wants.py`'s, whether a collection or
    #  this derivation asks for the write.
    ends = None
    if holds_at is not None:
        ends = (holds_at + timedelta(seconds=_patience(store, holder))).isoformat()
    save_want(store, _local(holder), Want(
        uri=child, holder=holder, desire=desire, label=label, ends=ends,
        holds_at=holds_at.isoformat() if holds_at is not None else None,
        derived_at=clock.now().isoformat() if holds_at is not None else None,
        about=abouts, points=tuple(points), shape=shape_lines, side=side))
    log.info("%s reads unmet: pursuing %s", desire.rsplit("#", 1)[-1], child.rsplit("#", 1)[-1])
    return child


def _patience(store: ox.Store, holder: str) -> float:
    """The seconds a plan is given after the instant its want must hold at — the keeper's pick,
    or none where the holder states none."""
    found = rows(store, _PATIENCE_Q, (), holder=holder, patience=PATIENCE_S)
    return float(found[0]["s"]) if found and found[0].get("s") else 0.0


def _local(holder: str) -> str:
    """The holder's local name — what a graph this derivation writes is called, for eyes."""
    return holder.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def narrowed(store: ox.Store, shape: str, own: str, instance: str | None, abouts: tuple) -> tuple[str, ...]:
    """The desire's met-test as THIS want's: the same shape under the want's own name, its
    target the one instance the want is about where the cluster had one, and only the property
    blocks and `sh:sparql` constraints about what the want is about — the universal instantiated
    at its witness (a-desire-is-universal-and-a-want-is-existential). A block or constraint
    saying nothing about what it is about is kept, as is one about `sh:this`, which is the
    instance. The triples, as N-Triples lines the write puts into the want's graph.

    Carved from the graphs of desires and wants, asked by classification, where a desire's shape
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
