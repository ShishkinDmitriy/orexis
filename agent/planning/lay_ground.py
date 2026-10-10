"""Laying the ground worlds: what the agent's own knowledge comes to over each period, one
graph per period, in the store a pass stands in.

**A PREDICTION IS AN ACTION NOBODY TAKES.** What it makes true is its graph's own contents —
concrete, because a prediction is a value at an instant — and what it takes away is
`orexis:retracts` on its catalogue row, a `DELETE … WHERE` naming `GRAPH $state`, because what
is standing in that place is not something a prediction can name in advance. Its period says
WHEN it applies rather than a precondition saying whether it may. So the timeline is laid by
exactly the machinery the search walks: fork the period before, run the retraction against the
fork, add what the prediction holds.

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
the rules the beliefs hold, reading the arrival with its revisions, the public graphs and the agent's
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

**WHAT IS BUILT IS CLASSIFIED, NOT RETURNED.** Each ground is a graph with the stretch it holds
over, `planning:GroundGraph`, so a reader asks `graphs_of(store, GROUND_GRAPH, at=T)` and is
handed the one world standing then. A list handed back would be a second place the answer lived
(a-reader-states-the-kinds-it-reads).
"""

from __future__ import annotations

import logging
from datetime import datetime

import pyoxigraph as ox

from agent.belief.transition import applied, asked, transitions
from agent.ontology import OREXIS, PUBLIC, STATE
from agent.hash_named_graph import digest_of, hash_named_graph
from agent.store import (fork, Raw, add_quads, bind, catalogue_of, classify, clear_graph, revisions_of, forget_graph,
                         graphs_of, quads, rows, update)

from .ontology import GROUND_GRAPH

_PROV = "http://www.w3.org/ns/prov#"

log = logging.getLogger("lay_ground")


def _foreseen(store: ox.Store) -> list[tuple[datetime, str, str | None]]:
    """Every prediction this store holds — its graph, the instant it applies, and the pattern
    it supersedes — earliest first.

    ALL THREE ARE SAID OF THE GRAPH AND NONE INSIDE IT: a prediction's contents are what it
    ADDS, which is what a prediction naturally is — `GRAPH :next_temp { :air :hasTemp 30 }` —
    and a triple saying how to retract would be one of the facts it asserts. The catalogue
    already says what a graph is, whose it is and when it holds; how it supersedes is the same
    kind of statement about it.

    THE RETRACT IS A PATTERN AND THE ADDS ARE NOT, which is the whole shape of this. What a
    prediction says is concrete — a value at an instant; what it TAKES AWAY is whatever is
    standing in that place, which nobody can name in advance. So one is data and the other is a
    CONSTRUCT over `$state`, and a keyed reading falls out of it for free: the pattern matches
    the old observation node by its key and takes it whole.

    NO HOLDER. One agent, one volume (rule 4), so the store IS the scope and a prediction in it
    is this agent's by construction.

    A PREDICTION THAT RETRACTS NOTHING is legal and means it: a prediction of something the world
    does not yet say at all — a round opening, a claim arriving — adds without superseding.
    """
    said = """
SELECT ?prediction ?at ?retracts WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
               ?prediction a orexis:PredictionGraph ; dcterms:temporal/orexis:start ?at .
               OPTIONAL { ?prediction orexis:retracts ?retracts } } }
ORDER BY ?at ?prediction"""
    return sorted((datetime.fromisoformat(r["at"]), r["prediction"], r.get("retracts"))
                  for r in rows(store, said, ()))


