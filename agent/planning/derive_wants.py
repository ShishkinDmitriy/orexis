"""`derive_wants`: every desire judged, and a want minted for every cluster of what its
met-test reads unmet (judge-desires-then-derive-wants). ONE FUNCTION and one contract — after
the call the store holds every want its desires imply, and NOTHING STANDS BETWEEN A DESIRE AND
A WANT.

A stored judgment stood between the two once — what a met-test read, per desire per instant,
written to a working graph and read back by the minting and by whoever wanted a crossing. It is
gone, and everything it carried a want carries: which instance is in trouble, what the trouble
is about and the instant it must hold at. What a
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
import re
from datetime import datetime

import pyoxigraph as ox
import rdflib

from agent.ontology import OREXIS, RECORD
from agent.store import NAMESPACES, Memo, Raw, bind, graphs_of, rdflib_view, remember, rows

from .ontology import DESIRE, PLANNING, SHAPES, WANT
from .withdraw import FORGET_ONE_U
from .couplings import couplings
from .find_scopes import find_scopes

RECOGNIZED = PLANNING + "Recognized"

log = logging.getLogger("derive_wants")

MET_WHEN = PLANNING + "metWhen"
#  THE MET-TEST'S NEGATIVE TWIN: the avoided state, one select, unmet where it yields a row. A
#  desire carries one of the two, and the want minted under it carries the same one, narrowed
#  (#892); `weigh` judges either and the witnesses read the same, so nothing below this line
#  but `_mint` and `_targets_one_node` knows which a desire spoke.
UNMET_WHEN = PLANNING + "unmetWhen"
#  THE TWO OF A DESIRE'S OWN WORDS THIS FILE SORTS BY. They were matched as string SUFFIXES —
#  `p.endswith("#about")` at three sites — which is safe only because `_SAID_Q` four hundred
#  lines away filters to five named predicates, so nothing else can end in those letters. That
#  coupling was invisible at every site, and a sixth predicate whose local name ended in
#  `about` or `label` would have been read as one of these, silently.
ABOUT = PLANNING + "about"
ESTIMATES = PLANNING + "estimates"
KEYED_BY = PLANNING + "keyedBy"
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"

#  WHAT A DESIRE SAYS, from the graphs of desires and wants asked by class: what it is about,
#  what it points at, its label and its met-test. The OBJECT'S TYPE matters — a blank node
#  cannot be pointed at from another graph — so the caller reads the engine's own terms.
_SAID_Q = """
SELECT ?p ?o WHERE {
  GRAPH ?g { $desire ?p ?o
    FILTER(?p IN (planning:metWhen, planning:unmetWhen, planning:estimates, planning:about, rdfs:label)) }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a ?kind .
               VALUES ?kind { planning:DesireGraph planning:WantGraph } } }"""

#  WHAT THIS DERIVATION HAS MINTED UNDER ONE DESIRE, ACROSS ALL TIME and not at an instant.
#  A want's period is the stretch its TROUBLE occupies, so a want foreseen from three is not
#  handed to a reader standing at two — which is right for a reader asking what is wanted NOW,
#  and wrong for this, whose question is whether it has already minted this. Asked at an
#  instant it would _mint a second copy of every foreseen want on every pass until the trouble
#  arrived. Existence is not an instant question.
_STANDING_Q = """
SELECT ?w WHERE {
  GRAPH ?g { ?w a planning:Want ; prov:wasDerivedFrom $desire }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }
