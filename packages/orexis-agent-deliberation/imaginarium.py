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
query means the same thing here as it does in the belief base — `public_graphs()` discovers the
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

import logging
from datetime import datetime
from urllib.parse import quote

import pyoxigraph as ox

from orexis_agent_progression.ontology import GRAPH_PREFIX, STATE_GRAPH
from orexis_agent_progression.store import NAMESPACES as _NAMESPACES, render, Store

from . import asked

log = logging.getLogger("imaginarium")

#  Where a node's readings sit. Under the same root as every other graph, because a graph IRI is
#  a graph IRI — but in a store nothing else can open, which is what keeps `orexis:PossibleGraph`'s
#  promise that nothing here survives anything.
_POSSIBLE = GRAPH_PREFIX + "possible/"
#  What stands in a retraction graph for "this subject and predicate are gone here". Never
#  read as a value: what is asked of that graph is only whether a pair is in it.
_GONE = ox.NamedNode("http://example.org/orexis#gone")
#  Where a rewriting is held to parsing before it is run. An empty store, so the check costs
#  the parse and nothing else.
_PROBE = ox.Store()
#  What a node's three graphs are called while a rewriting is being remembered: the same rule
#  asked at two nodes differs only in these, so the text between them is the key.
_WORLD, _ADDS, _RETRACTS = "urn:orexis:asked:world", "urn:orexis:asked:adds", \
    "urn:orexis:asked:retracts"
_EXT = "urn:orexis:asked:extension:"


def _iri(step: str) -> str:
    """One step of a property path as a term a VALUES block takes — a rule spells a predicate
    either way and nothing else here resolves a prefix."""
    if step.startswith("<"):
        return step
    prefix, _, local = step.partition(":")
    return f"<{_NAMESPACES[prefix]}{local}>" if prefix in _NAMESPACES else step


class _Anything(frozenset):
    """The set of every predicate — for a world whose actions include a retraction no parse can
    bound (`?obs ?p ?o`), where every pattern is resolved rather than none."""

    def __contains__(self, item):
        return True


def _keyed_predicates(query) -> set | None:
    """What a keyed node of any class states — its key, what it carries, and its type.

    None where no class declares itself keyed, and then a retraction no parse can bound really
    is unbounded and every pattern is resolved.
    """
    from . import signature

    classes = signature.keys_of(query)
    if not classes:
        return None
    out = {_RDF_TYPE.value}
    for keys, carried in classes.values():
        out |= set(keys) | set(carried)
    return out


