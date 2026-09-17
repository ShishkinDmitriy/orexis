---
type: Decision
title: An afforder is a service between two collections, and it holds no query
description: >-
  Affording is not a collection that asks another collection - it is a SERVICE whose whole content
  is deciding what to ask, with the queries out of it. `Actions` reads the vocabulary's templates,
  `Affordances` runs one action's precondition against one world, and the afforder decides which
  actions are worth asking, whose wants to ask them against, and how often each side is asked.
  Splitting them let the templates be read once per pass instead of once per node - eighteen
  reads to one, on a three-disk solve - and a test in the package holds the service to writing no
  query and the collections to writing theirs.
status: accepted
timestamp: 2026-09-18T15:00:00Z
---

# What was refused

The shape proposed first was `Affordances` asking `Actions` — one collection calling another and
grounding what came back. The sovereign refused it: **a repository does not ask another
repository; the glue between them is a service, and a service holds no queries.**

That is right, and the reason is the one
[a-repository-is-not-a-service](/decisions/a-repository-is-not-a-service.md) already gives. A
repository answers questions about its own contents. The moment `Affordances` reaches for the
templates it is answering a question about somebody else's — and the tell is that it would then
have to decide *which* templates are worth asking about, which is not a fact about affordances at
all. Deciding is what a service does.

# So there are three things, and each holds exactly one kind of knowledge

| | knows | holds a query? |
|---|---|---|
| `Actions` | what the vocabulary declares | **authors one** — the only question it can phrase |
| `Affordances` | what one action comes to in one world | **authors none, runs the action's** |
| `Afforder` | what is worth asking, and how often | **neither** |

The middle row is the sharpest and was a surprise: `Affordances` writes no query text at all. The
select it runs is `orexis:available`, declared by whichever package ships the action, bound and
answered here. **That is the clearest statement of why an affordance is not an action** — the row
does not come from a query this tree wrote, it comes from a query the action carries. If this file
ever authors a select of its own, a new way of acting has stopped being a node in a new directory
(#207) and become an edit here.

# What the split bought, measured

Templates are public and timeless; a world's rows are neither. They were read together, once per
node, because one file held both questions. Counted on `world/hanoi`:

| | before | after |
|---|---|---|
| two-disk solve | 6 reads of the action list | 1 |
| three-disk solve | 18 | 1 |

**No claim about wall time**, and the omission is deliberate: the list is eleven rows and a pass is
dominated by the canonicaliser (#667), so the honest statement is seventeen fewer queries per
three-disk solve and nothing about the clock. Measuring that properly means alternating sides in
one session on this bench, and the expected effect is below the noise it would have to clear.

# How many afforders an agent has, and the first answer was wrong

One. The sovereign asked, and counting gave three: one per search pass, one per deliberator call,
and one per remembered candidate — `on_menu_now` builds it inside the loop over them.

The cause was a memo. The service held the templates and the abouts so it would ask once, which
made it STATEFUL, and a stateful service is a thing every caller has to keep — so every caller
kept its own and the memo bought nothing across them. **A collection knows when its own answer
goes stale; a service does not**, which is the whole of why the memo was in the wrong place.

It is on the stores now, where each has an invalidation already: `Actions` remembers against the
belief store, which forgets on every write (`Store.remember`, #552 — added for this exact
symptom, the same text fetched per fork by callers none of which could have answered
differently); `Desires.abouts` remembers against the projection, and a rebuild IS the
invalidation, since a rebuild is what every write that could change the answer already triggers.
Measured after: a three-disk solve asks for the templates eighteen times and queries twice.

The service is stateless and the agent holds ONE.

**And then the same question again, of the other collection.** The planner was still CONSTRUCTING
an `Affordances` — three times, once per node — because the world was in its constructor and the
world is the thing that moves. A world is part of the QUESTION, *what could I do there*, and not
part of what a collection IS. It is the first argument of the ask now, the agent holds one of
every collection and one afforder, and a search builds nothing but a door.

# The class is back, and this time it exists

There was an `afforder.py` that held a model, a collection, and a question belonging to the desire
modality, with no class in it at all — which is what *"there is no such class inside"* meant when
the sovereign first asked. The answer turned out not to be "there should be no afforder" but "the
afforder should be a service", and it could not be one while it also held its own query texts.
Its page came back for the same reason, one change after being folded away: the fold was right for
a service that did not exist and wrong for one that does.

# Seams left open

- **The menu's word is still ambiguous.** `Actions` is what `menu.md` describes and now has a
  class, but the WORD is used for the templates on that page and for the rows on eight others.
  That is #686 and it is prose rather than code.
- **`Actions` carries two columns of a node with many.** What an action makes true, costs, and
  comes to as steps are read by whoever needs them, from the same node. Whether those should
  gather onto the model is a question for the first reader that wants three of them at once; a
  model carrying every column makes every reader of one depend on all.
- **Nothing hoists the relevant set.** `only` is computed per ask and thrown away, where the
  templates and the abouts are now held for the pass. It is a frozenset intersection rather than
  a query, so it was not worth moving with this change.
