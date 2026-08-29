---
type: Decision
title: A repository is not a service, and Component was both
description: >-
  `Component` covered nine pages that split cleanly in two — the belief base and the imaginarium
  passively hold data scoped to one agent, while the deliberator, the revision seam and six
  others hold logic. The tell was in the type's own definition, which named the belief base and
  the imaginarium as its examples: both are repositories, so the word meant the passive half
  while being applied to the active one. Decided that `Service` and `Repository` are the two
  types, and that `Component` folds rather than surviving for whatever is left.
status: accepted
timestamp: 2026-08-29T00:00:00Z
---

# What was wrong

`Component` meant *a part of the implementation*, and nine pages carried it. Sorting them by
what they DO gives two groups and no third:

| | pages |
|---|---|
| holds data, passively, scoped to one agent | [belief-base](/domain/belief-base.md), [imaginarium](/domain/imaginarium.md) |
| holds logic | [actor](/domain/actor.md), [choir](/domain/choir.md), [clearing](/domain/clearing.md), [deliberation](/domain/deliberator.md), [executor](/domain/executor.md), [gateway](/domain/gateway.md), [revision](/domain/revision.md) |

**The type's own definition gave it away.** It read *"a part of the implementation — the belief
base, the imaginarium"*, and both examples are in the first row. The word was being explained by
the passive half and applied to the active one, which is why nothing it said helped an author
choose it.

**And a page named its own type in prose**, which is the signal the last split turned on:
[imaginarium](/domain/imaginarium.md) opens *"The store a plan thinks in"*, exactly as `auction`
opened "an auction is a PROCESS" and `onboarding` "the PHASE between".

# What is decided

**`Service` and `Repository`**, in the sense
[a-repository-is-passive-and-a-service-holds-the-logic](/decisions/a-repository-is-passive-and-a-service-holds-the-logic.md)
settled for the code: a repository wraps a store, scopes it to this agent and exposes `read()`;
a service holds the logic. The types now name the layering the mind already has.

**`Component` folds.** The rule is that a type falling to one member is a type to fold back, and
this one falls to none: both halves are named, and its stated examples were the repositories.
Keeping it for whatever might not fit either word would be keeping a word that means *neither of
the two things this is*, which is not a kind of thing.

**The choir is a service**, and it is the only one worth arguing. It is the mechanism by which
services ask each other — dispatch, not data — so it holds logic and belongs with the first
group. If a later page is genuinely neither, that is the moment to weigh a third type, on
evidence rather than in advance.

**Two repositories is thin, and that is the honest count.** The mind has four today — beliefs,
desires, intentions and the imaginarium — and six in the target. Only two have pages, because
the other two are already owned: [desire](/domain/desire.md) and
[intention](/domain/intention.md) state what their stores are, and a repository page for either
would be a second owner of a claim, which is the thing
`test_no_two_domain_pages_state_the_same_claim` refuses. Pointing beats extracting; the count
follows.

# Seams left open

- **The menu and history repositories have no page**, because neither exists in code — the menu
  modality's only instance is `graph/actions`, in the beliefs store, and history is
  [#311](https://github.com/ShishkinDmitriy/orexis/issues/311). When they land, `Repository`
  gains its third and fourth pages without another argument.
- **Nothing checks a page's type against the code it describes.** A page typed `Repository` whose
  subject grew logic would pass every gate. The gate that would catch it does not exist and may
  not be worth writing.
