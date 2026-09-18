---
type: Domain Concept
title: Effect
description: >-
  What taking an action would MAKE TRUE, stated on the action's own node in SHACL-AF's words
  — a construct for what it adds, and `orexis:retracts` for what it
  removes, which is ours because the standard has no deletion. It is what turns an affordance
  row from "this is available" into something a planner can reason about, and it carries the
  timing (`orexis:landsAfter`) so that
  the number a planner predicts and the number a keeper later verifies cannot be two numbers.
  Most means have no effect, and that is an ordinary answer.
---

# What it is

An [affordance](/domain/affordance.md) row says a [lever](/domain/lever.md) is available. It does
not say what pulling it would achieve — and a desire that is a shape needs exactly that, because
matching a desire to a lever means asking what the lever would make true.

So the effect sits on the [action](/domain/action.md) node itself, beside the availability
query and the taker, loaded into the action graph at genesis. The vocabulary is SHACL Advanced Features' — `sh:construct` for the query yielding
the triples applying it would add. One
term is ours, `orexis:retracts`, because the standard has none: SHACL rules exist to add entailments,
so nothing in it can say a thing stops being true.

**The engine is not SHACL's.** pySHACL will execute a `sh:SPARQLRule`, but only forward-chaining
to a fixpoint, mutating the graph — and a plan step is one rule against one hypothesis, which is
the opposite shape. A stored `sh:construct` is just a query, and this project already has an
engine that runs queries.

# Retraction is not decoration

The sensed graph **upserts** — one observation node per (subject, property), DELETE then INSERT
— so an effect predicting a reading that left the old one standing would put two results on one
node. A shape asking whether ANY reading sits past an edge would then answer about the reading
the dose just replaced, and a planner would reject the plan that works.

Order matters for the same reason: retract, then add. Observe's construct reuses the very node its
retraction names, so done the other way round the addition is removed by the retraction meant to
precede it and the possible world comes back holding neither reading.

# Two rules ship, and the pair is instructive

- **Observe** carries the current value forward with a new `sosa:resultTime`. Looking changes what
  you KNOW and nothing else, and the tempting error — predicting a reading inside the region,
  since that is what the agent wants — would teach a planner that a thirsty plant can be watered
  by looking at it.
- **Actuate** predicts the post-dose reading, which is the case that decided the whole shape of
  this: **opening a valve adds no triple.** It changes a number a later observation reports, and
  only a template that can predict the number can say so.

**Acquire is the third and it is honestly optimistic**: an agent does not control whether it wins,
so the rule predicts the world in which the bid clears. That is what planning does everywhere — a
STRIPS schema states what an action achieves, not what it achieves times a probability — and the
uncertainty lives in re-planning and monitoring, which is where this project already puts it.

# The prediction has ONE source, and it is enforced rather than intended

`litres / conversion` was already written twice in Python — the bidder sizing its expectation, the
actuator sizing its self-dose — before anything asked what a dose would do. Since #510 the actuator
computes nothing at all: what the rule predicted rides on the [step](/domain/step.md) as
`progression:predicts`, and the keeper holds the world to that, so what a planner uses to decide
whether dosing helps IS what the world is later held to, by construction rather than by discipline.

Two predictions would mean an agent planning against one future and verifying against another, and
the failure would look like a device lying rather than like arithmetic disagreeing with itself.

