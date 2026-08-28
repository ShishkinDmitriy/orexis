---
type: Decision
title: A package states what it needs of the world, and the belief base is the union
description: >-
  Genesis copies every ratified triple into every agent, so a bidder holds its rivals' wiring
  and a sensing rig holds venues it can never reach. Decided that a package may ship a
  `world.rq` — a CONSTRUCT, parameterised by the agent's own node, saying which triples it
  needs — and that an agent's public graph is the union of those projections over the kernel's
  bootstrap root. Three hazards are answered by ordering rather than managed — projections are
  evaluated against the ratified files and never against each other, entailment runs after the
  union so no agent holds a conclusion whose premises it lacks, and a shape failing for absence
  is a projection defect because the sovereign still validates the world entire.
status: accepted
timestamp: 2026-08-28T00:00:00Z
---

# What is true today

`agent/genesis.py::refresh_public` builds every agent's public knowledge the same way:

```python
st.put_graph(WORLD_GRAPH, "\n".join(world_files(world)), dataset=True)
```

Every ratified triple, verbatim, into every belief base — which [world](/domain/world.md)
records plainly. Isolation is per world and per agent's own graphs
([where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md)); *inside* a world
nothing is scoped at all. An agent that bids holds every rival's actuator wiring, every venue
it does not participate in, and the stake of every subject it does not act for.

That was never argued for. It is what "the world graph is public" turned into once public was
settled to mean *authored by the sovereign and identical for everyone* — a claim about
provenance, which nobody has yet read as a claim about necessity.

# What is decided

**A package may ship a `world.rq`**, beside the `ontology.ttl`, `shapes.ttl`, `rules.ru`,
`actions.ttl`, `desires.ru` and `review.rq` it already may — optional like all of them, and an
omission is a statement ([a-package-is-its-name](/decisions/a-package-is-its-name.md)). It is a
CONSTRUCT: the triples this package needs held, asked of the ratified world.

**It is parameterised by the agent's own node and nothing else.** `$me` is substituted before
it runs, exactly as [self-review](/decisions/self-review-is-a-capability.md) substitutes it into
a review rule. That keeps rule 1 whole — a projection names T-Box terms and one instance, which
is the instance every process is already allowed.

**The public graph becomes the union of the projections over a bootstrap root.** The root is the
kernel's own and is the smallest thing from which a projection can be written at all: the
agent's node, what it is, what it acts for, and what it composes. Everything past that is asked
for by whoever needs it.

# Why the package is the one that can say

This argument already won once, one step in. `Sensor`, `Actuator` and `Market` used to be loaded
by `agent/world.py`, and moved out to each package's own `wiring.py` for a reason that file still
records — the kernel had come to know what a probe, a valve and a venue are, expressed in SPARQL
where the import contracts could not see it
([self-is-bdi-and-wiring-is-the-packages](/decisions/self-is-bdi-and-wiring-is-the-packages.md)).

Loading moved and projecting did not, so the kernel still decides what every package gets to
read. A package holds the only statement of what its own terms mean; it is therefore the only
thing that can say which triples about them are worth holding.

# The grant comes first, and it is already the package's

The question this answers — *is this package needed at all* — was settled before this record.
Each package grants its own capability from its own premise, written in its own vocabulary, in
its own `rules.ru`: actuation asks for an actuator, market for a position in a venue, review for
a mandate whose ends differ, reporting for nothing at all because telemetry is everyone's. The
kernel runs them and reads the answer; it never holds an opinion about who should have what.

So a package already decides **whether** it applies. A projection is that same package deciding
**what it then needs to see**, and the two are one question asked twice, in order: a package
whose premise does not bind is not granted, is never imported
([a-package-is-its-name](/decisions/a-package-is-its-name.md)), and is asked for no projection.
Only granted packages project. That is what fixes the ordering above, and it is why the
projection could not have been designed before the grant was.

# Three hazards, answered by ordering

**A projection could rest on another's output.** Derivation rules already run once in
directory order, which is why a premise may use authored or entailed facts and never another
package's conclusions. A projection has the same hazard one step earlier, and it is removed
rather than managed: **every `world.rq` is evaluated against the ratified files**, never against
a partially built graph, and the results are unioned afterwards. No projection can observe
another, so no ordering exists to depend on.

**Entailment must not outrun what is held**, and the grant below forces the order. Genesis
loads the world entire and *transiently*, materialises the closure, and runs the derivations —
it has to, because that is how the grants are found. Only then do the granted packages'
projections run, against that graph; the union replaces the agent's public graph, the transient
whole world is dropped, and the closure is materialised **again over the union**. What an agent
keeps is therefore its projection plus what its projection alone entails. Materialising once and
keeping the result would leave it holding conclusions whose premises it does not have — a fact
with no reachable source, which is the thing
[who-put-the-fact-there](/decisions/who-put-the-fact-there.md) exists to prevent. Both engines
still read one graph, so [one-graph-both-engines-read](/decisions/one-graph-both-engines-read.md)
is untouched.

**A shape could fail for absence rather than for wrongness**, and pySHACL cannot tell them
apart. The split is by *who is asking*: `orexis-validate` holds the **whole** world to every
package's shapes at ratification, unchanged; `validate_agent` holds an agent to what it holds.
A world that validates whole while one of its agents fails at boot is therefore a **projection
defect with a name**, not an ambiguous failure — and it fails loudly at start, which is where
this project already puts that kind of error.

# What this does not change

- The world files. A projection is read at genesis; nothing about authoring a world moves.
- Onboarding, which reads the whole world because the sovereign is entitled to
  ([who-put-the-fact-there](/decisions/who-put-the-fact-there.md)).
- Rule 4. There was never a shared store, and each agent still builds its own.
- Public means authored-by-the-sovereign. What narrows is what a given agent is handed, not who
  may be shown a world.

# Seams left open

- **A projection is not a privacy boundary and must not be sold as one.** It narrows what an
  agent is given, and an adversarial member is constrained by its credentials and its topics,
  not by what genesis declined to copy.
- **Nothing yet measures what a projection costs.** The union could be nearly the whole world in
  a small society, and the benefit only appears at a size nobody has run.
- **The bootstrap root is a hand-written list of kernel terms.** It is small and it is the one
  place that must not be derived, which makes it the natural thing to get wrong when a new
  kernel word lands.
- **A GRANTED package that ships no `world.rq` gets nothing beyond the root**, which is the
  opposite of today's default and will surprise. The alternative — no projection means
  everything — makes the omission mean two things at once, and would leave the whole-world
  default reachable by forgetting a file. An ungranted package is not asked, so the surprise is
  bounded to packages an agent actually composed.
