"""What one named graph HOLDS, as a hash — and the hash written onto the graph's own row.

Two worlds are the same place when they state the same facts, and that is the question a
search asks at every fork: a world already seen is a cycle, and a pass that cannot see one
spends its whole budget going nowhere. So this hands back a digest of a graph's canonical
facts and leaves it on the catalogue row beside the graph's class and its period, where what
is true OF a graph is already written.

**IT IS THE CONTENT AND NOTHING ELSE.** A graph's name is for eyes and the order its triples
arrived in is the engine's, so neither is part of where a plan stands. Two things are read
rather than taken at face value, and both are cheap and both bite the moment a package's rule
starts minting:

- **A blank node is its CONTENT, not its label.** A rule that mints with `BNODE()` mints a
  different label every run, so two paths reaching one place would hash differently and every
  world would look novel. A blank node canonicalises to what is said about it and about what
  says it, recursively, with a revisit closing the walk — coarser than isomorphism and safe in
  the direction that matters, since conflating two worlds prunes a branch the frontier would
  have rejected as no better.
- **A number is its ROUNDED value**, to six decimals. Two worlds whose readings agree that far
  were the same place before this was a hash and still are. Only a NUMBER is rounded, and
  that is the one tolerance anybody chose here: every other term canonicalises to its kind
  and its text, so an IRI is not its own spelling as a string, a string is not the number it
  parses to, and a language tag is part of what a literal says. All three of those collided
  while every term collapsed to a bare Python value — `<urn:x>` with `"urn:x"`, `"1"` with
  `1`, and `"hi"@en` with `"hi"@de` — which made a search call two worlds one place that no
  domain would.

**NO CANONICALISATION BY CLASS, and that is a deliberate absence.** A package used to declare
which predicates IDENTIFY a node of a class (`orexis:keyedBy`) and which it CARRIES
(`orexis:carries`), so a reading could hash to its key and its value while its instant and its
node identity were dropped. Exactly one package ever declared it — sensing, about
`sosa:Observation` — and a sensing graph does not reach planning, so nothing here declared the
terms, `keys_of` answered `{}` for every store in this tree, and the branch was dead code with
a parameter threaded through four call sites to feed it. It comes back with sensing, and with
the re-root that was its other reader (a-term-nobody-reads-is-annotation).

**THE TERMS ARE PYOXIGRAPH'S, never rdflib's.** The record that built the imaginarium refused
an rdflib store by measurement and the same ruling holds here: the graph's quads are the
store's own, so canonicalising them where they are costs no conversion.

**IN THE COMMON PART**, beside the store: nothing here is the search's. A graph's contents
hashing to a value is a fact about a graph, and both layers stand on graphs.

WHAT ELSE WENT WITH THE MOVE. `advance` and `where` carried a world's diff forward step by
step without re-reading it, and `by_class`, `named`, `EMPTY` and `TYPE` served the cone and
the re-root. Not one had a caller: the diff was retired when a possible world came to be kept
rather than re-made, and the re-root has not come back yet.
"""

from __future__ import annotations

import hashlib

import pyoxigraph as ox

from .ontology import HASH
from .store import catalogue_of, quads, update

_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")

#  How far a literal is trusted, and it is the old canonical form surviving as a clause: two
#  worlds whose readings agree to six decimals were the same place before, and still are.
_ROUND = 6

#  SHA-256, NAMED IN THE VALUE. `hashlib` is the standard library's and 256 bits is past any
#  collision a pass could reach; what matters more is that the row says which, since a digest
#  whose algorithm is a convention is a digest nobody can check and nobody can migrate.
_ALGORITHM = "sha256"


def hash_named_graph(store, graph: str) -> str:
    """The canonical hash of what `graph` holds — written onto its catalogue row, and answered.

    WRITTEN AS WELL AS ANSWERED, because what a graph holds is a fact about the graph and the
    catalogue is where those live, beside its class and its period. Replaced rather than added
    to: a graph has one content, so re-hashing a graph that moved leaves one row and not two.

    A graph the store has never heard of hashes like an empty one, which is a state like any
    other — the ground before anything is predicted — rather than an error or a None.
    """
    digest = digest_of(store, graph)
    catalogue = catalogue_of(store)
    update(store, f"""
DELETE {{ GRAPH <{catalogue}> {{ <{graph}> <{HASH}> ?old }} }}
WHERE  {{ GRAPH <{catalogue}> {{ <{graph}> <{HASH}> ?old }} }}""")
    store.add(ox.Quad(ox.NamedNode(graph), ox.NamedNode(HASH), ox.Literal(digest),
                      ox.NamedNode(catalogue)))
    return digest


