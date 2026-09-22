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
from dataclasses import dataclass, replace
from datetime import datetime

import pyoxigraph as ox
import rdflib

from orexis.agent.ontology import FORESEEN, OREXIS
from orexis.agent.store import (NAMESPACES, bind, graphs_of, instant,
                                           rdflib_view, rows)


log = logging.getLogger("derive_wants")

WANT_GRAPH = OREXIS + "WantGraph"
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

#  DOES THE MET-TEST NAME ITS ONE NODE (`sh:targetNode`)?
_TARGETS_ONE_Q = """
ASK { GRAPH ?g { $desire orexis:metWhen ?s . ?s sh:targetNode ?n }
      GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph } }"""

#  HOW LONG A PLAN IS GIVEN after the instant its want must hold at — the keeper's pick, from
#  the record where review writes it. Progression's word, which this layer reads downward.
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
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a execution:IntentionGraph } }"""


#  WHAT THIS DERIVATION HAS MINTED UNDER ONE DESIRE, ACROSS ALL TIME and not at an instant.
#  A want's period is the stretch its TROUBLE occupies, so a want foreseen from three is not
#  handed to a reader standing at two — which is right for a reader asking what is wanted NOW,
#  and wrong for this, whose question is whether it has already minted this. Asked at an
#  instant it would mint a second copy of every foreseen want on every pass until the trouble
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

    Run whenever a pass stands on a desire or on any want under it, and by a package that has
    just written an instance, since a claim arriving should be a want arriving and not a want
    on the next tick. A package that calls this mints nothing; it says an instance is there and
    this does the rest (one-function-mints-every-want).

    IT IS THE DECOMPOSITION OF WHAT THE MET-TESTS READ. A desire is judged at the present and,
    where it reads met there, at every instant a prediction reaches; what comes back is
    witnesses, and a want is minted per cluster of them. Nothing is written between the two.

    **IT WITHDRAWS NOTHING.** Deriving what is wanted and taking away what is not are two acts,
    and this is the first. It used to be both — the same rows that minted also dropped, on the
    argument that the pass had just concluded what a second met-test would ask again — and the
    argument was right about the READING and wrong about the place: what it takes to avoid
    asking twice is that the conclusion be HANDED ON, not that one function do both. So the
    answer is the whole decomposition, and `forget_wants.withdraw` is given it. A caller that
    derives and does not withdraw has a store with wants nothing implies any more; a caller
    that withdraws against a set it did not derive has a bug this signature makes visible.

    The instant is EACH CLUSTER'S OWN. A desire unmet at the present derives wants with none.
    One met at the present derives them at the instants it reads unmet — and two debts cross
    at two deadlines, so the second is not filtered away by the first's; each cluster holds at
    its earliest witness. A desire met at every instant read derives NOTHING.

    WHOSE, FROM THE DESIRE: the graph a desire lives in says who holds it, so the wants it
    implies are written to graphs that holder owns. One agent, one volume, so the holder is
    the agent; a store holding several agents' desires derives for each.

    THE PRESENT IS THE CALLER'S, and it is the only thing besides the store this takes. It was
    read from the clock in five places in here, so "the present" was five reads that could
    disagree inside one pass and a test had to patch the clock to say when it stood.
    """
    shapes = shapes_in(store)
    wanted: set[str] = set()
    for holder, desire, shape in desires_in(store):
        #  ONE READ, OVER EVERY BOUNDARY. What comes back is each way this desire is failing
        #  with the stretch it fails over — the present among the instants and not above them.
        found = read_over_time(store, shapes, holder, desire, shape, now)
        if found is None:
            #  NOT JUDGED IS NOT MET. A desire whose met-test could not be run says nothing
            #  about its wants — so what stands under it is what it implies, and a dropper
            #  handed this answer cannot read silence as "no longer wanted" and take a want
            #  on a bad shape.
            wanted |= _standing_under(store, desire, now)
            continue
        _derive_under(store, shapes, holder, desire, found, now)
        wanted |= _named(store, desire, _said(store, desire), found)
    return wanted