ORDER BY ?w"""


def derive_wants(store: ox.Store, now: datetime) -> set[str]:
    """Mint a want under every desire for every cluster of what its met-test reads unmet, and
    answer with EVERY want those desires imply — the ones minted here and the ones already
    standing under the same name.

    IT READS THE WEIGHINGS THE PLANNER WROTE. A desire is judged where the search judges a
    want, by `weigh`, which the Planner calls for every desire in every ground before this —
    an act calls no other act — writing the met-test's report in each ground as a weighing
    with its violation rows: the instances in trouble, which constraint and what it is
    about. Read across the grounds in order, a violation has a stretch: the
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
    grounds = rows(store, _GROUNDS_Q, ())
    if not grounds:
        raise RuntimeError("the store holds no ground — lay_ground has not run")
    #  WHAT THE HOLDER'S CONSTRAINTS CAN MAKE COLLIDE, read once per holder over the reach from
    #  the present ground, the first laid (`couplings`): the instances a constraint couples are
    #  one cluster below, whatever desire they fall under. A holder with no constraint pays one
    #  query and couples nothing (one-mind-couples-the-wants-a-constraint-can-make-collide).
    present = grounds[0]["g"]
    coupled: dict = {}
    wanted: set[str] = set()
    for holder, desire in _desires_in(store):
        found = _troubles(store, desire, scopes, holder)
        if found is None:
            #  NOT JUDGED IS NOT MET. A desire whose met-test could not be run says nothing
            #  about its wants — so what stands under it is what it implies, and a dropper
            #  handed this answer cannot read silence as "no longer wanted" and take a want
            #  on a bad shape.
            wanted |= _standing_under(store, desire, now)
            continue
        if holder not in coupled:
            coupled[holder] = couplings(store, holder, present, now, memo=memo)
        _derive_under(store, shapes, scopes, holder, desire, found, now, coupled[holder])
        wanted |= _named(shapes, scopes, desire, _said(store, desire), found, coupled[holder],
                         _standing_under(store, desire, now))
    return wanted


def _standing_under(store: ox.Store, desire: str, now: datetime) -> set[str]:
    """Every want this derivation has minted under `desire`, whatever stretch it is over."""
    return {r["w"] for r in rows(store, _STANDING_Q, (), desire=desire)}


def _derive_under(store: ox.Store, shapes: rdflib.Graph, scopes: dict | None, holder: str,
                  desire: str, found: list[dict], now: datetime, coupled=None) -> list[str]:
    """The wants one desire's witnesses imply, minted where none stands. `found` is what its
    met-test read over time: one witness per way of failing, each carrying the boundary it
    first reads unmet at and the one it lifts at; `coupled` what the holder's constraints can
    make collide, which joins two instances into one want."""
    #  ONE WANT PER SCOPE OF WHAT IS IN TROUBLE, and per INSTANCE — UNLESS A CONSTRAINT COUPLES
    #  TWO: the results clustered by which of them some action can move together, and a want
    #  minted per cluster about exactly those, holding at the earliest instant among them. Every
    #  shipped world is one scope, so two properties of one bed are one want; two debts are two
    #  instances and two wants; two parcels whose vans can meet are one want about both, searched
    #  as one. A cluster that already has its want — `about` for `about` — is left standing.
    #
    #  UNLESS WHAT WAS FORESEEN HAS ARRIVED. A want minted at a foreseen instant says "hold
    #  at T", and a plan for it is placed to land at T (#619). A cluster unmet NOW whose want
    #  still says T — the holder asked before the claim lapsed, the pot crossed before the
    #  drift said it would — is re-minted with no instant, under the same name, so the
    #  kept cone and a standing intention meet the want they kept and a plan is found
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
    clusters = _clusters(scopes, found, coupled) or ([[]] if found else [])
    minted = []
    for cluster in clusters:
        about = tuple(sorted({w["about"] for w in cluster if w["about"]}))
        instances = tuple(sorted({w["instance"] for w in cluster}))
        instance = instances[0] if len(instances) == 1 else None
        keys = _keys_of(cluster)
        child = _name_of(shapes, desire, said, about, instance, keys)
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
        #  AND SO IS A WANT ALREADY ABOUT EVERY INSTANCE OF IT. A want a constraint coupled is
        #  about two parcels; once the plan has delivered one, the cluster still in trouble is
        #  the other parcel alone, under a name of its own — and minted, it was a second want
        #  about an instance the coupled want still pursues, and a second plan drove the same
        #  van down the same cells (measured on the dispatcher the day the courier's drives took
        #  time to land, #901). The coupled want is one-shot and carries where it has got to; the
        #  cluster is its, and it is kept under the name it has.
        covering = _covering(shapes, standing, instances, about)
        if covering is not None:
            log.debug("%s is still pursued by %s, which is about every instance of it",
                      child.rsplit("#", 1)[-1], covering.rsplit("#", 1)[-1])
            continue
        child = _mint(store, shapes, holder, desire, now, at, until, said,
                     about=about, instances=instances, keys=keys)
        if child is not None:
            minted.append(child)
    return minted


