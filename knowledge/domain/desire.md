---
type: Domain Concept
title: Desire
description: >-
  What an agent is trying to bring about, in two kinds. A DESIRE is standing and underived —
  no unpaid debts, this subject inside what it states it needs — authored or deduced once, held
  for the agent's life, and never handed to a search. A WANT is what the world deduces from one
  when a situation makes it bite: this debt closed before its window, this reading back in its
  region, bound to an instance, carrying the period it holds during, withdrawn when it is met.
  The agent holds desires; it pursues wants.
---

# What it is

BDI's middle letter. Belief has a whole store — see [belief-base](/domain/belief-base.md) — and
desire is what the agent is trying to bring about with it.

BDI's middle letter is the KERNEL's, granted by nothing — [capability](/domain/capability.md)
records why a stake stopped being a premise, and
[the-mind-is-not-a-package](/decisions/the-mind-is-not-a-package.md) has the argument. What
matters here is the consequence: every agent holds a desire store, and what differs between them
is whether their subject states anything to want.

Three things, three holders. [Sensing](/domain/sensing.md) deduces a [region](/domain/region.md)
per property the subject needs, with an envelope beside it, holds the [aim](/domain/aim.md) the
agent picked inside each, and contributes those stakes to what the agent pursues; the ledger
contributes the debts; and *what am I pursuing* is answered across
those and the [obligations](/domain/obligation.md) the agent did not source, by `Agent.pursuing`
merging every module's `desires()`.

What comes back from that merge is not desires. Neither kind below says how much it matters at
the instant it is asked about, and what supplies that is a [judgment](/domain/judgment.md) — made
per pass by whoever holds the stake, ranked against every other, and stored nowhere.

# Desire and want are two kinds, not two words