**And what it predicts is a [band](/domain/band.md), not a number (#579).** A dose reaches the
region; a bought lot reaches the region; the rule says which class the reading becomes and states
no arithmetic at all. How much to pour or to bid for is computed when the step is TAKEN, by the
actuator or the bidder from the reading in hand — which is where the conversion is read and where
[review](/domain/review.md) revises it. The search is never asked how big an act would be.

Two things follow, and both are the ruling's cost taken knowingly. A dose reaches the region from
below it or from inside it; **from above, more water helps nothing**, so the rule declares the
band the reading is already in and the step is pruned as a world already seen. And a **reading
must stand** for either rule to fire: with none, a rule yielding a reading would fabricate one,
and a world that knows where the pot is scores better than one that does not — so a content plant
would buy water to find out how wet it is. A look comes first, as it always did.

# When it lands, and how you would know

Two more terms hang off the rule, for the same single-source reason one axis over.

`orexis:landsAfter` is a SELECT yielding `?seconds`: how long until the WORLD CHANGE completes. A
query and not a number, because the duration is a function of the act — a two-litre dose holds a
valve open longer than a half-litre one. **Zero is a real answer** and the honest one for a look.

**There was a second term here, and it is gone.** `orexis:confirmedBy` named the route by which an
effect becomes knowable — by construction, by report, by observation, or not at all — and every
shipped effect answered *by observation*, so it discriminated nothing. The planner once read it to
decide which acts end a plan, which meant every lever ended one and the search never reached its
second step; that reading was removed, and nothing replaced it. A term stated on every action and
consulted by no one is annotation
([a-term-nobody-reads-is-annotation](/decisions/a-term-nobody-reads-is-annotation.md)).

The distinction it drew is real and the prose keeps it: a **constitutive** effect is true by
saying so — a claim issued, a round opened — and a **causal** one waits on the world. Conflating
them produces code that verifies an agent really did write down what it just wrote down, and
leaves a planner waiting for a confirmation nobody will send. What follows from that today is
where a watch is opened at all, which is each actor's own decision rather than a lookup.

# Most means have no effect, and that is fine — unless somebody's menu offers it

A lever whose consequences nobody has written down still works. What it cannot do is be
simulated, and simulating is now the only way anything gets decided — so the absence is an
ordinary answer to every caller (treating it as an error would make shipping a package a
two-file obligation) and a REFUSAL at exactly one place: `orexis-validate` will not pass a
world in which such a means puts a row on some agent's menu. Most means never do.

What a search must NOT do is conclude from part of the affordances. A plan that passed over any lever is
marked partial and defers, because the lever it could not simulate may be the one that works.

# How long it takes, asked by two readers

`orexis:landsAfter` is asked with a size and asked without one, and the difference is who is
asking. The KEEPER asks when the step is taken, with the litres the actor sized from the reading
in hand, and gets how long the valve will actually be open. The SEARCH asks about an act nobody
has sized — `$litres` is bound at nothing since an effect declared the band and not the number —
and used to get NOUGHT seconds, so a dose landed instantly in every imagined world and a
[Within](/domain/desire.md) want's room refused nothing.

Unsized, the rule answers the CEILING: the longest that valve can be open, whatever the actor
decides to pour. **Over-estimating is the safe direction for a deadline** — it refuses a plan
that might be late, where an under-estimate accepts one that will be — and it is the opposite of
the direction an admissible cost estimate must take, which is why the rule states it rather than
the kernel assuming it. The honest full answer is a RANGE, nothing to the ceiling
([#596](https://github.com/ShishkinDmitriy/orexis/issues/596)), and the other end waits for a consumer.

# And what the world does unaided

An effect is what a LEVER makes true. A [drift](/domain/prediction.md) is what the world makes
true while nobody pulls one — `sensing:Drift`, declared by the package that owns the physics,
in exactly this grammar: a construct, a retraction, and `$elapsed` in place of a taker.
`water:Drying` is the first, and it reads `water:driesPerDay`, which every plant has stated
since #164 and nothing in planning had ever read.

**It is run by sensing and read by the search as a prediction** (#643,
[the-drift-is-sensings-and-its-result-is-predictions](/decisions/the-drift-is-sensings-and-its-result-is-predictions.md)).
After every reading sensing runs each drift at the horizons its package lists beside it
(`sensing:atHorizon`), the next reading's window first, and writes one prediction per horizon,
a graph holding during its window; a premise a drift reads that moves between readings — a
debt in the ledger, a forecast — tells `orexis:repredict`, and sensing predicts again. The
search reads the prediction holding at a node's instant, the predicted reading standing in for
the one the world holds, except a key the plan itself changed — changed as the signature
reads it, so a look, whose diff nets to nothing, leaves the prediction standing: the plan's
branch beats the do-nothing branch, and no rule that knows a rate runs inside a pass. What the world does after
a step is not simulated in the pass; it is predicted once the plan is adopted, from the step's
band, which is the seam the record states.

**Two drifts, because a reading is known two ways.** One subtracts a rate from a VALUE, which
a reading the agent observed carries. The other crosses a BAND, which is all a reading an effect
predicted says (#579) — and how long that takes is the band's own width, from the facets genesis
minted it with, over the rate the world states. Nothing new is written down for it: a world that
re-ranges its bed or re-states its physics changes the answer by changing what it already says.

**A second package drifts the same way.** The climate package moves a bed's air toward what
surrounds it — one `climate:Diffusion` node per property, naming what it follows and how
fast — in the water package's two forms, reading the surroundings from whatever holds at the
instant the prediction is for
([a-drift-toward-the-surroundings-is-one-link-and-no-physics](/decisions/a-drift-toward-the-surroundings-is-one-link-and-no-physics.md)).

**And a third reads a record where the others read a rate.** The market's `market:Draining`
drains a vessel by the debts on it as their windows open (`market:owedFrom`): the level at a
future instant is what is held less what is owed to holders whose windows have opened by then
([a-claim-is-water-at-a-time](/decisions/a-claim-is-water-at-a-time.md)).

**The crossing is the first prediction at which the root reads unmet.** No drift says WHEN any
more: the instant a want with an `orexis:holdsAt` is derived at is the start of the earliest prediction
whose world violates the root's own met-test, asked through the door at each window's start
(#643). A prediction typed with the region band and the one below reads unmet, so the safe
direction (#633) falls out of the bands, and the resolution is the package's ladder — a pot
below its floor sixteen hours out is foreseen at the start of the window that reaches the day.

**And every band the reading may be in.** A drift types the reading it predicts with each band
its width reaches — the spread the world states beside the rate and the instrument's noise,
inside the rule's own text, read against the band definitions' facets — and no number
leaves it (#642). Sensing writes what the drifts predict as [predictions](/domain/prediction.md)
at the horizons a package lists beside its drift (`sensing:atHorizon`).

**And a plan is minutes where a band is days**, which says where this pays. The loner's region
takes six and a half days to cross; no plan reaches that far. A second drift once said what a
reading known only by its band does — the world a step reaches, where no number is left to
subtract from (#612) — and it fired inside a search between steps; since the search reads
predictions and runs no drift (#643) the only reading a drift is ever run from is the one the
instrument made, which carries a number, and the band drifts were struck as dead. What wants
the crossing time is the DERIVATION of a want met at that instant — *when will this leave its
region* is the same number read from the other end
([#619](https://github.com/ShishkinDmitriy/orexis/issues/619)), and it is what lets an agent
act before the crossing rather than at it.

**And a step that takes time makes a look somewhere new**, which is not a defect. A look's world
used to be its parent's, so cycle detection discarded it; if an hour passes inside the step, the
world moved while it ran and the look reaches somewhere genuinely different. Every shipped world
is unaffected, `sensing:Observing` landing at once — and where a step does take time, that is
what [#590](https://github.com/ShishkinDmitriy/orexis/issues/590) is for.

# An outcome the world decides

A dose reaches the region because water wets soil. Opening a **vent** reaches whichever band the
outside is in: the same act warms a bed on an afternoon and chills it on a night, so its rule
reads what is on the other side and declares the band that implies (`world/greenhouse`).

It is the first shipped effect whose declared outcome depends on a fact the agent cannot move,
and that is exactly what makes it expressible. A rule may read the OUTSIDE as a number even
though a possible world states what a reading IS rather than what it measures
([band](/domain/band.md)): no lever of the agent's writes it, so it is the same number at the
root of a cone and at every leaf — a constant of the plan rather than something a step might
have changed. What the plan CAN change, the rule reads as the band it is.

**The seam it left was time, and it is closed.** A rule is told when its act completes
(`$lands`, #588) — and, since #589, it is ASKED about the world holding at that instant: the
search hands the rule whatever graphs hold then, so a vent opening after dusk is judged against
the dusk a forecast states rather than against this afternoon. The rule learned nothing about
time to get there. What changed in it is one line: the outside is no longer read from `$state`,
because a step changes the bed and never the weather, so the outside is not a node's to hold —
it is whatever holds at the instant asked about, which is the sensed reading now and a forecast
later. See [a-graph-holds-during-a-stretch](/decisions/a-graph-holds-during-a-stretch.md).

The paragraphs below are how it stood before, kept because the argument for `$lands` is the
same one and the distinction between the two instants survives it.

**The seam as it was, and half of it closed first.** The outside at the moment a vent is
opened is not the outside at the moment the plan was made, and a plan that opens a vent after
dark is simulated against the afternoon. A rule can now be TOLD when its own act completes —
`$lands`, bound by the search from the pass's clock and the path's landings (#588), which is
also what stamps the reading a construct predicts, since that reading exists when the act
lands and not when the plan was made. What is still missing is what the outside WILL BE then:
a rule that can ask the question has nothing to read, because nothing in this agent's world
states a future reading. That is the [forecast](/domain/reading.md), #589, and until it exists
the world answers otherwise, the keeper's verdict says so, and the next pass replans — the cost
is a wasted step.

**And it is one instant only until [#596](https://github.com/ShishkinDmitriy/orexis/issues/596)**, which gives an act a DURATION rather than a
landing alone and a possible world the interval it holds over — each a range where it is not
known exactly, since a pour takes between nothing and the device's cap over its rate. What a
rule is told is then an interval, and a predicted reading is stamped with one.

**One instant is bound and the other is not**, and the market says why they are two. A rule's
WHERE describes the conditions the act is TAKEN in — a bid's own premise is that the round is
still open — while its construct describes the world the act REACHES. A bid lands the window
plus the pour after it is placed, so binding one instant to both would make every bid predict
nothing, the round having closed by the time the water arrives. So a WHERE still asks `NOW()`,
which is the real clock rather than the node's, and a rule that needs the instant it is taken
at cannot have it yet.

**The answer to that is not a better instant**, and it is [#598](https://github.com/ShishkinDmitriy/orexis/issues/598): what a WHERE asking `NOW()`
wants is a FACT — that the round is open — and time is another sense, writing such facts at
the belief-revision seam the way any other sensed change arrives. A rule reading a triple asks
no clock, in a simulated world or a real one, which is the whole class of wrong-clock question
gone rather than answered.
