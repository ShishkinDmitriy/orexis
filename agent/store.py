"""An agent's own belief base — an embedded quad store, private by construction.

There is no shared triplestore. Each agent holds one store containing the world as of the
version it booted with, the vocabulary, its own beliefs and its own readings. Nothing else can
reach it: it is a file inside that agent's container, not a service on a network.

That is the whole of the isolation. Before this, privacy was *enforced* — per-agent credentials
and a per-graph access registry over one shared server — and the enforcement had to be
configured, generated and reloaded, which meant a restart every time a principal was added, and
made twenty worlds depend on one process. Now an agent's store contains only what it may see,
so there is nothing left to enforce. See knowledge/decisions/where-the-belief-base-lives.md.

Two kinds of knowledge live here, and their lifetimes differ:

- **public** — the T-Box and the world. Not the agent's to keep: replaced from the ratified
  files on every start, so an agent that restarts picks up an amended world.
- **private** — its beliefs, and what it has sensed. Written at birth, and the agent's
  thereafter. Start and stop must never touch them.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Callable

import pyoxigraph as ox

from assembly import loader
from .ontology import AG, CLASSIFICATION_GRAPH, ONTOLOGY_GRAPH, PUBLIC_GRAPH

# A SPARQL SELECT -> the SPARQL-JSON results dict. The seam every reader is written against,
# unchanged from when this was an HTTP client, so nothing above here knows the difference.
QueryFn = Callable[[str], dict]

# Which graphs are public — ASKED, not listed. A graph IRI is an instance, and code that named
# five of them was doing what rule 1 forbids everywhere else; `ag:PublicGraph` is the term, the
# instances are declared in the kernel's `agent/ontology.ttl`, and adding one is a vocabulary edit
# that touches no Python.
#
# `rdfs:subClassOf*` rather than a bare type, because this runs BEFORE the closure — it is what
# tells the loader where to put the closure. The one graph named here is the bootstrap root: the
# T-Box has to be loaded somewhere before it can be asked anything, exactly as an agent is handed
# its own id before it can discover anything else.
_DISCOVER = f"""
SELECT ?g WHERE {{ GRAPH <{ONTOLOGY_GRAPH}> {{
  ?g a ?class . ?class rdfs:subClassOf* <{PUBLIC_GRAPH}> .
}} }}"""

#  THE AGENT'S OWN GRAPHS — what a plan must carry into its imaginarium and a validation must
#  read beside the state. Two sources, because a graph is classified wherever it can be: a
#  package declares its own in its ontology (sensing's instruments graph, and the kernel does
#  not know its name), while a PER-AGENT graph cannot be declared in a T-Box at all — it does
#  not exist until its agent does — so the agent types its own at boot into the classification
#  graph (genesis.classify_own_graphs).
#
#  BOTH of those are named here, and both are the bootstrap root rather than a reader
#  enumerating: they are where a graph says what it IS, and there is nowhere else to ask.
#
#  What is EXCLUDED and why, because each was a real answer this query gave before:
#    public       — the world declares every agent's belief graph by name, so city's store can
#                   see that `beliefs/fern` exists. A name is not content, but carrying it
#                   would be carrying somebody else's;
#    possible     — the deliberation trace is a record of a pass, not a fact about the world,
#                   and a hypothesis has no place in a hypothesis;
#    another store's — the intention ledger is classified here and held elsewhere, so the
#                   result is intersected with what this store actually has.
_OWN = f"""
SELECT DISTINCT ?g WHERE {{
  {{ GRAPH <{CLASSIFICATION_GRAPH}> {{ ?g a ?class }} }}
  UNION
  {{ GRAPH <{ONTOLOGY_GRAPH}> {{ ?g a ?class ; <{AG}arrivedBy> ?arrival }} }}
  ?class rdfs:subClassOf* <{AG}Graph> .
  #  ASKED OF THE GRAPH AND NOT OF THE CLASS THAT MATCHED: `graph/classification` is typed
  #  both public and belief, so a filter on one binding lets it through on the other. Both
  #  run in the DEFAULT graph, which `query` unions from the public ones — inside a GRAPH
  #  block pyoxigraph evaluates the NOT EXISTS before the UNION binds `?g`, and every row
  #  is dropped.
  FILTER NOT EXISTS {{ ?g a ?any . ?any rdfs:subClassOf* <{PUBLIC_GRAPH}> }}
  FILTER NOT EXISTS {{ ?g a ?hyp . ?hyp rdfs:subClassOf* <{AG}PossibleGraph> }}
}}"""

# Sent with every query. This is the ONLY set a query may use — some engines silently pre-bind
# common prefixes and others do not, so relying on that works in one and fails in another.
# `test_store.py` holds the codebase to this list.
#
# Three sources, and none of them is a registry. The KERNEL'S OWN external vocabularies are
# the six it speaks itself — RDF, RDFS, OWL, XSD, SHACL, PROV — stable, standardised, and the
# language a BDI engine's structure is written in (a want is a shape, a graph says who put a
# fact there). Every OTHER external vocabulary — `sosa:`, `ssn-system:`, `unit:`, `schema:`,
# `dcterms:` — is DISCOVERED, read off the `@prefix` lines of whichever ontology declares it,
# exactly as every namespace under this project's own base is: `sosa:` reaches a query because
# sensing's ontology says so, not because the kernel knows what a reading looks like (#378).
# What keeps a discovered label honest is `agent.loader`'s refusal of one label bound to two
# IRIs anywhere in the tree — which is the whole of what the old "an external vocabulary is not
# a package's to bind" argument needed, and it holds without the kernel naming the vocabulary.
# `ag:` arrives the discovered way too, from the kernel's own `agent/ontology.ttl`.
#
# Assembled eagerly, at import. A malformed or missing ontology is then an error the moment the
# store is imported rather than the first time a query runs, which is the failure that used to
# arrive in production — see the module docstring of `tests/test_store.py`.
_KERNEL = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    #  Queried, not just validated against, since a desire became a shape: what an agent
    #  pursues is SHACL, so reading its numbers is an ordinary query over ordinary triples.
    "sh": "http://www.w3.org/ns/shacl#",
    "prov": "http://www.w3.org/ns/prov#",
}

for _label, _iri in loader.external_prefixes().items():
    if _KERNEL.get(_label, _iri) != _iri:
        raise RuntimeError(f"prefix {_label!r} is the kernel's, bound to <{_KERNEL[_label]}>, "
                           f"and an ontology binds it to <{_iri}>")

NAMESPACES = {**loader.external_prefixes(), **_KERNEL, **loader.prefixes()}

PREFIXES = "\n" + "\n".join(
    f"PREFIX {label}: <{iri}>" for label, iri in sorted(NAMESPACES.items())
) + "\n"

DECLARED = frozenset(NAMESPACES)


# How many decimal places a derived number is written with. Well under the eighteen the store's
# fixed-point xsd:decimal can hold, and far more than a statistic deserves.
#
# This is not tidiness. A Python float divided out to full precision produces lexical forms like
# `0.0039920159680638745` — nineteen fractional digits — which the store accepts, returns, and
# reports the datatype of quite happily, and then FAILS TO COMPARE: every `=` and `>` against it
# raises, and a SPARQL `BIND` whose expression raises leaves its variable unbound while keeping
# the row. So a rule silently produced a solution binding nothing instead of an error, which is
# the most expensive shape a bug can take. Round on the way in and the whole class is gone.
PLACES = 6


def decimal(value: float) -> str:
    """A derived number as a SPARQL literal the store can actually do arithmetic on."""
    return f'"{value:.{PLACES}f}"^^xsd:decimal'


def bindings(results: dict) -> list[dict]:
    """The rows of a SPARQL-JSON result, flattened to {var: value-string}."""
    rows = results.get("results", {}).get("bindings", [])
    return [{k: v.get("value") for k, v in row.items()} for row in rows]


class Store:
    """One agent's quad store. Persistent when given a path, in memory when not.

    A path is the normal case: beliefs must survive a restart, or every start would be a
    partial re-birth and a belief would be configuration again. In-memory exists for tests, and
    for tools that build a world, read it and throw it away.
    """

    def __init__(self, path: str | Path | None = None):
        self.path = str(path) if path else None
        self._store = ox.Store(self.path) if self.path else ox.Store()
        self._public: list | None = None  # discovered on demand; see public_graphs()

    # --- what counts as public, according to the store itself ---

    def recorded_graphs(self) -> list[str]:
        """The agent's own graphs — what a plan carries into its imaginarium and a validation
        reads beside the state. Asked, never listed.

        NAMED WHETHER OR NOT THE GRAPH EXISTS YET, which is deliberate and was learned by
        intersecting with `graph_names()` and watching every world fail to boot: `sensed` has
        no graph until the first reading, and a validation that stopped naming it lost the
        state its shapes are written against. A graph that is not there contributes nothing —
        which is exactly how sensing's instruments graph behaved before it had ever been
        written — so the tolerant list is also the correct one.

        The intention ledger is named here and held in a store of its own; asking this store
        for it yields nothing, for the same reason.
        """
        return sorted(row["g"] for row in bindings(self.query(_OWN)))

    def public_graphs(self) -> list[str]:
        """Every graph the vocabulary types as an `ag:PublicGraph`.

        Cached because it is asked before every query and the answer only moves when something
        is written. Any write drops the cache rather than trying to work out whether it mattered
        — the query is small and a stale answer here is an empty result rather than an error,
        which is the failure mode this whole design keeps having to guard against.

        Empty until a T-Box is loaded, and that is correct: a store nobody has told anything to
        has no public knowledge. Naming a graph explicitly still reads it, so the tools that
        build a bare store and query one graph are unaffected.
        """
        if self._public is None:
            rows = self._store.query(PREFIXES + _DISCOVER)
            self._public = sorted(str(row["g"].value) for row in rows)
        return self._public

    # --- reading ---

    def query(self, sparql: str) -> dict:
        """Read. There is no privileged variant: it is all yours, and only yours.

        An unqualified pattern reads **public knowledge** — the vocabulary, the world, and what
        the rules and the RDFS closure made of them, merged. That is what almost every caller
        wants, and stating it once here is what keeps the five public graphs from leaking into
        sixty queries.

        A `GRAPH <x>` clause still reads exactly `x`, private graphs included. So the two forms
        say different things on purpose: *what does the society know* versus *what is written
        precisely here* — and a review's write boundary is checkable because the second exists.
        """
        out = io.BytesIO()
        public = [ox.NamedNode(g) for g in self.public_graphs()]
        self._store.query(PREFIXES + sparql, default_graph=public).serialize(
            output=out, format=ox.QueryResultsFormat.JSON
        )
        return json.loads(out.getvalue())

    def construct(self, sparql: str):
        """Run a CONSTRUCT and hand back the triples, which are not written anywhere.

        The one thing `query` cannot do: it serialises results as JSON bindings, and a
        CONSTRUCT has none — it has a graph. Added for effect rules (#238), where the answer to
        "what would this lever make true" is a set of triples nobody has asserted and nobody
        should: a possible world is computed and dropped, so the only honest return here is the
        triples themselves.

        Reads the same public default graph an ordinary query does, so a rule sees the world
        and the vocabulary and not another agent's beliefs.
        """
        public = [ox.NamedNode(g) for g in self.public_graphs()]
        return list(self._store.query(PREFIXES + sparql, default_graph=public))

    # Kept so callers written against the old two-door store still read: with one private store
    # per agent, the distinction it drew — "as myself" versus "as admin" — has no meaning.
    query_all = query

    def query_union(self, sparql: str) -> dict:
        """Read with the default graph as the union of EVERYTHING this store holds.

        For two callers. The sovereign's question channel (packages/orexis-capability-reporting/sovereign.py): an
        agent answering its sovereign answers about its WHOLE self — beliefs, record,
        evidence, revisions — not only the public knowledge an ordinary query reads, and
        making the sovereign spell each private graph IRI would be rule 1's own trap
        (a graph IRI is an instance). And the desires store's build (agent/desire.py), whose
        question — what are this store's graphs — is about the whole store for the same
        reason. Still read-only by construction: this is the same
        query API, which structurally cannot execute an update.
        """
        out = io.BytesIO()
        self._store.query(PREFIXES + sparql, use_default_graph_as_union=True).serialize(
            output=out, format=ox.QueryResultsFormat.JSON
        )
        return json.loads(out.getvalue())

    def get_graph(self, graph_iri: str) -> str:
        """A graph's contents as Turtle, or empty if it does not exist yet.

        A graph nobody has written to is not an error: `:sensed` is absent until the first
        reading, and a caller should be able to say so rather than crash.
        """
        out = io.BytesIO()
        self._store.dump(
            output=out, format=ox.RdfFormat.TURTLE, from_graph=ox.NamedNode(graph_iri)
        )
        return out.getvalue().decode()

    def quads(self, graph_iri: str):
        """One graph's contents as QUADS, for a reader that is going to put them somewhere else.

        `get_graph` says the same thing in Turtle, and going through text is what a copy must
        not do: a serialise-and-reparse relabels blank nodes, so an observation node would come
        out the far side unequal to the one a retraction names. It is also the same trap
        `effects._triple` exists for, one layer up — a term crossing a boundary as text stops
        being that term. The one caller is `agent.imaginarium`, which is filling a second store
        with what this one holds.
        """
        return self._store.quads_for_pattern(None, None, None, ox.NamedNode(graph_iri))

    def has_graph(self, graph_iri: str) -> bool:
        """Whether anything has been written here — how birth knows it already happened."""
        return any(self._store.quads_for_pattern(None, None, None, ox.NamedNode(graph_iri)))

    # --- writing ---

    def update(self, sparql: str) -> None:
        self._store.update(PREFIXES + sparql)
        self._public = None

    def put_graph(self, graph_iri: str, ttl: str, dataset: bool = False) -> None:
        """Replace a graph with the given Turtle. Public knowledge only — see the module note.

        `dataset=True` parses **TriG** instead, which is Turtle plus `GRAPH <iri> { … }` blocks.
        Every existing `.ttl` is valid TriG unchanged — Turtle is a syntactic subset — and
        `to_graph` is the destination for the document's *default* graph only, so a file with no
        `GRAPH` block behaves exactly as it did. A file that grows one puts those triples where
        it says — which is how a world states a root desire (#298): a named block, and beside
        it the typing that makes the catalog call the graph what it is.

        **A graph the file names is REPLACED, exactly as the named one is.** The first draft
        cleared only `graph_iri` and said so; the day a world actually declared a block, that
        gap became an amendment bug — a ratification that dropped a desire would have left it
        readable forever, because loading is additive and a quad store keeps what nobody
        removes. So the document is parsed apart first, and every graph it names is cleared
        before its quads land: what a world's files say is what the store holds, for the named
        blocks as for the world graph itself.
        """
        graph = ox.NamedNode(graph_iri)
        if dataset:
            parsed = ox.Store()
            parsed.load(ttl, format=ox.RdfFormat.TRIG)
            for named in parsed.named_graphs():
                self._store.remove_graph(named)
            self._store.remove_graph(graph)
            for quad in parsed:
                self._store.add(quad if not isinstance(quad.graph_name, ox.DefaultGraph)
                                else ox.Quad(quad.subject, quad.predicate, quad.object, graph))
        else:
            self._store.remove_graph(graph)
            self._store.load(ttl, format=ox.RdfFormat.TURTLE, to_graph=graph)
        self._public = None

    def endow_graph(self, graph_iri: str, ttl: str) -> list[str]:
        """Add whatever the Turtle authors that the graph has NEVER held. Touch nothing held.

        The amendment half of birth (#202): a world may grant an agent a new capability, and
        the capability's opening beliefs must reach a volume that already exists — but a
        belief the agent holds is the agent's, revisions included, so the unit of novelty is
        the TERM: a predicate the graph holds is skipped whole, whatever its value, and one
        it has never held is added with its blank-node closure (an aim is a structure, not a
        triple). The term and not the (subject, predicate) pair, measured rather than
        assumed: a beliefs graph has one owner, in whatever spelling its era wrote — a
        volume from before the worlds-own-their-individuals sweep says `ag:fern_agent` where
        today's files say the world's name — and pair-keying read that drift as novelty,
        doubling a migrated belief the first time the two met. Returns the terms added, so
        the caller can say what the amendment endowed; empty means the volume already holds
        everything authored, which is every boot but the first after an amendment.
        """
        graph = ox.NamedNode(graph_iri)
        held = {q.predicate
                for q in self._store.quads_for_pattern(None, None, None, graph)}
        authored = list(ox.parse(ttl, format=ox.RdfFormat.TURTLE))
        by_subject: dict = {}
        for t in authored:
            by_subject.setdefault(t.subject, []).append(t)

        added: list[str] = []
        queue: list = []
        for t in authored:
            if isinstance(t.subject, ox.BlankNode):
                continue  # reached only through the pair that owns it
            if t.predicate in held:
                continue
            queue.append(t)
            added.append(t.predicate.value)
        seen_bnodes: set = set()
        i = 0
        while i < len(queue):
            t = queue[i]
            i += 1
            self._store.add(ox.Quad(t.subject, t.predicate, t.object, graph))
            if isinstance(t.object, ox.BlankNode) and t.object not in seen_bnodes:
                seen_bnodes.add(t.object)
                queue.extend(by_subject.get(t.object, []))
        if added:
            self._public = None
        return sorted(set(added))

    def graph_names(self) -> list[str]:
        """Every named graph actually present, whatever anyone still declares."""
        return [str(g.value) for g in self._store.named_graphs()]

    def clear_graph(self, graph_iri: str) -> None:
        """Empty one graph. For the computed ones, which are written by update rather than
        loaded from a file and so have no `put_graph` to replace them wholesale."""
        self._store.remove_graph(ox.NamedNode(graph_iri))
        self._public = None

    def load_file(self, path: str | Path, graph_iri: str) -> None:
        """Read a ratified file straight into a graph, without going through a string."""
        self._store.load(path=str(path), format=ox.RdfFormat.TURTLE,
                         to_graph=ox.NamedNode(graph_iri))
        self._public = None

    def optimize(self) -> None:
        """Compact the store. Blocking, and worth it only when something says it is needed.

        The belief base is an LSM tree, and every reading is a DELETE followed by an INSERT — so
        each one appends a new version plus a tombstone, and the old versions are reclaimed only
        by compaction. Compaction is size-triggered, and a few hundred triples never approach
        any threshold: the file grows for ever while the triple count does not move. Nothing
        reclaimed here is data, so nothing is lost by asking for it explicitly.

        See knowledge/decisions/a-belief-is-a-pick-within-a-range.md and issue #45.
        """
        self._store.optimize()

    def __len__(self) -> int:
        return len(self._store)