They were one thing said two ways until a standing desire got a child of its own (#618), and
the distinction is this:

| | a **desire** | a **want** |
|---|---|---|
| when it holds | at every instant; its graph states no period | on an occasion, during a period of its own, swept when that ends |
| what says when | its type, and a graph with no period | its graph's period, and `orexis:holdsAt` where it must hold AT an instant |
| what it is bound to | a class, usually — or an instance a world ratified | one instance, with the binding the situation gives it |
| is it pursued | never | it is the only thing a search is ever handed |

**Standing versus occasioned is the whole of it, and the TYPE carries it.** `orexis:Desire` and
`orexis:Want` are disjoint classes, so a reader says which it means and no reader infers a kind
from a binding — which is what let a node be one by type and the other by binding at once, in
three shipped worlds, until [a-kind-is-a-type-not-a-binding](/decisions/a-kind-is-a-type-not-a-binding.md)
took the ambiguity out.

**How it came to be is provenance, not kind.** Most wants are derived, and `prov:wasDerivedFrom`
names the desire; the pursuit road recomputes, withdraws and derives them again as the world
moves. But a world may ratify a want DIRECTLY, and three do — hanoi's *every disk home*, the
courier's *every parcel delivered*, the tower's — authored once, standing there for the agent's
whole life, and handed to a search like any other. A desire is likewise usually deduced at
genesis and may equally be ratified. Who wrote it says nothing about which kind it is.

*No overdue debts* is a desire, and the market declares it for any agent that hosts a venue. A
claim arriving derives a want under it — **close this debt before its window closes** — and that
want is what gets planned, met and withdrawn, while the desire stands unchanged for the next
one. OVERDUE rather than unpaid, deliberately: a host that owes water and has not yet poured it
is not in violation of anything, and a rule that said so would read unmet from the instant a
claim cleared.

**One road derives, for both.** The desire's own met-test, compiled to the select whose rows
are its violations, asked at the start of each prediction the agent holds; the rows are the
instances in trouble and the first instant each appears is its witness
([one-road-derives-every-want](/decisions/one-road-derives-every-want.md)). Sensing's region
desire is witnessed by what the drift predicts of a reading; *no overdue debts* by what the
ledger predicts of a debt — that it lapses at its deadline, a prediction written beside the
debt when the claim arrives. Neither package mints a want. The ledger wrote its own for a
while, a second deriver reaching the same family by a different door, and stopped when its
deadline became a prediction like any other.

The two live in two graph families, and the names already said so before this page did:
`orexis:RootsGraph` holds the desires, authored at genesis and holding at every instant;
`deliberation:PursuedGraph` holds one graph per want, each with its period.

**The kind is `orexis:Desire` and a want is an `orexis:Want` under it**, which is a subclass —
so every query asking `?d a orexis:Desire` still finds both through the materialised closure,
and one that means the standing kind alone says so.

# It is deduced, not authored

Nothing writes a desire, and the kernel derives none. Genesis collects `desires.ru` from every
loaded package exactly as it collects `rules.ru` and runs them at birth into the agent's roots
graph — a root holds for the agent's whole life and no rebuild touches it (#644) — and what belongs in one is a want whose
PREMISE belongs to that package: `packages/orexis-capability-sensing/desires.ru` computes the region
want from what the subject and its instruments state — the result is a
[region](/domain/region.md); that page has the intersection, the two kinds of bearer, and why a
graph found by TYPE rather than by name is what makes a second source of desire possible — and
the freshness want beside it, because both premises are that package's facts: a range a subject
states in `ssn-system`, an instrument this agent polls and the horizon it keeps. What stays the
kernel's is the mind — what a want is, when one is met, how wants rank — and it has no reading
in it ([the-stake-is-sensings-want](/decisions/the-stake-is-sensings-want.md)).

What the derivation mints is a NODE (`orexis:Desire`) carrying the met-test as a SHACL shape
(`orexis:metWhen`) and a label a dashboard or the ask channel can print — reified so a want can
say how badly it is unmet, not only whether it is. The measure is deliberately NOT the
kernel's in any part: whoever needs the number asks the choir (`Module.desire_urgency`), and
the capability that owns the question answers from its own declaration —
[sensing](/domain/sensing.md)'s, for any want about an observed property, resolved by the
want's KIND at answer time; that page has the mechanics. The argument is
[a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md)'s.

Deducing used to be granted by a stake — `orexis:actsFor` a subject that states what it needs — and
the stake still decides everything except whether a module exists: an agent advancing nobody's
interest states no ranges, so it holds no region, and the shapes that target a stake never reach
it. The sensing world's agent has three sensors and no region at all, by the fact rather than by
a grant.

# Two sources, one currency

A desire is either a **stake** — a property of the subject this agent acts for, wanted inside a
[region](/domain/region.md) — or a **obligation**, an [obligation](/domain/obligation.md) someone else
holds against it.

They are deliberately the same type. An agent's whole conduct is things it wants, pursued through
[affordances](/domain/affordance.md), and a deliberator that had to ask which kind it was holding
would be the second decision path this design exists to avoid.

**Urgency is unit-free in both cases, and that is the whole point of the type.** A stake's comes
from the survival envelope — how much room is left before the subject ends; an obligation's from the
redeem window — how much time is left before the claim expires. The two become comparable without
either knowing how the other was computed.

# The kind is read, never flagged

A stake carries what is wanted and what it currently reads. An **epistemic** want carries the
instrument it was derived from. A debt is the market's own judgment — `OwedJudgment`, the kernel's type
with the claim it came from and whom it is owed to beside it — and the kernel's type carries
neither word. **Each kind is known by the premise it has and the others do not, which is what
`is_epistemic` reads** — there is no kind field, because a flag that can disagree with the data
beside it is a flag that eventually does; and a debt is known by its type, which the market
declares and only the market reads, since no kernel branch asks any more.

The third one had to become sayable when a property stopped having one want. Fern holds a
region in its moisture AND wants its probe to have spoken recently, and those are two things it
can be short of independently — so everything that used to ask "the want about this property"
had one answer and now has two, and answering by whichever is hotter would decide between two
different questions with a number that means the same thing in both.

# State is carried, not inferred

A desire states its own condition in its kind's vocabulary: `met`, `unmet` or `unmeasured` for a
stake; `met`, `stale` or `unmeasured` for an epistemic want; `standing` or `demanded` for an obligation.

An epistemic want's state is read off its MEASURE, so the label and the number cannot part
company: anything the measure does not call current is not current, and which KIND of
not-current it is — never looked, against looked and let it go cold — is the reading's to say.
It used to come off a staleness test that declines to judge at all where no horizon has been
published, so a want the measure scored maximal reported `met`.

**Carried rather than derived from urgency, and the distinction is not academic.** Urgency is 0
only exactly at the point being steered for, so "urgency > 0" counts a barrel sitting comfortably
inside its range as unmet. It read that way on the bench for about ten minutes and made a calm
society look stuck. The split is structural now: the desire's met-shape governs the state, its
declared measure governs the urgency, and met-and-urgent — inside the region, off the pick — is a
true situation rather than a contradiction.

A obligation is never *met*. It is discharged — and a discharged debt is history rather than something still wanted.

# Wanted is not the same as actionable

`pursuable` is separate from urgency, and an obligation nobody has presented is the case that needs it: it
stands, it may be hot, and it still must not be acted on. The holder is waiting for its own watch
to be live, and **a host that doses early spends the water where nothing is looking.**

Always true for a stake — a plant does not ask.

# It lives in the mind's stores, and the capability does not

`packages/orexis-agent-deliberation/desire.py` holds the TYPE, in the deliberation layer and
outside any capability, because a desire is a mental state and those are the mind's — the same
reason obligations and intentions are. Two packages need it and
neither may import the other: this capability produces desires,
[deliberation](/domain/deliberator.md) consumes them, and the only thing they are allowed to
share is a kernel word.

# What the rest of the society asks it

Four questions, and none of the askers imports this package — they arrive through the hooks
every module has (`agent/module.py`) or through `agent.provider(DESIRE)`.

| question | who asks | what it does with it |
|---|---|---|
| `band(property, value)` — LOW / OK / HIGH | [sensing](/domain/sensing.md), for the announcement | a host hears that a participant is in trouble, never how wet it is |
| `urgency(property, value)` — 0.0 to 1.0 | sensing, for the cadence | attention follows need: the closer to trouble, the closer it watches — and asked with NO value, the answer is maximal: ignorance in a wanted property is a need too (#137) |
| `region(property)` | anything that needs the range itself | the numbers |
| `aim(property)` — the pick inside the region | a bidder, at bid time, for the point a deficit is priced against | None is an answer: with no aim there is no deficit, and the bidder cedes rather than inventing one |

**The band is the region; urgency is the measure the want's kind declares, anchored at the
[aim](/domain/aim.md)** — a SPARQL SELECT [sensing](/domain/sensing.md) ships and runs for
observation-backed wants, which reads the pick out of the belief base at query
time, falls back to the region's centre only while none is picked, and scales by the survival
room on the side the value sits, the region's numbers arriving as substituted parameters read
off the deduced shapes. So urgency rises *inside* the region rather than waiting for the edge — an agent at the
edge of comfortable is already worth watching more closely than one in the middle — and it is
asymmetric per subject for free, because the room on each side is whatever that subject's two
ranges leave. One text, run against whichever world is being judged: the belief base for the live
number, a candidate possible world inside the planner. See
[a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md) and
[desire-is-deduced-from-the-ranges-the-world-states](/decisions/desire-is-deduced-from-the-ranges-the-world-states.md).

# The gap it is measured against

A region states where a subject should be. How far outside it something sits, and what that
distance is worth, is [gap](/domain/gap.md)'s.

# An artifact is named for the kind it produces

A `wants.ru` briefly existed and the sovereign asked why; the ruling then was that the files,
the queries and the hooks say desire — `desires.ru`, `desires.rq`, `Module.desires()` — and it
stands, because what a package contributes at genesis IS desires: standing, underived, one per
premise. What is deduced from them at runtime is wants, and the graph that holds them is named
for that. The rule is not *one word wins*; it is *name the artifact for what it makes*.

# What am I pursuing — the whole list, with status

`desires_of` answers the question a sovereign and a model actually ask — every want this agent
holds, hottest first, whoever sourced it — by joining `desires.rq` (the desire modality's half)
with `readings.rq` (the belief modality's), the judging done where the clock is. A stake and an obligation appear in one list
because urgency is the common currency — a litre owed and a pot drying rank against each other
instead of running down two paths that never meet — and each row says what state its desire is in:
a stake is `met`, `unmet`, `stale` or `unmeasured`, an obligation `standing`, `demanded` or
`settled`.

Three deliberate differences from the diff above:

- **A reading that went cold is its own want** (#240). `stale` sits beside `met` and `unmet`
  because a number past its horizon is not wrong, it has stopped being EVIDENCE — so it is
  reported at urgency 1.0, the same as never having looked, and for the same reason: ranking an
  agent by a distance it no longer trusts would rank it by something it does not know. The last
  reading is still carried on the row, because "this is what it said, and that was too long ago"
  is more useful than silence. **And it is repaired through the search like anything else**
  (#331): the want says positively what it wants — a reading of this exists, made by this
  instrument, taken recently enough — Observe's effect predicts exactly that, and the deliberator
  states the rule nowhere. Saying it positively is also what makes it fail loudly: a want that
  hunted for a reading past its horizon was satisfied by having no reading, and by having no
  horizon to judge one against, which is the same nothing wearing two hats.
- **Freshness is about the INSTRUMENT, not the stake.** A want exists for every SENSOR this
  agent polls — including one pointed at something it does not act for, which
  `world/loner`'s gardener does with its water butt, and including one whose property already
  carries a region, because knowing the number and the number being right are different things
  to be short of. If an agent went to the trouble of polling
  something, it wants to know what that reads now; a stake is what makes the VALUE matter, and
  this want is about knowing. And no want exists where there is no sensor: an epistemic want
  nothing could ever satisfy would sit at maximum urgency for ever, top every ranking, and
  inflate the `unactionable` count — training a reader to ignore the top row, which is the
  failure that count exists to prevent. That case is already reported once, by the shape saying
  a desire exists in a property this agent polls no sensor for.
- **An unmeasured want is a row here, at urgency 1.0.** No row is right for a diff and wrong for
  a ranking: not knowing whether the pot is dying is at least as urgent as knowing it is
  uncomfortable, which is the answer `urgency(None)` has always given.
- **`side` says which way out a stake sits.** For moisture only the low side has a lever, so a
  drowning plant and a dying one are both `unmet` at urgency 1.00 and mean opposite things. The
  shape says the same thing in `orexis:violationIs` now; the query still reaches it by comparing the
  value to the bounds, which is the same answer, and reading it off a validation report waits for
  something that produces one in the hot path.
- **A count is about wanting, not about distance.** `unmet` means the reading sits outside the
  region, and `unactionable` means a desire nothing can be done about — both read off the row's
  `state`. The first cut inferred them from urgency, which is zero only exactly at the point
  being steered for, so a barrel resting comfortably inside 1–5 reported one unmet and one
  unactionable desire and a calm society graphed as a stuck one. Ten minutes on the bench
  found it.
- **Whether anything can be DONE is not in the query.** That is the deliberator's answer — the
  actions are the union of what every loaded package contributes, and a copy of them inside a desire
  query would be free to disagree with the one the agent acts on. `pursued()` annotates each row
  by asking `propose_for`, and `series()` publishes the count, so a society drowning stops
  graphing like a society thirsty.

**The horizon is published, not recomputed.** `stale_after_s` works it out from the rhythm in
force — the board's own acknowledgement where it gives one, the agent's intent where it does
not — and none of that was ever written down: both were dicts on a module, lost at every restart
and invisible to `orexis-ask`. A shape cannot run a method, so freshness would have needed either
a second copy of that fallback chain in SPARQL, free to drift, or a baked constant, wrong the
moment urgency re-commands the cadence. The agent writes the ANSWER instead, per sensor, into its
instruments graph; everything reads what was written, and nothing can disagree with it.

Two things the query cannot do, and both are recorded where they bite. A obligation's urgency is the
fraction of its redeem window that has run, and this store binds **nothing** for
`duration / duration` — so the row carries `owedAt` and `expiresAt` and the division happens in
Python, pinned by a test that fails the day the engine grows the operation. And `lapsed` is the
reader's judgement rather than a `NOW()` inside the query, because a deadline judged by the
store and an urgency judged by Python are two clocks.

**Three states of measurement, told apart** (#124). A row carries `at` — when the sensed side
was true — and does not judge its own freshness, because how old is too old is the agent's own
rule (the cadence it commanded plus its grace, sensing's to answer). `gaps()` returns
everything, stale included, since "last I looked I was dry and I cannot see any more" is
information; `current()` is the same diff with the agent's rule applied, and is what the report
is computed over — so a dead sensor's upserted last reading makes `worst_gap` **disappear
rather than reassure**, and `reading_age_s` on the same dashboard says why. The blind case — a
desire in a property the agent polls no sensor for — warns at the gate (the mirror of #111)
and shows at runtime as `desires` and `desires_measured` diverging. It is
`sensing:UnwatchedRegionShape`, named for what it checks since
[#275](https://github.com/ShishkinDmitriy/orexis/issues/275) — the shape was called
`BeyondSurvivalShape` after a survival check that had moved into the deduction, so a warning
about a blind region arrived under a heading about dying. An earlier version of this page reached
for `desire:UnwatchedDesireShape`, a name that existed nowhere, which is how the mismatch was
found.

Consumers today: `reports()` discloses `desires`, `desires_measured` and `worst_gap` into the
health series; the envelope the deduction derives beside each region turns |gap| = 1 into a
**warning** at boot — never a refusal, because an agent past its envelope must be allowed to
start precisely so it can do something about it; and whoever holds the sensing provider may call `gaps()` or `current()` for the rows
themselves.

# What it is not

- **Not an aim.** A region is a range and an aim is a point inside it. The aim (`sensing:aims`,
  which replaced `water:hasTarget`) stays a private belief in `beliefs/<id>.ttl`, is the agent's
  to move within its
  [mandate](/decisions/self-review-is-a-capability.md), and is checked against the region at boot.
  Range public, pick private — see
  [a-belief-is-a-pick-within-a-range](/decisions/a-belief-is-a-pick-within-a-range.md).
- **Not a market position.** Judging a reading used to live in `market:Bidding`, which made
  having an opinion about your own state conditional on having somewhere to bid. An agent acting
  for a plant in a world with no economy still knows when that plant is in trouble; it simply has
  nobody to ask for help.
- **Not an intention.** Nothing here plans or commits. The third letter has its own concept
  now — [intention](/domain/intention.md), a commitment to reduce a gap this capability names —
  and the split is deliberate: desire says where the world should be, intention says what I am
  already doing about it.
- **Not universal.** An agent that acts for nothing derives no desire capability at all — no
  module, no region, no band. `world/sensing`'s agent is exactly that: three sensors, no stake,
  and it records.

# A want met by absence

A desire may state its met-test NEGATIVELY: `orexis:unmetWhen` points at the avoided state —
a node carrying one `sh:select` whose rows mean the want is unmet — the twin of
`orexis:metWhen`, one of the two and never both (`orexis:MetTestShape`). Such a want is pure
ratified data, authored directly in the asserted block, and NO capability is in the room:
there is nothing to grant, so the kernel lifts it into pursuit and judges it — binary, by
running the pattern with `$this` and `$state` substituted against whichever world is asked,
the store's engine live and candidate alike. It usually states no `orexis:about`, and so
ranges over every affordance as a call does: any lever might exit a state. Its hard twin is
not a desire at all — a ratified violation shape, pruned in the search at every step. See
[a-want-met-by-absence](/decisions/a-want-met-by-absence.md).

**And the kernel writes that negation itself for a want authored as a shape** (#497). A shape
is positive and universal — every parcel at its destination — and rows are existential, so
judging a shape by rows means turning it inside out; the search does that once per pass, in
`packages/orexis-agent-progression/violation.py`, compiling the shape's constraints into the one select whose rows are the focus
nodes that violate it, and runs that on the store's own engine at every candidate world for a
millisecond where the judge's reader floors at tens. Computed, never stored — and shown, per
pass, as `deliberation:judgedBy` in the [trace](/domain/deliberator.md) (#502). The two puzzle
worlds author their goals positively — `courier:delivered`, `hanoi:solved` — and nobody writes
"a parcel astray" by hand. Coverage is the fragment the derivations emit and a shape outside it
refuses, named, never compiling to something quiet; `tests/test_violation.py` holds every
compiled select to the judge on the same world. An authored `orexis:unmetWhen` stays the road
for an aversion, whose content IS the avoided state — and since #499 it too may be a shape,
compiled to its conformance select, so both polarities read either form. The two terms are
not folded: `unmetWhen S` is `metWhen [sh:not S]` in logic, and an author made to write "met
when not the marker" gets back the double negative the compiler takes away.

**The rule of thumb, agreed with the sovereign (2026-09-02).** Author in SHACL what is a test
over a focus node or a monotone rule from one — a met-test, an avoided state, a structural
derivation — because then its predicates are data, the kernel can compile it, and relevance
can read it. Author in SPARQL what enumerates, computes, aggregates or retracts — a
precondition (rows: lever and target), an [effect](/domain/effect.md) (it retracts, and SHACL
cannot), an estimate (arithmetic and a sum). The compiler runs one way, every shape in the
fragment to a select and no select to a shape, so the choice is made at authoring and the
direction is never ambiguous.

# A want that can say how far it still is

A desire may also carry `orexis:estimates`: a node with one `sh:select` binding `?estimate`,
the cost still to pay before the want is met, in the unit the actions' `orexis:costs` are
stated in, run with `$state` naming whichever world is being judged. Urgency is the want's,
cost is the action's, and an estimate is the want speaking about cost — which is why it hangs
off the desire and not off any action. A want that declares none is not zero away; every
unmet world reads equally far and the search falls back on urgency and cost alone.

**It must never overstate.** The [planner](/domain/planner.md) is best-first on cost plus
estimate and ends a pass when the head of its open list passes the cheapest achiever found,
which is sound exactly because the estimate is a floor under what any plan through a world
would finally spend. An estimate that overstated would end the pass on a dearer plan than
exists, and nothing would go red.

**The desire owns the term; the package owns the measure.** That promise is a claim about the
package's own actions and their costs, and only their declarer can keep it, so the node a
want points at — the estimate's and the avoided pattern's alike — is declared in the domain
package's ontology beside the actions, and a world asserts the want and points at it
(`world/courier/desire.ttl` says `orexis:estimates courier:drivesOwed`). A world may still
write a select inline beside an asserted want, as the avoidance tests do, and the kernel
reads either road; the domains ship theirs. The road after this one is derivation — the
package deduces the want from what the world states, as
[desire-is-deduced-from-the-ranges-the-world-states](/decisions/desire-is-deduced-from-the-ranges-the-world-states.md)
argues for plants — and then a world states parcels and nothing about wanting them delivered.

# Desires an agent did not source

The class was a class from the start because a second source was expected, and
[obligation](/domain/obligation.md) is it — what the agent owes because the society issued a claim
against its hardware, scored and pursued by this same machinery.

# A desire is the top of one tree of wants

A **desire** is the top of one tree: a starting point the decomposition grows from, with
nothing above it to have come from — which is what the word means here, and why there is no separate "root
desire" to be a second kind of anything. Typically it is a statement over a class of things — an
agent holds one per premise: acting for subjects yields the welfare root, holding instruments
the freshness root, being able to incur obligations the debts root — so the whole is a
**forest**, and an agent with no premises has no trees. A ratified desire may instead name an
instance from the start; its position, not its level, is what makes it one.

**A desire is never pursued.** It is the premise of what is: the wants a search is handed are
derived under it — at-end when the root's shape is violated, at an instant when a prediction
says it will be — and each is gone when met
([an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it](/decisions/an-always-want-is-a-root-and-what-is-pursued-is-derived-from-it.md)).

# What is derived under it

The want a search is handed for a desire that reads unmet is a node of its own, bound
`prov:wasDerivedFrom` the desire, POINTING at its met-test, avoided state
and estimate — one owner each — and restating only the root's address, what it is about, which
is what the menu joins a want by. It is minted by the pursuit road the first time the desire
reads unmet, into the agent's own pursued graph (`deliberation:PursuedGraph`, projected into the
desire modality like the promises), and named for the desire with a suffix, so a second episode
of the same desire pursues the same node and everything keyed by it finds what it kept. While it
stands the container presents IT in the desire's place, carrying the desire's own row — its
measure, its reading, its property — and naming the desire, so a keeper's verdict, a bidder's
lookup and a mark by either name meet the same want. It is withdrawn when its plan finishes, or
when it reads met with nothing standing for it; a desire still unmet derives it again. A met desire
with nothing derived under it is nothing to pursue, and no pass runs for it.

A desire that reads met may still foresee: where it states `orexis:foresees` and a drift's
crossing falls within that stretch, the want derived under it must hold AT the crossing
— met at the instant and the instant after, its room the stretch to it — and the search for it
begins where the present's own drift stands at the instant less the longest landing on the
menu, so the plan's first step is placed at the instant less the plan's own duration and held
there. It reads met the moment the newest prediction crosses later than the instant, which is
what a dose does, and is withdrawn like the other.

A desire is DECLARED, which is what separates it from the wants below it: a package states one
per premise in its `desires.ru` and genesis runs it once, or a world ratifies one through its
asserted desire block — the sovereign speaking rather than the agent. Neither is the agent's own
authoring, and neither is a derivation: what is derived is the want.

# Where instances enter

A declared desire speaks only T-Box words, and its met-test's target is the class it quantifies
over. The instances enter as WANTS: the met-test compiled to the select whose rows are its
violations, run now and at each prediction's start, names every instance in trouble and when —
this fern's moisture at 14:32, this debt at its deadline — and one want is minted per
[scope](/domain/scope.md) of them
([one-road-derives-every-want](/decisions/one-road-derives-every-want.md)). Code still names no
instance anywhere: the world's files author them and the packages write them as they arrive, and
a ratified desire's instance is authored there too. What holds at every level is the provenance
discipline — deduced or ratified, never the agent's own authoring — rather than any rule about
where the T-Box ends.

# Each node states its why

A node names its parent and the premises that imply it — the range statement, the roster
membership — in PROV. Walking from a hot leaf up to its labelled root therefore reads as an
explanation, which is what the ask channel shows a sovereign; and where a ratified
instance-level statement overrides a type-level one, the leaf's derivation names it, so the
override is audited in the graph.

# The depth is earned

Every level must name a consumer or fold back: leaves feed repair matching, the property node
carries the pick and the series, the instance node the walk and the override audit, the desire
the rolled-up urgency and the entry point of the asking. The test, the consumers and the
argument are in
[a-desire-is-a-forest-of-derived-roots](/decisions/a-desire-is-a-forest-of-derived-roots.md).
