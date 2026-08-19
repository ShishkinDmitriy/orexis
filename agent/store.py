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

from . import loader
from .ontology import ONTOLOGY_GRAPH, PUBLIC_GRAPH

# A SPARQL SELECT -> the SPARQL-JSON results dict. The seam every reader is written against,
# unchanged from when this was an HTTP client, so nothing above here knows the difference.
QueryFn = Callable[[str], dict]

# Which graphs are public — ASKED, not listed. A graph IRI is an instance, and code that named
# five of them was doing what rule 1 forbids everywhere else; `ag:PublicGraph` is the term, the
# instances are declared in `packages/core/agora/ontology.ttl`, and adding one is a vocabulary edit
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

# Sent with every query. This is the ONLY set a query may use — some engines silently pre-bind
# common prefixes and others do not, so relying on that works in one and fails in another.
# `test_store.py` holds the codebase to this list.
#
# Two halves, and the split is who owns the namespace. The EXTERNAL vocabularies are the
# kernel's: stable, standardised, and not a package's to redefine. Everything under this
# project's own base is ASSEMBLED — `agent.loader` reads it off the ontologies that declare the
# terms, so a package with a namespace of its own is nameable in SPARQL without anything here
# learning it exists. `ag:` arrives that way too, from `packages/core/agora/ontology.ttl`: the base
# vocabulary is a package like any other, and hard-coding it here would have made it the one
# exception for no reason but habit.
#
# Assembled eagerly, at import. A malformed or missing ontology is then an error the moment the
# store is imported rather than the first time a query runs, which is the failure that used to
# arrive in production — see the module docstring of `tests/test_store.py`.
_EXTERNAL = {
    "sosa": "http://www.w3.org/ns/sosa/",
    #  Queried, not just validated against, since a desire became a shape: what an agent
    #  pursues is SHACL, so reading its numbers is an ordinary query over ordinary triples.
    "sh": "http://www.w3.org/ns/shacl#",
    "prov": "http://www.w3.org/ns/prov#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    # Units, as IRIs rather than as strings. SOSA deliberately defines none and names QUDT as
    # one of the vocabularies to reach for, so this is the standard companion to what is already
    # in use. `http://`, not `https://`, which is the canonical form QUDT publishes.
    #
    # Here rather than in `scalings/identity/ontology.ttl` even though that package is the
    # only one that uses it, because the split above is about OWNERSHIP and not about who reads
    # it: an external vocabulary is not a package's to bind, and a package that could rebind
    # `unit:` could silently redirect every unit in the society. Borrowed and not imported — the
    # IRIs are referenced, nothing of QUDT is loaded, and `agent/inference.py` gains no axioms.
    "unit": "http://qudt.org/vocab/unit/",
    # Part-whole, for the one relation SOSA and SSN do not have. Their combined 44 object
    # properties contain nothing linking a Procedure to a Procedure — `ssn:hasSubSystem` is
    # System to System — and a composite part needs to say that one procedure's product is
    # included in another's. Measured across all three published vocabularies before reaching
    # outside them.
    #
    # dcterms because it is the standard generic mereology and declares NO domain and NO range,
    # so applying it to procedures borrows nothing and constrains nothing; its definition is
    # "included either physically or logically in the described resource", and logically is the
    # case here. Deliberately not a step or invocation relation — see dht11's ontology for why
    # this part makes that distinction load-bearing.
    "dcterms": "http://purl.org/dc/terms/",

    # How a figure states its number and its unit. schema.org's `value`/`unitCode` pair is
    # what the W3C's own worked DHT22 example uses to say a Frequency is two seconds, and it
    # completes an idiom half-adopted already: #77 put `unit:` IRIs on sensors and then wrote
    # the number beside them in a term of ours. External, so it belongs here rather than in a
    # package — one that could rebind `schema:` could redefine every figure in the society.
    "schema": "https://schema.org/",

    # What a device can honour, rather than what it is being asked for. SSN's System
    # capabilities module, borrowed on the same terms as everything else here: the IRIs are
    # referenced and none of SSN is loaded.
    #
    # `ssn:` is here for one axiom and would otherwise not be. `ssn-system:hasSystemCapability`
    # hangs off an `ssn:System`, and what makes that reach a sensor is `sosa:Sensor
    # rdfs:subClassOf ssn:System` — asserted in the SSN document, which is neither SOSA nor this
    # module, and which nothing here loads. Borrowing an IRI brings its DEFINITION and not the
    # axioms other documents state ABOUT it; `capabilities/sensing/ontology.ttl` restates that
    # one so the module reaches what it is supposed to reach.
    "ssn": "http://www.w3.org/ns/ssn/",
    "ssn-system": "http://www.w3.org/ns/ssn/systems/",
}

NAMESPACES = {**_EXTERNAL, **loader.prefixes()}

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

    # Kept so callers written against the old two-door store still read: with one private store
    # per agent, the distinction it drew — "as myself" versus "as admin" — has no meaning.
    query_all = query

    def query_union(self, sparql: str) -> dict:
        """Read with the default graph as the union of EVERYTHING this store holds.

        For exactly one caller: the sovereign's question channel (agent/sovereign.py). An
        agent answering its sovereign answers about its WHOLE self — beliefs, record,
        evidence, revisions — not only the public knowledge an ordinary query reads, and
        making the sovereign spell each private graph IRI would be rule 1's own trap
        (a graph IRI is an instance). Still read-only by construction: this is the same
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
        it says, which is what a world will need when genesis starts writing values it picked
        beside the ranges the sovereign stated.

        Note what that does NOT clear: a graph named inside the file is not removed here, because
        this method is told one name. Nothing declares one yet; see the decision record.
        """
        graph = ox.NamedNode(graph_iri)
        self._store.remove_graph(graph)
        self._store.load(
            ttl, format=ox.RdfFormat.TRIG if dataset else ox.RdfFormat.TURTLE, to_graph=graph)
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
