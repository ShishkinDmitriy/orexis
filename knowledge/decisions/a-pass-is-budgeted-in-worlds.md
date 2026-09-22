---
type: Decision
title: A pass is budgeted in worlds, not in depth
description: >-
  #494's decision. The ceiling on what one deliberation may spend is `deliberation:budgetWorlds`, a
  count of possible worlds the pass may fork, stated by the sovereign in the agent's beliefs
  like a patience, bounded by a kernel shape, defaulted by the engine where unstated; the
  search stops there and answers with its best. `MAX_DEPTH` is gone. Refused: keeping a depth
  beside the budget (two ceilings on one thing, and the second bounds nothing a plan needs);
  a budget in seconds (a pass would answer differently on the same world from one run to the
  next, and every test of the search would become a race); demanding the pick of every agent
  as the patience is demanded (a missing patience makes a commitment meaningless, a missing
  budget merely leaves the ceiling where the kernel put it).
status: accepted
timestamp: 2026-09-01T23:30:00Z
---

# A pass is budgeted in worlds, not in depth

`Planner.MAX_DEPTH = 2` was, by its own comment, *the ceiling on how much compute a pass may
spend* — a constant rather than a belief, because an agent that could revise it could spend an
afternoon planning while its plant died. Both halves of that were right and one has moved.
The ceiling must not be the agent's to move; but depth stopped being a ceiling on compute the
day the search became best-first ([#492](https://github.com/ShishkinDmitriy/orexis/issues/492)).
Under breadth-first, bounding the depth bounded the tree. Under best-first the open list
follows the want's estimate as deep as it likes, and a depth bounds only how far ahead a plan
may reach — which nothing needs, since a plan is re-derived every pass and only its head is
acted on.

What a pass spends is worlds: forks in the [imaginarium](/domain/imaginarium.md), each a
measured cost per mutable-slice size
([measure-the-search](/runbooks/measure-the-search.md)). So the ceiling is stated in that unit,
`deliberation:budgetWorlds`, and the search counts what it forks and stops there. It is anytime by
construction — `best` and the achievers are kept as it goes — so stopping loses nothing
already found, and a spent budget answers with the cheapest achiever in hand, or the nearest
world, or the finding that nothing helps, exactly as an emptied open list does. The levers a
spent budget never reached are written in the trace as such, so a reader sees "the pass could
not afford this" and not "this was weighed and lost".

The pick is authored where the patience is, in the agent's own beliefs, and read where every
pick is read, by the search. The agent does not move it, for the reason the constant gave.
`orexis:BudgetShape` holds a stated one to a single integer inside constitutional bounds.

# What was refused

**A depth kept beside the budget**, as a horizon on plan length. Two ceilings on one pass,
and the second bounds nothing a consumer needs: no reader of a plan acts on more than its
head, and the `Within` scope already refuses a step that lands after the want lapses, which
is the only horizon a plan has been shown to need.

**A budget in seconds.** It is what a dying plant cares about, and it was refused for what it
would do to every answer: the same world, the same want, the same pass would answer with
more or fewer steps depending on the machine and its load, and each test of the search
becomes a race. A world's cost per fork is a measurement, in the runbook, so a sovereign who
knows the world can state seconds' worth of worlds; the pass stays reproducible and the
sovereign keeps the unit that means something. A time cap as a second guard, for the day a
mutable slice grows past what the runbook measured, is a seam below.

**Demanding the pick of every agent**, as `orexis:KeeperShape` demands a patience of every
region want. A missing patience makes a commitment meaningless; a missing budget leaves the
ceiling where the kernel put it, sized for a plant. Every plant world would have had to
state a number it has no opinion about. The shape bounds what is stated and demands
nothing.

# Amended 2026-09-06: a resumed pass is charged for new worlds only

Since #553 a pass may begin with worlds kept from the pass before, re-rooted on the present.
The budget counts what THIS pass forks; the kept worlds cost nothing again, since the store
already imagined them and the trace says how many there were (`deliberation:keptWorlds`).
The ceiling is unchanged and still one number: a second ceiling on the cone's size was
weighed and refused for the reason this record refused depth — it would bound a thing
nobody needs bounded, since a cone is dropped whole the moment the present leaves it.

# Seams left open

- **A plateau spends a deeper budget.** A pass that answers NOT_BETTER inside its budget has
  found a plateau — hanoi's optimal path moves away from the goal — and the answer is to
  escalate: a larger budget, then Consulting, which is the amortisation tower the intention
  records describe. Not built; the budget is one number.
- **Metering.** The [wallet](/domain/wallet.md) is designed to pay for thinking and does not
  yet; a pass's worlds are the unit it would be charged in, and the two words meet there.
- **A time cap beside the count**, for a slice large enough that a world costs seconds. Not
  until a world shows it.
- **A remembered plan seeds the bound** ([#469](https://github.com/ShishkinDmitriy/orexis/issues/469)):
  re-simulating last pass's plan costs a world a step and gives a bound before the first
  fork, so a small budget prunes from its first node rather than its last.

# Issues this closes

[#494](https://github.com/ShishkinDmitriy/orexis/issues/494). The depth-as-mandate seam in
[the-domain-is-a-plug-in-and-hanoi-is-the-proof](/decisions/the-domain-is-a-plug-in-and-hanoi-is-the-proof.md)
is taken here, in worlds rather than depth.