def _keys_of(cluster: list[dict]) -> tuple[str, ...]:
    """The key terms that PLACED the cluster's witnesses in their scope — the bed whose reading
    is in trouble, where what the witness is about, the soil's property, is two pumps' and
    placed it nowhere — sorted; nothing where what the witnesses are about placed them."""
    return tuple(sorted({k for w in cluster for k in w.get("placed", ())}))


def _named(shapes: rdflib.Graph, scopes: dict | None, desire: str, said,
           found: list[dict], coupled=None, standing: set[str] = frozenset()) -> set[str]:
    """The names the clusters of `found` come to — what minting would call them, or the want
    among `standing` that is already about every instance of a cluster, as `_derive_under` reads it.

    One namer for both halves: `_derive_under` mints under these names and `_withdraw_under`
    keeps what is under them, so the two can never disagree about which want a cluster is.
    """
    out = set()
    for cluster in _clusters(scopes, found, coupled):
        about = tuple(sorted({w["about"] for w in cluster if w["about"]}))
        instances = tuple(sorted({w["instance"] for w in cluster}))
        name = _name_of(shapes, desire, said, about, instances[0] if len(instances) == 1 else None, _keys_of(cluster))
        out.add(name if name in standing else (_covering(shapes, standing, instances, about) or name))
    return out


def _covering(shapes: rdflib.Graph, standing: set[str], instances: tuple, about: tuple) -> str | None:
    """The want among `standing` whose met-test targets every instance of a cluster that is about
    those instances themselves — one a constraint coupled about these and more, still pursuing
    them — or None. Read off the `sh:targetNode`s of the shape or the avoided state the want
    carries, which is where `_narrowed` wrote what a want is about. A cluster about a PROPERTY
    of an instance is never covered this way: a tank's level want targets the tank, and the
    tank's temperature out beside it is a second want, as `a_second_cluster_beside_a_standing_want`
    has always said; and a cluster about no instance is nobody's but its own."""
    from rdflib import URIRef
    from rdflib.namespace import SH

    if not instances or not set(about) <= set(instances):
        return None
    wanted = set(instances)
    for want in sorted(standing):
        for polarity in (MET_WHEN, UNMET_WHEN):
            shape = shapes.value(URIRef(want), URIRef(polarity))
            if shape is not None and wanted <= {str(t) for t in shapes.objects(shape, SH.targetNode)}:
                return want
    return None


def _clusters(scopes: dict | None, witnesses: list, coupled=None) -> list[list]:
    """The witnesses grouped by SCOPE — which of them some action can move together — so a
    want is minted per group. Two in one scope are one want and one cone; two in different
    scopes are two, planned apart and concatenated, which is the mechanism `scope.md` says the
    concept exists for. A witness naming no property, or one no scope holds, joins every group
    it could belong to, which with one scope is the one group.

    AND BY WHAT A CONSTRAINT CAN MAKE COLLIDE. Two instances of one scope in trouble over one
    stretch are two groups — two parcels, two wants, two searches that cannot see each other's
    plan — unless `coupled` says a constraint the holder holds can join them: then they are ONE
    group, one want about both and one search, which finds the plan optimal for both by
    construction and in which the constraint makes the colliding world impossible. The two-vans
    constraint joins two parcels whose vans can meet on a cell and leaves two on disjoint grids
    apart (`couplings`, one-mind-couples-the-wants-a-constraint-can-make-collide). A desire
    couples nothing: what it reads unmet is minted here, never held against a plan.

    THE SCOPES ARE READ, NEVER COMPUTED: `scope_actions` wrote them (scope-actions), read
    once per call and handed in, and a store holding no scope graph is refused rather than
    clustered as one scope — the
    loud direction, since one want about everything is what a missing partition would have
    quietly minted.

    A WITNESS IS PLACED BY WHAT IT IS ABOUT, AND THEN BY ITS KEY. What it is about is a
    property term, and where that is one scope's — the soil's, with one pump — the witness is
    that scope's and its key says nothing more. Where the property is two scopes' — the soil's,
    with a pump on each bed — the witness is placed where the property's scopes and its key's
    MEET: the reading in trouble names the bed, which is the pump's scope's and the heater's,
    and the two together are the one pump's. Two beds' witnesses are then two groups and two
    wants, each searched where its pump is, and the key that placed each is remembered on the
    witness (`placed`) for the want's name and its `planning:keyedBy`. A witness the meet
    places in no one scope is loose, as a witness naming no property always was.

    Measured on every shipped world before #593: one scope, so one group. The greenhouse is
    two by key, and two beds each with a pump are two more."""
    if not witnesses:
        return []
    if scopes is None:
        raise RuntimeError("the store holds no scope graph — scope_actions has not run")
    groups: dict = {}
    loose = []
    for w in witnesses:
        about = [w["about"]] if w["about"] else []
        placed = scopes.meet(about)
        w["placed"] = ()
        if len(placed) != 1 and w.get("key"):
            narrowed = scopes.meet([*about, *w["key"]])
            if len(narrowed) == 1:
                placed, w["placed"] = narrowed, w["key"]
        scope = next(iter(placed)) if len(placed) == 1 else None
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
    if coupled is not None and len(groups) > 1:
        groups = _coupled(groups, coupled)
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