def facts_of(store, *graphs: str) -> frozenset:
    """The canonical facts the named graphs state, together — the same form a digest is made
    of, answered rather than hashed, for a reader that compares two sets fact by fact: what a
    step predicts against what the present holds. Each fact is a nested tuple of plain
    values, so it survives a round trip through JSON."""
    return _facts(q for graph in graphs for q in quads(store, graph))


def digest_of(store, graph: str) -> str:
    """The canonical hash of what `graph` holds, answered and written NOWHERE — for a writer
    that puts it on the graph's row itself, in the same update as the row's class and period,
    rather than paying a second round trip to have it written here. `hash_named_graph` above
    is this plus the write, for a graph whose row already stands."""
    return _digest(_facts(quads(store, graph)))


def _digest(facts: frozenset) -> str:
    """One hash of a fact set, `sha256:<hex>`, stable ACROSS PROCESSES.

    NOT PYTHON'S `hash`, which is salted per interpreter for strings: a digest built on it
    differs between two runs of one agent, which is invisible inside a pass and wrong the
    moment a hash is written down — and writing it down is what this is for.
    """
    return f"{_ALGORITHM}:" + hashlib.sha256(
        "\n".join(sorted(repr(f) for f in facts)).encode()).hexdigest()


def _facts(triples) -> frozenset:
    """The canonical facts a set of triples states — what of it counts as 'where I am'.

    Read twice: once to learn what hangs off each blank node, once to emit, because a blank
    node's canonical form is its neighbourhood and a single pass would not have it yet.
    """
    triples = [(t.subject, t.predicate, t.object) for t in triples]
    outgoing, incoming = {}, {}
    for s, p, o in triples:
        if isinstance(s, ox.BlankNode):
            outgoing.setdefault(s, []).append((p, o))
        if isinstance(o, ox.BlankNode):
            incoming.setdefault(o, []).append((s, p))
    world = _World(outgoing, incoming)
    return frozenset((world.term(s), p.value, world.term(o)) for s, p, o in triples)


class _World:
    """One `_facts` call's view of its triples: each blank node's neighbourhood, held once
    rather than re-derived per triple. `memo` is why: a blank node with k triples would
    otherwise have its content walked k times, and the belief base carries whole SHACL shape
    trees of them."""

    def __init__(self, outgoing, incoming):
        self.outgoing = outgoing
        self.incoming = incoming
        self.memo = {}

    def term(self, x):
        """One term's canonical form: a blank node is its content, and everything else is its
        KIND and its value — because a form that is a bare string cannot tell an IRI from a
        literal that spells it."""
        if isinstance(x, ox.BlankNode):
            if x not in self.memo:
                self.memo[x] = self._content(x, frozenset())
            return self.memo[x]
        if isinstance(x, ox.Literal):
            return _literal(x)
        return ("iri", x.value)

    def _content(self, node, seen) -> tuple:
        """A blank node as what is said about it, so identity minted per run cannot differ.

        Recursive because a blank node may point at another; `seen` stops a cycle, which then
        canonicalises by its shape up to the revisit.
        """
        if node in seen:
            return ("bnode", "~")
        seen = seen | {node}
        out = sorted(((p.value, self._leaf(o, seen)) for p, o in self.outgoing.get(node, ())),
                     key=repr)
        into = sorted(((self._leaf(s, seen), p.value) for s, p in self.incoming.get(node, ())),
                      key=repr)
        return ("bnode", tuple(out), tuple(into))

    def _leaf(self, x, seen):
        if isinstance(x, ox.BlankNode):
            return self._content(x, seen)
        if isinstance(x, ox.Literal):
            return _literal(x)
        return ("iri", x.value)


#  WHAT COUNTS AS A NUMBER, and so what gets rounded. Named rather than discovered by trying
#  `float()` on every literal: that is what made `"1"` and `1` one fact, and a string that
#  happens to parse is still a string.
_XSD = "http://www.w3.org/2001/XMLSchema#"
_NUMERIC = frozenset(_XSD + name for name in (
    "decimal", "double", "float", "integer", "long", "int", "short", "byte",
    "nonNegativeInteger", "positiveInteger", "nonPositiveInteger", "negativeInteger",
    "unsignedLong", "unsignedInt", "unsignedShort", "unsignedByte"))


def _literal(o: "ox.Literal"):
    """A literal as its KIND and its value: a number rounded, anything else its text beside
    the language it is in or the datatype it carries.

    A number whose lexical form the engine will not parse falls through to the text, which is
    the safe direction — two literals that are not the same text are then not the same fact.
    """
    if o.datatype.value in _NUMERIC:
        try:
            return ("num", round(float(o.value), _ROUND))
        except (TypeError, ValueError):
            pass
    return ("lit", o.value, o.language or o.datatype.value)
