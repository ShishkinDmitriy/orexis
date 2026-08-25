"""Where a plan stands: a world as the net diff it holds against the one the agent is in.

Cycle detection compares worlds, and for a long time "the world" was one number — the goal's
own value, rounded. Cheap, and it caught the +3/−3 oscillation it was built for, but a world
differing in anything EXCEPT that number was indistinguishable from where you started: buy the
water first and the soil is no wetter, so the step that makes the plan possible had the
signature of doing nothing and died as a cycle at depth 1. That is #258, and it is what kept
the one genuine chain in the shipped worlds (#255) out of reach.

So the signature is now the world REACHED, held as its net diff against the base world — not
the diffs accumulated along the path, or +3 then −3 would look novel while netting to nothing.
A possible world is `(base − retracted) + added`, step by step, and the same equation holds for
the diff: each step's additions and retractions move a pair of sets `(D+, D−)` — what this
world holds that the base does not, and what the base holds that this world lost — by exact set
algebra, so advancing costs the size of the step's diff and never the size of the world.

**Comparing raw triples would never collide at all.** Every effect rule mints its predicted
observation with `BNODE()` and stamps it `NOW()`, so two runs that reach the same place differ
in node identity and in microseconds, and the whole point of the signature — that a world
already seen is discarded — would quietly stop happening. The facts compared are therefore
CANONICAL, and the canonical form states what "the same place" means here:

- **An observation is its upsert key and its value, and nothing else.** The sensed graph holds
  one node per (subject, property) — the invariant every effect's `ag:retracts` already leans
  on — so a reading canonicalises to that key plus its result, with the number rounded as the
  old signature rounded it. Node identity, `sosa:resultTime`, the `rdf:type` scaffolding: none
  of it is part of where a plan stands, which is also what keeps a look pruned — Observe
  predicts the value it found, its diff nets to nothing, and "look, then look" stays a world
  already seen. A reading with no result contributes NOTHING: a first look's valueless
  observation states no fact about the world, so it too collides with its parent, exactly as
  `test_a_sensing_action_still_ends_a_plan_with_no_rule_of_its_own` requires.
- **Every other triple counts as itself**, with numeric literals rounded the same way and a
  blank node labelled by its content rather than its identity, so two paths minting different
  blank nodes for the same claim still collide. "I now hold a claim" stops looking like
  "nothing happened", which is the sentence this module exists for.

**The terms are pyoxigraph's, never rdflib's.** The record that built the imaginarium refused
an rdflib store by measurement, and the same ruling holds here: an effect's diff arrives as
pyoxigraph triples and the base is the store's own quads, so canonicalising them where they
are costs no conversion at all. The flat rdflib worlds the search also builds exist for one
consumer — pySHACL — and the signature never touches them. Nothing here runs a query or names
a graph: facts are computed from whatever triples the caller hands over.
"""

from __future__ import annotations

import pyoxigraph as ox

#  sosa WAS spelled here — an observation's upsert key and its result, by name. A package
#  declares that now: `?class ag:keyedBy ?p` (the predicates that identify a node of that class)
#  and `?class ag:carries ?p` (what such a node states), and this reads the declaration.
_RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_KEYS_Q = """
SELECT ?class ?keyed ?carried WHERE {
  ?class <http://example.org/orexis#keyedBy> ?keyed .
  ?class <http://example.org/orexis#carries> ?carried }"""


def keys_of(query) -> dict:
    """class IRI -> (frozenset of key predicate IRIs, frozenset of carried predicate IRIs)."""
    from .store import bindings

    out: dict = {}
    for r in bindings(query(_KEYS_Q)):
        keyed, carried = out.setdefault(r["class"], (set(), set()))
        keyed.add(r["keyed"]); carried.add(r["carried"])
    return {c: (frozenset(k), frozenset(v)) for c, (k, v) in out.items()}

#  How far a literal is trusted, and it is the OLD signature surviving as a clause: two worlds
#  whose readings agree to six decimals were the same place before, and still are.
_ROUND = 6

EMPTY = (frozenset(), frozenset())


