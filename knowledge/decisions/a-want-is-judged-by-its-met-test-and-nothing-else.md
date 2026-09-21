---
type: Decision
title: A want is judged by its met-test, and nothing scores a world by degree
description: >-
  Three things were called urgency and none of them was the same question - a rank across
  wants, a capability's graded measure of how badly one want was unmet in a given world, and
  how pressing a single reading was. The sovereign struck all three. What replaces the first
  is nothing, because `Deliberator.pursued` plans for every want it is handed and the rank
  only ever decided which was searched first; what replaces the second is the want's own
  met-test, which every want has by construction and which the judge was already held to;
  what replaces the third is a fact about progression - a step standing or an expectation
  open - because the cadence was always for sensing frequently after acting and waiting for
  feedback. The search loses its gradient and keeps its ordering, since `orexis:estimates`
  is cost-to-go and untouched.
status: accepted
timestamp: 2026-09-21T18:00:00Z
---

# Three questions wearing one word

The sovereign's thesis, running through this whole stretch of work: *it is just juggling of
words*. Urgency was the clearest case left. Three things carried the name and no two of them
were the same question.

| | what it answered | who read it |
|---|---|---|
| `Want.urgency` | which want is worst | nothing |
| `Agent.desire_urgency` | how unmet one want is in one imagined world | the planner's best-first ordering; sensing's gaps and freshness; the cadence |
| `sensing:urgency` | how pressing one reading is | the cadence |

They were not strengths of one scale, which is the thing
[shall-must-and-may-are-not-strengths-of-one-scale](/decisions/shall-must-and-may-are-not-strengths-of-one-scale.md)
argued about the SOURCES of desire and which turns out to be true one level down as well.

# The first had no reader at all

`Deliberator.pursued` is `[(want, self.propose_for(want)) for want in self.agent.pursuing()]`.
Every want it is handed is planned for. So the hottest-first order decided which was SEARCHED
FIRST and nothing else — and four packages each computed a number its own way to produce it:
the ledger a fraction of each redeem window (Python, because this engine will not divide two
durations), hosting a flat 1.0 for every call, sensing its declared measure, and the kernel a
fraction-of-stretch for a want holding at an instant.

What would actually rank a thirsty fern against an overdue debt is what their plans cost and
how long they take. That is the search's answer and it arrives after the search, which is the
sovereign's own sentence: *urgency we can estimate only after planning and plans durations.*

**The order was load-bearing where the field was not**, and that is the part worth keeping.
Four test fixtures took `next(g for g in pursuing() if g.observed_property == MOISTURE)` and
got the STAKE, because a region want sorted ahead of the freshness want about the same property.
Unsorted they get whichever comes first. Three were found by grepping the field; the fourth
was found by CI, in a file that never mentions an urgency.

# The second was a second judgment path

A want carries a met-test. The judge is held to it, the derivation mints the want because it
read unmet, and `violation.unmet_select` compiles it to the select whose rows are its
violations — which is what
[a-verdict-the-search-reads-is-a-query](/decisions/a-desire-is-a-shape.md) bought. And beside
it the search asked a capability a DIFFERENT question: on a scale from 0 to 1, how bad is this
world? Sensing answered from `measures.ttl`, a declared SPARQL measure per kind of want,
evaluated against whichever world was being judged.

Two paths to one verdict is the shape this repo keeps removing. `_urgency_in` is `0.0 if
self._met_in(node, judgment) else 1.0` now — a sign flip over the met-test rather than a
judgment of its own — and its three branches were already binary before the capability was
asked at all.

## What that costs, stated rather than discovered

**The search no longer sees partial progress.** A dose too small to bring a reading inside its
band scores exactly as standing still does. The planner's own docstring made this argument
FOR the measure, and it was right: *"a dose that moves a fern from 0.30 to 0.44 leaves the
same single violation it started with, so a planner scoring by count would refuse every dose
too small to finish the job — and refuse the second one for the same reason, having never
taken the first."*

What survives it is that a search CHAINS. A repair is found where the plan reaches the met
state, by one step or by several, and the frontier is still ordered — `orexis:estimates` is
cost-to-go and nothing here touched it. What is genuinely gone is the pruning the slope
bought, which
[a-prune-is-only-as-good-as-when-its-bound-arrives](/decisions/a-plan-is-a-path-of-graph-diffs.md)
measured at sixty percent of the courier's forks.

**Measured before it was believed.** hanoi, courier, the greenhouse, the planning suite and
the dealer's two-step all still plan. That is evidence and not proof: the worlds this repo
ships are ones whose repairs reach the met state in one or two steps.

## And it is STRICTER, which was not expected

A toy lever in `test_deliberation` wrote a new observation without retracting the one it
replaced, leaving the world claiming 0.30 AND 0.50 for one key. The measure read the newest
and called it repaired; the met-test sees the violation and does not. The fixture was leaning
on the measure's leniency, and every real effect declares `orexis:retracts` for exactly this
reason. One judgment path is a stricter judgment path.

