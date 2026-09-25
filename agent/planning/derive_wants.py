"""`derive_wants`: every desire judged, and a want minted for every cluster of what its
met-test reads unmet (judge-desires-then-derive-wants). ONE FUNCTION and one contract — after
the call the store holds every want its desires imply, and NOTHING STANDS BETWEEN A DESIRE AND
A WANT.

A stored judgment stood between the two once — what a met-test read, per desire per instant,
written to a working graph and read back by the minting and by whoever wanted a crossing. It is
gone, and everything it carried a want carries: which instance is in trouble, what the trouble
is about, which way it broke (`orexis:violationIs`) and the instant it must hold at. What a
met-test reads is a WITNESS, computed where it is needed and stored nowhere, because the answer
is about a situation and the situation has moved by the next pass.

A FUNCTION OVER THE STORE: handed the engine, a `pyoxigraph.Store`, and nothing else. The
judging says what each desire reads and whose it is, the scope graph says which witnesses
cluster, the graphs of desires say what a desire is about and what its met-test is, the graphs
of wants say what already stands, and the pick record says how long a plan is given after its
instant. The present is the CALLER'S — a parameter, so this is a function of a store
and an instant and reads no clock.

What was minted this time comes back for the caller that asked whether its own want was
re-minted. A caller holding a projection of the wants refreshes it on a non-empty answer —
announcing a write is the repository's contract, and a function that writes past it leaves the
refresh to whoever holds one.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime

import pyoxigraph as ox
import rdflib

from agent.ontology import DESIRE, OREXIS, RECORD, SHAPES, WANT
from agent.store import NAMESPACES, Memo, Raw, bind, graphs_of, rdflib_view, remember, rows

from .withdraw import FORGET_ONE_U
from .find_scopes import find_scopes

RECOGNIZED = OREXIS + "Recognized"

log = logging.getLogger("derive_wants")

OREXIS_MET_WHEN = OREXIS + "metWhen"
#  THE TWO OF A DESIRE'S OWN WORDS THIS FILE SORTS BY. They were matched as string SUFFIXES —
#  `p.endswith("#about")` at three sites — which is safe only because `_SAID_Q` four hundred
#  lines away filters to five named predicates, so nothing else can end in those letters. That
#  coupling was invisible at every site, and a sixth predicate whose local name ended in
#  `about` or `label` would have been read as one of these, silently.
OREXIS_ABOUT = OREXIS + "about"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

#  WHAT A DESIRE SAYS, from the graphs of desires and wants asked by class: what it is about,
#  what it points at, its label and its met-test. The OBJECT'S TYPE matters — a blank node
#  cannot be pointed at from another graph — so the caller reads the engine's own terms.
_SAID_Q = """
SELECT ?p ?o WHERE {
  GRAPH ?g { $desire ?p ?o
    FILTER(?p IN (orexis:metWhen, orexis:unmetWhen, orexis:estimates, orexis:about, rdfs:label)) }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { orexis:DesireGraph orexis:WantGraph } } }"""

#  WHAT THIS DERIVATION HAS MINTED UNDER ONE DESIRE, ACROSS ALL TIME and not at an instant.
#  A want's period is the stretch its TROUBLE occupies, so a want foreseen from three is not
#  handed to a reader standing at two — which is right for a reader asking what is wanted NOW,
#  and wrong for this, whose question is whether it has already minted this. Asked at an
#  instant it would _mint a second copy of every foreseen want on every pass until the trouble
#  arrived. Existence is not an instant question.
_STANDING_Q = """
SELECT ?w WHERE {
  GRAPH ?g { ?w a orexis:Want ; prov:wasDerivedFrom $desire }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a orexis:WantGraph ; orexis:arrivedBy orexis:Derived } }
