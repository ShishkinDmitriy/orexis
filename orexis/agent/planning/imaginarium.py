"""Where a plan's possible worlds are held — a store that was never a file.

A plan is `(beliefs − retracts) + adds`, applied step after step, and every step's rule is a
SPARQL query. A query reads ONE store, so the question "what would be true here" is answerable
only if there is a store in which *here* is what is true. There was not: `agent/effects.py`
computed each step honestly and asked the belief base for the next one, so the first step was
right and every step after it was predicted from the reading on disk. Depth beyond 1 was
nominal for any desire about a measured value, which is most of them.

So the rules are run against a SECOND pyoxigraph store, in memory for the life of one plan —
the **imaginarium**, in the sovereign's word, and the word says the thing that matters: what is
in it never happened. See
knowledge/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md.

**IT IS A STORE.** The graphs a rule may read are copied in, so an ordinary query means the
same thing here as it does in the belief base — `graphs_of(PUBLIC)` discovers the same names
off the same ontology graph, and `effects.apply` cannot tell the two apart. What differs is
that this one was constructed with no path, so it is memory and there is nothing to clean up:
the whole store is dropped when the plan ends, and a crash mid-plan leaves nothing behind to
find. That is most of why it is a store of its own rather than a graph in the agent's — a
graph can be forgotten to be dropped, and a store that was never on disk cannot be.

IT WAS A CLASS TWICE OVER, and the surface is what settled it both times. It SUBCLASSED
`Store`, which handed every caller a volume's lifecycle — `put_graph`, `load_file`, `optimize`,
`endow_graph` — on an object holding worlds that never touch a disk; then it HELD one and
forwarded, which was twenty-two methods of which the search called five. The other seventeen
came across from a predecessor whose search had a cone, a re-root and a remembered plan, and
answered nobody here. What is left is what does work: filling a store, forking a world, and
dropping one. Everything else a caller wants of a possible world it asks of the store, exactly
as it asks it of the belief base, which is the whole claim of the paragraph above.

**One named graph per search NODE, and none of them is ever mutated.** The obvious reading is a
single hypothesis graph each step overwrites, and it is wrong: the search is breadth-first, so
siblings are alive at the same time and *branching* rather than backtracking is the hard case. A
world is therefore a VALUE — written once when the node is created, and choosing another branch
is binding `$state` to another name. There is nothing to restore because nothing was disturbed.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote

import pyoxigraph as ox

from orexis.agent.ontology import GRAPH_PREFIX, STATE_GRAPH, local_of
from orexis.agent.store import add_quads, forget_graph, remove_quads, update

from .init_imaginarium import init_imaginarium

#  Where a node's readings sit. Under the same root as every other graph, because a graph IRI is
#  a graph IRI — but in a store nothing else can open, which is what keeps `orexis:PossibleGraph`'s
#  promise that nothing here survives anything.
_POSSIBLE = GRAPH_PREFIX + "possible/"

#  AND ONE GRAPH PER WANT'S PLAN. A name is for eyes and nothing depends on it: a reader asks
#  the catalogue for `planning:PlanGraph`, and the writer that made it may name what it wrote.
_PLAN = GRAPH_PREFIX + "plan/"


def plan_graph(want: str) -> str:
    """The graph one want's plan is written into — one per want, replaced whole."""
    return _PLAN + quote(local_of(want), safe="")
_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


def imagine(beliefs: ox.Store, scope: str, now: datetime) -> ox.Store:
    """A store of its own, filled from `beliefs` by `init_imaginarium` — which is all this
    ever was.

    IT IS A STORE AND NOT A CLASS. There was an `Imaginarium` holding one, and what it added
    was twenty-two forwarding methods over the store's own functions, of which the search
    called five; the other seventeen came across from a predecessor whose search had a cone, a
    re-root and a remembered plan, and answered nobody here. A class that holds one store and
    forwards is the store with a longer name to type — the same finding as `Wants`, `Plan` and
    `Want`, arrived at from the doors rather than from the fields.

    `scope` names which imaginarium this is — a pass makes one per scope of the vocabulary —
    and `now` is the instant its grounds are laid from, since the present cannot be read off a
    store: nothing there marks it.
    """
    return init_imaginarium(beliefs, ox.Store(), scope, now)


