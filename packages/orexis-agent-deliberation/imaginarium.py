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

**It is a `Store` because that is what it is.** The graphs a rule may read are copied in, so an
ordinary query means the same thing here as it does in the belief base — `public_graphs()`
discovers the same names off the same ontology graph, and `effects.apply` cannot tell the two
apart. What differs is that this one was constructed with no path, so it is memory and there is
nothing to clean up: the whole store is dropped when the plan ends, and a crash mid-plan leaves
nothing behind to find. That is most of why it is a store of its own rather than a graph in the
agent's — a graph can be forgotten to be dropped, and a store that was never on disk cannot be.

**One named graph per search NODE, and none of them is ever mutated.** The obvious reading is a
single hypothesis graph each step overwrites, and it is wrong: the search is breadth-first, so
siblings are alive at the same time and *branching* rather than backtracking is the hard case. A
world is therefore a VALUE — written once when the node is created, and choosing another branch
is binding `$state` to another name. There is nothing to restore because nothing was disturbed.
"""

from __future__ import annotations

from urllib.parse import quote

import pyoxigraph as ox

from orexis_agent_progression.ontology import GRAPH_PREFIX
from orexis_agent_progression.store import Store

#  Where a node's readings sit. Under the same root as every other graph, because a graph IRI is
#  a graph IRI — but in a store nothing else can open, which is what keeps `ag:PossibleGraph`'s
#  promise that nothing here survives anything.
_POSSIBLE = GRAPH_PREFIX + "possible/"


class Imaginarium(Store):
    """The graphs a rule may read, in memory, plus one graph per world the plan imagines."""

    def __init__(self, store: Store, *private: str):
        """Copy what no step may change: public knowledge, and whichever private graphs are named.

        **Every public graph, asked rather than listed.** The record budgeted for four — world,
        derived, entailed, beliefs, 486 quads — on the reasoning that those are what the shipped
        rules read. Measured, that set makes the actuation and market CONSTRUCTs bind nothing:
        both walk `?term market:ofGood ?good`, and a valuation term is stated in a package's
        `ontology.ttl`, so it lands in the ontology graph along with the T-Box. Copying every
        public graph costs 10.4 ms and 2,646 quads on `world/loner` where the lean set is 0.6 ms
        and 165 — and the lean set is wrong in the way this file exists to prevent, since a
        pattern reaching a graph nobody copied returns an EMPTY RESULT rather than an error: no
        rows, no exception, and a planner that quietly finds every lever useless. Eleven
        milliseconds on a pass costing over a second is not a price worth that.

        It is also the rule the rest of the repo follows. `store.public_graphs()` ASKS the
        vocabulary which graphs are public; naming four of them here would be the enumeration
        rule 1 forbids, and adding a fifth public graph would silently stop reaching this.

        `private` is what the agent alone holds and a rule still names: its beliefs, which every
        prediction's conversion comes out of, and its readings, which are where the search
        starts. Both are copies. Nothing in here is ever written back.
        """
        super().__init__()                       # no path: memory, and not the belief base
        for iri in list(store.public_graphs()) + list(private):
            for quad in store.quads(iri):
                self._store.add(quad)
        self._public = None

    def reached(self, parent: str, path, added, retracted) -> str:
        """The world one step past `parent`: its readings, less what the step retracts, plus what
        it adds. Returns the new graph's name, which is what a rule's `$state` is bound to.

        **Fork, do not replay.** A node's readings are made by copying its parent's and applying
        the diff. Recomputing a world by replaying from the root would sound cheaper and is the
        shape of the bug this exists to close: replay re-runs each step's rule, and a rule
        re-run has to be re-run against *something* — which was the store. Materialising per
        node is what makes a step's baseline the previous step's conclusion.

        Retraction before addition, and the order is load-bearing for the same reason it is in
        `effects.world_after`: the sensed graph holds one observation node per (subject,
        property), and Observe's construct reuses the very node its retraction names. Added
        first, the addition would be removed by the retraction meant to precede it and the
        possible world would come back holding neither reading.
        """
        name = _name(path)
        node = ox.NamedNode(name)
        gone = {(t.subject, t.predicate, t.object) for t in retracted}
        for quad in self._store.quads_for_pattern(None, None, None, ox.NamedNode(parent)):
            if (quad.subject, quad.predicate, quad.object) not in gone:
                self._store.add(ox.Quad(quad.subject, quad.predicate, quad.object, node))
        for triple in added:
            self._store.add(ox.Quad(triple.subject, triple.predicate, triple.object, node))
        return name


def _name(path) -> str:
    """One graph per node, named by the path that reached it.

    The search needs no tree structure added to it and none is wanted: `_Node.taken` is already
    the ordered tuple of affordance rows applied to get here, so the path IS the ancestry
    anything asks about, and what this design adds is a name for it.

    DETERMINISTIC, in the sense `trace._uri` means it: built from the IRIs themselves rather
    than from `hash()`, which Python salts per interpreter. Nothing outside one plan reads these
    names, so determinism buys reproducibility in a log rather than findability in a store —
    but a name that moved between runs would make two traces of the same search incomparable,
    which is the one thing anybody reads them for.
    """
    tail = ".".join(f"{quote(_local(row.action), safe='')}-{quote(_local(row.via), safe='')}"
                    for row in path)
    return _POSSIBLE + (tail or "here")


def _local(iri: str) -> str:
    """The tail of an IRI. A world's individuals share one namespace and a means is the
    kernel's, so within one agent's menu the tails are unique — and a name only has to be
    unique inside the one plan that mints it."""
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