ORDER BY ?w"""


def derive_wants(store: ox.Store, now: datetime) -> set[str]:
    """Mint a want under every desire for every cluster of what its met-test reads unmet, and
    answer with EVERY want those desires imply — the ones minted here and the ones already
    standing under the same name.

    IT READS THE WEIGHINGS THE PLANNER WROTE. A desire is judged where the search judges a
    want, by `weigh`, which the Planner calls for every desire in every ground before this —
    an act calls no other act — writing the met-test's report in each ground as a weighing
    with its violation rows: the instances in trouble, which constraint, what it is about,
    which way it broke. Read across the grounds in order, a violation has a stretch: the
    first ground it holds in is when the trouble begins, the first later ground it does not is
    when it lifts. A want is minted per cluster of them. Nothing stands between a desire and
    a want but the weighings, which are in the store where a reader can see what the
    derivation saw — and a desire with no weighing in some ground is not judged, which is
    not the same as met.

    **IT WITHDRAWS NOTHING.** Deriving what is wanted and taking away what is not are two
    acts, and this is the first: the answer is the whole decomposition, and `withdraw` is
    given it. A caller that derives and does not withdraw has a store with wants nothing
    implies any more; a caller that withdraws against a set it did not derive has a bug this
    signature makes visible.

    WHOSE, FROM THE DESIRE: the graph a desire lives in says who holds it, so the wants it
    implies are written to graphs that holder owns. THE PRESENT IS THE CALLER'S, the one
    thing besides the store this takes, for when the agent found what it minted.
    """
    memo = Memo()
    shapes = remember(memo, ("shapes",),
                      lambda: rdflib_view(store, *graphs_of(store, DESIRE, WANT, RECORD, SHAPES)))
    scopes = find_scopes(store)
    if not rows(store, _GROUNDS_Q, ()):
        raise RuntimeError("the store holds no ground — lay_ground has not run")
    wanted: set[str] = set()
    for holder, desire in _desires_in(store):
        found = _troubles(store, desire)
        if found is None:
            #  NOT JUDGED IS NOT MET. A desire whose met-test could not be run says nothing
            #  about its wants — so what stands under it is what it implies, and a dropper
            #  handed this answer cannot read silence as "no longer wanted" and take a want
            #  on a bad shape.
            wanted |= _standing_under(store, desire, now)
            continue
        _derive_under(store, shapes, scopes, holder, desire, found, now)
        wanted |= _named(shapes, scopes, desire, _said(store, desire), found)
    return wanted


def _standing_under(store: ox.Store, desire: str, now: datetime) -> set[str]:
    """Every want this derivation has minted under `desire`, whatever stretch it is over."""
    return {r["w"] for r in rows(store, _STANDING_Q, (), desire=desire)}


def _derive_under(store: ox.Store, shapes: rdflib.Graph, scopes: dict | None, holder: str,
                  desire: str, found: list[dict], now: datetime) -> list[str]:
    """The wants one desire's witnesses imply, minted where none stands. `found` is what its
    met-test read over time: one witness per way of failing, each carrying the boundary it
    first reads unmet at and the one it lifts at."""
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
    #  where the desire ranges over several (`_name_of`). Two tanks low about their level are
    #  two clusters and two names; keyed by what they were about alone, the second read the
    #  first as standing, and by construction the second _mint had overwritten the first.
    standing = _standing_under(store, desire, now)
    said = _said(store, desire)
    #  THE FALLBACK IS FOR A DESIRE UNMET NOW AND NOTHING ELSE: one want about everything the
    #  desire is about, for a desire whose select yields rows naming no property. A desire that
    #  reads MET at every boundary reaches this loop with NO clusters, so what stands under it
    #  is withdrawn.
    clusters = _clusters(scopes, found) or ([[]] if found else [])
    minted = []
    for cluster in clusters:
        about = tuple(sorted({w["about"] for w in cluster if w["about"]}))
        instances = {w["instance"] for w in cluster}
        instance = next(iter(instances)) if len(instances) == 1 else None
        child = _name_of(shapes, desire, said, about, instance)
        #  THE STRETCH THIS CLUSTER IS IN TROUBLE OVER: from the earliest boundary any of its
        #  ways of failing reads unmet at, to the earliest one they have ALL lifted by. A
        #  cluster where one way never lifts is open-ended, because the cluster is not repaired
        #  while any of it stands.
        at = min((w["at"] for w in cluster), default=now)
        lifts = [w["until"] for w in cluster] or [None]
        until = None if any(u is None for u in lifts) else max(lifts)
        #  A WANT ALREADY STANDING FOR THIS CLUSTER IS LEFT ALONE, whatever stretch it was
        #  minted over. It used to be re-minted when what was foreseen arrived, because the
        #  want carried the instant it must hold at and the present outranked it; the stretch
        #  is on the graph now and a want in trouble from three is in trouble from three
        #  whether it is two o'clock or four.
        if child in standing:
            continue
        #  ONE SIDE OR NONE: the witnesses of a cluster agree where the same block found them
        #  all, and two sides in one cluster is a want about two troubles, which says neither.
        sides = {w["side"] for w in cluster if w["side"]}
        child = _mint(store, shapes, holder, desire, now, at, until, said,
                     about=about, instance=instance,
                     side=next(iter(sides)) if len(sides) == 1 else None)
        if child is not None:
            minted.append(child)
    return minted


def _named(shapes: rdflib.Graph, scopes: dict | None, desire: str, said,
           found: list[dict]) -> set[str]:
    """The names the clusters of `found` come to — what minting would call them.

    One namer for both halves: `_derive_under` mints under these names and `_withdraw_under`
    keeps what is under them, so the two can never disagree about which want a cluster is.
    """
    out = set()
    for cluster in _clusters(scopes, found):
        about = tuple(sorted({w["about"] for w in cluster if w["about"]}))
        instances = {w["instance"] for w in cluster}
        out.add(_name_of(shapes, desire, said, about,
                        next(iter(instances)) if len(instances) == 1 else None))
    return out


def _clusters(scopes: dict | None, witnesses: list) -> list[list]:
    """The witnesses grouped by SCOPE — which of them some action can move together — so a
    want is minted per group. Two in one scope are one want and one cone; two in different
    scopes are two, planned apart and concatenated, which is the mechanism `scope.md` says the
    concept exists for. A witness naming no property, or one no scope holds, joins every group
    it could belong to, which with one scope is the one group.

    THE SCOPES ARE READ, NEVER COMPUTED: `scope_actions` wrote them (scope-actions), read
    once per call and handed in, and a store holding no scope graph is refused rather than
    clustered as one scope — the
    loud direction, since one want about everything is what a missing partition would have
    quietly minted.

    Measured on every shipped world: one scope, so one group. The code path is the same the
    day a world splits, and a scope is over PREDICATES — two debts to two hosts are one scope,
    correctly, since they may draw from one vessel."""
    if not witnesses:
        return []
    if scopes is None:
        raise RuntimeError("the store holds no scope graph — scope_actions has not run")
    groups: dict = {}
    loose = []
    for w in witnesses:
        scope = scopes.get(w["about"]) if w["about"] else None
        #  AND BY THE STRETCH. Two ways of failing that one action could move together are one
        #  want only where they are in trouble over the SAME stretch: a want's period is its
        #  trouble's, and a plan for one is placed to land where that trouble begins, so one
        #  want cannot be placed at two instants. Keyed by scope and instance alone, a level
        #  dropping at half past and a temperature rising an hour in became one want starting
        #  at the EARLIER — which says the temperature is in trouble from half past, and it is
        #  not. Worse where one lifts: a cluster is open-ended where any of its ways never
        #  lifts, so a transient dip joined to a standing trouble lost its own end.
        key = ((scope, w["instance"], w["at"], w["until"])
               if scope is not None or w["about"] == w["instance"] else None)
        (groups.setdefault(key, []) if key is not None else loose).append(w)
    if not groups:
        return [loose]
    #  A WITNESS NAMING NO SCOPE joins every group it could belong to, as it always has — but
    #  only those in trouble over its own stretch, since joining one at another instant would
    #  widen that group's period to cover a trouble it is not about.
    for w in loose:
        shared = [g for k, g in groups.items() if (k[2], k[3]) == (w["at"], w["until"])]
        for group in shared or groups.values():
            group.append(w)
    return list(groups.values())


def _said(store: ox.Store, desire: str) -> list[tuple[str, object]]:
    """What the desire says, as `(predicate, the engine's own term)` — the TYPE is load-bearing,
    since a blank node has no name another graph could point at."""
    solutions = store.query(bind(_SAID_Q, desire=desire), prefixes=NAMESPACES)
    return sorted(((str(s["p"].value), s["o"]) for s in solutions), key=lambda pair: (pair[0], str(pair[1])))


def _tail(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _name_of(shapes: rdflib.Graph, desire: str, said, about: tuple, instance: str | None) -> str:
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
    #  NARROWER THAN THE DESIRE, or the desire's own name. A want carries what it is about in
    #  its NAME only where the cluster covers less than the desire does: a desire about one
    #  property mints `<desire>.pursued` exactly as it always did, and one about soil and air
    #  broken on soil alone mints a second node. Inlined because this is the one place that
    #  asks it — it was a helper while `_mint` also needed the desire's own abouts, to default a
    #  want's stored ones, and a want states none now.
    declared = {str(o.value) for p, o in said if p == OREXIS_ABOUT}
    tails = [_tail(a) for a in about] if about and set(about) != declared else []
    if instance is not None and instance not in about and not _targets_one_node(shapes, said):
        tails.insert(0, _tail(instance))
    return desire + ".pursued" + "".join(f".{t}" for t in tails)


def _targets_one_node(shapes: rdflib.Graph, said) -> bool:
    """Does the desire's met-test name the one node it is about (`sh:targetNode`)? Read off
    the shapes already crossed for the pass — it was an ASK per cluster, three queries on the
    plans case for a fact the crossing already held."""
    from rdflib import URIRef
    from rdflib.namespace import SH
    return any((URIRef(str(o.value)), SH.targetNode, None) in shapes
               for p, o in said if p == OREXIS_MET_WHEN)


# --- what a want IS on disk, and how one goes -------------------------------------------
#
#  THE DERIVATION OWNS ITS OWN WRITES. These were module functions in `wants.py` beside the
#  collection, so the one function that mints wants had to reach into a repository to put one
#  down. A want's graph, what the catalogue says of it and the period it holds during are
#  decided where the want is decided; `wants.py` reads them back and names none of it.





def _graph_of(agent_id: str, at: datetime, until: datetime | None) -> str:
    """The graph the wants in trouble over ONE STRETCH live in, named for that stretch.

    A WANT'S TEMPORAL EXTENT IS ITS GRAPH'S PERIOD, and it is said once. A want used to carry
    `orexis:holdsAt` — the instant it must hold at — beside a graph whose period ran from when
    it was derived, so the same fact was in two places and neither said the whole of it. The
    period IS the trouble now: from the boundary it begins at to the one it lifts by. `at what
    instant is this wanted` is then a question the DOOR answers — `find_wants(store, at=T)`
    hands back what is in trouble at T, for any T, with no reader special-casing the present.

    ONE GRAPH PER STRETCH, not one per want. Wants that are in trouble over the same stretch
    share it; wants over different stretches get one each. That is what lets the period be
    stated once per graph rather than once per want, and `forget_want` already knew how to
    take one want out of a graph that holds others.

    WHEN THE AGENT FOUND IT is a different axis and stays on the want, in PROV's words
    (`prov:generatedAtTime`): the period says when the trouble is, provenance says when we
    learned of it, and a graph whose period began at derivation could say neither.
    """
    tail = f"{_stamp(at)}--{_stamp(until) if until else 'open'}"
    return f"http://example.org/orexis/graph/pursued/{agent_id}/{tail}"


def _stamp(at: datetime) -> str:
    """An instant as a name-safe segment. For eyes: a reader asks the catalogue."""
    return at.isoformat().replace(":", "").replace("+", "p")


#  WITHDRAWAL IS ITS OWN MODULE (`withdraw.py`, and `forget_want.py` for one want). This
#  file decides what is WANTED; taking a want away is the other half of the want's life and
#  has its own reasons. `_write` below runs the one text they share, since replacing a want
#  whole is removing it and putting it back.

def _write(store, agent_id: str, uri: str, holder: str, desire: str, label: str,
           now: datetime, at: datetime, until: datetime | None = None, *,
           points: tuple = (), shape: tuple = (), side: str | None = None) -> None:
    """Write one derived want over the ENGINE: its graph, replaced whole, and the catalogue's
    account of that graph — its family, how it arrived, whose it is and the period it holds
    during — in one update, so a want and what is said about it land together or not at all.

    PRIVATE, AND `_mint` IS THE ONLY CALLER. It was `save_want`, public, with one production
    caller and eight in a test that used it to seed stores for `find_wants` — so the read was
    being tested THROUGH the writer, and a matching pair of bugs would have passed. The test
    writes its rows itself now, and this is what the derivation does when it has decided.

    IT TAKES ARGUMENTS AND NOT A MODEL. There was a want TYPE, built here and taken apart on
    the next line, which is the store duplicated in Python for the length of one expression;
    worse, four of its eleven fields — `points`, `shape`, `holder`, `ends` — were populated on
    this path and left empty by every read, so a want read back silently carried `shape=()`.
    That cost a session: the search's met-test asked the model for its shape, got nothing, and
    reported every want exhausted. The type is gone from both ends now — `find_wants` answers
    with uris, and what a reader needs beside one it reads out of the want's own graph.

    THE KNOWLEDGE STAYS IN THIS FILE (#677): the derivation decides what a want IS — its name,
    its label, what it points at, when it must hold — and where a want is kept is this module's.
    The catalogue is found by its own row and every kind the vocabulary puts a want graph
    beneath is written from one `rdfs:subClassOf` step, the closure being materialised at
    genesis (one-graph-both-engines-read).

    THE GRAPH IS SHARED BY STRETCH, so this takes the want OUT and puts it back rather than
    replacing the graph whole: a second want in trouble over the same stretch lives there too,
    and dropping the graph to re-write one of them would take the other with it. `_forget_one`
    is the text for that and existed already, for a debt sharing the ledger's record.

    AND THE PERIOD IS WRITTEN ONCE, guarded, for the reason that sharing exposed: a period is a
    BLANK NODE, and a blank node in an `INSERT` is a new node every time it runs. Asserted per
    want, three wants in one graph gave that graph three periods and every read joining through
    `dcterms:temporal` returned each want three times. The classification itself is plain
    triples and idempotent by RDF; only the period needed guarding.

    AND NO `orexis:about`. A want used to state the one domain property it was in trouble
    over, and actions joined themselves to it to find the want they served. That is filtering
    to the goal's predicates, which the closure exists because it is wrong: *"filtering to the
    goal's predicates deletes every chain; closing backward through preconditions keeps the
    bid that makes the dose possible"*. WHAT a want reads is its met-test's to say and the
    closure's to walk; what may repair it is the planning problem, and a want that named one
    property had answered it before the planner was asked. The word survives where it is
    about a SHAPE BLOCK — which property one constraint concerns — because that is the shape's
    own structure, and `_narrowed` carves by it.
    """
    graph = _graph_of(agent_id, at, until)
    said_points = " ".join(f"<{uri}> <{p}> <{o}> ." for p, o in points)
    shape_lines = "\n  ".join(shape)
    #  INSTANTS CROSS HERE AND NOWHERE ELSE. The store keeps them as `xsd:dateTime` literals
    #  and everything above works in instants, so this is where the two forms meet.
    #
    #  WHEN THE AGENT FOUND IT, always and not only for a foreseen one: the period says when
    #  the trouble IS and this says when we learned of it, which is the arrival axis and PROV's
    #  to state. A want used to carry `orexis:holdsAt` beside it — the instant it must hold at
    #  — which the period now says, and said it only for foreseen wants, so a want in trouble
    #  now recorded neither instant.
    found_at = f' ; prov:generatedAtTime "{now.isoformat()}"^^xsd:dateTime'
    #  WHICH WAY IT BROKE, where the met-test's block said so (`orexis:violationIs`).
    broke = f" ; orexis:violationIs <{side}>" if side else ""
    #  THE STRETCH, on the graph: from the boundary this trouble begins at to the one it lifts
    #  by, open where nothing the agent can see ahead to repairs it. A fact the predictions
    #  state, which is the only honest source for one — the predecessor took the closing
    #  instant from the KEEPER'S PATIENCE, a figure about how long a commitment blocks
    #  re-adoption of itself, which is a different question wearing the same unit.
    period = (f' ; orexis:start "{at.isoformat()}"^^xsd:dateTime'
              + (f' ; orexis:end "{until.isoformat()}"^^xsd:dateTime' if until else ""))
    store.update(bind(FORGET_ONE_U, graph=Raw(f"<{graph}>"), want=Raw(f"<{uri}>")) + f""" ;
INSERT {{
  GRAPH <{graph}> {{
  <{holder}> orexis:holds <{uri}> .
  <{uri}> a orexis:Want{found_at}{broke} ;
      orexis:state <{RECOGNIZED}> ;
      prov:wasDerivedFrom <{desire}> ;
      rdfs:label {json.dumps(label)} .
  {said_points}
  {shape_lines} }}
  GRAPH ?cat {{ <{graph}> a orexis:WantGraph ; orexis:arrivedBy orexis:Derived ;
      orexis:beliefsOf <{holder}> . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> dcterms:temporal
      [ a dcterms:PeriodOfTime{period} ] . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }}
         FILTER NOT EXISTS {{ GRAPH ?cat {{ <{graph}> dcterms:temporal ?held }} }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ orexis:WantGraph rdfs:subClassOf ?kind }} }}""",
                 prefixes=NAMESPACES)


def _mint(store: ox.Store, shapes: rdflib.Graph, holder: str, desire: str, now: datetime,
         at: datetime, until: datetime | None = None, said=None,
         about: tuple = (), instance: str | None = None, side: str | None = None) -> str | None:
    """Derive the want pursued under `desire` and write it to the pursued graph, named by
    `_name_of`. None, and the desire stays the goal, where the desire states its met-test inline:
    a blank node has no name another graph could point at, and copying it would make a second
    owner of the claim."""
    said = _said(store, desire) if said is None else said
    #  `about` NAMES AND DOES NOT NARROW. What a cluster is about distinguishes two wants
    #  under one desire — soil now, air later, two nodes — and that is an IDENTITY. It is not
    #  written onto the want, because a stated property is the planning problem answered in
    #  advance (see `_write`).
    child = _name_of(shapes, desire, said, about, instance)
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
        if p in (OREXIS_ABOUT, RDFS_LABEL):
            continue
        if p == OREXIS_MET_WHEN:
            met_test = str(o.value)
            continue
        points.append((p, str(o.value)))
    #  THE MET-TEST IS THE DESIRE'S INSTANTIATED AT THE WITNESS: carved from where the desire's
    #  shape lives and _narrowed to this cluster — the instance as its target, the blocks about
    #  what the want is about — and written into the want's own graph under its own name, so
    #  the want is judged on its instance and a plan for one tank is not refused for another's.
    shape_lines: tuple = ()
    if met_test is not None:
        own = child + ".met"
        shape_lines = _narrowed(shapes, met_test, own, instance, about)
        points.append((OREXIS_MET_WHEN, own))

    labels = [str(o.value) for p, o in said if p == RDFS_LABEL]
    label = "pursued: " + (labels[0] if labels else desire.rsplit("#", 1)[-1])
    #  FORESEEN, where the trouble has not begun: for eyes, since the stretch itself is on
    #  the graph and every reader asks the period.
    if at > now:
        label = f"foreseen: {label[len('pursued: '):]} at {at.isoformat(timespec='minutes')}"
    #  IT HOLDS FROM ITS DERIVATION AND IT DOES NOT END BY THE CLOCK. A want minted here
    #  ends when the decomposition stops producing it — `_withdraw_under`, on the same rows
    #  that minted it — and that is the whole of what ends one. It used to carry a period end
    #  as well, at its instant plus the KEEPER'S PATIENCE, and that was wrong three ways: the
    #  patience answers how long a commitment blocks re-adoption of itself, which is a
    #  different question from how long after its instant a want stays readable; it made the
    #  planning layer borrow the ledger's figure to size something planning writes; and it was
    #  a second authority on a question withdrawal already answers, with a number reached for
    #  because at _mint time, before any plan exists, no duration is in sight at all.
    #
    #  WHAT ENDS BY THE CLOCK (#645) is a graph whose ending is a FACT — a round closing, a
    #  claim expiring — where nobody is left to conclude it. A want's ending is a CONCLUSION,
    #  and the derivation that draws it runs every pass. Nothing carries an `ends` in Python:
    #  a field only the writer filled and no read returned is the empty-result trap wearing a
    #  dataclass, and a want whose window genuinely IS a fact — a debt's — is written by
    #  whoever knows that, not by this.
    #
    #  THE WANT, AND THE REPOSITORY WRITES IT (#677). What is derived is decided here — the
    #  binding, the label, what it points at — and where a want is kept, how its graph is
    #  classified and what period it holds during are `wants.py`'s, whether a collection or
    #  this derivation asks for the write.
    _write(store, _local(holder), child, holder, desire, label, now, at, until,
           points=tuple(points), shape=shape_lines, side=side)
    log.info("%s reads unmet: pursuing %s", desire.rsplit("#", 1)[-1], child.rsplit("#", 1)[-1])
    return child


def _local(holder: str) -> str:
    """The holder's local name — what a graph this derivation writes is called, for eyes."""
    return holder.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _narrowed(shapes: rdflib.Graph, shape: str, own: str, instance: str | None, abouts: tuple) -> tuple[str, ...]:
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
    #  From the graphs that hold desires and wants, crossed ONCE for the pass and handed in:
    #  this runs per want minted, and fetching it here crossed every one of them per want.
    cbd = shapes.cbd(URIRef(shape))
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

