"""Laying the ground worlds: what the agent's own knowledge comes to over each period, one
graph per period, in the store a pass stands in.

**A PREDICTION IS AN ACTION NOBODY TAKES.** What it makes true is its graph's own contents —
concrete, because a prediction is a value at an instant — and what it takes away is whatever stood
under the same KEY: every triple of the ground whose subject and predicate some triple of the
prediction has, as PDDL assigns a fluent (#988). A prediction carries no text saying what it
supersedes; its own triples say it, and `orexis:retracts` — a `DELETE … WHERE` naming `GRAPH $state`,
written by the prediction package in this package's form — was retired for the reason #666 gave
the effects: a rule does not say which world it reads. Its period says WHEN it applies rather than a
precondition saying whether it may. So the timeline is laid by exactly the machinery the search walks:
fork the period before, take the keys out of the fork, add what the prediction holds.

**AND SO IS A BELIEF THAT BEGINS LATER** (#987). A forecast is anyone's word about what will hold
later, the predictor's own among them (foresight-is-derived-where-the-model-is-the-agents-and-asked-
for-where-it-is-anothers), and a peer's cell from ten seconds on, a round said to open at one, is a
graph with a period ahead. Where some text of the pass reads what it adds it is a writer of it, as a
prediction is (`_predicted`), so it is cut whole into its changeable part and laid where its period
begins — fork, keys out, forecast in — and in no ground before it: laid into the present with
everything changeable, it stood under the van today. Read beside every world instead, the butt it says
will hold water at half past would stand beside the empty butt the present holds. One nothing reads is
not where the search can be, and lays no ground: a committed step of the agent's own is such a belief,
and laid, every later step of a plan was a boundary. An end lays no ground: a value stands until its
key is assigned.

WHY IT HAD TO BECOME A DIFF. A prediction used to be a STATE — a graph holding the reading it
foretold — and a door handed a reader every graph holding at an instant, so a met-test asked at
a foreseen instant saw the reading AND the prediction of it. A shape holds over EVERY value, so
the stale one still violated: measured, a tank low now and a prediction refilling it read *unmet
from twelve, lifts NEVER*, because the present's 5 outlived the prediction's 20. Nothing was
wrong with the prediction; there was no place in the pass where it REPLACED anything.

**AND WHAT IT BRINGS IS AN ARRIVAL** (#944). The mind reads what the agent holds of a subject — the
bed's soil, dry — and never the reading, so a ground that only swapped the observation would keep the
present's state for ever, and a foreseen crossing would read met. A predicted observation arriving in
a ground triggers the transitions there, as a received one does in the present: belief's machine and
the rules the beliefs hold, reading the arrival with its revisions, the common beliefs and the agent's
own state as the ground before left it, and changing the ground alone. So the hold reaches the
forecast — a bed believed dry and resting at 0.3001 is foreseen dry, as the present holds it — and a
prediction still triggers nothing in the belief base: the runner prepares the target, and here the
target is the ground being laid.

**AND THE PERIODS COLLAPSE.** Each ground is hashed as a possible world is, and where two
neighbouring periods reach the same facts the second is not a period at all: nothing a met-test
can read moved, so nothing it could answer differs there. Measured on three boundaries whose
middle prediction restated the present — three boundaries, two grounds. That is what bounds the
judging: a desire is asked once per DISTINCT ground rather than once per boundary, so a store
thick with predictions that say nothing new costs a pass nothing.

**A PERIOD IS TOLD FROM THE ONE BEFORE IT BY EVERYTHING A GROUND HOLDS, AND ITS ROW'S HASH IS
TAKEN WITHIN WHAT IS READ.** Two questions, and they were one digest until the hash was narrowed.
The hash on a ground's row is what `reroot` finds the present by, so it reads only what some
text reads — a reading's instant, which none does, is not what the present differs by. Whether a
boundary is a period at all is asked of the whole graph, as it always was. Collapsing by what is
read too was built and struck the same day (2026-10-05): once a plan for a foreseen crossing is
adopted the prediction answers it, every ground ahead reads inside again and differs from the
present only by a number, so all of them folded into the present; the want minted for the
crossing was then weighed in the present ground, read met there, and its intention was ended as
reached before the dose was due — #858 again, by another door.

**AND A GROUND IS WHAT THE SEARCH CAN CHANGE, AND NOTHING ELSE** (#953). Before the present is laid,
every graph a search reads beside its worlds is cut in two: what some writer of the scope can write —
an effect of one of the actions handed, a transition, or a prediction, whose retraction takes out of a
ground what stands where it adds — into a `planning:ChangeableGraph` derived from it, and the rest left
where it was (`footprint.changeable`, `_predicted`). The present ground is laid from the
changeable graphs, so a fork copies what a step can change, and a world reads every remainder beside
it; the two are disjoint, so no value an effect replaced stands beside the one that replaced it. The
cut is made here and not where the imaginarium is filled, because a case lays its grounds in its own
store; it is taken back before it is made again, so laying twice cuts once. What defines what the agent
can do — the vocabulary, the actions, the flows, the shapes, the constraints, the derivations — is no
fact a step changes and is never cut.

**WHAT IS BUILT IS CLASSIFIED, NOT RETURNED.** Each ground is a graph with the stretch it holds
over, `planning:GroundGraph`, so a reader asks `graphs_of(store, GROUND_GRAPH, at=T)` and is
handed the one world standing then. A list handed back would be a second place the answer lived
(a-reader-states-the-kinds-it-reads).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime

import pyoxigraph as ox

from agent.belief.transition import run, transitions
from agent.ontology import BELIEF, DERIVED, KNOWN, OREXIS, PREDICTION
from agent.hash_named_graph import digest_of, hash_named_graph
from agent.store import (fork, Raw, add_quads, bind, catalogue_of, classify, clear_graph, revisions_of, forget_graph,
                         graphs_of, instant, quads, rows, update)

from . import footprint
from .ontology import CHANGEABLE_GRAPH, GROUND_GRAPH

_PROV = "http://www.w3.org/ns/prov#"
_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

log = logging.getLogger("lay_ground")


def _foreseen(store: ox.Store, now: datetime) -> list[tuple[datetime, str, bool]]:
    """Every boundary ahead of `now` this store holds — the instant, the graph laid there and whether
    it is a prediction — earliest first: each prediction's start, and the start of every belief whose
    changeable part was cut (`_split`), the part laid being the changeable graph.

    BOTH ARE SAID OF THE GRAPH AND NEITHER INSIDE IT: a prediction's contents are what it ADDS,
    which is what a prediction naturally is — `GRAPH :next_temp { :air :hasTemp 30 }` — and the
    catalogue says what a graph is, whose it is and when it holds. What it supersedes is read off
    what it adds: every triple standing under one of its keys, a key being a subject and a
    predicate, goes when the boundary is laid (`_fork`). Nothing is said about how.

    A BELIEF HOLDING LATER IS LAID THE SAME WAY (#987): a forecast of anyone's — a peer's cell from
    ten seconds on, a round said to open at one — is a graph the present has not reached, cut whole
    into its changeable part where some text of the pass reads what it adds, since it then writes it
    (`_predicted`), and applied where its period begins, superseding by key, as a prediction is. Its
    END is no boundary: a value stands in a ground until something assigns its key, as a
    prediction's last stretch stands past the horizon, and what an ending MEANS stays its owner's
    (#645). One saying nothing the pass reads is cut only where another writer's pattern reaches it,
    and is otherwise read beside every world at the world's own period, as every remainder is.

    NO HOLDER. One agent, one volume (rule 4), so the store IS the scope and a prediction in it
    is this agent's by construction.

    A PREDICTION WHOSE KEYS STAND NOWHERE is legal and means it: a prediction of something the
    world does not yet say at all — a round opening, a claim arriving — adds without superseding.
    """
    said = """
SELECT ?prediction ?at WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?prediction a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?at } }
ORDER BY ?at ?prediction"""
    ahead = [(datetime.fromisoformat(r["at"]), r["prediction"], True) for r in rows(store, said, ())]
    ahead += [(datetime.fromisoformat(r["start"]), r["piece"], False)
              for r in rows(store, _PIECES_AHEAD_Q, (), now=instant(now))]
    return sorted(ahead)


#  THE CHANGEABLE PART OF EVERY BELIEF THAT BEGINS AFTER `$now`, and when: laid where its period begins,
#  and in no ground before it.
_PIECES_AHEAD_Q = """
SELECT ?piece ?start WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?piece a planning:ChangeableGraph ; prov:wasDerivedFrom ?source .
               ?source dcterms:temporal/orexis:start ?start . FILTER(?start > $now) } }
