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

import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime

import pyoxigraph as ox
import rdflib

from orexis_agent_execution.ontology import FORESEEN, OREXIS
from orexis_agent_execution.store import NAMESPACES, bind, graphs_of, instant, rows


log = logging.getLogger("derive_wants")

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


_STANDING_Q = """
SELECT ?w ?holdsAt WHERE {
  GRAPH ?g { ?w a orexis:Want ; prov:wasDerivedFrom $desire .
             OPTIONAL { ?w orexis:holdsAt ?holdsAt } }
  GRAPH ?cat {
    ?cat a orexis:CatalogueGraph . ?g a orexis:WantGraph ; orexis:arrivedBy orexis:Derived .
    OPTIONAL { ?g dcterms:temporal ?period .
               OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } } }
  FILTER(!BOUND(?start) || ?start <= $now) FILTER(!BOUND(?end) || ?end > $now) }
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
    for holder, desire, shape in desires_in(store, now):
        #  WHAT IT READS NOW, and what it reads ahead only where now is met: a desire in
        #  trouble already is pursued as it stands, and a crossing is a thing in the future.
        present = read_now(store, shapes, holder, desire, shape, now)
        standing = _standing_under(store, desire, now)
        if present is None:
            #  NOT JUDGED IS NOT MET. A desire whose met-test could not be run says nothing
            #  about its wants — so what stands under it is what it implies, and a dropper
            #  handed this answer cannot read silence as "no longer wanted" and take a want
            #  on a bad shape.
            wanted |= standing
            continue
        unmet_now = bool(present)
        found = present if unmet_now else read_ahead(store, shapes, holder, desire, shape, now)
        _derive_under(store, holder, desire, found, unmet_now, now)
        said = _said(store, desire)
        names = _named(store, desire, said, found)
        #  AND THE FORESEEN HALF, where anything would otherwise be dropped: `found` is the
        #  present alone when the desire is unmet now — a crossing is not minted for while
        #  there is trouble already — so a want minted at a foreseen instant is absent from it,
        #  and a dropper reading this answer would take it the moment any OTHER instance went
        #  unmet now. A presented debt did exactly that to an unpresented one. Read only when
        #  something stands that these names do not cover, so a pass with nothing stale pays
        #  nothing for it.
        if unmet_now and standing - names:
            names |= _named(store, desire, said,
                            read_ahead(store, shapes, holder, desire, shape, now))
        wanted |= names
    return wanted


def _standing_under(store: ox.Store, desire: str, now: datetime) -> set[str]:
    """Every want this derivation minted under `desire` and that still holds at `now`."""
    return {r["w"] for r in rows(store, _STANDING_Q, (), desire=desire, now=instant(now))}


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
        child = mint(store, holder, desire, now, said, holds_at=at, about=about, instance=instance,
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
    desire reuses it, and everything keyed by the want finds what it kept.

    THE NAME LIVES WITH THE WRITER. It was two functions in two modules — a `pursued_graph`
    in the layer's vocabulary holding the prefix, and this holding the prefix plus the want's
    local part — and the first had no caller but the second. A vocabulary module holds TERMS,
    which are public and which code is written against; a graph's name is for eyes, owned by
    whoever writes the graph and depended on by nothing, which is why `test_layout.py` refuses
    a READER that imports one. This module writes these graphs, classifies them and drops
    them, so it names them.
    """
    return f"http://example.org/orexis/graph/pursued/{agent_id}/{uri.rsplit('#', 1)[-1]}"


#  WITHDRAWAL IS ITS OWN MODULE (`forget_wants.py`). This file decides what is WANTED; taking
#  a want away is the other half of the want's life and has its own reasons — which graph it
#  is in, whether that graph holds others, what the catalogue still says of it. `_write`
#  below imports the one text they share, since replacing a want whole is removing it and
#  putting it back.
from .forget_wants import RECOGNIZED, forget_graph   # noqa: E402  (see the note above)