def _standing_under(store: ox.Store, desire: str, now: datetime) -> set[str]:
    """Every want this derivation has minted under `desire`, whatever stretch it is over."""
    return {r["w"] for r in rows(store, _STANDING_Q, (), desire=desire)}


def _derive_under(store: ox.Store, shapes: rdflib.Graph, holder: str, desire: str,
                  found: list[Witness], now: datetime) -> list[str]:
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
    #  where the desire ranges over several (`name_of`). Two tanks low about their level are
    #  two clusters and two names; keyed by what they were about alone, the second read the
    #  first as standing, and by construction the second mint had overwritten the first.
    standing = _standing_under(store, desire, now)
    said = _said(store, desire)
    #  THE FALLBACK IS FOR A DESIRE UNMET NOW AND NOTHING ELSE: one want about everything the
    #  desire is about, for a desire whose select yields rows naming no property. A desire that
    #  reads MET at every boundary reaches this loop with NO clusters, so what stands under it
    #  is withdrawn.
    clusters = _clusters(store, found) or ([[]] if found else [])
    minted = []
    for cluster in clusters:
        about = tuple(sorted({w.about for w in cluster if w.about}))
        instances = {w.instance for w in cluster}
        instance = next(iter(instances)) if len(instances) == 1 else None
        child = name_of(store, desire, said, about, instance)
        #  THE STRETCH THIS CLUSTER IS IN TROUBLE OVER: from the earliest boundary any of its
        #  ways of failing reads unmet at, to the earliest one they have ALL lifted by. A
        #  cluster where one way never lifts is open-ended, because the cluster is not repaired
        #  while any of it stands.
        at = min((w.at for w in cluster), default=now)
        lifts = [w.until for w in cluster] or [None]
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
        sides = {w.side for w in cluster if w.side}
        child = mint(store, shapes, holder, desire, now, at, until, said,
                     about=about, instance=instance,
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
        #  AND BY THE STRETCH. Two ways of failing that one action could move together are one
        #  want only where they are in trouble over the SAME stretch: a want's period is its
        #  trouble's, and a plan for one is placed to land where that trouble begins, so one
        #  want cannot be placed at two instants. Keyed by scope and instance alone, a level
        #  dropping at half past and a temperature rising an hour in became one want starting
        #  at the EARLIER — which says the temperature is in trouble from half past, and it is
        #  not. Worse where one lifts: a cluster is open-ended where any of its ways never
        #  lifts, so a transient dip joined to a standing trouble lost its own end.
        key = ((scope, w.instance, w.at, w.until)
               if scope is not None or w.about == w.instance else None)
        (groups.setdefault(key, []) if key is not None else loose).append(w)
    if not groups:
        return [loose]
    #  A WITNESS NAMING NO SCOPE joins every group it could belong to, as it always has — but
    #  only those in trouble over its own stretch, since joining one at another instant would
    #  widen that group's period to cover a trouble it is not about.
    for w in loose:
        shared = [g for k, g in groups.items() if (k[2], k[3]) == (w.at, w.until)]
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
    #  NARROWER THAN THE DESIRE, or the desire's own name. A want carries what it is about in
    #  its NAME only where the cluster covers less than the desire does: a desire about one
    #  property mints `<desire>.pursued` exactly as it always did, and one about soil and air
    #  broken on soil alone mints a second node. Inlined because this is the one place that
    #  asks it — it was a helper while `mint` also needed the desire's own abouts, to default a
    #  want's stored ones, and a want states none now.
    declared = {str(o.value) for p, o in said if p == OREXIS_ABOUT}
    tails = [_tail(a) for a in about] if about and set(about) != declared else []
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





def graph_of(agent_id: str, at: datetime, until: datetime | None) -> str:
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


#  WITHDRAWAL IS ITS OWN MODULE (`forget_wants.py`). This file decides what is WANTED; taking
#  a want away is the other half of the want's life and has its own reasons — which graph it
#  is in, whether that graph holds others, what the catalogue still says of it. `_write`
#  below imports the one text they share, since replacing a want whole is removing it and
#  putting it back.
from .forget_wants import RECOGNIZED, _forget_one   # noqa: E402  (see the note above)


def _write(engine, agent_id: str, uri: str, holder: str, desire: str, label: str,
           now: datetime, at: datetime, until: datetime | None = None, *,
           points: tuple = (), shape: tuple = (), side: str | None = None) -> None:
    """Write one derived want over the ENGINE: its graph, replaced whole, and the catalogue's
    account of that graph — its family, how it arrived, whose it is and the period it holds
    during — in one update, so a want and what is said about it land together or not at all.

    PRIVATE, AND `mint` IS THE ONLY CALLER. It was `save_want`, public, with one production
    caller and eight in a test that used it to seed stores for `find_wants` — so the read was
    being tested THROUGH the writer, and a matching pair of bugs would have passed. The test
    writes its rows itself now, and this is what the derivation does when it has decided.

    IT TAKES NO `Want`. The type was built here and taken apart on the next line, which is the
    store duplicated in Python for the length of one expression; worse, four of its eleven
    fields — `points`, `shape`, `holder`, `ends` — were populated on this path and left empty
    by every read, so `want.shape` on a want read back was silently `()`. That cost a session:
    the search's met-test asked the model for its shape, got nothing, and reported every want
    exhausted. `Want` is the READ model now and these are arguments, which is what they are.

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
    own structure, and `narrowed` carves by it.
    """
    graph = graph_of(agent_id, at, until)
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
    engine.update(_forget_one(graph, uri) + f""" ;
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


def mint(store: ox.Store, shapes: rdflib.Graph, holder: str, desire: str, now: datetime,
         at: datetime, until: datetime | None = None, said=None,
         about: tuple = (), instance: str | None = None, side: str | None = None) -> str | None:
    """Derive the want pursued under `desire` and write it to the pursued graph, named by
    `name_of`. None, and the desire stays the goal, where the desire states its met-test inline:
    a blank node has no name another graph could point at, and copying it would make a second
    owner of the claim."""
    said = _said(store, desire) if said is None else said
    #  `about` NAMES AND DOES NOT NARROW. What a cluster is about distinguishes two wants
    #  under one desire — soil now, air later, two nodes — and that is an IDENTITY. It is not
    #  written onto the want, because a stated property is the planning problem answered in
    #  advance (see `_write`).
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
        if p in (OREXIS_ABOUT, RDFS_LABEL):
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
        shape_lines = narrowed(shapes, met_test, own, instance, about)
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
    #  because at mint time, before any plan exists, no duration is in sight at all.
    #
    #  WHAT ENDS BY THE CLOCK (#645) is a graph whose ending is a FACT — a round closing, a
    #  claim expiring — where nobody is left to conclude it. A want's ending is a CONCLUSION,
    #  and the derivation that draws it runs every pass. `Want` carries no `ends` at all now:
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


def narrowed(shapes: rdflib.Graph, shape: str, own: str, instance: str | None, abouts: tuple) -> tuple[str, ...]:
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

# --- JUDGING A DESIRE ---------------------------------------------------------------
#
#  JUDGING A DESIRE: running its met-test over the world as it stands and as it is predicted
#  to stand, and saying what it read — as WITNESSES, computed and never stored.
#
#  A desire is universal and a want is existential: the met-test's violation rows are the
#  instances in trouble, each one a witness, and `derive_wants` mints a want per cluster of them.
#  There is no third thing between the two. A stored judgment used to stand there — the
#  met-test's answer per desire per instant, written to a working graph and read back — and it
#  is gone: everything it carried a WANT carries now, and what it was for, telling the next
#  step what the met-test read, is what a witness is.
#
#  THIS IS THE ONLY PLACE THAT READS A PREDICTION. What a desire reads at a foreseen instant is
#  a question about the world, asked here and nowhere else: `derive_wants` asks it to mint and
#  `crossing_of` asks it for an instant, and both get the same answer from the same code rather
#  than from two paths that could disagree.
#
#  WHAT A CALLER TAKES IS THE ANSWER TO ITS OWN QUESTION. A `Witness` is the grain a want is
#  minted at and `derive_wants` clusters on it, so it lives here beside `read_ahead`, which
#  dedups on two of its fields. Every other caller wants an INSTANT — the crossing, or whether
#  a want is still unmet by one — and is handed that, rather than rows to reduce itself.
#
#  A FUNCTION OVER THE STORE: handed the engine, a `pyoxigraph.Store`, and nothing else. Which
#  graphs hold desires, which are predictions and which hold at an instant, the catalogue says;
#  who holds a desire, the desire's own graph says; what a met-test means, its shape says. The
#  present is the caller's, handed in.


log = logging.getLogger("judging")

#  EVERY DESIRE THE STORE HOLDS, who holds it and its met-test, from the graphs of desires
#  holding at the present — the desires graph states no period, the world's asserted graph
#  none, and a graph of desires with one is read while it holds. A desire, its holder and its
#  met-test are written together — one rule derives them, one file ratifies them — so the
#  pattern matches within one graph.
#  NO PERIOD, AND NO FILTER FOR ONE. A desire is authored once at genesis into a graph with no
#  period, which holds at every instant as the T-Box does; everything sourced AT A TIME — a
#  want, an obligation, a round, a prediction — is the graph that holds during one
#  (a-root-holds-always-and-an-outdated-graph-is-dropped). This carried the same period filter
#  every timed read carries, unbound on every row of every store there has ever been, and what
#  it cost was not a cycle: it told a reader that a desire can be timed, which is the one
#  thing that would make it a want.
_DESIRES_Q = """
SELECT DISTINCT ?holder ?desire ?shape WHERE {
  GRAPH ?g { ?holder orexis:holds ?desire . ?desire a orexis:Desire .
             OPTIONAL { ?desire orexis:metWhen ?shape } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph } }
ORDER BY ?holder ?desire"""

#  ONE desire, its holder and its met-test — for a reader asking about one.
#  WHEN THE HOLDER FORESEES: the start of every prediction of theirs, whatever its window —
#  the future states a desire is judged at, given to this and never computed here (#643).
#  EVERY INSTANT THE WORLD THIS AGENT READS CAN CHANGE AT, and the kind of graph is not the
#  question. A graph holds during a stretch: at its START it begins to be handed out and at its
#  END it stops, so those are the only instants at which a judgment can differ from the one
#  before. Everything between two boundaries is one world.
#
#  BOTH ENDS, and the end is the half that was missing. A start alone says when trouble may
#  ARRIVE; an end says when it may LIFT — the pot dries at three and the forecast refills it at
#  six — and without it a want could say when it began and never that it stops.
#
#  NO KIND. It asked for `orexis:PredictionGraph` and so saw only what sensing's drifts wrote:
#  the market had to type its debt-lapse graph as a prediction to be looked at, which it is not
#  — it is a graph holding from a deadline. A round that opens later and a claim whose window
#  closes later are boundaries too, and nobody has to remember a class to be foreseen.
_BOUNDS_Q = """
SELECT DISTINCT ?at WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g dcterms:temporal ?period .
               { ?period orexis:start ?at } UNION { ?period orexis:end ?at }
               FILTER(?at > $now)
               OPTIONAL { ?g orexis:beliefsOf ?owner } FILTER(!BOUND(?owner) || ?owner = $holder) } }