def _where(text: str) -> tuple:
    """A query split into what comes before its WHERE's brace, the body inside it, and what
    follows. Raises ValueError where the text has no WHERE this can find."""
    i = text.index("WHERE")
    j = text.index("{", i)
    depth = 0
    for k in range(j, len(text)):
        depth += (text[k] == "{") - (text[k] == "}")
        if depth == 0:
            return text[:j], text[j + 1:k], text[k + 1:]
    raise ValueError("unbalanced WHERE")


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

        It is also the rule the rest of the repo follows. `store.public_graphs()` ASKS the
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
        from orexis_agent_progression.ontology import PERIODS_GRAPH
        self._store.copy_graphs(
            store, *list(store.public_graphs(ever=True)), PERIODS_GRAPH, *private)
        #  WHICH PREDICATES A KEYED NODE CARRIES (#553): a retraction of one of these matches
        #  by KEY — every value the node carries under that predicate — never by the exact
        #  value the rule named. Within one pass the two agree, since the value the rule
        #  read is the value the world holds; across a re-root they do not, because the
        #  present is observed and the prediction was not, and an exact retract that misses
        #  leaves two readings on one node, which is the failure `orexis:retracts` exists to
        #  prevent. One rule, everywhere, is easier to keep true than two.
        from . import signature
        self._carried = frozenset(
            pred for _, carried in signature.keys_of(self._store.query).values() for pred in carried)
        #  A NODE IS ITS DIFF (#666): graph name -> (what the path adds, what it retracts), each
        #  a graph of its own and each O(the path's change). A world is MATERIALISED only where
        #  something asks for one whole — the judge at the border, a text the rewriting refuses
        #  — and `_whole` is which of them exist now.
        self._diff: dict = {}
        self._whole: set = set()
        self._moves = None                  # the predicates some action writes; asked once
        self._refused: set = set()          # texts the rewriting could not be trusted with
        self._rewritten: dict = {}          # and the rest, rewritten once and kept
        self._wanted: dict = {}             # per rewriting: which predicates a path needs whole
        self._made: set = set()             # the extensions already built, per world

    # --- the doors a rule is asked through ------------------------------------------------
    #
    #  Named one at a time, on purpose. Each is here because something asks it OF a possible
    #  world: `effects` runs a package's rule (`construct`, `query`, `remember`), the urgency
    #  choir measures a want at an instant (`query_at`), the search runs a compiled violation
    #  select (`query_over`), and a test reads a world back (`quads`, `get_graph`, `dump_nt`).
    #  A door nothing asks for is not forwarded, which is what makes this list the contract
    #  rather than an accident of what a base class happened to carry.

    def query(self, sparql: str, substitutions: dict | None = None) -> dict:
        text = self._asked(sparql)
        if text is sparql:
            return self._store.query(sparql, substitutions)
        #  OVER PUBLIC KNOWLEDGE AND THE AGENT'S OWN, which is what a rule's own door reads
        #  and what a rewritten pattern needs (#666). `query` alone reads the PUBLIC graphs,
        #  so a pattern that used to reach the world through `GRAPH $state` would, rewritten,
        #  fall back on a default graph the readings are not in — no error and no empty
        #  result, but an answer computed from the step's own additions and nothing else.
        #  Measured on the courier's distance heuristic, which came back 0 for every world:
        #  the same reading as the `BIND`-inside-a-`UNION` trap its own comment records, and
        #  the same consequence — a search told it was already home.
        return self._store.query_over(text, *self._store.public_graphs(),
                                      *self._store.recorded_graphs(),
                                      substitutions=substitutions)

    def query_at(self, sparql: str, substitutions: dict | None = None, *,
                 at: datetime | None = None) -> dict:
        return self._store.query_at(self._asked(sparql), substitutions, at=at)

    def query_over(self, sparql: str, *graphs: str, substitutions: dict | None = None) -> dict:
        #  A compiled select names no world in its text — the caller passes it as one of the
        #  graphs merged into the default graph — so the world to read as a diff is found
        #  there instead, and the base stands in its place.
        node = next((g for g in graphs if g in self._diff), None)
        if node is None:
            return self._store.query_over(sparql, *graphs, substitutions=substitutions)
        text = self._asked(sparql, node)
        if text is sparql:                                   # refused: answer it whole
            return self._store.query_over(sparql, *graphs, substitutions=substitutions)
        return self._store.query_over(
            text, *[STATE_GRAPH if g == node else g for g in graphs], substitutions=substitutions)

    def construct(self, sparql: str, substitutions: dict | None = None,
                  at: datetime | None = None):
        #  `at` is the time door and dropping it is not a smaller signature, it is a rule asked
        #  about the wrong instant — which returns an EMPTY RESULT rather than an error.
        return self._store.construct(self._asked(sparql), substitutions, at)

    # --- a world that is a diff, read as one ----------------------------------------------

    def _asked(self, sparql: str, node: str | None = None) -> str:
        """`sparql` with whichever of our worlds it names read as the diff it is (#666).

        The rewriting is `asked.resolved`, held to the world it replaces by
        `tests/test_asked.py`. Where it REFUSES — a property path over a predicate a step
        moves is the shape that does — the world is materialised instead and the text comes
        back untouched, which is what this file did for every text before. So a refusal costs
        what the old road cost, and nothing is ever answered from half a world.

        DONE ONCE PER RULE, not once per ask. A bound text differs per node only in the three
        graph IRIs, so those become tokens, the rewriting is remembered against the text that
        is left, and what a node pays is two substitutions. Scanned and parse-checked afresh
        every time instead, the rewriting cost more than the copy it removes — a hanoi solve
        went from 0.74 s to 1.39 s with the fork already flat.
        """
        if node is None:
            node = next((g for g in self._diff if f"<{g}>" in sparql), None)
        if node is None:
            return sparql
        adds, retracts = self._diff[node]
        key = sparql.replace(node, _WORLD).replace(adds, _ADDS).replace(retracts, _RETRACTS)
        if key in self._refused:
            self.world(node)
            return sparql
        if key not in self._rewritten:
            self._rewritten[key] = self._rewriting(key)
        template = self._rewritten[key]
        if template is None:
            self.world(node)                    # answer it whole, as this always used to
            return sparql
        text = template.replace(_ADDS, adds).replace(_RETRACTS, retracts)
        for token, steps in self._wanted.get(key, {}).items():
            text = text.replace(token, self._extension(node, steps))
        return text

    def _rewriting(self, key: str) -> str | None:
        """One rule's text, rewritten — or None where it must be answered whole.

        Held to PARSING before it is ever run. A rewriting that does not parse is a defect in
        the scanner, and the engine is where it would surface: as a raised error in the middle
        of a pass rather than as a slower answer. Checked here, on the one miss, and the answer
        remembered.
        """
        wanted: dict = {}

        def extension(steps):
            """A path asking for its own predicates whole. Named by a token here and by a
            graph per world at the ask, so one rewriting serves every node."""
            token = f"{_EXT}{len(wanted)}"
            wanted[token] = steps
            return token

        try:
            head, body, tail = _where(key)
            inside = asked.resolved(body, _ADDS, _RETRACTS, self._moving(),
                                    world=("$state", f"<{_WORLD}>"), extension=extension)
        except (ValueError, asked.Refused):
            return None
        self._wanted[key] = wanted
        text = f"{head}{{{inside}}}{tail}"
        try:
            probe = text.replace(_ADDS, "urn:a").replace(_RETRACTS, "urn:r")
            for token in wanted:
                probe = probe.replace(token, "urn:e")
            _PROBE.query(probe, prefixes=_NAMESPACES)
        except SyntaxError as bad:
            log.error("the rewriting would not parse, answering whole: %s", bad)
            self._refused.add(key)
            return None
        return text

    def _moving(self) -> frozenset:
        """The predicates some action writes, in the spellings a rule writes them.

        Asked ONCE — the action graph is public knowledge and only a write could change it —
        and over-answering is the safe direction: a predicate wrongly called movable costs a
        union in one pattern, where one wrongly called fixed reads the world the pass began in.
        """
        if self._moves is None:
            from . import effects, relevance
            from orexis_agent_progression.store import NAMESPACES
            out, anything = set(), False
            for iri in relevance.actions_of(self._store.query):
                rule = effects.rule_for(self, iri)
                for kind in ("construct", "retracts"):
                    text = (rule or {}).get(kind)
                    if not text:
                        continue
                    written = relevance.writes_of_construct(text)
                    if written is not relevance.ANYTHING:
                        out |= {str(p) for p in written}
                        continue
                    #  A RETRACTION THAT TAKES A WHOLE NODE — `CONSTRUCT { ?obs ?p ?o }`, the
                    #  shape of every upsert here — writes no predicate a parser can name, and
                    #  read as "anything" it puts every pattern in every rule through a union:
                    #  measured, that is the difference between 1.08x a read and 1.72x, and it
                    #  doubled a hanoi pass. What such a rule can actually take is what the
                    #  node it names STATES, and the package that mints those nodes declares
                    #  exactly that — `orexis:keyedBy` and `orexis:carries` on the class, plus
                    #  the type itself, since a reading's bands are types (#576).
                    #
                    #  Under-reading this is the one way the rewriting goes wrong quietly, so
                    #  it is not left to inspection: `tests/test_asked.py` runs every rule both
                    #  ways and a predicate wrongly called fixed answers differently there.
                    keyed = _keyed_predicates(self._store.query)
                    if keyed is None:
                        anything = True
                    else:
                        out |= keyed
            #  Both spellings, since a rule names a predicate either way and nothing here
            #  resolves a prefix.
            for iri in list(out):
                for prefix, ns in NAMESPACES.items():
                    if iri.startswith(str(ns)):
                        out.add(f"{prefix}:{iri[len(str(ns)):]}")
            #  AND `a`, which is how a rule spells rdf:type and how every band is written
            #  (`?obs a sensing:InRegion`). Missed, the bands a dose predicts were read from
            #  the world the pass began in, no reading was in any band, and the measure
            #  scored every dosed world at its not-knowing maximum — a plan that satisfied
            #  the want and reported itself no better than standing still.
            if _RDF_TYPE.value in out:
                out.add("a")
            self._moves = _Anything() if anything else frozenset(out)
        return self._moves

    def _extension(self, node: str, steps) -> str:
        """A graph holding, as THIS world states them, just the predicates a path walks.

        The one thing a rewriting cannot do: a closure has to run inside a single graph, and
        no union of graphs gives it one. So the predicates it walks are materialised — which
        is a copy, but of one predicate rather than of the world, and built once per world
        however many times the path is asked. Where that predicate IS most of the world —
        hanoi's `on`, which is the whole of its state — it costs what the old copy cost and
        the rule is no worse off; anywhere else it is a fraction of it.
        """
        name = _POSSIBLE + "extension/" + quote(node[len(_POSSIBLE):], safe="") + "/" + \
            quote("+".join(sorted(steps)), safe="")
        if name in self._made:
            return name
        adds, retracts = self._diff[node]
        values = " ".join(_iri(step) for step in sorted(steps))
        self._store.update(
            f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} WHERE {{ "
            f"  {{ GRAPH <{adds}> {{ ?s ?p ?o }} VALUES ?p {{ {values} }} }} UNION "
            f"  {{ GRAPH <{STATE_GRAPH}> {{ ?s ?p ?o }} VALUES ?p {{ {values} }} "
            f"     FILTER NOT EXISTS {{ GRAPH <{retracts}> {{ ?s ?p ?gone }} }} }} }}",
            forget=False)
        self._made.add(name)
        return name

    def world(self, name: str) -> str:
        """This world whole, materialised on demand and kept until it is dropped.

        What a node holds is its diff; a caller that needs every triple — the judge at the
        border, the entailment, a text the rewriting refused — asks here and pays the copy
        this design exists to avoid. Most nodes are never asked.
        """
        if name not in self._diff or name in self._whole:
            return name
        adds, retracts = self._diff[name]
        self._store.update(f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} WHERE {{ "
                           f"GRAPH <{STATE_GRAPH}> {{ ?s ?p ?o }} "
                           f"FILTER NOT EXISTS {{ GRAPH <{retracts}> {{ ?s ?p ?gone }} }} }}",
                           forget=False)
        self._store.update(f"INSERT {{ GRAPH <{name}> {{ ?s ?p ?o }} }} WHERE "
                           f"{{ GRAPH <{adds}> {{ ?s ?p ?o }} }}", forget=False)
        self._whole.add(name)
        return name

    def remember(self, key, compute):
        return self._store.remember(key, compute)

    def quads(self, graph_iri: str):
        self.world(graph_iri)
        return self._store.quads(graph_iri)

    def get_graph(self, graph_iri: str) -> str:
        self.world(graph_iri)
        return self._store.get_graph(graph_iri)

    def dump_nt(self, *graph_iris: str) -> str:
        for graph in graph_iris:
            self.world(graph)
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
        self.world(graph)
        return [ox.Triple(q.subject, q.predicate, q.object)
                for q in self._store.quads(graph) if q.subject == subject]

    def reached(self, parent: str, path, added, retracted) -> str:
        """The world one step past `parent`, as the DIFF it is: its parent's adds and retracts,
        plus this step's. Returns the new world's name, which is what a rule is bound to.

        **A node is its diff, and a diff is what a read resolves against** (#666). This used to
        copy the parent's readings and apply the step — O(the world) per node against O(the
        step), free while a world is a handful of readings and 58% of a padded solve once it is
        not. The copy is gone; `world()` makes one on demand for the few callers that need every
        triple, and most nodes are never asked.

        ACCUMULATED AGAINST THE ROOT, never one layer per step. A node holds what the whole path
        adds and what the whole path retracts, so a read is two cases however deep the search
        goes; a chain of layers would be one case per step and a pass would slow with its own
        depth.

        Retraction before addition, and the order is load-bearing for the reason it always was:
        the readings hold one observation node per (subject, property), and Observe's construct
        reuses the very node its retraction names.
        """
        name = _name(path)
        adds, retracts = _POSSIBLE + "adds/" + name[len(_POSSIBLE):], \
            _POSSIBLE + "retracts/" + name[len(_POSSIBLE):]
        self._store.clear_graph(adds)
        self._store.clear_graph(retracts)
        if parent in self._diff:
            for source, into in zip(self._diff[parent], (adds, retracts)):
                self._store.update(f"INSERT {{ GRAPH <{into}> {{ ?s ?p ?o }} }} WHERE "
                                   f"{{ GRAPH <{source}> {{ ?s ?p ?o }} }}", forget=False)
        self._diff[name] = (adds, retracts)
        self._whole.discard(name)
        self._store.clear_graph(name)
        self.amend(name, added, retracted)
        return name

    def amend(self, name: str, added, retracted) -> None:
        """Apply a diff to a world already reached — a step's own effect, and what the world did
        while the step ran (#592). Retraction before addition, by term, as `reached` says.

        BY KEY where the predicate is one a keyed node carries (#553): a retraction matches
        every value the node holds under that predicate, never the exact value the rule named.
        """
        if name not in self._diff:                      # the root's readings, and nothing else
            return self._write(name, added, retracted)
        adds, retracts = self._diff[name]
        gone = ox.NamedNode(retracts)
        #  WHAT THE PATH RETRACTS, by (subject, predicate): every shipped retraction is an
        #  upsert of one such pair or the outright removal of one, and by subject alone a
        #  step would hide facts it never touched.
        self._store.add_quads((ox.Quad(t.subject, t.predicate, _GONE, gone)
                               for t in retracted), forget=False)
        #  and out of what the path adds, since a fact added and then retracted is gone.
        self._store.remove_quads(
            [q for t in retracted
             for q in self._store.quads_for_pattern(t.subject, t.predicate, None,
                                                    ox.NamedNode(adds))], forget=False)
        self._store.add_quads((ox.Quad(t.subject, t.predicate, t.object, ox.NamedNode(adds))
                               for t in added), forget=False)
        if name in self._whole:
            self._write(name, added, retracted)

    def _write(self, name: str, added, retracted) -> None:
        """The same diff, into a world that has been materialised."""
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
        #  ASKED OF WHAT THE PATH ADDED, not of the whole world (#666). The nodes being typed
        #  are the ones this step minted, and they are in the adds graph; entailing against a
        #  materialised world would make one per node for an answer about a handful of
        #  triples. Where the world is not a diff — the agent's own readings — it is the graph
        #  itself, as it always was.
        where = self._diff[name][0] if name in self._diff else name
        out = []
        for node, cls in subjects.items():
            key_preds = keys[cls][0]
            key = [(t.predicate, t.object) for t in added
                   if t.subject == node and t.predicate.value in key_preds]
            if len(key) != len(key_preds):
                continue
            among = " ".join(f"?x <{p.value}> {render(o)} ." for p, o in key)
            out += [ox.Triple(n, _RDF_TYPE, c) for n, c in self._store.entail(where, among=among)
                    if n == node]
        #  AND INTO THE WORLD THIS IS ABOUT. `Store.entail` asserts into the graph it was asked
        #  about; where that is the adds graph the bands are already in the diff, and where a
        #  world has also been materialised it needs them too.
        if name in self._whole:
            self._write(name, out, [])
        return out

    def drop(self, name: str) -> None:
        """Forget one imagined world's graph (#553, #487). The node that named it keeps its
        two lists, and `Planner._graph` re-makes the graph from the nearest kept ancestor when
        a rule next has to run against it. The root's readings are never dropped here."""
        if name != STATE_GRAPH:
            self._store.clear_graph(name)
            self._whole.discard(name)
            for made in [m for m in self._made
                         if m.startswith(_POSSIBLE + "extension/"
                                         + quote(name[len(_POSSIBLE):], safe="") + "/")]:
                self._store.clear_graph(made)
                self._made.discard(made)

    def holds(self, name: str) -> bool:
        """Whether this world is MATERIALISED now — a copy of every triple, not the diff that
        is always kept. What `drop` forgets and what `world` makes."""
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