# --- WHAT THE WEIGHINGS SAY --------------------------------------------------------------
#
#  EVERY DESIRE THE STORE HOLDS and who holds it, from the graphs of desires — a desire, its
#  holder and its met-test are written together, so the pattern matches within one graph. NO
#  PERIOD, AND NO FILTER FOR ONE: a desire is authored once into a graph with no period,
#  which holds at every instant as the T-Box does.
_DESIRES_Q = """
SELECT DISTINCT ?holder ?desire WHERE {
  GRAPH ?g { ?holder orexis:holds ?desire . ?desire a orexis:Desire }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph } }
ORDER BY ?holder ?desire"""

#  THE TIMELINE: every ground, earliest first — the present, and what each prediction makes
#  of it. Each is a world a desire is judged in, and their order is what gives a violation
#  its stretch.
_GROUNDS_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start } }
ORDER BY ?start"""

#  WHAT ONE DESIRE'S WEIGHINGS SAY, ground by ground: the verdict, and every violation with
#  its instance, its constraint, what it is about and which way it broke.
_TROUBLES_Q = """
SELECT ?start ?met ?instance ?constraint ?about ?side WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?x a planning:Weighing ; planning:for $desire ; planning:weighs ?g .
    ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start .
    OPTIONAL { ?x planning:met ?met }
    OPTIONAL { ?x planning:violation ?v . ?v planning:instance ?instance .
               OPTIONAL { ?v planning:constraint ?constraint }
               OPTIONAL { ?v orexis:about ?about }
               OPTIONAL { ?v orexis:violationIs ?side } } } }