ORDER BY ?at"""

#  WHERE THE SHAPES LIVE: every graph of desires and of wants, whatever its period — a
#  desire's shape and its blank-node closure sit in a desire graph whole, a derived want's own
#  in its want graph, and the whole belief base parsed into rdflib cost half a second per
#  shape for a closure of forty triples (#711).
_SHAPE_GRAPHS_Q = """
SELECT DISTINCT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind . FILTER(isIRI(?g))
               VALUES ?kind { orexis:DesireGraph orexis:WantGraph } } }
ORDER BY ?g"""

#  WHAT A WANT NARROWS ITS DESIRE TO: its own met-test, which is the desire's carved to the
#  cluster the want was minted from and targeted at its instance.
@dataclass(frozen=True)
class Witness:
    """One way a desire is failing, and when it first does: the instance that failed, the
    constraint it failed, what that constraint is about where its block says, WHICH WAY it
    broke where the block says that, and the instant.

    A universal is refuted by a witness, and the want minted under it is the universal
    instantiated at that witness (one-function-mints-every-want). This is what a stored
    judgment's result was, and it is computed rather than stored: a want is where any of it
    is kept.
    """

    instance: str
    constraint: str
    about: str | None
    at: datetime
    side: str | None = None
    #  WHEN IT LIFTS: the earliest boundary after `at` at which this same way of failing reads
    #  MET again, or None where nothing the agent can see ahead to repairs it. A prediction is
    #  what usually says so — the pot dries at three and the forecast refills it at six — and
    #  it is the want's period end, which is the only honest one: what ENDS a want's trouble is
    #  a fact about the world, not a figure borrowed from the ledger.
    until: datetime | None = None


def desires_in(store: ox.Store) -> list[tuple[str, str, str | None]]:
    """Every desire the store holds, as `(holder, desire, met-test or None)`.

    NO INSTANT, because there is nothing to ask one about: a desire holds always. One agent,
    one volume, so the holder is the agent; a store holding several agents' desires answers
    for each.
    """
    return [(r["holder"].value, r["desire"].value,
             r["shape"].value if r["shape"] is not None else None)
            for r in store.query(_DESIRES_Q, prefixes=NAMESPACES)]


def read_over_time(store: ox.Store, shapes: rdflib.Graph, holder: str, desire: str,
                   shape: str | None, now: datetime) -> list[Witness] | None:
    """Every way this desire is failing, each with the stretch it fails over — or None where
    there is no compilable met-test to ask, which is not the same as met.

    ONE LOOP OVER EVERY BOUNDARY, `now` first. The met-test is run at each; what comes back per
    instant is which `(instance, constraint)` pairs read unmet there. A pair is one WAY the
    desire is failing, and the instants it is unmet at give it an interval:

        at      = the earliest boundary it reads unmet
        until   = the earliest boundary AFTER that at which it reads met again, or None

    IT WAS TWO FUNCTIONS AND A BRANCH. `read_now` judged the present over one set of graph
    kinds, `read_ahead` judged the future over another and only where the present read met, and
    each recorded the earliest unmet instant and stopped. Three things fall out of joining
    them. The present stops being privileged — it is the first boundary, and "unmet now" is
    `at == now`. The two kind lists become one, since a prediction's own period already keeps
    it out of the present. And a want can say when its trouble LIFTS, which neither half could
    see: `read_ahead` stopped at the first unmet instant and never asked what came after, so a
    pot that dries at three and is refilled by the forecast at six was a want with a beginning
    and no end.

    A BOUNDARY IS WHERE A JUDGMENT CAN DIFFER and nowhere else: everything between two of them
    is one world (`boundaries`).
    """
    select = compiled(shapes, shape, desire)
    if select is None:
        return None
    #  What each way of failing reads at each instant — unmet where the select bound a row.
    seen: dict[tuple[str, str], Witness] = {}
    lifted: dict[tuple[str, str], datetime] = {}
    for at in boundaries(store, holder, now):
        rows_ = _witnesses_at(store, select, holder, at, now)
        if rows_ is None:
            return None                 # the engine refused the text at some instant
        unmet = set()
        for w in rows_:
            key = (w.instance, w.constraint)
            unmet.add(key)
            seen.setdefault(key, w)
        #  AND WHAT READS MET HERE, for a way of failing that was unmet earlier: the first such
        #  instant is when the trouble lifts. Only the first — a way that fails, lifts and fails
        #  again is one want over the first stretch, and the second is a boundary away.
        for key in seen.keys() - unmet:
            lifted.setdefault(key, at)
    return sorted((replace(w, until=lifted.get((w.instance, w.constraint)))
                   for w in seen.values()),
                  key=lambda w: (w.at, w.instance, w.constraint))


def shapes_in(store: ox.Store) -> rdflib.Graph:
    """Every graph of desires and of wants, as one rdflib graph — where a desire's shape lives
    with its blank-node closure, and a derived want's own.

    WHICH graphs is this module's question; the crossing itself is the store's
    (`store.rdflib_view`), and so is the reason it is N-Triples. The engine's blank-node labels
    are its own, so two graphs' nodes never collide in one text.

    **ONCE PER PASS, AND THE CALLER HOLDS IT.** It is handed down to `narrowed` rather than
    re-fetched there, which it used to be: `narrowed` runs once per want minted, so a pass that
    minted two wants crossed every desire and want graph THREE times — measured — while this
    function's own docstring said "parsed once" and cited the #711 measurement that makes that
    expensive. Crossing is what costs; the answer cannot change inside a pass that has not
    written a shape.
    """
    return rdflib_view(store, *[row["g"].value for row
                                in store.query(_SHAPE_GRAPHS_Q, prefixes=NAMESPACES)])


def compiled(shapes: rdflib.Graph, shape: str | None, of: str) -> str | None:
    """`shape` compiled to the select whose rows are its VIOLATIONS — `?this`, which
    constraint, `?_about` and `?_side` where the constraint's block says them — or None, with
    a word in the log, where there is no shape or the compiler refuses it.

    THE REPORT AND NOT THE FOCUS NODES (one-function-mints-every-want): a desire universal over
    several properties fails per property, and the rows are what say which. The planner
    compiles the same shape the same way for the law it holds candidates to."""
    from orexis.agent.violation import Unsupported, report_select

    if shape is None:
        return None
    try:
        return report_select(shapes.cbd(rdflib.URIRef(shape)), rdflib.URIRef(shape))
    except Unsupported as exc:
        log.warning("%s: its met-test cannot be compiled, so it is not judged: %s",
                    of.rsplit("#", 1)[-1], exc)
        return None


def boundaries(store: ox.Store, holder: str, now: datetime) -> list[datetime]:
    """THE PRESENT AND EVERY INSTANT AFTER IT AT WHICH THE WORLD THIS HOLDER READS CHANGES,
    in order — a period starting, a period ending, and nothing else.

    `now` is the first of them and is not otherwise special. It used to be: the present was
    judged over one set of graph kinds and the future over another, the future only where the
    present read met, and "the present outranks the instant" was a branch. It is arithmetic
    now — the earliest boundary a witness is unmet at is either `now` or it is not.
    """
    return [now] + [datetime.fromisoformat(row["at"].value)
                    for row in store.query(bind(_BOUNDS_Q, holder=holder, now=instant(now)),
                                           prefixes=NAMESPACES)]


def _witnesses_at(store: ox.Store, select: str, holder: str, at: datetime,
                  now: datetime) -> list[Witness] | None:
    """The met-test's rows over the graphs `holder`'s desire is judged over at `at`, as
    witnesses — one per distinct row, since two predictions holding at one instant give one
    instance two offending values and both are told. None where the engine refuses the text.

    ONE SELECT PER DESIRE PER INSTANT, and not one union of them: the compiler measured a
    single UNION of every shape at thirteen times the cost of the selects asked one by one.
    """
    graphs = [ox.NamedNode(g) for g in graphs_of(store, *FORESEEN, holder=holder, at=at, now=now)]
    try:
        found = store.query(select, prefixes=NAMESPACES, default_graph=graphs)
        names = [v.value for v in found.variables]
        seen: dict[tuple, Witness] = {}
        for solution in found:
            row = {name: solution[name] for name in names if solution[name] is not None}
            seen.setdefault(tuple(sorted((k, str(v)) for k, v in row.items())), Witness(
                instance=row["this"].value,
                constraint=row["_constraint"].value if "_constraint" in row else "",
                about=row["_about"].value if "_about" in row else None,
                side=row["_side"].value if "_side" in row else None,
                at=at))
    except Exception as exc:                                        # noqa: BLE001
        log.error("a met-test could not be read at %s: %s", at, exc)
        return None
    return [seen[key] for key in sorted(seen)]