def lay_ground(store: ox.Store, now: datetime, within: frozenset | None = None,
               landings=()) -> list[str]:
    """Build one ground world per period the agent can see, classified with its stretch.

    `within` is what a world of this imaginarium is identified by — the Planner's to say, from
    what its texts read — and the hash on each ground's row is taken within it: a reading's
    instant, which no text reads, is then not a fact the present differs by. None hashes whole.
    Which boundary is a period is asked of the whole graph either way.

    `landings` are the instants steps in flight land at — the Planner's to say, off the
    intentions — and each ahead of `now` is a period of its own WHATEVER IT HOLDS: a want a
    reconsideration mints is searched from the ground in which the step in flight has landed, so
    the plan it finds begins after it, and a plan is placed at its root's instant (#905,
    knowledge/domain/execution/commitment.md). What the ground holds is what the agent already
    sees holding then, and the step's own prediction is not applied again: a fictive step wrote
    it into the present when it was taken, and a step a drift reads as a committed step is in the
    predictions already. So it is not collapsed into the ground before it by hash, which is the
    one thing that makes it a boundary rather than a prediction.

    The present is the first, and is the agent's readings as they stand. Each prediction that
    applies later is run against the ground standing before it and the diff applied; a ground
    that hashes the same as the one before it is not a period, and is dropped.

    Answers with the graphs it made, earliest first. What a READER takes is `world_at`.

    PUBLIC, AND IN PLACE: it lays the grounds into whichever store it is handed. `prepare_ground`
    lays them into the imaginarium it fills; a case that holds the derivation to the store it
    leaves lays them into the case's own store, so every graph the case declared — a ledger
    among them — stays where the derivation reads it.
    """

    ahead = _foreseen(store)
    here = _present(store, now)
    #  THE TRANSITIONS A PREDICTED OBSERVATION TRIGGERS, and the agent's own state they read and change
    #  as the grounds are laid, from the present's: asked only where something is foreseen.
    rules = transitions(store) if ahead else []
    own = _own_state(store) if rules else None
    public = graphs_of(store, PUBLIC) if rules else []
    made, marks = [here], _marked(store, here, within)
    opened = [now]
    landing = {at for at in landings if at > now}
    for at, group in _by_instant(ahead, landing):
        if at <= now:
            continue                    # a prediction already reached is the present's, not ahead
        #  EVERYTHING BEGINNING AT ONE INSTANT IS ONE WORLD CHANGE. A boundary is an instant,
        #  not a prediction: two drifts that both start at one o'clock describe ONE world, and
        #  forking once per prediction made two grounds with the same name and a period from the
        #  instant to itself — which holds at no instant at all, so a reader standing after it
        #  was handed NO ground and the agent went blind past the boundary. Each retract is
        #  read against the ground standing BEFORE the instant, so they supersede in parallel
        #  rather than one seeing another's work.
        added, retracts = [], []
        for prediction, supersedes in group:
            for graph in (prediction, *revisions_of(store, prediction)):
                added += list(_triples(store, graph))       # the predicted reading and its side
            if supersedes:
                retracts.append(supersedes)
        if not added and not retracts and at not in landing:
            #  A prediction that changes nothing is not a period — an early-out, not a guard:
            #  the hash below reaches the same answer, having laid the graph first.
            continue
        there = _fork(store, here, _name(at), added, retracts)
        if rules:
            _transitioned(store, there, [prediction for prediction, _ in group], rules, own, public)
        mark = _marked(store, there, within)
        if mark == marks and at not in landing:
            #  THE SAME GROUND UNDER ANOTHER NAME. Nothing a met-test can read moved, so this
            #  instant answers what the one before it answered and is not a period of its own.
            forget_graph(store, there)
            continue
        #  THE ONE BEFORE IT ENDS HERE. A ground holds until the next one begins, which is not
        #  known until it does — so each is classified when its successor arrives, and the last
        #  is left open because nothing the agent can see ends it.
        classify(store, here, GROUND_GRAPH, OREXIS + "Derived", start=opened[-1], end=at)
        made.append(there)
        opened.append(at)
        here, marks = there, mark
    classify(store, here, GROUND_GRAPH, OREXIS + "Derived", start=opened[-1])
    if own is not None:
        clear_graph(store, own)
    log.debug("%d ground world(s) over %d prediction(s)", len(made), len(ahead))
    return made


#  THE STATE GRAPHS THE AGENT DERIVED — what the transitions wrote of each arrival of testimony, the
#  subject beliefs among them — as against those it received, which are testimony.
_DERIVED_Q = """
SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                               ?g a orexis:StateGraph ; orexis:arrivedBy orexis:Derived } } ORDER BY ?g"""

#  WHERE THE AGENT'S OWN STATE IS KEPT WHILE THE GROUNDS ARE LAID: a working graph, not a belief,
#  handed by name to the transitions and taken away when the last ground is laid. Its name is for eyes.
_OWN = "http://example.org/orexis/graph/ground/own-state"


