---
type: Decision
title: A desire could be a graph, and a plan a path of diffs — the widening, mapped before it is needed
description: The sovereign's question re-derived STRIPS from inside the graph, and this
  architecture is already its degenerate case — menu rows are action schemas, the Reflex a
  depth-1 planner, intentions committed steps, verification the monitoring. The widening is
  effects on the menu row, deduced goal patterns, and a bounded Planning member; its guardrails
  are the two standing principles, and its first honest customer is the supplier's empty barrel.
status: accepted
timestamp: 2026-08-17T12:19:35Z
---

# A desire could be a graph, and a plan a path of diffs

Asked by the sovereign in three steps that are one idea: desire as a whole graph rather than
one aim fact ("now the value is this, the desired value is another"); generalised past
datatype properties to a generic graph diff; and plans whose every step is defined by what it
adds to the graph and what it deletes, so that a diff remains and a path must be found. That
is classical planning — STRIPS — lifted to RDF, and the useful discovery is that this
architecture is already its degenerate case:

| planning concept | already here |
|---|---|
| action schema: preconditions | a menu row's WHERE clause — the plumbing walk IS one |
| action schema: effects | `market:direction` — a one-bit effect ("this property rises") |
| goal state | the region and the aim — a goal over one datatype property |
| planner | the Reflex — greedy, depth 1 |
| committed plan step | an intention, lifecycle and patience included |
| execution monitoring | the verification arc — expected effect vs observed, UNMET and false-knowledge |

## What the field already settled, and what we are deliberately not taking

STRIPS is 1971, and the fifty years after it are worth naming — not to adopt, but so that the
next widening is a lookup rather than a re-derivation.