def _coupled(groups: dict, coupled) -> dict:
    """The groups with those a constraint couples merged: two groups of one scope over one
    stretch whose instances `coupled.joins` are one, under the first's key, and transitively —
    three vans that can each meet the next are one search. A group keyed by another scope or
    another stretch is never joined: a constraint reaches across neither, since a want is one
    period and a scope's actions write nothing another scope's constraint reads."""
    keys = sorted(groups, key=lambda k: tuple(str(x) for x in k))
    parent = {k: k for k in keys}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if (a[0], a[2], a[3]) == (b[0], b[2], b[3]) and coupled.joins(a[1], b[1]):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra
    merged: dict = {}
    for k in keys:
        merged.setdefault(find(k), []).extend(groups[k])
    return merged


def _said(store: ox.Store, desire: str) -> list[tuple[str, object]]:
    """What the desire says, as `(predicate, the engine's own term)` — the TYPE is load-bearing,
    since a blank node has no name another graph could point at."""
    solutions = store.query(bind(_SAID_Q, desire=desire), prefixes=NAMESPACES)
    return sorted(((str(s["p"].value), s["o"]) for s in solutions), key=lambda pair: (pair[0], str(pair[1])))


def _tail(iri: str) -> str:
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _name_of(shapes: rdflib.Graph, desire: str, said, about: tuple, instance: str | None,
             keys: tuple = ()) -> str:
    """The name of the want minted under `desire` for one cluster of its witnesses: the desire's,
    suffixed, so a second episode of the same cluster pursues the same node and everything
    keyed by it — the planner's kept cone, the executor's intentions — finds what it kept.

    NAMED FOR WHAT IT IS ABOUT where that is NARROWER than the desire, so two wants under one
    desire — soil now, air later — are two nodes; and for the desire alone where it is not,
    which is every want there was before this: a desire about one property mints
    `<desire>.pursued` exactly as it always did. AND FOR THE INSTANCE where the desire ranges
    over several — its shape targets a class, or whatever bears a property, rather than one
    node — since two tanks low about their level are two clusters, two plans, and would be one
    name otherwise (found by the derivation's own table, `tests/derive_wants/`); a desire whose shape names
    its one node (`sh:targetNode`, sensing's and the greenhouse's) keeps its names, and an
    instance the want is already about (a debt, `planning:about sh:this`) is not said twice.
    AND FOR THE KEY THAT PLACED IT where the cluster was placed by one: two beds each with a
    pump under a desire targeting the grower are two clusters about the one property, and
    `.pursued.SoilMoisture` twice would be one node and one plan for two pumps.
    """
    #  NARROWER THAN THE DESIRE, or the desire's own name. A want carries what it is about in
    #  its NAME only where the cluster covers less than the desire does: a desire about one
    #  property mints `<desire>.pursued` exactly as it always did, and one about soil and air
    #  broken on soil alone mints a second node. Inlined because this is the one place that
    #  asks it — it was a helper while `_mint` also needed the desire's own abouts, to default a
    #  want's stored ones, and a want states none now.
    declared = {str(o.value) for p, o in said if p == ABOUT}
    tails = [_tail(a) for a in about] if about and set(about) != declared else []
    tails = [_tail(k) for k in keys] + tails
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
               for p, o in said if p in (MET_WHEN, UNMET_WHEN))


