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

from orexis_agent_execution.ontology import (BELIEF, DESIRE, GRAPH_PREFIX, OREXIS, PREDICTION,
                                             PUBLIC, RECORD, STATE, STATE_GRAPH, WANT, local_of)
from .init_imaginarium import init_imaginarium
from .ontology import PLANNING
from orexis_agent_execution.store import (Memo, add_quads, catalogue_of, classify,
                                           clear_graph, construct, contains_graph, copy_graphs,
                                           dump_nt, entail, get_graph, graphs_of,
                                           quads, quads_for_pattern, query, query_over, reader,
                                           remove_quads, render, update)

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


class Imaginarium:
    """The graphs a rule may read, in memory, plus one graph per world the plan imagines.

    It HOLDS a store rather than being one, and the difference is the whole point. As a subclass
    it offered `put_graph`, `load_file`, `optimize`, `drop_graph` and two dozen more — a volume's
    lifecycle, meaningless for worlds that never touch a disk — and the search reached through
    them without anything marking where the repository ended and the handle began. What is
    reachable now is what is written below: the verbs a search needs, and the doors a rule is
    asked through. Everything else about how worlds are KEPT is behind `self._store`.
    """

    def __init__(self, beliefs: ox.Store, scope: str, now: datetime):
        """A store of its own, filled by `init_imaginarium` — which is all this ever was.

        The copying is the function above, over two engines. What is left here is making the
        empty store and holding it, since this class exists to be the DOORS a rule is asked
        through and not to be the copy.

        `self.engine` is a bare `pyoxigraph.Store` and is public, because the doors below are
        a convenience and not a boundary: a caller that means to hand a rule the engine — the
        search does, on every fork — takes it rather than going through a forwarding method.
        The predecessor held a `Store` wrapper here and forwarded twenty-odd of its methods.

        `scope` names which imaginarium this is — a pass makes one per scope of the vocabulary
        — and `now` is the instant its grounds are laid from, since the present cannot be read
        off a store: nothing there marks it.
        """
        self.engine = ox.Store()                    # no path: memory, and not the belief base
        #  THE PASS'S MEMO, and the pass is what this object IS. A rule text and the action
        #  templates cannot change while a search runs — nothing here writes public knowledge
        #  — so the lifetime is exactly this object's, which is why the memo is its and not
        #  the store's (an-agent-is-four-things).
        self.memo = Memo()
        init_imaginarium(beliefs, self.engine, scope, now)

    @property
    def _carried(self) -> frozenset:
        """WHICH PREDICATES A KEYED NODE CARRIES (#553): a retraction of one of these matches
        by KEY — every value the node carries under that predicate — never by the exact value
        the rule named. Within one pass the two agree, since the value the rule read is the
        value the world holds; across a re-root they do not, because the present is observed
        and the prediction was not, and an exact retract that misses leaves two readings on one
        node, which is the failure `orexis:retracts` exists to prevent. One rule, everywhere,
        is easier to keep true than two.

        ASKED ON FIRST USE and kept, rather than computed while filling the store: it is a
        function of the public graphs, which nothing writes after `init_imaginarium` has run, and
        leaving it out of the filling is what let the filling become a function over two
        stores with nothing of this class in it.
        """
        if (found := self.__dict__.get("_carried_memo")) is None:
            from . import signature
            found = frozenset(pred for _, carried in
                              signature.keys_of(reader(self.engine, PUBLIC)).values() for pred in carried)
            self.__dict__["_carried_memo"] = found
        return found

    # --- the doors a rule is asked through ------------------------------------------------
    #
    #  Named one at a time, on purpose. Each is here because something asks it OF a possible
    #  world: `effects` runs a package's rule (`construct`, `query`, `remember`), the urgency
    #  choir measures a want at an instant (`query_at`), the search runs a compiled violation
    #  select (`query_over`), and a test reads a world back (`quads`, `get_graph`, `dump_nt`).
    #  A door nothing asks for is not forwarded, which is what makes this list the contract
    #  rather than an accident of what a base class happened to carry.

    def query(self, sparql: str, graphs, substitutions: dict | None = None) -> dict:
        return query(self.engine, sparql, graphs, substitutions)

    def query_over(self, sparql: str, *graphs: str, substitutions: dict | None = None) -> dict:
        return query_over(self.engine, sparql, *graphs, substitutions=substitutions)

    def graphs_of(self, *kinds: str, at: datetime | None = None) -> list[str]:
        return graphs_of(self.engine, *kinds, at=at)

    def construct(self, sparql: str, graphs, substitutions: dict | None = None):
        #  Handed its graphs like `query`: the instant and the world a rule is asked about are
        #  in the list the search built, and a list built for the wrong instant returns an
        #  EMPTY RESULT rather than an error (#666), so the search builds it in one place.
        return construct(self.engine, sparql, graphs, substitutions)

    def note(self, quads, *, whole: bool = False) -> None:
        """Write into the imagined store — what a PASS knows about the worlds it made.

        The doors here are named one at a time and each because something asks it of a
        possible world; this one is asked by the search recording what it has worked out — a
        world's parent, what it spent to reach it, what its want reads there. That belongs
        beside the worlds and not in the belief base: it is this pass's, it dies with the
        pass, and a reader that wants to take the next iteration needs both in one store.

        Not a general escape. A caller that means to change a WORLD uses `amend` or `reached`,
        which keep a node's readings a diff of its parent's; this writes about worlds rather
        than in them.

        QUADS AND NOT AN UPDATE, and the difference was measured: as `INSERT DATA` this cost
        38% of a hanoi solve — two SPARQL texts parsed per fork, where the writing itself is
        nothing. These rows are ABOUT worlds and classify nothing, which used to have to be
        ASSERTED to the store (`forget=False`) so it would not throw away its catalogue index
        on the write. There is no index to throw away now — nothing is kept between calls —
        so the assertion is gone with the thing it was made to.

        `whole` says these quads are the COMPLETE account of every graph they name, so what
        was there is cleared first. A re-rooted cone keeps some of its nodes and drops the
        rest, and re-bases every one it keeps — new depths, new costs, a new clock — so its
        account is rewritten rather than amended, and a row for a world that is gone cannot
        survive to be offered as somewhere to search from.
        """
        quads = list(quads)
        if whole:
            for name in {q.graph_name.value for q in quads}:
                clear_graph(self.engine, name)
        add_quads(self.engine, quads)

    def forget_plan(self, graph: str) -> None:
        """Drop a want's plan — the whole graph, because that is what a plan is.

        It enumerated names before: the steps are called `<plan>.0`, `<plan>.1`, so clearing
        one meant removing every subject a plan of up to sixty-four steps MIGHT have used,
        a count the writer had to guess and a shorter plan had to over-clear. A plan of its
        own is cleared by being one.
        """
        clear_graph(self.engine, graph)

    def classify_plan(self, graph: str, want: str) -> None:
        """Say what a plan's graph IS, so a reader asks the catalogue and never the name."""
        classify(self.engine, graph, PLANNING + "PlanGraph", OREXIS + "Derived")

    def quads_for_pattern(self, subject=None, predicate=None, obj=None, graph=None):
        """What the store holds matching a pattern — a reader of this store's own rows."""
        return list(quads_for_pattern(self.engine, subject, predicate, obj, graph))

    def unnote(self, quads) -> None:
        """Take back one of `note`'s rows — the mirror of `note`.

        A world leaves the frontier when it is opened, and the row that said it was there has
        to go with it: a frontier asked of the store is only the frontier if what it names is
        still open.
        """
        remove_quads(self.engine, quads)

    def remember(self, key, compute):
        return self.memo.get(key, compute)

    def quads(self, graph_iri: str):
        return quads(self.engine, graph_iri)

    def get_graph(self, graph_iri: str) -> str:
        return get_graph(self.engine, graph_iri)

    def dump_nt(self, *graph_iris: str) -> str:
        return dump_nt(self.engine, *graph_iris)

    def copy_in(self, source, *graphs: str) -> None:
        """Graphs from ANOTHER store, copied in under their own names — the wants (#547).

        The desire modality owns a store of its own, in memory and derived from the beliefs,
        so what this agent pursues is not among the graphs the constructor copies. The judge
        has always read the wants beside the world, because the packages' shapes target them
        (`orexis:DesireShape`, the keeper's, a region's) — they rode into the border as text.
        Copied in here, a target is resolved at a node by the store that holds the world, and
        the border is written by one dump. Read-only like everything else in here.
        """
        copy_graphs(self.engine, source, *graphs)

    def refresh(self, source, *graphs: str) -> None:
        """Make each of `graphs` say what `source` says there now — the present's graphs a
        resumed pass reads beside its kept worlds: a round opened, a claim arrived, a debt
        written since the cone was made, and the catalogue that says what they are. A timed
        graph is not part of the invariant half by design (#589), so a change to one keeps
        the cone; it must not keep the copy."""
        for graph in graphs:
            self.observe(source, graph)

    def observe(self, source, graph: str) -> None:
        """Make `graph` say what `source` says there, replacing whatever it held.

        The root's readings after a re-root: the present is OBSERVED, so its graph is refreshed
        from the belief base rather than re-made from the old root plus the matched diff. The
        two agree exactly there, and the observed one is what says the present is the present.
        """
        clear_graph(self.engine, graph)
        self.copy_in(source, graph)

    def border_text(self, *graphs: str) -> str:
        """These worlds as one text for the judge, which takes text at the border.

        The CONTRACT, and a caller depends on it: the text CONCATENATES — every line stands
        alone, so a pass writes the invariant half once and joins each node's readings with
        `+`, instead of re-serialising a world per judged node. Which serialisation keeps that
        promise is this store's business and no reader's; it is N-Triples, and the reason is
        in `Store.dump_nt`.
        """
        return dump_nt(self.engine, *graphs)

    def node_of(self, graph: str, subject) -> list:
        """Everything this world says about one subject, as triples — the whole node, type and
        key included.

        A retraction is canonicalised like an addition, so a reading retracted without its type
        is two plain triples that cancel nothing (#619); a caller replacing a node needs all of
        it, and asking for it a quad at a time is how it came to be asked for wrongly.
        """
        return [ox.Triple(q.subject, q.predicate, q.object)
                for q in quads(self.engine, graph) if q.subject == subject]

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
        name = world_of(path)
        node = ox.NamedNode(name)
        #  THE COPY IS THE ENGINE'S, not a Python loop over quads. The loop cost 4.75 ms per
        #  fork on a 1,000-triple world against 3.29 ms this way, and 59 ms against 44 at
        #  10,000 — a quarter, all of it the interpreter's overhead per quad rather than the
        #  store's. Blank node identity survives it, measured: a bnode matched in the WHERE is
        #  the same term when inserted, which matters because a held shape IS a blank node.
        #  A possible world is classified as nothing and holds during no period, so copying
        #  one could never change what the predecessor's wrapper had learned by asking — which
        #  it threw away on every write regardless, at ten percent of a hanoi solve until the
        #  caller asserted otherwise. Nothing is learned by asking here.
        update(self.engine, f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} "
                        f"WHERE {{ GRAPH <{parent}> {{ ?s ?p ?o }} }}")
        #  Retraction after the copy rather than during it, and by TERM rather than by text: a
        #  DELETE DATA would have to re-serialise every literal with its datatype, which is the
        #  mistake `effects._triple` already made once in the other direction. The lists are
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
                gone += list(quads_for_pattern(self.engine, triple.subject, triple.predicate,
                                                        None, node))
            else:
                gone.append(ox.Quad(triple.subject, triple.predicate, triple.object, node))
        remove_quads(self.engine, gone)
        add_quads(self.engine, (ox.Quad(t.subject, t.predicate, t.object, node) for t in added))

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
            out += [ox.Triple(n, _RDF_TYPE, c) for n, c in entail(self.engine, name, among=among)
                    if n == node]
        return out

    def drop(self, name: str) -> None:
        """Forget one imagined world's graph (#553, #487). The node that named it keeps its
        two lists, and `Planner._graph` re-makes the graph from the nearest kept ancestor when
        a rule next has to run against it. The root's readings are never dropped here."""
        if name != STATE_GRAPH:
            clear_graph(self.engine, name)

    def holds(self, name: str) -> bool:
        """Whether this world's graph is materialised now."""
        return contains_graph(self.engine, name)


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
