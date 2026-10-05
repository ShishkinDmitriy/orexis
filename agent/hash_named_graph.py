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

**A WORLD IS HASHED WITHIN WHAT IS READ, and no package declares a word of it.** A caller
may say what a world is identified by — `within`, a set of predicates and classes — and only the
facts it names are then where the world stands, a type fact counting by its class, which is how
the footprint keys a type pattern. The Planner says it for every world of an imaginarium: the
scope's members, joined with every predicate a text the pass evaluates reads or writes — the
actions' preconditions and effects, the desires' met-tests and estimates. A scope alone names
what an action can CHANGE, and a fact a met-test reads that no action writes must still tell
two presents apart.
Measured on the greenhouse and the terrace, 2026-10-03: every reading re-stamps its observation
with the instant it arrived at, no rule reads `sosa:resultTime`, and the re-root read every
reading as a surprise — the grower's cone went every ten minutes with the soil at 0.92 and the
air at 21.0 both times, and a step landing as predicted could never match, since the real landing
always carries an instant the effect never wrote. Hashed within what is read, a fact nothing
reads is not a place the search can be in: the instant, who made the reading, and the number it
gave inside its band, since the texts read the side. A graph hashed with nothing said, or for a
store holding a text that cannot be read, is hashed whole, as before.

What was weighed and refused here: a package declaring which predicates IDENTIFY a node of a
class (`orexis:keyedBy`) and which it CARRIES (`orexis:carries`), so a reading could hash to
its key and its value. Exactly one package ever declared it — sensing, about
`sosa:Observation` — and the branch was dead code with a parameter threaded through four call
sites to feed it (a-term-nobody-reads-is-annotation). What the texts read says the same thing from
the other side, for every package at once; and dropping every
dateTime from the digest instead would have been a kernel rule about a datatype, wrong for a
round, whose period is state.

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


def hash_named_graph(store, graph: str, within: frozenset | None = None) -> str:
    """The canonical hash of what `graph` holds — written onto its catalogue row, and answered.
    `within` is what the world is identified by, predicates and classes; None hashes every fact.

    WRITTEN AS WELL AS ANSWERED, because what a graph holds is a fact about the graph and the
    catalogue is where those live, beside its class and its period. Replaced rather than added
    to: a graph has one content, so re-hashing a graph that moved leaves one row and not two.

    A graph the store has never heard of hashes like an empty one, which is a state like any
    other — the ground before anything is predicted — rather than an error or a None.
    """
    digest = digest_of(store, graph, within)
    catalogue = catalogue_of(store)
    update(store, f"""
DELETE {{ GRAPH <{catalogue}> {{ <{graph}> <{HASH}> ?old }} }}
WHERE  {{ GRAPH <{catalogue}> {{ <{graph}> <{HASH}> ?old }} }}""")
    store.add(ox.Quad(ox.NamedNode(graph), ox.NamedNode(HASH), ox.Literal(digest),
                      ox.NamedNode(catalogue)))
    return digest


def digest_of(store, graph: str, within: frozenset | None = None) -> str:
    """The canonical hash of what `graph` holds, answered and written NOWHERE — for a writer
    that puts it on the graph's row itself, in the same update as the row's class and period,
    rather than paying a second round trip to have it written here. `hash_named_graph` above
    is this plus the write, for a graph whose row already stands. `within` as there."""
    return _digest(_facts(_within(quads(store, graph), within)))


def _within(triples, within: frozenset | None):
    """The triples `within` names — every one, where nothing is said.

    A TYPE FACT COUNTS BY ITS CLASS, because that is how the partition keys a type pattern:
    `?x a hanoi:Peg` reads `hanoi:Peg` and not `rdf:type` (`footprint`), so what is read names
    classes, and the market's effects write typed nodes. Read by
    predicate alone, two worlds differing in a type an effect wrote would have been one place —
    and a pruned fork is the failure this hash exists to prevent. `rdf:type` itself is a member
    only where some text reads a type through a variable class, and then every type counts."""
    if within is None:
        return triples
    return [t for t in triples if t.predicate.value in within
            or (t.predicate == _RDF_TYPE and isinstance(t.object, ox.NamedNode) and t.object.value in within)]


def _digest(facts: frozenset) -> str:
    """One hash of a fact set, `sha256:<hex>`, stable ACROSS PROCESSES.

    NOT PYTHON'S `hash`, which is salted per interpreter for strings: a digest built on it
    differs between two runs of one agent, which is invisible inside a pass and wrong the
    moment a hash is written down — and writing it down is what this is for.
    """
    return f"{_ALGORITHM}:" + hashlib.sha256(
        "\n".join(sorted(repr(f) for f in facts)).encode()).hexdigest()


def _facts(triples) -> frozenset:
    """The canonical facts a set of triples states — what of it counts as 'where I am'."""
    return frozenset(forms(triples))


def forms(triples) -> list[tuple]:
    """The canonical form of EACH triple, in the order given, in the universe of the triples
    given — a blank node being its neighbourhood there. For a writer deciding which of a
    rule's conclusions it already holds: a triple whose form is among the forms of what
    stands says nothing new, whatever label its blank node was minted with.

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
    return [(world.term(s), p.value, world.term(o)) for s, p, o in triples]


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