# --- what a want IS on disk, and how one goes -------------------------------------------
#
#  THE DERIVATION OWNS ITS OWN WRITES. These were module functions in `wants.py` beside the
#  collection, so the one function that mints wants had to reach into a repository to put one
#  down. A want's graph, what the catalogue says of it and the period it holds during are
#  decided where the want is decided; `wants.py` reads them back and names none of it.





def _graph_of(agent_id: str, at: datetime, until: datetime | None) -> str:
    """The graph the wants in trouble over ONE STRETCH live in, named for that stretch.

    A WANT'S TEMPORAL EXTENT IS ITS GRAPH'S PERIOD, and it is said once. A want used to carry
    `planning:holdsAt` — the instant it must hold at — beside a graph whose period ran from when
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
           points: tuple = (), shape: tuple = ()) -> None:
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

    AND NO `planning:about`. A want used to state the one domain property it was in trouble
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
    #  to state. A want used to carry `planning:holdsAt` beside it — the instant it must hold at
    #  — which the period now says, and said it only for foreseen wants, so a want in trouble
    #  now recorded neither instant.
    found_at = f' ; prov:generatedAtTime "{now.isoformat()}"^^xsd:dateTime'
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
  <{holder}> planning:holds <{uri}> .
  <{uri}> a planning:Want{found_at} ;
      planning:state <{RECOGNIZED}> ;
      prov:wasDerivedFrom <{desire}> ;
      rdfs:label {json.dumps(label)} .
  {said_points}
  {shape_lines} }}
  GRAPH ?cat {{ <{graph}> a planning:WantGraph ; orexis:arrivedBy orexis:Derived ;
      orexis:beliefsOf <{holder}> . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> dcterms:temporal
      [ a dcterms:PeriodOfTime{period} ] . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }}
         FILTER NOT EXISTS {{ GRAPH ?cat {{ <{graph}> dcterms:temporal ?held }} }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ planning:WantGraph rdfs:subClassOf ?kind }} }}""",
                 prefixes=NAMESPACES)