ORDER BY ?start ?instance ?constraint"""


def _desires_in(store: ox.Store) -> list[tuple[str, str]]:
    """Every desire the store holds, as `(holder, desire)`. One agent, one volume, so the
    holder is the agent; a store holding several agents' desires answers for each."""
    return [(r["holder"], r["desire"]) for r in rows(store, _DESIRES_Q, ())]


def _troubles(store: ox.Store, desire: str) -> list[dict] | None:
    """Every way `desire` is failing, each with the stretch it fails over — or None where any
    ground was not judged, which is not the same as met.

    A WAY OF FAILING is one `(instance, constraint)` pair, and the grounds it is violated in
    give it an interval: `at`, the start of the earliest ground it reads unmet in; `until`,
    the start of the first later ground it reads met in, or None where nothing the agent can
    see ahead repairs it. The present is the first ground and is not otherwise special —
    "unmet now" is `at == the present`. A way that fails, lifts and fails again is one want
    over the first stretch, and the second is a ground away.
    """
    found = rows(store, _TROUBLES_Q, (), desire=desire)
    if not found or any(r.get("met") is None for r in found):
        return None
    seen: dict[tuple, dict] = {}
    lifted: dict[tuple, datetime] = {}
    by_ground: dict[str, list] = {}
    for r in found:
        by_ground.setdefault(r["start"], []).append(r)
    for start, group in sorted(by_ground.items()):
        at = datetime.fromisoformat(start)
        unmet = set()
        for r in group:
            if not r.get("instance"):
                continue
            key = (r["instance"], r.get("constraint", ""))
            unmet.add(key)
            seen.setdefault(key, {"instance": r["instance"], "constraint": r.get("constraint", ""),
                                  "about": r.get("about"), "side": r.get("side"), "at": at})
        for key in seen.keys() - unmet:
            lifted.setdefault(key, at)
    return sorted(({**w, "until": lifted.get(k)} for k, w in seen.items()),
                  key=lambda w: (w["at"], w["instance"], w["constraint"]))
