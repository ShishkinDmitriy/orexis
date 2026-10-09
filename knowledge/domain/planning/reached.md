---
type: Domain Concept
title: Reached
term: http://example.org/orexis/planning#reachedWhen
description: >-
  A want is reached where its own met-test reads met in the ground it is weighed in, and goes. A
  desire may hand its wants a reaching test narrower than the one it mints by - planning:reachedWhen -
  so a reading straying across a bound on its noise mints one want and withdraws none until it clears.
---

# What it is

A [want](/domain/planning/desire.md) is **reached** where its met-test reads met in the ground it is
weighed in: the present, for a want in trouble now, and the ground holding at its instant for one
minted at a foreseen crossing. A want reached goes once no plan is walking it, as the
[runtime](/domain/kernel/runtime.md) says, and the search judging a possible world asks the same test
of it.

Which met-test a want carries is its desire's to say. Unsaid, the desire's own, narrowed to the
want's instance. Where the desire also points with `planning:reachedWhen` at a shape — its
**reaching test** — the want carries that shape instead, narrowed the same way and written under
`planning:metWhen` on the want, so a want is still judged by its met-test and by nothing else; what
changed is which test it was handed.

# Two tests, one each way

The desire's met-test **mints**: where it reads unmet, at the present or at an instant foreseen, a
want is minted as it would be with no second test. The reaching test **keeps**: a standing want under
the desire is implied while it reads unmet where the want was weighed, and goes once it reads met
there. Neither remembers anything. Which side the agent was on is the want's existence — minted, it
is held to the reaching test; not minted, only the met-test can mint — and the sides both tests read
are what sensing's rules concluded of the reading alone
([a-belief-is-crisp-and-an-estimator-may-reason-with-probability](/decisions/a-belief-is-crisp-and-an-estimator-may-reason-with-probability.md)).

Under a reaching test a want's stretch is open. The desire's weighings say where its met-test lifts,
and a forecast lifting a dry bed back above its floor and no further lifts it there while the want
is still unreached; a want whose period closed there would stand searched by nobody, and stand again
under the same name at the next dip. What ends it is the want reached, which no ground of the
desire's says.

# Which range mints and which reaches

```turtle
:the_bed_is_comfortable planning:metWhen :comfortable ; planning:reachedWhen :comfortable_again .
```

The greenhouse's met-test reads a soil reading `sensing:below` a range the bed has as its operating
range — `( sensing:below [ sh:inversePath ssn-system:hasOperatingRange ] )`, walking back from the
range to whatever holds it as one. Its reaching test reads `sensing:below` of any range, which is
every shipped desire's test before this word, and the [narrower range](/domain/kernel/narrower-range.md)
is among them. So a dry bed is wanted from the operating floor and reached back inside the narrower
range; a bed stating no narrower range is reached at its operating range, as it always was; and a
world stating no reaching test mints and withdraws exactly as before. A dose's effect writes
`sensing:inside` of every range its reading was below, the narrower one with them, so the world a
plan reaches reads the want met; its command aims at the operating range's middle, inside both.

# Why a second range and not a margin

A margin — the probe's noise stated on the sensor, the narrower bound derived from it — was the other
way to say where a want is reached, and it is refused. Derived by planning, it is a sensing word in
planning's mouth; derived by sensing, it is a second set of sides under words of their own beside
`below`, `inside` and `above`, which every met-test, effect and drift would then have to choose
between. A range the world states reuses all three sides, prediction's crossings and the effects
untouched, and its two numbers are where the world says what it measured of its instrument.

# An aversion

A desire minting by an avoided state (`planning:unmetWhen`) may state a reaching test too, and it is
a shape: the complement of a wider avoided state, said positively — for a reading, no reading above
any range the subject states, as plain as any met-test. A reaching test authored as an avoided state
would need a word of its own and was not built: what an avoided state names relationally — two tanks
on one stand — is discrete, and nothing about it flips on noise.