def _mint(store: ox.Store, shapes: rdflib.Graph, holder: str, desire: str, now: datetime,
         at: datetime, until: datetime | None = None, said=None,
         about: tuple = (), instances: tuple = (), keys: tuple = ()) -> str | None:
    """Derive the want pursued under `desire` and write it to the pursued graph, named by
    `_name_of`. None, and the desire stays the goal, where the desire states its met-test inline:
    a blank node has no name another graph could point at, and copying it would make a second
    owner of the claim. `instances` are the cluster's — one, where the want is about one; two
    where a constraint coupled them, and then the want is about both."""
    said = _said(store, desire) if said is None else said
    instance = instances[0] if len(instances) == 1 else None
    #  `about` NAMES AND DOES NOT NARROW. What a cluster is about distinguishes two wants
    #  under one desire — soil now, air later, two nodes — and that is an IDENTITY. It is not
    #  written onto the want, because a stated property is the planning problem answered in
    #  advance (see `_write`).
    #
    #  THE KEY NAMES AND IS WRITTEN, `planning:keyedBy` — the one row a want states beside its
    #  met-test. It is not a property and answers nothing about what may repair the want; it is
    #  the witness's own coordinate, the bed whose reading was in trouble, which the shape cannot
    #  carry: the desire targets the grower and reaches the readings by a path, and the other
    #  bed's come down the same path. The instance goes into the shape as its target
    #  (`_narrowed`), and the key would go there too if a shape could say it — rewriting the
    #  constraint to name the bed was refused, since where the restriction belongs differs by
    #  constraint and a derivation that writes a constraint of its own owns a grammar
    #  (a-scope-is-a-predicate-on-a-key). The Planner reads it to place the want
    #  where its scope's imaginarium is.
    child = _name_of(shapes, desire, said, about, instance, keys)
    points = [(KEYED_BY, k) for k in keys]
    met_test = estimate = None
    for p, o in said:
        if isinstance(o, ox.BlankNode):
            log.warning("%s states its %s inline; it is pursued itself", desire.rsplit("#", 1)[-1],
                        p.rsplit("#", 1)[-1])
            return None
        #  WHAT IT IS ABOUT is the witnesses' where the shape named them per block, and the
        #  desire's whole where it did not; the avoided state is pointed at as ever, and the
        #  met-test and the estimate are carried, instantiated, below. The label is read here
        #  too and is not a point: a want's is made from it.
        if p in (ABOUT, RDFS_LABEL):
            continue
        if p in (MET_WHEN, UNMET_WHEN):
            met_test = (p, str(o.value))
            continue
        if p == ESTIMATES:
            estimate = str(o.value)
            continue
        points.append((p, str(o.value)))
    #  THE MET-TEST IS THE DESIRE'S INSTANTIATED AT THE WITNESS: carved from where the desire's
    #  shape lives and _narrowed to this cluster — the instance as its target, the blocks about
    #  what the want is about — and written into the want's own graph under its own name, so
    #  the want is judged on its instance and a plan for one tank is not refused for another's.
    #  UNDER THE DESIRE'S OWN POLARITY: a shape it is met when stays a shape, `.met`; an avoided
    #  state it is unmet when stays a select, `.avoided`, its one `sh:select` carried whole and
    #  each instance written as `sh:targetNode` beside it, which the compiler reads as it reads a
    #  shape's (#892). The names are for eyes; a reader asks the want which it carries.
    shape_lines: tuple = ()
    if met_test is not None:
        polarity, shape = met_test
        own = child + (".met" if polarity == MET_WHEN else ".avoided")
        shape_lines = _narrowed(shapes, shape, own, instances, about)
        points.append((polarity, own))
    #  AND SO IS THE ESTIMATE, where it speaks of the instance: the desire's select with `$this`
    #  bound to the one instance this want is about, written beside the met-test under the
    #  want's own name (`_instantiated`). The desire's select sums over every instance, which
    #  is right for the desire and overstated the want's — a want per parcel read the other
    #  parcel's drives in its `planning:remaining` and forked the other van (#893). A select
    #  that names no `$this` points at the desire's as ever, and so does a want a constraint
    #  coupled about several instances: its estimate is the desire's sum over them, which is the
    #  joint plan's cost and the A* key the coupled search wants — and the whole sum, so where a
    #  third instance is astray and coupled to neither it is counted too, a seam
    #  (knowledge/domain/planning/constraint.md).
    if estimate is not None:
        own = child + ".estimate"
        lines = _instantiated(shapes, estimate, own, instance)
        shape_lines += lines
        points.append((ESTIMATES, own if lines else estimate))

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
           points=tuple(points), shape=shape_lines)
    log.info("%s reads unmet: pursuing %s", desire.rsplit("#", 1)[-1], child.rsplit("#", 1)[-1])
    return child


def _local(holder: str) -> str:
    """The holder's local name — what a graph this derivation writes is called, for eyes."""
    return holder.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _narrowed(shapes: rdflib.Graph, shape: str, own: str, instances: tuple, abouts: tuple) -> tuple[str, ...]:
    """The desire's met-test as THIS want's: the same shape under the want's own name, its
    targets the instances the want is about — one `sh:targetNode` each, where the cluster had
    any — and only the property blocks and `sh:sparql` constraints about what the want is about —
    the universal instantiated at its witnesses (a-desire-is-universal-and-a-want-is-existential).
    A block or constraint saying nothing about what it is about is kept, as is one about
    `sh:this`, which is each instance. The triples, as N-Triples lines the write puts into the
    want's graph.

    Carved from the graphs of desires and wants, asked by classification, where a desire's shape
    lives; a shape that names its one node (`sh:targetNode`) narrows to the same node, so
    sensing's wants and the greenhouse's keep their target and lose only the blocks they are
    not about. A want a constraint coupled about two parcels targets the two and not the class,
    so a third parcel astray is not this want's to judge; a cluster with no instance — the
    fallback, one want about everything the desire is about — keeps the desire's targets.
    """
    from rdflib import Graph, URIRef
    from rdflib.namespace import SH


    about_p = URIRef(PLANNING + "about")
    targets = {SH.targetNode, SH.targetClass, SH.targetSubjectsOf, SH.targetObjectsOf, SH.target}
    #  From the graphs that hold desires and wants, crossed ONCE for the pass and handed in:
    #  this runs per want minted, and fetching it here crossed every one of them per want.
    cbd = shapes.cbd(URIRef(shape))
    keep = {URIRef(a) for a in abouts}
    out, dropped = Graph(), Graph()
    for p, o in cbd.predicate_objects(URIRef(shape)):
        if p in targets and instances:
            continue
        if p in (SH.property, SH.sparql):
            about = cbd.value(o, about_p)
            if about == SH.this:
                #  ABOUT THE INSTANCES THEMSELVES: kept where the want is about any of them, or
                #  about no instance at all, and dropped only where the cluster is about something
                #  else — the block's parcel, under a cluster about the moisture.
                if instances and keep and not keep & {URIRef(i) for i in instances}:
                    dropped += cbd.cbd(o)
                    continue
                about = None
            if keep and about is not None and about not in keep:
                dropped += cbd.cbd(o)
                continue
        out.add((URIRef(own), p, o))
    for instance in instances:
        out.add((URIRef(own), SH.targetNode, URIRef(instance)))
    for s, p, o in cbd:
        if s != URIRef(shape) and (s, p, o) not in dropped:
            out.add((s, p, o))
    return tuple(line for line in out.serialize(format="nt").splitlines() if line.strip())