def facts(triples, keys: dict | None = None) -> frozenset:
    """The canonical facts a set of triples states — what of it counts as 'where I am'.

    `triples` is anything with `.subject`, `.predicate` and `.object` — a step's diff as
    `effects.apply` returns it, or the base as the store's own quads — and is read twice:
    once to learn which nodes are KEYED (typed with a class some package declared `ag:keyedBy`)
    and what hangs off each blank node, once to emit. A keyed node canonicalises to its class,
    its key values and what it carries — never its identity, and never anything else on it
    (an instant, who made it), which is what keeps a look from being a new world every time.
    `keys` is `keys_of(query)`; with none given, nothing is keyed and every triple counts.
    """
    keys = keys or {}
    triples = [(t.subject, t.predicate, t.object) for t in triples]
    typed, outgoing, incoming = {}, {}, {}
    for s, p, o in triples:
        if p == _RDF_TYPE and isinstance(o, ox.NamedNode) and o.value in keys:
            typed[s] = o.value
        if isinstance(s, ox.BlankNode):
            outgoing.setdefault(s, []).append((p, o))
        if isinstance(o, ox.BlankNode):
            incoming.setdefault(o, []).append((s, p))
    keyed = {}
    for s, cls in typed.items():
        key_preds, _ = keys[cls]
        key = tuple(sorted((p.value, _term_value(o)) for a, p, o in triples
                           if a == s and p.value in key_preds))
        if len(key) == len(key_preds):
            keyed[s] = (cls, key)
    world = _World(keyed, outgoing, incoming)
    out = set()
    for s, p, o in triples:
        if s in keyed:
            cls, key = keyed[s]
            if p.value in keys[cls][1]:
                out.add(("keyed", cls, key, p.value, _literal(o)))
            continue
        out.add((world.term(s), p.value, world.term(o)))
    return frozenset(out)


def _term_value(o):
    return o.value if isinstance(o, (ox.NamedNode, ox.BlankNode)) else _literal(o)


def advance(diff: tuple, added: frozenset, retracted: frozenset, base: frozenset) -> tuple:
    """One step on: the diff of `(world − retracted) + added`, given the diff of `world`.

    Exact for sets, which a canonical fact set is: `D+` gains what was added and was never the
    base's, `D−` gains what was retracted and was, and each loses what the other half of the
    step gave back — so a path that returns to the base world returns to `EMPTY`, however it
    got there.
    """
    dplus, dminus = diff
    return (frozenset((dplus - retracted) | (added - base)),
            frozenset((dminus | (retracted & base)) - added))


class _World:
    """One `facts` call's view of its triples: the observation keys, and each blank node's
    neighbourhood — what a term needs to canonicalise, held once rather than re-derived per
    triple. `memo` is why: a blank node with k triples would otherwise have its content walked
    k times, and the belief base carries whole SHACL shape trees of them."""

    def __init__(self, observations, outgoing, incoming):
        self.observations = observations
        self.outgoing = outgoing
        self.incoming = incoming
        self.memo = {}

    def term(self, x):
        """One term's canonical form: an IRI is itself, a number is its rounded value, a blank
        node is its content — and an observation reached as an OBJECT is its upsert key, the
        same identity its own triples canonicalise to."""
        if x in self.observations:
            return ("obs",) + self.observations[x]
        if isinstance(x, ox.BlankNode):
            if x not in self.memo:
                self.memo[x] = self._content(x, frozenset())
            return self.memo[x]
        if isinstance(x, ox.Literal):
            return _literal(x)
        return x.value

    def _content(self, node, seen) -> tuple:
        """A blank node as what is said about it, so identity minted per run cannot differ.

        Recursive because a blank node may point at another; `seen` stops a cycle, which then
        canonicalises by its shape up to the revisit — coarser than isomorphism and safe in the
        direction that matters here, since conflating two worlds prunes a branch the frontier
        would have rejected as no better, while the identity-noise this removes would have made
        every world novel and cycle detection decorative.
        """
        if node in seen:
            return ("bnode", "~")
        seen = seen | {node}
        out = sorted(((p.value, self._leaf(o, seen)) for p, o in self.outgoing.get(node, ())),
                     key=repr)
        into = sorted(((self._leaf(s, seen), p.value) for s, p in self.incoming.get(node, ())
                       if s not in self.observations),
                      key=repr)
        return ("bnode", tuple(out), tuple(into))

    def _leaf(self, x, seen):
        if x in self.observations:
            return ("obs",) + self.observations[x]
        if isinstance(x, ox.BlankNode):
            return self._content(x, seen)
        if isinstance(x, ox.Literal):
            return _literal(x)
        return x.value


def _literal(o):
    if isinstance(o, ox.Literal):
        try:
            return round(float(o.value), _ROUND)
        except (TypeError, ValueError):
            return o.value
    return o.value