## Three second-order faults fell out, and the third is an issue

- **`gaps_of` read the aim through the desire PROJECTION**, so a re-pick did not move the diff
  until a rebuild. The declared measure read `$picks` live, which is why nothing had noticed.
  It reads the belief base now.
- **Freshness read a horizon the agent recomputed.** Sensing already MARKS a reading
  `sensing:staleSince` when its deadline lands, and *every reader asks the triple* — so the
  want's state reads the mark rather than doing the arithmetic a second way.
- **And the planner's met-tests come off the projection**, which is the same root cause a
  third time and is filed rather than fixed here (see the seams). All three were invisible
  while a measure that read the belief base live answered first.

# The third was never about a want

`sensing:urgency` paced the board: `slow + (fast - slow) * urgency`, so a board watched harder
the nearer a reading sat to trouble, with a one-step lookahead on the predicted value
(tighten-only) so a window could not open just before a trend crossed.

The sovereign, asked: *the idea with cadence was to sense frequently when we executed
something and wait for feedback. So it is more progressing concept. Some Attention.* That is
a fact about what is in flight, not a degree — and the rule was already half written inside
`reading_urgency`, which returned 1.0 while the keeper held an open expectation.

So the cadence asks the keeper and nobody else: a step standing (patience-bounded) or an
expectation open. Both halves it used to merge fold into that one question, including the
market's — a claim held is a step standing to present it, and `Keeper.standing` takes the
action as an OPTION, so sensing asks without naming a word of the market's. The hook is gone.

**The opening burst survives as a fact.** An agent with a region want and no current reading is not
calm, it is blind, and the first intention is always to look. That used to arrive as "not
knowing is maximally urgent" — the graded answer standing in for something that was never a
degree.

**A dry pot nobody is doing anything about is now watched slowly.** That reads as a regression
until it is said out loud: no amount of looking changes a number.

# What was removed

`Want.urgency` and its four producers; `Agent.desire_urgency` and `Module.desire_urgency`;
`orexis:desireUrgency`; sensing's `measures.ttl`, `_declared_measure` and `_DECLARED_MEASURES`;
hosting's measure; bidding's contribution to sensing's hook; `choir.urgency` and
`sensing:urgency`; the #133 trend bound; and the `orexis-validate` gate that refused a world
holding a region want nothing could weigh — which existed because an unmeasured want scored a flat
1.0 everywhere, and has nothing left to refuse now that every want is judged by a met-test it
has by construction.

`Region.urgency` became `Region.distance`: it was the live arithmetic, then a reference the
tests held the declared query to, and it is live again with one reader — the diff sensing
reports — anchored at the aim rather than the centre.

# A call had to grow its own met-test

Hosting answered "is this call met" through the choir, and it was the LAST reader of a measure
— the reason removing one reached the market at all. It read both the graph rounds stand in
and the graph a plan imagines them into, which is what let a host plan to open a round.

A call carries `orexis:unmetWhen` now, exactly as the debt did in
[#635](/decisions/a-package-owns-its-namespace.md): a select whose rows are the venue having no
round, in a `market:CallsGraph` the host classifies when it writes the call. It names no world
(#666), so the runner's graph list answers for both the standing round and the imagined one.
Writing one asks for the desire projection to be rebuilt, as the ledger does when it writes a
debt — a capability that asks for a derivation is not minting.

# Seams left open

- **What Attention properly is, is not decided here.** This change unlinks the cadence from a
  measure and gives it the two facts that were already in the code. Whether it should also
  follow a plan's shape — watch what the next step reads, pace by a step's predicted landing —
  is the sovereign's, and was explicitly deferred.
- **Nothing ranks wants, and one day something should.** The sovereign's sentence names the
  replacement — what the plans cost and how long they take — and that is a change to make when
  a society has more wants than it can serve at once, with the plans in hand to compare.
- **The trend bound is gone and its case is not.** #133's hazard was real: a sleep granted on
  the present can begin moments before a value crosses. Nothing watches for that now.
- **The planner compiles a want's met-test from the desire PROJECTION**, so a want minted
  without a rebuild falls through `_met_in` to the row's live state, which is the same in every
  imagined world. The measure read the belief base live and was asked first, so it answered
  for those worlds and the gap was never reached; with one judgment path it is load-bearing.
  Every production writer already rebuilds, which is what makes this a debt rather than a
  defect — [#766](https://github.com/ShishkinDmitriy/orexis/issues/766), and the fix is the
  one this area keeps taking: read the store, not the projection.
- **`deliberation:wouldReach` keeps a decimal range** holding two values. Narrowing it to a
  boolean is a vocabulary change nothing needs yet, and the range is the ends of the scale it
  used to span.