def _instantiated(shapes: rdflib.Graph, node: str, own: str, instance: str | None) -> tuple[str, ...]:
    """The desire's estimate as THIS want's: the node its `planning:estimates` points at, under
    the want's own name, its `sh:select` with `$this` bound to the one instance the want is
    about — the universal's measure instantiated at its witness, as `_narrowed` instantiates
    the shape. Nothing, where the want is about no one instance or the select never speaks of
    `$this`: the desire's select is then the want's, and the want points at it as before.

    `$this` is SHACL's word for the instance and `store.bind`'s one token that may go unbound —
    unbound it parses as a variable, so a select written to stand it in subject position and
    bind it onto the variable it groups by runs over every instance for a desire and over one
    for a want, the one text both ways (`domains/courier/shapes.ttl`). The triples, as
    N-Triples lines the write puts into the want's graph.
    """
    from rdflib import Graph, Literal, URIRef
    from rdflib.namespace import SH

    text = shapes.value(URIRef(node), SH.select)
    if instance is None or text is None or not _speaks_of_this(str(text)):
        return ()
    out = Graph()
    for p, o in shapes.predicate_objects(URIRef(node)):
        if p == SH.select:
            o = Literal(bind(str(o), this=ox.NamedNode(instance)))
        out.add((URIRef(own), p, o))
    return tuple(line for line in out.serialize(format="nt").splitlines() if line.strip())


def _speaks_of_this(text: str) -> bool:
    """Does a select carry the `$this` token — whole-token, as the binder matches it?"""
    return re.search(r"\$this\b", text) is not None

# --- WHAT THE WEIGHINGS SAY --------------------------------------------------------------
#
#  EVERY DESIRE THE STORE HOLDS and who holds it, from the graphs of desires — a desire, its
#  holder and its met-test are written together, so the pattern matches within one graph. NO
#  PERIOD, AND NO FILTER FOR ONE: a desire is authored once into a graph with no period,
#  which holds at every instant as the T-Box does.
_DESIRES_Q = """
SELECT DISTINCT ?holder ?desire WHERE {
  GRAPH ?g { ?holder planning:holds ?desire . ?desire a planning:Desire }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:DesireGraph } }
ORDER BY ?holder ?desire"""

#  THE TIMELINE: every ground, earliest first — the present, and what each prediction makes
#  of it. Each is a world a desire is judged in, and their order is what gives a violation
#  its stretch.
_GROUNDS_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start } }
ORDER BY ?start"""

#  WHAT ONE DESIRE'S WEIGHINGS SAY, ground by ground: the verdict, and every violation with
#  its instance, its constraint, what it is about and the value that offended where it is a
#  node — a literal is keyed by nothing, and the ground it was read in, where what the node
#  names is read.
_TROUBLES_Q = """
SELECT ?start ?g ?met ?instance ?constraint ?about ?offending WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?x a planning:Weighing ; planning:for $desire ; planning:weighs ?g .
    ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start .
    OPTIONAL { ?x planning:met ?met }
    OPTIONAL { ?x planning:violation ?v . ?v planning:instance ?instance .
               OPTIONAL { ?v planning:constraint ?constraint }
               OPTIONAL { ?v planning:about ?about }
               OPTIONAL { ?v planning:offending ?offending FILTER(isIRI(?offending)) } } } }
