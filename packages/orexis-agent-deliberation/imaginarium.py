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

**It HOLDS a store; it is not one.** The graphs a rule may read are copied in, so an ordinary
query means the same thing here as it does in the belief base — `graphs_of(PUBLIC)` discovers the
same names off the same ontology graph, and `effects.apply` cannot tell the two apart. What
differs is that this one was constructed with no path, so it is memory and there is nothing to
clean up: the whole store is dropped when the plan ends, and a crash mid-plan leaves nothing
behind to find. That is most of why it is a store of its own rather than a graph in the agent's
— a graph can be forgotten to be dropped, and a store that was never on disk cannot be.

It SUBCLASSED one until the surface was counted. That handed every caller a volume's lifecycle
— `put_graph`, `load_file`, `optimize`, `endow_graph` — on an object holding worlds that never
touch a disk, and the search used the inherited half beside the intended one with nothing
marking the seam. What it offers now is written down: the verbs a search needs, and the doors
below, chosen one at a time.

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

from orexis_agent_progression.ontology import GRAPH_PREFIX, PUBLIC, STATE_GRAPH
from orexis_agent_progression.store import render, Store

#  Where a node's readings sit. Under the same root as every other graph, because a graph IRI is
#  a graph IRI — but in a store nothing else can open, which is what keeps `orexis:PossibleGraph`'s
#  promise that nothing here survives anything.
_POSSIBLE = GRAPH_PREFIX + "possible/"
_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")


