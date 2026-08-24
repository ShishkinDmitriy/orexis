---
type: Domain Concept
title: Means
term: http://example.org/orexis#Means
description: >-
  The KIND of an act, and a T-Box term — `ag:Observe`, `ag:Actuate`, `ag:Acquire`, `ag:Apply`,
  `ag:Offer`. Not the instrument it goes through, which is the lever, and not what taking it
  would make true, which is the effect. A means is what an intention commits to (`ag:by`), what
  an affordance row offers, and what an effect rule attaches to (`ag:effectOf`) — three
  unrelated parts of the design joined by one term, which is why it is the noun to be exact
  about. There are five and no registry: each is declared by the package that owns the acting,
  and the kernel lists none of them.
---

# What it is

A **means** is *what kind of act this is*. Five exist, each an `ag:Means` in the T-Box:

| | |
|---|---|
| `ag:Observe` | look — obtain a reading where the gap is unmeasured or too stale to act on |
| `ag:Actuate` | move a property directly, where the lever and the resource are both mine |
| `ag:Acquire` | obtain what would reduce a gap — here, bid in a market |
| `ag:Apply` | spend a held claim against the world |
| `ag:Offer` | the host's move — open a round on a venue it convenes |

It is a **term**, not an instance, so code may name one. That is the exception rule 1 carves
out, and it is what lets `search.py` say `_ACTUATE` in Python while never naming a valve.

# It is not the lever, and it is not the effect

Three nouns sit next to each other and the project has used them loosely, including in this
bundle. They are distinct and the distinction is load-bearing:

- a **means** is the kind of act — `ag:Actuate`;
- a **[lever](/domain/lever.md)** is the instrument it goes through — *this* valve, *this* venue;
- an **[effect](/domain/effect.md)** is what taking it would make true.

One means reaches many levers: a host with three valves actuates through each of them, and the
[affordance](/domain/affordance.md) row is one per pair. One means carries at most one effect
rule, which is why `ag:effectOf` points from the rule to the means and not to the lever — what a
dose *does* is a fact about dosing, not about which valve did it.

# Why it is the joint

A means is named in three places that otherwise know nothing about each other, and that is the
whole reason it must be exact:

- an **affordance** row offers one — *what could I do*;
- an **effect** rule attaches to one via `ag:effectOf` — *what would that make true*;
- an **[intention](/domain/intention.md)** commits to one via `ag:by` — *what I am doing about it*;
- an **[actor](/domain/actor.md)** is linked to one via `ag:takenBy` — *who carries it out*.

So a plan's step, the rule that simulated it, and the ledger row that remembers it all name the
same term, and a reader can join them without anything storing a correspondence.

# Five, and nothing lists them

There is no registry of means, in the same way there is no registry of packages or of
affordance kinds. Each is declared in the ontology of whoever owns the acting, and a sixth would
arrive as a declaration plus an `affordances.rq` — [package](/domain/package.md)'s mechanic
again. The kernel names some of them in Python, but only as terms it was handed: nothing anywhere
enumerates the set.

**The ladder is their order, not a ranking of quality.** `ag:Actuate` is offered exactly where
both chains end at the agent — the lever is mine and so is the resource — and `ag:Acquire` where
the resource is someone else's. Acting with what is yours is cheaper than buying what is not —
and nothing states that preference any more. A rung table used to sort the rows cheapest-first,
and it went with the chain that read it; what chooses between two rungs now is which of them
reaches the better world. That is a better question and it does not answer this one: two rungs
reaching the SAME world are separated by whichever the menu returns first, which is alphabetical
and nobody's ranking. It bites nothing shipped, because the two are disjoint per source by
construction — a source with a shop is contested, so its pump yields no Actuate row.