ORDER BY ?start ?instance ?constraint ?offending"""

#  WHAT A NODE NAMES IN A GROUND, as the objects of its own facts — the terms a reading is keyed
#  by, its feature and its property, among the rest. Values, never predicates: a key is values.
_NAMES_Q = """
SELECT DISTINCT ?o WHERE { GRAPH $ground { $node ?p ?o } FILTER(isIRI(?o)) }"""


def _desires_in(store: ox.Store) -> list[tuple[str, str]]:
    """Every desire the store holds, as `(holder, desire)`. One agent, one volume, so the
    holder is the agent; a store holding several agents' desires answers for each."""
    return [(r["holder"], r["desire"]) for r in rows(store, _DESIRES_Q, ())]


def _troubles(store: ox.Store, desire: str, scopes=None, holder: str | None = None) -> list[dict] | None:
    """Every way `desire` is failing, each with the stretch it fails over — or None where any
    ground was not judged, which is not the same as met. `holder` is who holds the desire, read
    off its graph by the caller, and is never part of a key.

    A WAY OF FAILING is one `(instance, constraint, key)` triple, and the grounds it is
    violated in give it an interval: `at`, the start of the earliest ground it reads unmet in;
    `until`, the start of the first later ground it reads met in, or None where nothing the
    agent can see ahead repairs it. The present is the first ground and is not otherwise
    special — "unmet now" is `at == the present`. A way that fails, lifts and fails again is
    one want over the first stretch, and the second is a ground away.

    THE KEY is what the offending value is keyed by, read off the ground it offended in: the
    scope members among what the node names — its feature, the bed — less what the violation
    is about, which is said already, and less a member of every scope, which tells nothing.
    Two beds' readings below under a desire that targets the grower are one `(grower, 0)` and
    two ways of failing, where they were one; a literal offends keyed by nothing, and a desire
    targeting the tank has the tank as its instance already. The key is the NAMED members and
    never the node, so a reading superseded by a prediction of the same bed is the same way of
    failing across the grounds.
    """
    found = rows(store, _TROUBLES_Q, (), desire=desire)
    if not found or any(r.get("met") is None for r in found):
        return None
    seen: dict[tuple, dict] = {}
    lifted: dict[tuple, datetime] = {}
    by_ground: dict[str, list] = {}
    names: dict[tuple, tuple] = {}
    #  A MEMBER OF EVERY SCOPE TELLS NOTHING and is no part of a key — the same word `admit`
    #  lives by: a value no scope holds alone refuses nothing. AND THE HOLDER'S OWN IRI NEVER IS,
    #  directly: the agent id is the one constant of the agent's whole world (the one instance a
    #  process is handed at boot) and cannot tell two of its own troubles apart, where an
    #  observation names it as whose it is and a prediction's copy of it does not, so keyed by it
    #  the present and the foreseen ground were two ways of failing under one name, two want
    #  graphs and two roots, and the plan hung under the foreseen one. It fell out of the key by
    #  the every-scope rule while every shipped world was one scope; the day the allotment's market
    #  texts became readable it was four, the grower a member of two, and the accident showed (#908).
    everywhere = scopes.all() if scopes else frozenset()
    for r in found:
        by_ground.setdefault(r["start"], []).append(r)
    for start, group in sorted(by_ground.items()):
        at = datetime.fromisoformat(start)
        unmet = set()
        for r in group:
            if not r.get("instance"):
                continue
            keyed = ()
            if scopes and r.get("offending"):
                keyed = names.setdefault((r["g"], r["offending"]), tuple(sorted(
                    o for o in {r["offending"], *(n["o"] for n in rows(store, _NAMES_Q, (), ground=r["g"], node=r["offending"]))}
                    if o in scopes and scopes[o] != everywhere and o != r.get("about") and o != holder)))
            key = (r["instance"], r.get("constraint", ""), keyed)
            unmet.add(key)
            seen.setdefault(key, {"instance": r["instance"], "constraint": r.get("constraint", ""),
                                  "about": r.get("about"), "key": keyed, "at": at})
        for key in seen.keys() - unmet:
            lifted.setdefault(key, at)
    return sorted(({**w, "until": lifted.get(k)} for k, w in seen.items()),
                  key=lambda w: (w["at"], w["instance"], w["constraint"], w["key"]))