def _own_state(store: ox.Store) -> str:
    """The agent's own state as the present ground holds it — every state graph the agent derived,
    copied into a working graph of its own — and the working graph's name.

    APART FROM THE GROUND because a ground is one graph and holds testimony beside the state: the
    observations the present holds and the predicted ones each boundary brings. A transition is handed
    the arrival and no other testimony, so that its WHERE says what it is about (#947); read over the
    whole ground, climate's soil transition would judge every soil observation the ground holds, not
    only the one arriving. So the state is kept here, beside the grounds, as the transitions change it
    ground by ground — the state before a boundary being what the ground before it was left holding."""
    clear_graph(store, _OWN)
    for r in rows(store, _DERIVED_Q, ()):
        update(store, f"INSERT {{ GRAPH <{_OWN}> {{ ?s ?p ?o }} }} WHERE {{ GRAPH <{r['g']}> {{ ?s ?p ?o }} }}")
    return _OWN


def _transitioned(store: ox.Store, ground: str, arrivals: list[str], rules, own: str, public: list[str]) -> None:
    """Every transition each of `arrivals` triggers, applied in `ground` as it is laid (#944).

    A PREDICTED OBSERVATION IS AN ARRIVAL THERE, as a received one is in the present: each triggers
    every transition once, in the order the predictions came, order by order through belief's machine,
    reading itself with its revisions, the public graphs and the agent's own state as the ground before
    left it — and nothing else — so a bed believed dry and resting at 0.3001 is foreseen dry, held by the
    margin as the present holds it. What an order deletes is taken out of the ground, and what it inserts
    put into it; the working state follows. The runner prepares the target, as every runner does: here
    it is the ground being laid, and the present is never written to. No budget is spent: a ground
    holds what its predictions make of it, whole, or it is no ground."""
    for arrival in arrivals:
        reads = [arrival, *revisions_of(store, arrival), *public, own]
        for order in rules:
            change = asked(store, order, reads)
            applied(store, change, ground, [ground])
            applied(store, change, own, [own])


def _present(store: ox.Store, now: datetime) -> str:
    """The agent's readings as they stand, as a ground of its own.

    COPIED RATHER THAN USED IN PLACE. The state graph is what the agent BELIEVES; a ground is
    what a pass stands on, and a pass must be able to fork one without the belief base moving.
    """
    name = _name(now)
    _relaid(store, name)
    #  THE READINGS, WHAT WAS CONCLUDED OF THEM AND WHAT THE AGENT HOLDS OF THEIR SUBJECTS: every state
    #  graph, the subject beliefs the transitions derived among them, which the met-tests and the
    #  effects speak, and each one's revisions — so the ground a pass stands on holds them all, and a
    #  fork writes a state as it writes any fact.
    states = graphs_of(store, STATE)
    for source in [*states, *revisions_of(store, *states)]:
        update(store, f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} "
                       f"WHERE {{ GRAPH <{source}> {{ ?s ?p ?o }} }}")
    return name


def _marked(store: ox.Store, ground: str, within: frozenset | None) -> str:
    """Write the ground's hash on its row, within what is read where that is said, and answer
    the digest of everything it holds — what a period is told from the one before it by. One
    digest where nothing is said, since the two are then the same."""
    if within is None:
        return hash_named_graph(store, ground)
    hash_named_graph(store, ground, within)
    return digest_of(store, ground)


def _by_instant(predictions, landings=()) -> list[tuple[datetime, list[tuple[str, str | None]]]]:
    """The predictions grouped by the instant they apply, earliest first — one entry per
    BOUNDARY rather than one per prediction — and every landing a boundary too, with what
    predictions apply there or none."""
    out: dict = {at: [] for at in landings}
    for at, prediction, supersedes in predictions:
        out.setdefault(at, []).append((prediction, supersedes))
    return sorted(out.items())


def _fork(store: ox.Store, parent: str, name: str, added, retracts: list[str]) -> str:
    """The ground one boundary past `parent`: its facts, less what each prediction there
    retracts, plus what they all add.

    THE SAME FORK A SEARCH MAKES (`fork`), and the order — copy, every delete,
    then the adds — is said there: a boundary is ONE world change, and the predictions
    beginning at an instant supersede in parallel. A prediction's retraction is bound HERE,
    to the ground this boundary makes, because what `$state` means is the caller's — an
    action's is bound to the world its step makes.
    """
    _relaid(store, name)
    fork(store, parent, name, added, [bind(text, state=Raw(f"<{name}>")) for text in retracts])
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
