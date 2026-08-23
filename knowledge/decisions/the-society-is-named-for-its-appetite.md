---
type: Decision
title: The society is named for its appetite, not its market
description: >-
  The project is renamed from Agora to Orexis — Aristotle's term for the desire that moves
  an agent to act. Agora failed on uniqueness (the PyPI name taken, dozens of unrelated
  projects) and named the wrong thing besides — the auction is one capability among eight
  and the architecture's own showcase of a replaceable implementation, while the desiring
  mind is the kernel nothing swaps out. The rename is total: repository, package, commands,
  environment variables, image tags and the ontology namespace, which is why existing
  belief volumes need rebirth.
status: accepted
timestamp: 2026-08-23T00:00:00Z
---

# Context

The project was called Agora, and the name had two defects. The practical one: agora is a
crowded name — the PyPI package is taken and the repository shared its name with dozens of
unrelated projects, so the project could not be found by its own name. The truthful one is
more interesting: the name pointed at the wrong feature.

Agora names the marketplace. But the market here is **one capability package among eight**,
and it is this architecture's own flagship example of interchangeability — pay-as-bid and
uniform-price are two members of one [bid-matching](/decisions/bid-matching-is-a-capability.md)
family, and `hosting.py` never learns which answered. A name should survive every planned
substitution, and a name that points at the most explicitly replaceable part does not. What
nothing swaps out is the mind: a [belief is a pick within a range](/decisions/a-belief-is-a-pick-within-a-range.md),
a [desire is a shape](/decisions/a-desire-is-a-shape.md), an
[intention is an amortised deliberation](/decisions/an-intention-is-an-amortised-deliberation.md),
and [a market arises where want meets supply](/decisions/a-market-arises-where-want-meets-supply.md)
— the market itself is downstream of wanting.

# The choice

**Orexis** — ὄρεξις, Aristotle's term in *De Anima* for the desire that moves an agent to
action; the concept the D in BDI descends from. It names the kernel: agents that want, and
act because they want. It is easy to say in every language a contributor is likely to speak
(o-REK-sis), nearly unclaimed (fourteen repositories against the search cap of thirty for
every other candidate tried, PyPI free at decision time), and its existing holders — a Greek
dips maker in North London, a marketing agency in Kerala — are nowhere near software.

Candidates considered and set aside, over four rounds: *Katallaxy* (precise but hard to say),
*Allotment* (good pun, weak abroad), *Torg*, *Veche*, *Artel* (easy to say; a tabletop-game
trademark, a pronunciation trap, an appliance conglomerate respectively), *Volya* (warm, but
meaningless outside the Slavic world). The deciding argument was the kernel-not-plug-in one
above: once the auction was recognised as the replaceable part, only mind-side names remained.

# What the rename covers

Everything, deliberately — a half-rename leaves two names to explain forever. The repository,
the distribution name, every `orexis-*` command, every `OREXIS_*` environment variable, the
container image tags, the core package directory `packages/core/orexis/`, and the ontology
namespace: `http://example.org/orexis#` and each package's namespace under it. The prefix
label `ag:` stays — it is a local binding, every query and rule already speaks it, and it
reads as well for *agent* as it ever did for *agora*.

# Consequences

Renaming the namespace renames every IRI, and an agent's volume holds facts under the old
ones. A society running under the Agora namespace cannot be amended into the new one:
its agents need `rebirth`, which discards beliefs by design. This was accepted knowingly —
at decision time every world in the tree is a development world.

# Seams left open

- The PyPI name `orexis` was free at decision time but is not registered; whoever first
  publishes the distribution claims it.
- Old GitHub URLs redirect after a repository rename, so links in issues and history keep
  working; nothing was done, and nothing needs to be.