ORDER BY ?start ?piece"""


def lay_ground(store: ox.Store, now: datetime, within: frozenset | None = None,
               landings=(), actions=None) -> list[str]:
    """Build one ground world per period the agent can see, classified with its stretch.

    `within` is what a world of this imaginarium is identified by — the Planner's to say, from
    what its texts read — and the hash on each ground's row is taken within it: a reading's
    instant, which no text reads, is then not a fact the present differs by; and a belief ahead
    saying nothing within it lays no ground (`_predicted`). None hashes whole, and lays every one.
    Which boundary is a period is asked of the whole graph either way.

    `landings` are the instants steps in flight land at — the Planner's to say, off the
    intentions — and each ahead of `now` is a period of its own WHATEVER IT HOLDS: a want a
    reconsideration mints is searched from the ground in which the step in flight has landed, so
    the plan it finds begins after it, and a plan is placed at its root's instant (#905,
    knowledge/domain/execution/commitment.md). What the ground holds is what the agent already
    sees holding then, and the step's own prediction is not applied again: a fictive step wrote
    it into the present when it was taken, and a step a flow reads as a committed step is in the
    predictions already. So it is not collapsed into the ground before it by hash, which is the
    one thing that makes it a boundary rather than a prediction.

    The present is the first, and is the agent's state as it stands — what can change of every
    belief that has begun. Each prediction that applies later, and the changeable part of each
    belief beginning later, is run against the ground standing before it and the diff applied; a
    ground that hashes the same as the one before it is not a period, and is dropped.

    `actions` are the scope's — the Planner's to say — whose effects, with every transition, say what
    is changeable and so what a ground holds; None means every action the store holds.

    Answers with the graphs it made, earliest first. What a READER takes is `world_at`.

    PUBLIC, AND IN PLACE: it lays the grounds into whichever store it is handed. `prepare_ground`
    lays them into the imaginarium it fills; a case that holds the derivation to the store it
    leaves lays them into the case's own store, so every graph the case declared — a ledger
    among them — stays where the derivation reads it.
    """

    _split(store, actions, now, within)
    ahead = _foreseen(store, now)
    here = _present(store, now)
    #  THE TRANSITIONS A PREDICTED OBSERVATION TRIGGERS, and the agent's own state they read and change
    #  as the grounds are laid, from the present's: asked only where something is predicted. A belief
    #  laid ahead triggers none: it triggered them when it arrived, and what they made of it holds over
    #  its period and is laid beside it.
    rules = transitions(store) if any(predicted for _, _, predicted in ahead) else []
    own = _own_state(store) if rules else None
    stated = _whole(store, graphs_of(store, BELIEF, common=True)) if rules else []
    made, marks = [here], _marked(store, here, within)
    opened = [now]
    landing = {at for at in landings if at > now}
    for at, group in _by_instant(ahead, landing):
        if at <= now:
            continue                    # a prediction already reached is the present's, not ahead
        #  EVERYTHING BEGINNING AT ONE INSTANT IS ONE WORLD CHANGE. A boundary is an instant,
        #  not a prediction: two flows that both start at one o'clock describe ONE world, and
        #  forking once per prediction made two grounds with the same name and a period from the
        #  instant to itself — which holds at no instant at all, so a reader standing after it
        #  was handed NO ground and the agent went blind past the boundary. Each retract is
        #  read against the ground standing BEFORE the instant, so they supersede in parallel
        #  rather than one seeing another's work.
        added, predictions = [], [graph for graph, predicted in group if predicted]
        for prediction in predictions:
            for graph in (prediction, *revisions_of(store, prediction)):
                added += list(_triples(store, graph))       # the predicted reading, and what was concluded of it
        for piece in (graph for graph, predicted in group if not predicted):
            added += list(_triples(store, piece))           # what can change of a belief beginning here
        if not added and at not in landing:
            #  A prediction that changes nothing is not a period — an early-out, not a guard:
            #  the hash below reaches the same answer, having laid the graph first.
            continue
        there = _fork(store, here, _name(at), added)
        if rules and predictions:
            _transitioned(store, there, predictions, rules, own, stated)
        mark = _marked(store, there, within)
        if mark == marks and at not in landing:
            #  THE SAME GROUND UNDER ANOTHER NAME. Nothing a met-test can read moved, so this
            #  instant answers what the one before it answered and is not a period of its own.
            forget_graph(store, there)
            continue
        #  THE ONE BEFORE IT ENDS HERE. A ground holds until the next one begins, which is not
        #  known until it does — so each is classified when its successor arrives, and the last
        #  is left open because nothing the agent can see ends it.
        classify(store, here, GROUND_GRAPH, DERIVED, start=opened[-1], end=at)
        made.append(there)
        opened.append(at)
        here, marks = there, mark
    classify(store, here, GROUND_GRAPH, DERIVED, start=opened[-1])
    if own is not None:
        clear_graph(store, own)
    log.debug("%d ground world(s) over %d boundar(ies) ahead", len(made), len(ahead))
    return made


#  THE BELIEFS THE AGENT DERIVED — what the transitions wrote of each arrival of testimony, the subject
#  beliefs among them — as against those it received, which are testimony: no revision, which goes with
#  its source, and nothing everyone reads; as `trigger` reads the agent's own state.
_DERIVED_Q = """
SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                               ?g a orexis:BeliefGraph ; orexis:arrivedBy orexis:Derived .
                               FILTER NOT EXISTS { ?g a belief:RevisionGraph }
                               ?g orexis:ownedBy ?owner . } } ORDER BY ?g"""

#  WHERE THE AGENT'S OWN STATE IS KEPT WHILE THE GROUNDS ARE LAID: a working graph, not a belief,
#  handed by name to the transitions and taken away when the last ground is laid. Its name is for eyes.
_OWN = "http://example.org/orexis/graph/ground/own-state"


def _own_state(store: ox.Store) -> str:
    """The agent's own state as the present ground holds it — every belief the agent derived that is
    no revision and nothing everyone reads, copied into a working graph of its own — and the working graph's name.

    APART FROM THE GROUND because a ground is one graph and holds testimony beside the state: the
    observations the present holds and the predicted ones each boundary brings. A transition is handed
    the arrival and no other testimony, so that its WHERE says what it is about (#947); read over the
    whole ground, climate's soil transition would judge every soil observation the ground holds, not
    only the one arriving. So the state is kept here, beside the grounds, as the transitions change it
    ground by ground — the state before a boundary being what the ground before it was left holding."""
    clear_graph(store, _OWN)
    for g in _whole(store, [r["g"] for r in rows(store, _DERIVED_Q, ())]):
        update(store, f"INSERT {{ GRAPH <{_OWN}> {{ ?s ?p ?o }} }} WHERE {{ GRAPH <{g}> {{ ?s ?p ?o }} }}")
    return _OWN


def _transitioned(store: ox.Store, ground: str, arrivals: list[str], rules, own: str, stated: list[str]) -> None:
    """Every transition each of `arrivals` triggers, applied in `ground` as it is laid (#944).

    A PREDICTED OBSERVATION IS AN ARRIVAL THERE, as a received one is in the present: each triggers
    every transition once, in the order the predictions came, rule by rule through belief's machine,
    reading itself with its revisions, the common beliefs and the agent's own state as the ground before
    left it — and nothing else — so a bed believed dry and resting at 0.3001 is foreseen dry, held by the
    margin as the present holds it. Each rule is the engine's own update, run twice over the same reads:
    `WITH` the ground, which no rule reads, and then `WITH` the working state, so what it deletes is
    taken out of both and what it inserts put into both, and the next rule reads the state this one
    left (#953). The runner prepares the target, as every runner does: here it is the ground being
    laid, and the present is never written to. No budget is spent: a ground holds what its predictions
    make of it, whole, or it is no ground."""
    for arrival in arrivals:
        reads = [arrival, *revisions_of(store, arrival), *stated, own]
        for rule in (rule for order in rules for rule in order):
            run(store, [rule], ground, reads)
            run(store, [rule], own, reads)


def _present(store: ox.Store, now: datetime) -> str:
    """The agent's state as it stands, as a ground of its own.

    COPIED RATHER THAN USED IN PLACE. The state graph is what the agent BELIEVES; a ground is
    what a pass stands on, and a pass must be able to fork one without the belief base moving.
    """
    name = _name(now)
    _relaid(store, name)
    #  WHAT THE SEARCH CAN CHANGE OF WHAT THE AGENT HOLDS: every changeable graph `split` cut — the
    #  subject beliefs the transitions derived, which the met-tests and the effects speak, a van's
    #  cell, a venue's being open — so a fork writes what a step changes and copies nothing else, and
    #  every remainder is read beside it (#953). NO READING: what a sensor said is a percept, of no
    #  kind cut here, and crosses into no ground (#944); what the ground holds of it is the subject belief.
    #  AND NOTHING THAT BEGINS LATER (#987): a belief holding from an instant ahead is laid where it begins,
    #  and the present held it as if it held now — a peer's cell from ten seconds on stood under the van today.
    ahead = {r["piece"] for r in rows(store, _PIECES_AHEAD_Q, (), now=instant(now))}
    for source in graphs_of(store, CHANGEABLE_GRAPH):
        if source in ahead:
            continue
        update(store, f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} "
                       f"WHERE {{ GRAPH <{source}> {{ ?s ?p ?o }} }}")
    return name


#  THE VOCABULARY, which no step changes and no split cuts: the one belief read beside every world
#  whole. What the agent reads to act — its actions, flows, shapes and constraints — is no belief,
#  and no split reaches it (#953).
_DEFINING = (OREXIS + "OntologyGraph",)

#  EVERY GRAPH CUT BY THE PATTERNS ASKED NOW, and saying which a graph was cut by: its row's alone.
_CUT_BY_Q = """SELECT ?g WHERE { GRAPH $cat { ?g planning:cutBy $by } }"""
_CUT_U = """DELETE { GRAPH $cat { $g planning:cutBy ?was } } INSERT { GRAPH $cat { $g planning:cutBy $by } }
WHERE { OPTIONAL { GRAPH $cat { $g planning:cutBy ?was } } }"""

#  EVERY CHANGEABLE GRAPH AND THE GRAPH IT WAS CUT FROM.
_CUT_Q = """
SELECT ?piece ?source WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  ?piece a planning:ChangeableGraph . OPTIONAL { ?piece prov:wasDerivedFrom ?source } } }"""


def _split(store: ox.Store, actions, at: datetime, within: frozenset | None = None) -> list[str]:
    """Cut out of every graph a search reads beside its worlds what the search can change, each into a
    `planning:ChangeableGraph` derived from it — what `actions`' effects (every action's where None)
    and the transitions can write (`footprint.changeable`) — leaving the rest where it was. The
    changeable graphs made.

    A CUT STANDS WHILE ITS SOURCE AND ITS PATTERNS DO (#953): the source's row says the patterns it was
    cut by (`planning:cutBy`, their digest), and a graph whose row says the patterns asked now is left as
    it stands. Any other is taken back first — its changeable graph put back into it — and cut again, so
    the cut is a function of what the graphs hold now and laying twice cuts once; a changeable graph
    whose source is gone is dropped, since a refresh forgot the source and copied it whole again."""
    cat = catalogue_of(store)
    patterns = footprint.changeable(store, actions, at)
    if patterns is not footprint.ANYTHING:
        patterns = sorted(set(patterns) | _predicted(store, at, within), key=lambda p: (p[0], p[1] or ""))
    by = _signature(patterns)
    pieces: dict[str, list[str]] = {}
    for r in rows(store, _CUT_Q, ()):
        source = r.get("source")
        if source and _classified(store, source):
            pieces.setdefault(source, []).append(r["piece"])
        else:
            forget_graph(store, r["piece"])
    defining = set(graphs_of(store, *_DEFINING))
    standing = {r["g"] for r in rows(store, _CUT_BY_Q, (), cat=Raw(f"<{cat}>"), by=ox.Literal(by))}
    made = []
    for graph in graphs_of(store, *KNOWN):
        if graph in defining or graph in standing:
            continue
        for piece in pieces.get(graph, ()):
            add_quads(store, [ox.Quad(q.subject, q.predicate, q.object, ox.NamedNode(graph))
                              for q in store.quads_for_pattern(None, None, None, ox.NamedNode(piece))])
            forget_graph(store, piece)
        update(store, bind(_CUT_U, cat=Raw(f"<{cat}>"), g=graph, by=ox.Literal(by)))
        g = ox.NamedNode(graph)
        if patterns is footprint.ANYTHING:
            cut = list(store.quads_for_pattern(None, None, None, g))
        else:
            cut = list(dict.fromkeys(q for p, o in patterns
                                     for q in store.quads_for_pattern(None, ox.NamedNode(p), _term(o), g)))
        if not cut:
            continue
        piece = f"{graph}.changeable"
        for q in cut:
            store.remove(q)
        add_quads(store, [ox.Quad(q.subject, q.predicate, q.object, ox.NamedNode(piece)) for q in cut])
        classify(store, piece, CHANGEABLE_GRAPH, DERIVED)
        add_quads(store, [ox.Quad(ox.NamedNode(piece), ox.NamedNode(_PROV + "wasDerivedFrom"),
                                  ox.NamedNode(graph), ox.NamedNode(cat))])
        made.append(piece)
    log.debug("%d changeable graph(s) cut over %s pattern(s)", len(made),
              "every" if patterns is footprint.ANYTHING else len(patterns))
    return made


def _signature(patterns) -> str:
    """The digest of a set of patterns, as the cut a source's row says it was made by."""
    text = "every" if patterns is footprint.ANYTHING else "\n".join(f"{p} {o or ''}" for p, o in patterns)
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _predicted(store: ox.Store, now: datetime, within: frozenset | None = None) -> set:
    """What the predictions write, as patterns, and what every belief beginning after `now` that some
    text of the pass reads does: each predicate one adds, or what was concluded of it, a type with its
    class. A prediction is a writer too: its retraction takes out of the ground what stands where it
    adds, so a belief in that place has to be in the ground for it to go. A belief holding later is laid
    as a prediction is (#987), so it is a writer the same way — the butt a forecast says will hold water
    at half past supersedes the empty butt the present holds, and the two must meet in one ground to do
    so. ONE NOTHING READS IS NOT: `within` is what the pass's texts read, and a fact no text reads is not
    a place the search can be in (cone), so a belief ahead saying nothing read — a committed step of the
    agent's own, whose window and filling no met-test asks — writes nothing a ground holds and lays no
    ground; laid, every later step of a plan was a boundary, and a dispatcher's pass laid five grounds for
    three (measured). None reads anything, and lays every belief ahead."""
    ahead = [r["g"] for r in rows(store, _BELIEFS_AHEAD_Q, (), now=instant(now))]
    if within is not None:
        ahead = [g for g in ahead if _reads_any(store, [g, *revisions_of(store, g)], within)]
    graphs = [*graphs_of(store, PREDICTION), *ahead]
    out = set()
    for graph in (*graphs, *revisions_of(store, *graphs)):
        for q in store.quads_for_pattern(None, None, None, ox.NamedNode(graph)):
            typed = q.predicate.value == _RDF_TYPE and isinstance(q.object, ox.NamedNode)
            out.add((q.predicate.value, f"<{q.object.value}>" if typed else None))
    return out


def _reads_any(store: ox.Store, graphs, within: frozenset) -> bool:
    """Whether some text reads a triple of `graphs`: its predicate is in `within`, or it is a type fact
    whose class is — as a world is hashed within what is read (`hash_named_graph`)."""
    for graph in graphs:
        for q in store.quads_for_pattern(None, None, None, ox.NamedNode(graph)):
            if q.predicate.value in within:
                return True
            if q.predicate.value == _RDF_TYPE and isinstance(q.object, ox.NamedNode) and q.object.value in within:
                return True
    return False


#  EVERY BELIEF WHOSE PERIOD BEGINS AFTER `$now` — a forecast of anyone's the present has not reached.
_BELIEFS_AHEAD_Q = """
SELECT ?g WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?g a orexis:BeliefGraph ; dcterms:temporal/orexis:start ?start . FILTER(?start > $now) } }
ORDER BY ?g"""


def _whole(store: ox.Store, graphs) -> list[str]:
    """`graphs` and every changeable graph cut from one of them: each as it stood before the cut."""
    graphs = list(graphs)
    wanted = set(graphs)
    return [*graphs, *(r["piece"] for r in rows(store, _CUT_Q, ()) if r.get("source") in wanted)]


def _classified(store: ox.Store, graph: str) -> bool:
    """Whether the catalogue still says what `graph` is — a graph a refresh forgot says nothing."""
    return bool(store.query(f"ASK {{ GRAPH <{catalogue_of(store)}> {{ <{graph}> a ?kind }} }}"))


def _term(text: str | None):
    """The fixed object of a pattern, as the engine's term — None where anything stands there."""
    if text is None:
        return None
    if text.startswith("<"):
        return ox.NamedNode(text[1:-1])
    return next(iter(ox.parse(f"<urn:s> <urn:p> {text} .".encode(), format=ox.RdfFormat.N_TRIPLES))).object


def _marked(store: ox.Store, ground: str, within: frozenset | None) -> str:
    """Write the ground's hash on its row, within what is read where that is said, and answer
    the digest of everything it holds — what a period is told from the one before it by. One
    digest where nothing is said, since the two are then the same."""
    if within is None:
        return hash_named_graph(store, ground)
    hash_named_graph(store, ground, within)
    return digest_of(store, ground)


def _by_instant(ahead, landings=()) -> list[tuple[datetime, list[tuple[str, bool]]]]:
    """What is laid, grouped by the instant it applies, earliest first — one entry per BOUNDARY
    rather than one per graph, each graph with whether it is a prediction — and every landing a
    boundary too, with what applies there or nothing."""
    out: dict = {at: [] for at in landings}
    for at, graph, predicted in ahead:
        out.setdefault(at, []).append((graph, predicted))
    return sorted(out.items())


#  WHAT A BOUNDARY TAKES OUT OF THE GROUND IT MAKES: every triple under a key some prediction there adds
#  to — the key being its subject and predicate, so a value is replaced as PDDL assigns a fluent (#988).
_SUPERSEDE_U = """DELETE { GRAPH $state { ?s ?p ?o } } WHERE { GRAPH $state { ?s ?p ?o } VALUES (?s ?p) { $keys } }"""


def _fork(store: ox.Store, parent: str, name: str, added) -> str:
    """The ground one boundary past `parent`: its facts, less whatever stood under a key the
    predictions there add to, plus what they all add.

    THE SAME FORK A SEARCH MAKES (`fork`), and the order — copy, the delete, then the adds — is
    said there: a boundary is ONE world change, and the predictions beginning at an instant
    supersede in parallel. The keys are read off what is added, and the delete is bound HERE, to
    the ground this boundary makes; a blank-node subject names nothing across graphs and keys
    nothing.
    """
    _relaid(store, name)
    keys = sorted({(t.subject, t.predicate) for t in added if isinstance(t.subject, ox.NamedNode)}, key=str)
    supersede = [bind(_SUPERSEDE_U, state=Raw(f"<{name}>"),
                      keys=Raw(" ".join(f"(<{s.value}> <{p.value}>)" for s, p in keys)))] if keys else []
    fork(store, parent, name, added, supersede)
    #  AND WHICH GROUND IT CAME FROM, in the store rather than in its name. What MADE it is
    #  not said: a ground is made by predictions nobody takes, and its own period says when —
    #  which is the one thing a possible world has no answer for and a ground does.
    add_quads(store, [ox.Quad(ox.NamedNode(name), ox.NamedNode(_PROV + "wasDerivedFrom"),
                              ox.NamedNode(parent), ox.NamedNode(catalogue_of(store)))])
    return name


#  THE VERDICTS ABOUT A GROUND, with the violation rows hanging off each.
_UNWEIGH_U = """
DELETE { GRAPH ?cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      ?x a planning:Weighing ; planning:weighs $world ; ?p ?o .
                      OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"""


def _relaid(store: ox.Store, name: str) -> None:
    """Take back a ground standing under the name this pass is about to lay under — its
    facts, its row and every weighing of it.

    THE IMAGINARIUM OUTLIVES THE PASS, and a ground is named for its instant, so a boundary the
    last pass's predictions reached too — a prediction at one o'clock, seen from noon and again
    from a minute past — is laid under the name it had. Laid on top, the old facts would stand
    beside the new; kept, its weighings would be verdicts about what it used to hold, and
    `unweighed` would not ask again. The ground of the last PRESENT keeps its name and its
    rows: `reroot` is what decides whether the present is the world it was.
    """
    forget_graph(store, name)
    update(store, bind(_UNWEIGH_U, world=name))


def _triples(store: ox.Store, world: str):
    return (ox.Triple(q.subject, q.predicate, q.object) for q in quads(store, world))


def _name(at: datetime) -> str:
    """A ground's name, for eyes: the instant it opens at. Nothing depends on it — every
    reader asks the class. It carried the scope's name too, and the scope was a parameter
    for that alone: one imaginarium holds one scope's grounds, so the name said nothing."""
    stamp = at.isoformat().replace(":", "").replace("+", "p")
    return f"http://example.org/orexis/graph/ground/{stamp}"
