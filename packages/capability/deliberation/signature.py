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

Nothing here reads a store or names a graph: facts are computed from the flat worlds the
search already builds, and the base's facts are computed once per pass.
"""

from __future__ import annotations

import rdflib

_SOSA = rdflib.Namespace("http://www.w3.org/ns/sosa/")

#  How far a literal is trusted, and it is the OLD signature surviving as a clause: two worlds
#  whose readings agree to six decimals were the same place before, and still are.
_ROUND = 6

EMPTY = (frozenset(), frozenset())


def facts(graph) -> frozenset:
    """The canonical facts a set of triples states — what of it counts as 'where I am'."""
    observations = {
        s: (f, p)
        for s, p in graph.subject_objects(_SOSA.observedProperty)
        for f in graph.objects(s, _SOSA.hasFeatureOfInterest)
    }
    out = set()
    memo = {}
    for s, p, o in graph:
        if s in observations:
            if p == _SOSA.hasSimpleResult:
                foi, prop = observations[s]
                out.add(("obs", str(foi), str(prop), _literal(o)))
            continue
        out.add((_term(s, graph, observations, memo), str(p),
                 _term(o, graph, observations, memo)))
    return frozenset(out)


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


def _term(x, graph, observations, memo):
    """One term's canonical form: an IRI is itself, a number is its rounded value, a blank
    node is its content — and an observation reached as an OBJECT is its upsert key, the same
    identity its own triples canonicalise to.

    `memo` holds each blank node's finished label for the duration of one `facts` call — a
    node with k triples is otherwise recomputed k times, and the belief base carries whole
    SHACL shape trees of them. Only a label computed from the top (no path context) is
    memoisable, which is exactly what every call from here is.
    """
    if x in observations:
        foi, prop = observations[x]
        return ("obs", str(foi), str(prop))
    if isinstance(x, rdflib.BNode):
        if x not in memo:
            memo[x] = _content(x, graph, observations, frozenset())
        return memo[x]
    if isinstance(x, rdflib.Literal):
        return _literal(x)
    return str(x)


def _literal(o):
    if isinstance(o, rdflib.Literal):
        try:
            return round(float(o), _ROUND)
        except (TypeError, ValueError):
            return str(o)
    return str(o)


def _content(node, graph, observations, seen) -> tuple:
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
    outgoing = sorted(
        ((str(p), _leaf(o, graph, observations, seen)) for p, o in graph.predicate_objects(node)),
        key=repr)
    incoming = sorted(
        ((_leaf(s, graph, observations, seen), str(p)) for s, p in graph.subject_predicates(node)
         if s not in observations),
        key=repr)
    return ("bnode", tuple(outgoing), tuple(incoming))


def _leaf(x, graph, observations, seen):
    if x in observations:
        foi, prop = observations[x]
        return ("obs", str(foi), str(prop))
    if isinstance(x, rdflib.BNode):
        return _content(x, graph, observations, seen)
    if isinstance(x, rdflib.Literal):
        return _literal(x)
    return str(x)