- **PDDL** is what STRIPS became: a standard language for exactly the action schemas above,
  with typed parameters, conditional effects and numeric fluents. The CONSTRUCT-per-means below
  is a PDDL effect schema written in SPARQL, and the reason to know that is
  [#268](https://github.com/ShishkinDmitriy/orexis/issues/268) — Acquire has no effect rule, so
  the planner is blind to how every plant actually acts. That is a missing effect schema, and
  PDDL has a settled answer for the shape of one.
- **HTN planning** decomposes a task into a fixed method rather than searching, which is what
  *acquire upstream, then offer downstream* IS. We arrived at it by writing the method down as
  `plan.rq`, which is an HTN method by another name. The relevance is that HTN's bound is the
  method library rather than the depth — so if depth 3 is ever wanted, the question to ask is
  whether another method should be written down, not whether the search should go deeper.
- **The frame problem** is the one to know about before it bites. Classical planning assumes
  what an action does not mention does not change; a graph diff over a store that other
  processes write does not get that for free.
  [#258](https://github.com/ShishkinDmitriy/orexis/issues/258) — cycle detection asking "where am
  I" with a number only some plans move, closed by making the signature the world's net diff —
  was a frame problem in the small, and the depth-2
  limitation recorded above (a rule's CONSTRUCTs run against the STORE, so the second step never
  sees what the first added to the WORLD) is the same thing again.

What stays refused is unchanged and is the last seam below: preconditions are SPARQL and search
is bounded by construction, never open-ended. Naming PDDL is not proposing to parse it.

So the generalisation is a WIDENING, not a rebuild — and one precedent makes "desire as a
graph" less exotic than it sounds: **SHACL shapes are already desired graphs.** The sovereign
holds them about worlds and validation is gap detection; a desiring agent holding a deduced
pattern about the world-state is the same machinery pointed at runtime.

## One formalism, a modality axis

Asked next by the sovereign, and it is the sharpest formulation of the whole idea: are these
just two KINDS of shape — one validating a world, unviolable, and one desired? Yes — and the
axis already has two points in the house, with the third legal by SHACL's own rules:

| modality | severity | violated means | who reacts | when |
|---|---|---|---|---|
| must hold | `sh:Violation` | illegitimate — refused | a human, at the gates | ratification, boot, each revision |
| should hold | `sh:Warning` | legitimate, worth noticing | an operator | the gates |
| should become | a custom severity (`sh:severity` is any IRI) | legitimate, unsatisfactory — a GAP | the agent, through its levers | continuously |

Three asymmetries keep the kinds from collapsing. WHO THEY BIND: a validating shape is the
society's, everyone held identically; a desired shape is a stake, deduced per agent — and
neither may be weakened by the agent, which is the symmetry that matters. DEGREE AND TIME:
conformance is boolean now; a want has signed distance (what urgency, bidding and the alarm
bands consume — the violation must carry its measure) and is pursued TOWARD, tolerating being
unmet while the plan runs, which is the entire reason intentions exist. THE REACTION PATH:
violation refuses, warning notes, desire feeds the menu — which is where this record's
machinery clicks in: gap, affordance rows, lever or plan.

## The guardrails, which are the two standing principles

**A desire answers to something public.** The region is deduced from stated ranges precisely
so an agent cannot want less and call itself satisfied
([the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md)).
A desired GRAPH must come from the same discipline — deduced or ratified patterns, never
privately authored goals — or the self-satisfaction loophole returns at graph scale.

**Control the derivative.** Effects flow through levers the graph authorises: every plan edge
is a menu row, precondition-checked as Acquire walks the plumbing. A plan is a path through
the AFFORDANCE graph, never arbitrary surgery an agent imagines onto the world.

## The first honest customer

Multi-step planning is not needed by anything shipped — heat beside water is two parallel
one-steps — with one real exception: **the supplier's empty barrel**. "Water fern" dead-ends
when the tank is dry; the true plan is *refill, then sell* — two steps with a genuine
dependency, expressible only with effects ("refilling makes `lotCapacity > 0` true, which is
every bidder's Acquire precondition"). The float switch the terrace build adds makes the
precondition observable. Depth 2 suffices; that is the scale to build for.

## The path in, when it is wanted

1. **Effects join the menu row** — [#127](https://github.com/ShishkinDmitriy/orexis/issues/127)
   gave direction; the row grows its add/delete template, owned where direction is owned: the
   lever's meaning states what applying it makes true.
2. **Goal patterns are deduced** from the same statements the regions come from — a region
   becomes a one-pattern goal, and plants notice nothing.
3. **A `Planning` member joins the deliberation family** — the seat the family was built to
   offer: Reflex (depth 1), Planning (bounded search, depth 2–3), Consulting above both, where
   the model PROPOSES a plan and the effect machinery VERIFIES each step's preconditions —
   deterministic-bid applied to plans: the model picks, code checks.
4. **Monitoring is already built**: an intention chain whose step's expected diff fails to
   appear is the unconfirmed-dose logic, generalised.

## Affordances are premises, so the menu is a tool list nothing registers

Asked by the sovereign on seeing the ledger and the menu side by side: why not store
affordances — can't they be added dynamically, like a model's tools? And could SHACL search
them? The three answers are one design.

**Rows are not stored because their premises are.** An affordance is a conclusion; what the
store holds is everything it is concluded FROM, so a row exists exactly while its plumbing
walk holds — cut the pipe and the row vanishes, which a test pins. A stored row could
outlive its premise silently, and "adding an affordance" would become writing a row —
arbitrary surgery, the one move refused everywhere. Which is why they ARE dynamic, and
dynamic the only safe way: add the premises (a valve, a venue, one valuation triple) and the
row appears, precondition-checked by construction. Every barrel arc demonstrated it — the
supplier's menu gained its Acquire row the day the city's consent triple existed, and no
menu was edited anywhere. Consulting's recorded contract is the runtime case of the same
move: the model's whole output is an affordance AS PREMISES, held to shapes, adopted, and
then exploited by the reflex free forever.

The sovereign pressed the claim and found its limit, which belongs here beside it: what is
dynamic this way is INSTANCES of affordance kinds — the KINDS are hardcoded branches in the
menu query, one file in the deliberation package walking other packages' terms. A new kind of
move (the Actuate rung, a fan's lever) means editing that file: a registry, in the tree whose
claim is that adding a package edits nothing. The fix is the repo's mechanic applied a fourth
time — a package ships its own `affordances.rq` beside its `rules.ru` and `review.rq`, and
the menu is the union of what the loaded packages contribute; a kind whose execution reduces
to an existing actor then ships no Python at all. Implemented as proposed (#207), with the
toy-package test proving a new KIND appears with no edit outside its directory — and #208
beside it: gaps are the choir too (`Module.notices()`), the keeper ticks on its patience clock,
and the marketless watching finally reaches the ledger the sovereign asks.

**So the menu is a tool list in the LLM sense, with two upgrades**: nothing registers the
tools — the world implies them, per agent, per stake — and the tool call is split by
deterministic-bid: the model picks the row, code computes the arguments. A row is a tool
signature (means, property, lever, direction as its one-bit effect), and the list is data on
the ask channel, not prose in a prompt.

**And SHACL is the search the modality axis implies.** The axis above already makes desired
shapes goals and validation gap-detection; the sovereign's addition completes it: a report's
violation carries the focus node, the property and the measure, and MATCHING violations to
affordance effects — rows whose good, property and direction would move the violated
component toward conformance — is plan search as shape repair. What SHACL buys over the bare
SPARQL menu: a package ships its goal-shape the way it ships `review.rq`, and gaps arrive as
structured report entries rather than ad-hoc bindings. The caution to carry with it is the
axis's own asymmetry, now load-bearing: conformance is boolean while a want has signed
distance, so a goal-shape must state its measure or the planner ranks repairs blind.

## What the sovereign settled: effects are CONSTRUCTs, and a plan is checked by simulating it

Asked after step 8 landed, in the sovereign's own framing: a goal is a single triple's value in
a range today — what if it were a GRAPH? What if the desire were *the existence of a fresh
observation* — extra triples, and a recent date? Then intentions must construct graphs, a plan
may hold more than one action, and possible worlds might be worth keeping in the store.

**The first half is already true, which is the useful thing to notice.** Since a desire became a
shape, what fern holds is not a triple: it is a property shape walking `ag:actsFor` and then the
inverse of `sosa:hasFeatureOfInterest`, demanding `sh:qualifiedMinCount 1` over a shape that
matches `sosa:observedProperty` AND `sosa:hasSimpleResult` in range. That is *there exists an
observation, of this property, about my subject, whose value is inside my region* — existence
over a reified structure five triples deep, of which the range is one leaf. Freshness adds
`sosa:resultTime` to the same qualified shape and nothing else.

What blocks freshness is only the comparand. SHACL core compares against a literal written IN
the shape, and "within the last N seconds" needs *now*, so a freshness goal has to be
`sh:sparql`. That is acceptable, and the rule it establishes is worth stating: **declarative or
SPARQL is decided per goal KIND, by whether anything reads numbers out of it.** A region is
declarative because `urgency` divides by its bounds on every reading; freshness has no distance
to divide by — a boolean and an age, both cheap — so nothing is lost by hiding it in a query.

### A means says what it makes true, as a CONSTRUCT

`effects.rq` beside `affordances.rq` and `rules.ru`: a package ships, per means, a CONSTRUCT
yielding the triples that applying it WOULD add. Chosen over two alternatives the sovereign was
shown:

- *a shape fragment the result satisfies*, matched symbolically against the goal — cheaper, no
  simulation, and limited to the vocabulary of components somebody thought to define;
- *add/delete triple patterns*, the textbook STRIPS form this record first sketched — simplest
  to reason about, and wrong for the one lever that matters most. **Opening a valve adds no
  triple.** It changes a number that a LATER observation reports, and no add/delete template
  can state that without predicting the number.

A CONSTRUCT can predict it, because this project already computes that prediction: the keeper
records `ag:expectsDelta` when it adopts an Apply, and actuation converts millilitres to a
delta. Which forces a constraint worth naming before anyone writes the code: **the number an
effect predicts and the number verification expects must come from one source.** Two sources
means an agent that plans against one future and checks against another, and the disagreement
would show up as false UNMET verdicts — the shape of the false-knowledge bug, arriving from the
planning side.

### Chaining needs no new language, because the menu is a query

A plan step's precondition is already the affordance row's WHERE clause: a row that cannot hold
does not exist. So the recursion is *re-run the menu in the possible world*. An effect that makes
a missing row appear IS the step before it, and the dealer's acquire-then-offer chain stops being
hand-written: refilling makes the vessel serveable, serveability is the offer row's premise, and
the row appears in the simulated world. One query, used twice — as the list of levers, and as the
test of whether a lever would exist.

### Possible worlds are computed, not kept

The store already answers this, in the rule that keeps affordances out of it: **what is stored is
premises, never conclusions**, because a stored conclusion can outlive the premise it came from.
A possible world is a conclusion from beliefs plus an effect. So it is built per candidate,
validated, and dropped.

The exception is a reader outside the process — a Consulting member being shown the options, or a
sovereign asking *why did you choose that*. For those it may be materialised into a graph of its
own class, cleared at the start of every planning pass exactly as genesis clears its write
targets, carrying PROV to the affordance row that generated it. Never public, never in belief,
and never a graph class anything else reads: the modality frame has the room for it — belief is
*is*, the menu is *could do*, and this is *would be, if I did*.

Validation of a candidate runs the goal shape **unfocused**, which is not a detail: pySHACL
answers qualified value shapes wrong under `focus_nodes`, measured both ways round
([a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md)), and every goal shape here is
qualified. A candidate world validated with a focus would be silently judged by the wrong
answer.

### The sovereign's three amendments: rules in the store, and the diff as the report

Asked immediately after the above, and each one changed it.

**"Means should be persisted, and be SHACL, with a CONSTRUCT as the effect."** That is a
standard, and we already depend on it: SHACL Advanced Features' `sh:SPARQLRule` carries
`sh:condition` — a shape that must hold for the rule to apply — and `sh:construct`, the query
text as a literal in the graph. Preconditions as shapes, effects as CONSTRUCTs, both persisted,
both readable by a model and a sovereign, no vocabulary invented. **Measured on pySHACL 0.40.1:
the rule fires, and `sh:condition` gates it correctly** — two targets, the one whose condition
failed got nothing. It needs `inplace=True`; without it the constructed triples land in a clone
pySHACL discards, which is the silent-nothing shape this project keeps meeting.

The record's standing rule survives it, because it was about a different thing. *Rows are not
stored because their premises are* is about INSTANCES — this valve, this venue — and a stored
row can outlive the plumbing it was concluded from. A rule is a SCHEMA. Schemas already live in
the store: that is what `ontology.ttl` and `shapes.ttl` are. So the means keeps its stored rule
and the menu keeps computing its rows, and neither claim gives way.

**"Does CONSTRUCT support deletion?"** No — and neither does SHACL-AF, whose rules exist to add
entailments. So a retraction template sits beside the construct one, and the simulator computes
`(beliefs − retracts) + adds`, side-effect free.

It is needed, and the reason is measurable rather than theoretical: **the sensed graph upserts.**
`sensed_writer` does DELETE-then-INSERT on one deterministic observation node per (subject,
property). An effect predicting a new reading that does not retract the old one leaves that node
carrying two `sosa:hasSimpleResult` values in the possible world — and the survival envelope is
`sh:qualifiedMaxCount 0` over readings outside it, so a stale bad reading left in place reports a
catastrophe in a world where the plan has just fixed it. The planner would reject the plan that
works. It fails the other way too: a stale GOOD reading satisfies a region goal the predicted
value misses.

**"Do we search the diff, and should a means describe which diff it repairs — moisture low means
watering, moisture high means a fan?"** Yes, and the diff is a thing this stack already produces:
the validation REPORT of the goal shape against belief. Each result carries its focus node, its
path, its value and — the useful part — `sh:sourceConstraintComponent`, which names WHAT failed.
So a means declares a shape over validation RESULTS: the diffs it repairs. Everything is a shape,
including the description of what a lever is for.

One thing has to change first, and it is the change this record's own reader asked for from a
different direction. **The region shape must split into two property shapes**, one for below the
floor and one for above the ceiling. Today the range test is nested inside a qualified value
shape, so the violated component is `QualifiedMinCount` — *no conforming reading exists* — which
does not say which SIDE the reading is on. Watering and a fan repair opposite sides, and a report
that cannot tell them apart cannot select between them. Splitting makes the violation name the
side, which is also what makes a message say "0.91 is above 0.65" and what a dashboard needs to
stop showing a drowning plant as a thirsty one.

And when it does, `market:direction` becomes redundant: Raises repairs the below-violation,
Lowers repairs the above-violation, and the one-bit effect that was hardcoded into a reflex
becomes a match between two shapes. That is a fourth special case this widening should DELETE
rather than keep.

### Unreachable is not the same as unequipped

The sovereign, sharpening "what if the desire is not possible": *what if I have two levers in the
menu and they do not work together — I need to increase by 2, and I hold only +3 and −3?*

That is a different failure from a want nothing points at, and the difference matters to whoever
must fix it. Nothing is missing from the menu; the levers point the right way; their GRANULARITY
cannot land inside the region. From −2, the reachable set is a lattice at ±3 — it never contains
the target. A want nothing points at says *equip me*; a want whose levers overshoot says *my
equipment is too coarse for my ends, or my ends are too tight for my equipment*, and the remedies
are different: a finer lever, or a wider region, or an admission that oscillation is the best
this rig can do.

**It is the case that decides simulation over symbolic matching.** Repair-matching — the
violation is Below, this lever repairs Below, therefore propose it — cannot see an overshoot: it
compares the violation's kind to the lever's kind and both are exactly right. A possible world
sees it immediately, because after applying the effect the goal is still violated, from the other
side. The sovereign chose CONSTRUCT-and-simulate before this case came up; this is what that
choice buys.

Three requirements follow, none of which a planner written for the reflex's world would have:

- **Cycle detection.** +3 then −3 returns to the starting world. A search that does not notice
  will spend its whole depth budget going nowhere. Worlds here are belief plus a small diff, so
  comparing the NET diff of the world reached is enough — never the diffs accumulated along the
  path, or an oscillation that nets to nothing would look novel. Graph isomorphism is not needed
  and would not be affordable; what is needed instead is a CANONICAL form, because every effect
  mints its predicted observation with `BNODE()` and stamps it `NOW()`, so raw triples never
  collide at all. An observation canonicalises to its upsert key and its value — identity and
  `sosa:resultTime` are not part of where a plan stands — and any other blank node to its
  content ([#258](https://github.com/ShishkinDmitriy/orexis/issues/258), which is what lets a
  step that moves something other than the goal's number count as somewhere new; see
  `agent/signature.py`).
- **Depth exhaustion is an ANSWER, not a failure.** "No bounded plan reaches this goal" is a
  distinct outcome from "no lever repairs this violation", and the two must reach the report as
  different things or the sovereign is told to buy a fan when the problem is dose size.
- **Satisfice: prefer the world with the lowest urgency, and act only if it beats doing nothing.**
  This is where the widening pays for itself in behaviour rather than expressiveness. The reflex
  today acts whenever a lever's direction matches the gap's sign, with NO check that the outcome
  is an improvement — which is how a society floods a plant while every module behaves as
  written. Simulation turns "does this lever point the right way" into "does this lever leave me
  better off", and the second question is the one worth asking.

**And most of it is checkable before anything runs.** The region's width is the tolerance that
makes a coarse lever usable at all: the goal is not "+2", it is "inside 0.45–0.65", and a dose
that overshoots the far edge from every reachable starting point is a rig that can never settle.
When the smallest step a lever can take exceeds the width of the region it is aimed at, there are
starting points from which no sequence of doses lands inside, and the agent will oscillate for
ever. That is a fact about ratified files — a device's calibration against a subject's stated
ranges — so it belongs at the gates beside "a board faster than its mandate can honour", not at
3am on the bench.

### A sensing action is always the last step

Building the effects (#238) surfaced a limit that belongs here before a planner is written
against it. Observe's rule constructs an observation carrying the value last seen and a current
`sosa:resultTime` — the only honest prediction available, since nobody can say what a look will
find. On a FIRST look there is no value to carry, so the constructed reading has none, and a
range shape asked about an unknown value is satisfied vacuously: SHACL is two-valued, and it
renders "unknown" as "not violated".

The temptation is to call that a bug and make the unmeasured shape demand a RESULT. Do not: then
no honest effect could ever satisfy it — predicting a value you cannot know is the dishonest
alternative — and an agent could never plan to look at all. The semantics are right as they
stand, and they are the ones already in the house: `urgency(None)` is 1.0 and the first intention
is always to look, because the unmeasured want is about HAVING LOOKED, not about knowing a good
value.

What follows is a constraint on the planner rather than on the shapes. **A possible world with no
violations means "nothing I can foresee is wrong", not "the world will be fine"** — so a plan may
not chain PAST a sensing action. What to do after looking depends on what the look returns, which
is contingent planning, and the bounded answer this project should take is the simple one: a
sensing action ends a plan. Look, then decide again with a reading in hand.

**Nothing enforces this but the effect itself, and that is the right amount.** The search once
carried a guard, reading `ag:confirmedBy ag:ByObservation` to spot a sensing act — a different
question whose answer is the same for every lever here, so the guard matched all of them,
nothing was ever added to the next depth, and the search never went past one step at all (#254).
Removing it changes no behaviour: Observe's effect predicts the value it found, so the world it
reaches has its parent's signature and the cycle check discards it, exactly as a zero-size bid
is discarded. What that rests on is the canonical form:
[#258](https://github.com/ShishkinDmitriy/orexis/issues/258) made the signature carry where a
plan IS — the world's net diff — and a look still nets to nothing there, because an observation
canonicalises to its upsert key and its value and a valueless first look states no fact at all.
A signature that counted a fresher `sosa:resultTime` as somewhere new would make each look a
new world, and this becomes a live question again.

That also disposes of a nonsense the search would otherwise produce — "look, then water" scored
as a two-step plan whose second step was chosen against a value nobody had yet seen.

### `plan.rq` is a narrative, not a path to a goal

The sovereign ruled that the hand-written plan should be dropped *if the planner can create it*.
It cannot, and the reason is not a missing feature: **acquire-then-offer is not a path to any goal
the supplier holds.**

Probed against the real world rather than argued. The supplier's one chosen goal is its own stake
in `StoredLitres`, and its chosen menu is Acquire from the city and Observe. Offering does not
raise stock — it SELLS stock — so no state the supplier wants is nearer for having offered, and
Acquire alone satisfies serveability. The two-step is a true and useful description of the
dealer's business cycle. It is not a plan in the planner's sense, and asking a goal-directed
search to reproduce it was asking the wrong question.

So the acceptance test was right in spirit and wrong in one of its two examples. The spirit holds:
a widening must ABSORB the special cases it replaces or it is machinery bolted beside them, and
`value is None -> OBSERVE` was exactly such a case and is gone (#240). `plan.rq` is not one. It is
an exposition of a business cycle for a reader, with no runtime caller, and it stands with this
note beside it saying why the planner will never produce it.

**The genuine multi-step dependency this record describes — refill, then deliver — is
`Acquire → Apply`, and it is a DUTY.** For a while `propose_for` routed a duty to the honoured
row serving its counterparty and never to the planner — the one chain in the shipped worlds with
a true dependency was the one the planner was not allowed to see. Closed by
[#255](https://github.com/ShishkinDmitriy/orexis/issues/255): a duty simulates first, its met-test
is the discharged-pattern over the record, and `market:ApplyEffect` states what serving makes
true with the vessel's level as its premise — a premise that cannot bind predicts nothing, so a
dry serve is discarded as somewhere already reached and the step that IS reachable is the
Acquire whose effect raises the very level the premise reads. Refill-then-serve emerges from two
rules that never mention each other, which is what this record promised chaining would be. The
search speaks for a duty only when it FOUNDS a plan; a vessel nobody has read binds no premise
and proves nothing, so anything short of a plan falls back to the honoured row and the actuation
boundary, unchanged.

### Two limits found by building, and one is structural

**The bindings were computed once and reused at every depth**, so a second dose predicted the same
world the first had reached and cycle detection discarded it as already seen. The search was depth
1, silently, for every means that moves a measured property — a planner that reported plans and
never made one longer than a step. Fixed, and pinned by a test that fails if the bindings stop
advancing with the world.

**The structural one was that a rule's CONSTRUCTs ran against the STORE.** So
`(beliefs − retracts) + adds` held for one step and stopped holding for the next — the retraction
re-asked the store, found the observation still stored, and never saw what the previous step added
to the world. After two steps a world held two readings and the reader took the stale one.

FIXED (#254): a rule is run against the agent's **imaginarium**, a second pyoxigraph store held in
memory for the life of one plan, with one named graph per node of the search. No rule changed —
`$sensed` was already a substituted parameter, and every shipped effect reads exactly one mutable
graph. See [a-rule-is-asked-about-a-world-not-about-a-store](/decisions/a-rule-is-asked-about-a-world-not-about-a-store.md),
which also records the two things this record got wrong about it. Chief among them: a THIRD limit
was hiding underneath, and the first two hid it. The frontier guard below asked the confirmation
route to identify a sensing act, every effect here answers `ag:ByObservation`, and so nothing was
ever added to the next depth — the search ran at depth 1 whatever `MAX_DEPTH` said, which is why
nobody in a running society ever saw the two readings this section describes. That guard is
gone rather than replaced — see the sensing-action section below.

### An invented number does not give a wrong answer — it gives a convincing one

Worth keeping from building the planner, because it nearly shipped as a discovery. A first draft
asked the actuator nothing and assumed half a litre for a dose. Every simulated dose then
overshot, and the planner duly reported a rig too coarse to settle inside its region — which is
#244's exact signature, arriving as evidence, with numbers attached. The rig was fine. The
invented figure had manufactured a finding.

That is the sharper form of the rule this project already keeps ("do not invent constants"): a
made-up number does not produce an obviously wrong answer that someone catches. It produces a
plausible one, in the shape of a defect the team is already looking for, and the more coherent
the surrounding design the more convincing the artefact. The dose is now asked of the actuator
that would deliver it, which is the same single-source argument as the delta and the timing,
reaching the third of three places it could have been faked.

### The cheap check and the expensive one are different questions

Measured on the bench before any of the planner was written: validating ONE goal shape costs
0.083s, and validating everything the packages ship costs 1.73s — twenty times more. Checking
every candidate against the whole rulebook would make a depth-2 pass take twenty-two seconds to
answer a question about rules no effect could have broken.

So the two are asked differently, and the split follows from what each is FOR. The goal shape
is the search — asked of every candidate, because that is what choosing means. Legality is a
guarantee about what an agent COMMITS to, so it is asked once, of the world the winning plan
would actually reach. An agent that never commits to an illegitimate world is the property that
was wanted; validating the roads not taken buys nothing and costs everything.

The seam that leaves: a winner refused for illegality yields NO plan, rather than falling back to
the best legal candidate. That is the safe direction and it is logged, but it means an agent that
could have acted legally does nothing. Nothing shipped can trigger it — no shape here refuses a
world a dose would reach — and the day one can, the fix is to ask the next candidate rather than
to ask them all.

### The test of whether this is a generalisation

Two hardcoded things must DISAPPEAR, not survive beside it:

1. `if value is None: return OBSERVE` in the reflex — *the first intention is always to look*.
   Under the widening that is a freshness goal, unmet, and Observe is the lever whose effect
   repairs it. The special case should fall out of the machinery rather than be kept for luck.
2. ~~The dealer's hand-written `plan.rq`~~ — **mis-specified, and building it is what showed
   why; see "a narrative, not a path to a goal" below.** Acquire-then-offer should be derived from effects and
   the re-run menu, not stated as a two-step in a file.

If either survives, this is added machinery rather than a widening, and should be refused on
those grounds.

### And a duty becomes a shape

The obligation record left a seam — *what a claim-sourced desire says exactly* — with the honest
note that "valve X open for three seconds" is an ACT, and desires here are states. Graph goals
answer it: the state is *this claim discharged*, which is a pattern over the ledger, and the act
stays an affordance. That closes the last place where a want is not a shape.

# Seams left open

- **Implemented at depth 2, when the trigger fired.** The city mains (#201) made the supplier
  refillable, and the Planning member took its seat: granted by the dealer premise (acting
  for a source it offers, refillable from a source another offers — levers that compose),
  subsuming the reflex, adding exactly ONE deduced goal past the region — the hosted lot must
  be serveable, which is every downstream buyer's silent Acquire precondition. The other half
  landed in the host: rounds are sized by the vessel's own freshest reading (the bench had
  sold 2 L lots from a barrel at 0.000 — phantom water, conservation violated live), and a
  LOW nobody can serve DEFERS the round, reopening the moment the witness reports the refill
  — acquire-then-offer, the two-step held by the market and observable in the logs. The plan
  is also data: `plan_for` returns the two rows through the two venues, the Consulting
  member's substrate. What was NOT built of the sketch: the add/delete template on menu rows
  (the serveability goal is deduced in the planner, not stated as row effects — sufficient at
  depth 2, and superseded rather than revisited: the section above replaces add/delete with a
  CONSTRUCT per means, for a reason that only shows up at an actuation) and goal patterns as shapes (one deduced goal exists; the
  severity-axis machinery stays future). `ag:Offer` is ledgered since #206: the
  "host keeps no gap ledger" line was crossed knowingly, because an owed round held in
  module memory was a promise a restart forgot and no ask could see — adopted on deferral,
  satisfied on the reopened round, recovered from the ledger at the next stock reading. The
  plan itself ships as `plan.rq` beside the menu contributions, so `plan_for` and the
  sovereign's ask channel run one text.
- **The convening gap is the planner's ceiling.** A dealer may want stock the upstream will
  not yet sell: the city convenes on LOW alone, so a planner pursuing serveability at
  stock 1.5 has no round to bid in until the region floor is crossed. That is
  [the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md)'s
  recorded seam ("half the lot can be wanted by agents none of whom can convene a round"),
  reached now from the buy side — the fix is a convening shock beyond the demand shock
  (market.md names four), not a deeper planner.
- **Plan search is bounded by construction**, not by hope: depth 2–3 over menu rows whose
  preconditions are SPARQL, never open-ended STRIPS search. If a domain ever wants more, that
  is a different decision, taken then.
- **Who ratifies a goal pattern** beyond the deduced ones is the same question as who ratifies
  an affordance the model proposes — answered by the consulted-at-the-edge record's split:
  present sovereign ratifies at genesis, absent sovereign means private adoption plus review.