class Imaginarium:
    """The graphs a rule may read, in memory, plus one graph per world the plan imagines.

    It HOLDS a store rather than being one, and the difference is the whole point. As a subclass
    it offered `put_graph`, `load_file`, `optimize`, `drop_graph` and two dozen more — a volume's
    lifecycle, meaningless for worlds that never touch a disk — and the search reached through
    them without anything marking where the repository ended and the handle began. What is
    reachable now is what is written below: the verbs a search needs, and the doors a rule is
    asked through. Everything else about how worlds are KEPT is behind `self._store`.
    """

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

        It is also the rule the rest of the repo follows. `store.graphs_of(PUBLIC)` ASKS the
        vocabulary which graphs are public; naming four of them here would be the enumeration
        rule 1 forbids, and adding a fifth public graph would silently stop reaching this.

        `private` is what the agent alone holds and a rule still names: its beliefs, which every
        prediction's conversion comes out of, and its readings, which are where the search
        starts. Both are copies. Nothing in here is ever written back.
        """
        self._store = Store()                       # no path: memory, and not the belief base
        #  EVERY public graph WHATEVER ITS PERIOD, and the table of periods with them (#619):
        #  a pass asks its rules at instants of its own — a step's landing, a want's instant —
        #  and a forecast holding then is a graph the present has not reached. Copied whole,
        #  the imaginarium's own door filters by the instant it is asked at, as the belief
        #  base's does; copied at now, a search could not see past the present's weather.
        self._store.copy_graphs(store, *dict.fromkeys([*store.graphs_of(PUBLIC), store.catalogue, *private]))
        #  WHICH PREDICATES A KEYED NODE CARRIES (#553): a retraction of one of these matches
        #  by KEY — every value the node carries under that predicate — never by the exact
        #  value the rule named. Within one pass the two agree, since the value the rule
        #  read is the value the world holds; across a re-root they do not, because the
        #  present is observed and the prediction was not, and an exact retract that misses
        #  leaves two readings on one node, which is the failure `orexis:retracts` exists to
        #  prevent. One rule, everywhere, is easier to keep true than two.
        from . import signature
        self._carried = frozenset(
            pred for _, carried in signature.keys_of(self._store.reader(PUBLIC)).values() for pred in carried)

    # --- the doors a rule is asked through ------------------------------------------------
    #
    #  Named one at a time, on purpose. Each is here because something asks it OF a possible
    #  world: `effects` runs a package's rule (`construct`, `query`, `remember`), the urgency
    #  choir measures a want at an instant (`query_at`), the search runs a compiled violation
    #  select (`query_over`), and a test reads a world back (`quads`, `get_graph`, `dump_nt`).
    #  A door nothing asks for is not forwarded, which is what makes this list the contract
    #  rather than an accident of what a base class happened to carry.

    def query(self, sparql: str, graphs, substitutions: dict | None = None) -> dict:
        return self._store.query(sparql, graphs, substitutions)

    def query_over(self, sparql: str, *graphs: str, substitutions: dict | None = None) -> dict:
        return self._store.query_over(sparql, *graphs, substitutions=substitutions)

    def graphs_of(self, *kinds: str, at: datetime | None = None) -> list[str]:
        return self._store.graphs_of(*kinds, at=at)

    def construct(self, sparql: str, graphs, substitutions: dict | None = None):
        #  Handed its graphs like `query`: the instant and the world a rule is asked about are
        #  in the list the search built, and a list built for the wrong instant returns an
        #  EMPTY RESULT rather than an error (#666), so the search builds it in one place.
        return self._store.construct(sparql, graphs, substitutions)

    def remember(self, key, compute):
        return self._store.remember(key, compute)

    def quads(self, graph_iri: str):
        return self._store.quads(graph_iri)

    def get_graph(self, graph_iri: str) -> str:
        return self._store.get_graph(graph_iri)

    def dump_nt(self, *graph_iris: str) -> str:
        return self._store.dump_nt(*graph_iris)

    def copy_in(self, source, *graphs: str) -> None:
        """Graphs from ANOTHER store, copied in under their own names — the wants (#547).

        The desire modality owns a store of its own, in memory and derived from the beliefs,
        so what this agent pursues is not among the graphs the constructor copies. The judge
        has always read the wants beside the world, because the packages' shapes target them
        (`orexis:DesireShape`, the keeper's, a region's) — they rode into the border as text.
        Copied in here, a target is resolved at a node by the store that holds the world, and
        the border is written by one dump. Read-only like everything else in here.
        """
        self._store.copy_graphs(source, *graphs)

    def observe(self, source, graph: str) -> None:
        """Make `graph` say what `source` says there, replacing whatever it held.

        The root's readings after a re-root: the present is OBSERVED, so its graph is refreshed
        from the belief base rather than re-made from the old root plus the matched diff. The
        two agree exactly there, and the observed one is what says the present is the present.
        """
        self._store.clear_graph(graph)
        self.copy_in(source, graph)

    def border_text(self, *graphs: str) -> str:
        """These worlds as one text for the judge, which takes text at the border.

        The CONTRACT, and a caller depends on it: the text CONCATENATES — every line stands
        alone, so a pass writes the invariant half once and joins each node's readings with
        `+`, instead of re-serialising a world per judged node. Which serialisation keeps that
        promise is this store's business and no reader's; it is N-Triples, and the reason is
        in `Store.dump_nt`.
        """
        return self._store.dump_nt(*graphs)

    def node_of(self, graph: str, subject) -> list:
        """Everything this world says about one subject, as triples — the whole node, type and
        key included.

        A retraction is canonicalised like an addition, so a reading retracted without its type
        is two plain triples that cancel nothing (#619); a caller replacing a node needs all of
        it, and asking for it a quad at a time is how it came to be asked for wrongly.
        """
        return [ox.Triple(q.subject, q.predicate, q.object)
                for q in self._store.quads(graph) if q.subject == subject]

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
        #  THE COPY IS THE ENGINE'S, not a Python loop over quads. The loop cost 4.75 ms per
        #  fork on a 1,000-triple world against 3.29 ms this way, and 59 ms against 44 at
        #  10,000 — a quarter, all of it the interpreter's overhead per quad rather than the
        #  store's. Blank node identity survives it, measured: a bnode matched in the WHERE is
        #  the same term when inserted, which matters because a held shape IS a blank node.
        #  `forget=False`: a possible world is classified as nothing and holds during no
        #  period, so copying one changes nothing the store learned by asking. Measured at
        #  ten percent of a hanoi solve when it did invalidate.
        self._store.update(f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} "
                        f"WHERE {{ GRAPH <{parent}> {{ ?s ?p ?o }} }}", forget=False)
        #  Retraction after the copy rather than during it, and by TERM rather than by text: a
        #  DELETE DATA would have to re-serialise every literal with its datatype, which is the
        #  road `effects._triple` already got wrong once in the other direction. The lists are
        #  a handful of triples, so a loop here costs nothing.
        self.amend(name, added, retracted)
        return name

    def amend(self, name: str, added, retracted) -> None:
        """Apply a diff to a world already forked — what the world did while a step ran (#592),
        written into the step's own fork after the step's effect. Retraction before addition,
        by term, for the reasons `reached` gives."""
        node = ox.NamedNode(name)
        gone = []
        for triple in retracted:
            if triple.predicate.value in self._carried:
                gone += list(self._store.quads_for_pattern(triple.subject, triple.predicate,
                                                        None, node))
            else:
                gone.append(ox.Quad(triple.subject, triple.predicate, triple.object, node))
        self._store.remove_quads(gone, forget=False)
        self._store.add_quads((ox.Quad(t.subject, t.predicate, t.object, node) for t in added),
                           forget=False)

    def entailed(self, name: str, added, keys) -> list:
        """The class memberships the vocabulary entails of the KEYED nodes `added` put in
        world `name` — a predicted reading's bands (#576) — asserted there and handed back
        as triples for the diff. Asked only about the nodes the step typed with a keyed
        class, so a fork costs one narrow question."""
        subjects = {t.subject: t.object.value for t in added
                    if t.predicate == _RDF_TYPE and isinstance(t.object, ox.NamedNode)
                    and t.object.value in keys}
        if not subjects:
            return []
        #  BY KEY, not by name: a rule mints its observation as a blank node, and a blank node
        #  cannot be named to a query — but a keyed node is its key, and the key is on the
        #  triples the step added. Asked about the whole forked world instead, the question
        #  cost a second and a half per fork, measured.
        out = []
        for node, cls in subjects.items():
            key_preds = keys[cls][0]
            key = [(t.predicate, t.object) for t in added
                   if t.subject == node and t.predicate.value in key_preds]
            if len(key) != len(key_preds):
                continue
            among = " ".join(f"?x <{p.value}> {render(o)} ." for p, o in key)
            out += [ox.Triple(n, _RDF_TYPE, c) for n, c in self._store.entail(name, among=among)
                    if n == node]
        return out

    def drop(self, name: str) -> None:
        """Forget one imagined world's graph (#553, #487). The node that named it keeps its
        two lists, and `Planner._graph` re-makes the graph from the nearest kept ancestor when
        a rule next has to run against it. The root's readings are never dropped here."""
        if name != STATE_GRAPH:
            self._store.clear_graph(name)

    def holds(self, name: str) -> bool:
        """Whether this world's graph is materialised now."""
        return self._store.contains_graph(name)


def name_of(path) -> str:
    """The graph a path of steps from this pass's root reaches — `_name`, for a caller that
    walks a plan back after the search to ask each step's parent world (#550)."""
    return _name(path)


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
    tail = ".".join(
        f"{quote(_local(row.action), safe='')}-{quote(_local(row.via), safe='')}"
        + (f"-{quote(_local(row.about), safe='')}" if row.about else "")
        for row in path)
    return _POSSIBLE + (tail or "here")


def _local(iri: str) -> str:
    """The tail of an IRI — unique enough only inside the one plan that mints these names.

    The segment carries (action, via, about), and the third is load-bearing since hanoi's
    one-Move ruling: a schema action yields several rows per lever differing only in what
    they are about, and named by (action, via) alone two siblings COLLIDED — the second
    child's quads merged into the first's graph, a disk resting on two supports at once, and
    the search saw a menu of duplicates pointing home. Six ground actions had been hiding
    the collision by differing in the action tail."""
    return iri.rsplit("#", 1)[-1].rsplit("/", 1)[-1]
