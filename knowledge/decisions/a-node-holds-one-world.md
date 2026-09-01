---
type: Decision
title: A node holds one world, and the second copy is gone
description: >-
  A search node used to hold its world twice — once as an imaginarium graph and once
  flattened into rdflib — and the second copy was fifty-five percent of a solve: 198,144
  Graph.add calls to express steps that changed four triples each. It existed because the
  judge read rdflib, and nothing does since the judge moved to Rust. What a node keeps now is
  its own readings as N-Triples; the invariant half of every world in a pass is written once.
  The alternative the sovereign proposed — a base graph with per-node deltas, queried as a
  union of named graphs — is refused by retraction: a union can add but cannot un-say, and
  tombstones would put FILTER NOT EXISTS into every package's rules. Measured on the bench:
  three disks from 5.52 s to 1.9 s.
status: accepted
timestamp: 2026-09-01T21:40:00Z
---

# A node holds one world, and the second copy is gone

`_Node` carried both an imaginarium graph — the world a rule reads, forked from its parent by
diff inside pyoxigraph — and `world`, that same world flattened over public knowledge into an
rdflib graph. The pair was deliberate and is recorded as such in
[a-rule-is-asked-about-a-world-not-about-a-store](/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md),
whose seam said plainly that materialising the second from the first was the piece of work the
design did not remove: two engines wanted different shapes of the same fact, and pySHACL only
speaks rdflib.

That premise expired when the judge moved to Rust
([the-judge-speaks-rust](/decisions/the-judge-speaks-rust.md)). Nothing on the planning path
reads rdflib any more, so the second copy was pure tax — measured at **55% of a hanoi solve,
198,144 `rdflib.Graph.add` calls**, a full copy of a 2,300-triple world per candidate to
express a step that changes four triples.

**What a node keeps now is its own readings, as N-Triples.** The rest of a judged world —
public knowledge, this agent's beliefs, whatever it records, and the wants — cannot be changed
by a step, so it is written ONCE per pass by the store's own engine and concatenated in front
of whichever node is being judged. N-Triples because its lines stand alone: two graphs join
with `+`, and nothing is re-parsed to merge them.

## The alternative, and why retraction refuses it

The sovereign asked the right question: *we have a named graph per possible world — why not
keep the first one big and the others on top of it, and query the list of named graphs?* It is
the natural design, and one fact kills it. **A union of graphs can add but cannot un-say.** A
move's `orexis:retracts` genuinely deletes — a disk leaves the peg it was on — and no
combination of overlay graphs expresses "this triple is no longer here". The repair would be
tombstones: a retraction writes a marker, and every query filters against it. That puts
`FILTER NOT EXISTS { ... tombstone ... }` into **every package's `rules.ru`**, which breaks the
contract those files are written under — that a rule is an ordinary SPARQL query about a world,
not a query about a bookkeeping scheme. A domain author would have to know how the planner
stores hypotheses in order to ask whether a disk is on a peg.

So the world stays materialised per node — but in ONE store, the Rust one, forked by diff,
which is what the imaginarium was always for. The copy that was deleted is not the world; it is
the translation of the world into another library.

## What did not change

The imaginarium still forks a graph per node rather than replaying, still writes each world
once and mutates none, and `$state` still names exactly what it did. A membership test the flat
copy answered with `in` is now a scoped SPARQL ask — scoped deliberately, because an unscoped
`GRAPH ?g` would read every SIBLING world in the same store, which is the hazard the naming
collision found the hard way in
[the-domain-is-a-plug-in-and-hanoi-is-the-proof](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md).

# Seams left open

- **One world per pass is still flattened into rdflib**, in `_offer`: the legality check carves
  the shapes an agent holds out of its own data with `cbd`, which is an rdflib walk over blank
  nodes. Once per pass rather than once per node, so it costs what one node used to.
- **The invariant is written whole, not shared.** Every judged world hands the engine the same
  ~2,300 lines again, and rudof re-parses them; its reader has a fixed floor of its own
  ([measure-the-search](/runbooks/measure-the-search.md)). A judge that could hold a graph
  across verdicts would remove both, and neither rudof's API nor pySHACL's ever offered that.