def reached(store: ox.Store, parent: str, path, added, retracted) -> str:
    """The world one step past `parent`: its readings, less what the step retracts, plus what
    it adds. Returns the new graph's name, which is what a rule's `$state` is bound to.

    **Fork, do not replay.** A node's readings are made by copying its parent's and applying
    the diff. Recomputing a world by replaying from the root would sound cheaper and is the
    shape of the bug this exists to close: replay re-runs each step's rule, and a rule re-run
    has to be re-run against *something* — which was the store. Materialising per node is what
    makes a step's baseline the previous step's conclusion.

    Retraction before addition, and the order is load-bearing for the same reason it is in
    `effects.world_after`: the sensed graph holds one observation node per (subject,
    property), and Observe's construct reuses the very node its retraction names. Added first,
    the addition would be removed by the retraction meant to precede it and the possible world
    would come back holding neither reading.
    """
    name = world_of(path)
    node = ox.NamedNode(name)
    #  THE COPY IS THE ENGINE'S, not a Python loop over quads. The loop cost 4.75 ms per fork
    #  on a 1,000-triple world against 3.29 ms this way, and 59 ms against 44 at 10,000 — a
    #  quarter, all of it the interpreter's overhead per quad rather than the store's. Blank
    #  node identity survives it, measured: a bnode matched in the WHERE is the same term when
    #  inserted, which matters because a held shape IS a blank node.
    update(store, f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} "
                  f"WHERE {{ GRAPH <{parent}> {{ ?s ?p ?o }} }}")
    #  Retraction after the copy rather than during it, and by TERM rather than by text: a
    #  DELETE DATA would have to re-serialise every literal with its datatype, which is the
    #  mistake `effects._triple` already made once in the other direction. The lists are a
    #  handful of triples, so a loop here costs nothing.
    remove_quads(store, (ox.Quad(t.subject, t.predicate, t.object, node) for t in retracted))
    add_quads(store, (ox.Quad(t.subject, t.predicate, t.object, node) for t in added))
    return name


def drop_world(store: ox.Store, name: str) -> None:
    """Forget one imagined world's graph (#553, #487), and what the catalogue said of it — its
    hash, written when the search hashed it. A row pointing at a graph that is gone is litter.
    The ground the search starts in is never dropped here."""
    if name != STATE_GRAPH:
        forget_graph(store, name)


def segment_of(row) -> str:
    """One filled action as a name-safe segment: the action and every value it bound.

    EVERY VALUE IS IN IT, and all of them are load-bearing: a schema action yields several rows
    differing in one parameter alone, and a segment built from fewer made two siblings COLLIDE —
    the second child's quads merged into the first's graph, a disk resting on two supports at
    once, and the search saw a menu of duplicates pointing home.
    """
    return "-".join(quote(local_of(part), safe="")
                    for part in (row.action, *(v for _, v in row.binding)))


def world_of(path) -> str:
    """One graph per node, named by the path that reached it.

    The search needs no tree structure added to it and none is wanted: `_Node.taken` is already
    the ordered tuple of steps taken to get here, so the path IS the ancestry
    anything asks about, and what this design adds is a name for it.

    DETERMINISTIC: built from the IRIs themselves rather
    than from `hash()`, which Python salts per interpreter. Nothing outside one plan reads these
    names, so determinism buys reproducibility in a log rather than findability in a store —
    but a name that moved between runs would make two traces of the same search incomparable,
    which is the one thing anybody reads them for.

    Each segment is `segment_of`, which is also how a candidate is named — a world IS its
    path, so the world a candidate reaches is its parent's name plus that candidate's segment.
    """
    return _POSSIBLE + (".".join(segment_of(row) for row in path) or "here")