def _write(engine, agent_id: str, uri: str, holder: str, desire: str, label: str,
           now: datetime, *, holds_at: str | None = None, derived_at: str | None = None,
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

    NO PERIOD END. A derived want ends when the decomposition stops producing it, never by the
    clock — see `mint` below for the argument.

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
    graph = graph_of(agent_id, uri)
    said_points = " ".join(f"<{uri}> <{p}> <{o}> ." for p, o in points)
    shape_lines = "\n  ".join(shape)
    #  INSTANTS CROSS HERE AND NOWHERE ELSE. A want carries them as instants, because what
    #  reads them — the keeper placing a step, a reader measuring the room left — works in
    #  instants; the store keeps them as `xsd:dateTime` literals. This is the boundary, so it
    #  is where the two forms meet, one line each way (`_moment` here, `_instant` on read).
    timed = (f' ; orexis:holdsAt "{_moment(holds_at)}"^^xsd:dateTime'
             f' ; prov:generatedAtTime "{_moment(derived_at)}"^^xsd:dateTime'
             if holds_at is not None else "")
    #  WHICH WAY IT BROKE, where the met-test's block said so (`orexis:violationIs`).
    broke = f" ; orexis:violationIs <{side}>" if side else ""
    engine.update(forget_graph(graph) + f""" ;
INSERT {{
  GRAPH <{graph}> {{
  <{holder}> orexis:holds <{uri}> .
  <{uri}> a orexis:Want{timed}{broke} ;
      orexis:state <{RECOGNIZED}> ;
      prov:wasDerivedFrom <{desire}> ;
      rdfs:label {json.dumps(label)} .
  {said_points}
  {shape_lines} }}
  GRAPH ?cat {{ <{graph}> a orexis:WantGraph ; orexis:arrivedBy orexis:Derived ;
      orexis:beliefsOf <{holder}> ;
      dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start "{now.isoformat()}"^^xsd:dateTime ] . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ orexis:WantGraph rdfs:subClassOf ?kind }} }}""",
                  prefixes=NAMESPACES)


def mint(store: ox.Store, holder: str, desire: str, now: datetime, said=None,
         holds_at: datetime | None = None, about: tuple = (), instance: str | None = None,
         side: str | None = None) -> str | None:
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
        shape_lines = narrowed(store, met_test, own, instance, about)
        points.append((OREXIS_MET_WHEN, own))

    labels = [str(o.value) for p, o in said if p.endswith("#label")]
    label = "pursued: " + (labels[0] if labels else desire.rsplit("#", 1)[-1])
    #  AT AN INSTANT (#619): bound `orexis:At`, holding at the crossing, its room opening now.
    if holds_at is not None:
        label = f"foreseen: {label[len('pursued: '):]} at {holds_at.isoformat(timespec='minutes')}"
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
    _write(store, _local(holder), child, holder, desire, label, now,
           holds_at=holds_at.isoformat() if holds_at is not None else None,
           derived_at=now.isoformat() if holds_at is not None else None,
           points=tuple(points), shape=shape_lines, side=side)
    log.info("%s reads unmet: pursuing %s", desire.rsplit("#", 1)[-1], child.rsplit("#", 1)[-1])
    return child


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
_DESIRES_Q = """
SELECT DISTINCT ?holder ?desire ?shape WHERE {
  GRAPH ?g { ?holder orexis:holds ?desire . ?desire a orexis:Desire .
             OPTIONAL { ?desire orexis:metWhen ?shape } }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:DesireGraph .
               OPTIONAL { ?g dcterms:temporal ?period .
                          OPTIONAL { ?period orexis:start ?start } OPTIONAL { ?period orexis:end ?end } }
               FILTER(!BOUND(?start) || $now >= ?start) FILTER(!BOUND(?end) || $now < ?end) } }
ORDER BY ?holder ?desire"""

#  ONE desire, its holder and its met-test — for a reader asking about one.
#  WHEN THE HOLDER FORESEES: the start of every prediction of theirs, whatever its window —
#  the future states a desire is judged at, given to this and never computed here (#643).
#  EVERY INSTANT THIS AGENT CAN SEE AHEAD TO, and the kind of graph is not the question.
#  A graph whose period STARTS in the future is a graph about the future: that is what a period
#  says, and a class saying it again is the same fact written twice. It asked for
#  `orexis:PredictionGraph` and so saw only what sensing's drifts wrote — the market had to
#  type its debt-lapse graph as a prediction to be looked at, which it is not; it is a graph
#  holding from a deadline. A round that opens later and a claim whose window starts later are
#  now instants too, and nobody has to remember a class to be foreseen.
#
#  PAST THE PRESENT, which the kind used to imply loosely and a period says exactly: a graph
#  whose start has been reached is holding NOW, and the present is read by the present's own
#  pass, not as a foreseen instant.
_STARTS_Q = """
SELECT DISTINCT ?start WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g dcterms:temporal/orexis:start ?start . FILTER(?start > $now)
               OPTIONAL { ?g orexis:beliefsOf ?owner } FILTER(!BOUND(?owner) || ?owner = $holder) } }
ORDER BY ?start"""

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


def desires_in(store: ox.Store, now: datetime) -> list[tuple[str, str, str | None]]:
    """Every desire the store holds at `now`, as `(holder, desire, met-test or None)`. One
    agent, one volume, so the holder is the agent; a store holding several agents' desires
    answers for each."""
    return [(r["holder"].value, r["desire"].value,
             r["shape"].value if r["shape"] is not None else None)
            for r in store.query(bind(_DESIRES_Q, now=instant(now)), prefixes=NAMESPACES)]


def read_now(store: ox.Store, shapes: rdflib.Graph, holder: str, desire: str,
             shape: str | None, now: datetime) -> list[Witness] | None:
    """What this desire's met-test reads at the PRESENT: its witnesses, empty where it is met,
    None where there is no compilable met-test to ask."""
    select = compiled(shapes, shape, desire)
    if select is None:
        return None
    return _witnesses_at(store, select, holder, now, now)


def read_ahead(store: ox.Store, shapes: rdflib.Graph, holder: str, desire: str,
               shape: str | None, now: datetime) -> list[Witness]:
    """Every (instance, constraint) this desire's met-test reads unmet at a FORESEEN instant,
    each at the EARLIEST instant it does — the instants being every prediction's start, where
    the dataset holds the prediction beside the present (#643).

    A CROSSING is the earliest of these: the instant the world a desire is about is judged to
    leave what the desire wants. The present is excluded — a desire unmet now is pursued as
    itself, and a crossing is a thing in the future.
    """
    select = compiled(shapes, shape, desire)
    if select is None:
        return []
    seen: dict[tuple[str, str], Witness] = {}
    for at in _starts(store, holder, now):
        for w in _witnesses_at(store, select, holder, at, now) or []:
            seen.setdefault((w.instance, w.constraint), w)
    return sorted(seen.values(), key=lambda w: (w.at, w.instance, w.constraint))


def shapes_in(store: ox.Store) -> rdflib.Graph:
    """Every graph of desires and of wants, parsed once — where a desire's shape lives with its
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


def compiled(shapes: rdflib.Graph, shape: str | None, of: str) -> str | None:
    """`shape` compiled to the select whose rows are its VIOLATIONS — `?this`, which
    constraint, `?_about` and `?_side` where the constraint's block says them — or None, with
    a word in the log, where there is no shape or the compiler refuses it.

    THE REPORT AND NOT THE FOCUS NODES (one-function-mints-every-want): a desire universal over
    several properties fails per property, and the rows are what say which. The planner
    compiles the same shape the same way for the law it holds candidates to."""
    from orexis_agent_execution.violation import Unsupported, report_select

    if shape is None:
        return None
    try:
        return report_select(shapes.cbd(rdflib.URIRef(shape)), rdflib.URIRef(shape))
    except Unsupported as exc:
        log.warning("%s: its met-test cannot be compiled, so it is not judged: %s",
                    of.rsplit("#", 1)[-1], exc)
        return None


def _starts(store: ox.Store, holder: str, now: datetime) -> list[datetime]:
    """Every instant ahead of `now` at which some graph this holder can read begins to hold —
    what foresight judges at, in order."""
    return [datetime.fromisoformat(row["start"].value)
            for row in store.query(bind(_STARTS_Q, holder=holder, now=instant(now)),
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


