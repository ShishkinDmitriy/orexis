---
type: Domain Concept
title: Desire
description: What an agent is trying to bring about — for each property its subject states a need in, the region to hold that property inside and the envelope outside which the subject ends. Deduced at genesis by intersecting every operating range that applies, never authored; the band and the urgency every other capability reads come from here.
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
per property the subject needs, with an envelope beside it, and contributes those stakes to what
the agent pursues; the deducer — the kernel's own module in this modality — holds the
[aim](/domain/aim.md) the agent picked inside each; and *what am I pursuing* is answered across
those and the [obligations](/domain/obligation.md) the agent did not source, by `Agent.pursuing`
merging every module's `desires()`.

# It is deduced, not authored

Nothing writes a desire, and the kernel derives none. The build collects `desires.ru` from every
loaded package exactly as genesis collects `rules.ru`, and what belongs in one is a want whose
PREMISE belongs to that package: `packages/capability/sensing/desires.ru` computes the region
want from what the subject and its instruments state — the result is a
[region](/domain/region.md); that page has the intersection, the two kinds of bearer, and why a
graph found by TYPE rather than by name is what makes a second source of desire possible — and
the freshness want beside it, because both premises are that package's facts: a range a subject
states in `ssn-system`, an instrument this agent polls and the horizon it keeps. What stays the
kernel's is the mind — what a want is, when one is met, how wants rank — and it has no reading
in it ([the-stake-is-sensings-want](/decisions/the-stake-is-sensings-want.md)).

What the derivation mints is a NODE (`ag:Desire`) carrying the met-test as a SHACL shape
(`ag:metWhen`) and a label a dashboard or the ask channel can print — reified so a want can
say how badly it is unmet, not only whether it is. The measure is deliberately NOT the
kernel's in any part: whoever needs the number asks the choir (`Module.desire_urgency`), and
the capability that owns the question answers from its own declaration —
[sensing](/domain/sensing.md)'s, for any want about an observed property, resolved by the
want's KIND at answer time; that page has the mechanics. The argument is
[a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md)'s.

Deducing used to be granted by a stake — `ag:actsFor` a subject that states what it needs — and
the stake still decides everything except whether a module exists: an agent advancing nobody's
interest states no ranges, so it holds no region, and the shapes that target a stake never reach
it. The sensing world's agent has three sensors and no region at all, by the fact rather than by
a grant.

# Two sources, one currency

A desire is either a **stake** — a property of the subject this agent acts for, wanted inside a
[region](/domain/region.md) — or a **duty**, an [obligation](/domain/obligation.md) someone else
holds against it.

They are deliberately the same type. An agent's whole conduct is things it wants, pursued through
[affordances](/domain/affordance.md), and a deliberator that had to ask which kind it was holding
would be the second decision path this design exists to avoid.

**Urgency is unit-free in both cases, and that is the whole point of the type.** A stake's comes
from the survival envelope — how much room is left before the subject ends; a duty's from the
redeem window — how much time is left before the claim expires. The two become comparable without
either knowing how the other was computed.

# The kind is read, never flagged

A stake carries what is wanted and what it currently reads. A duty carries the claim it came from
and whom it is owed to. An **epistemic** want carries the instrument it was derived from.
**Each kind is known by the premise it has and the others do not, which is what `is_duty` and
`is_epistemic` read** — there is no kind field, because a flag that can disagree with the data
beside it is a flag that eventually does.

The third one had to become sayable when a property stopped having one want. Fern holds a
region in its moisture AND wants its probe to have spoken recently, and those are two things it
can be short of independently — so everything that used to ask "the want about this property"
had one answer and now has two, and answering by whichever is hotter would decide between two
different questions with a number that means the same thing in both.

# State is carried, not inferred

A desire states its own condition in its kind's vocabulary: `met`, `unmet` or `unmeasured` for a
stake; `met`, `stale` or `unmeasured` for an epistemic want; `standing` or `demanded` for a duty.

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

A duty is never *met*. It is discharged — and a discharged debt is history rather than something still wanted.

# Wanted is not the same as actionable

`pursuable` is separate from urgency, and a duty nobody has presented is the case that needs it: it
stands, it may be hot, and it still must not be acted on. The holder is waiting for its own watch
to be live, and **a host that doses early spends the water where nothing is looking.**

Always true for a stake — a plant does not ask.

# It lives in the kernel, and the capability does not

`agent/desire.py` holds the TYPE, outside any package, because a desire is a mental state and
those are the kernel's — the same reason obligations and intentions are. Two packages need it and
neither may import the other: this capability produces desires,
[deliberation](/domain/deliberation.md) consumes them, and the only thing they are allowed to
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

# One word owns the concept

"Want" in prose means a desire — the records have always said both, and prose may. What may
not: an ARTIFACT named for the synonym, which is how a second vocabulary starts. The files,
the queries, the hooks and the classes say desire (`desires.ru`, `desires.rq`,
`Module.desires()`), ruled when a `wants.ru` briefly existed and the sovereign asked why.

# What am I pursuing — the whole list, with status

`desires_of` answers the question a sovereign and a model actually ask — every want this agent
holds, hottest first, whoever sourced it — by joining `desires.rq` (the desire modality's half)
with `readings.rq` (the belief modality's), the judging done where the clock is. A stake and a duty appear in one list
because urgency is the common currency — a litre owed and a pot drying rank against each other
instead of running down two paths that never meet — and each row says what state its desire is in:
a stake is `met`, `unmet`, `stale` or `unmeasured`, a duty `standing`, `demanded` or
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
  shape says the same thing in `ag:violationIs` now; the query still reaches it by comparing the
  value to the bounds, which is the same answer, and reading it off a validation report waits for
  something that produces one in the hot path.
- **A count is about wanting, not about distance.** `unmet` means the reading sits outside the
  region, and `unactionable` means a desire nothing can be done about — both read off the row's
  `state`. The first cut inferred them from urgency, which is zero only exactly at the point
  being steered for, so a barrel resting comfortably inside 1–5 reported one unmet and one
  unactionable desire and a calm society graphed as a stuck one. Ten minutes on the bench
  found it.
- **Whether anything can be DONE is not in the query.** That is the deliberator's answer — the
  menu is the union of what every loaded package contributes, and a copy of it inside a desire
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

Two things the query cannot do, and both are recorded where they bite. A duty's urgency is the
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
and shows at runtime as `desires` and `desires_measured` diverging. That warning has no shape
of its own: it is an `sh:sparql` constraint sitting inside `sensing:BeyondSurvivalShape`, whose
name and comment describe a survival check that moved into the deduction and is no longer
there ([#275](https://github.com/ShishkinDmitriy/orexis/issues/275)). An earlier version of this
page called it `desire:UnwatchedDesireShape`, which is the name it deserves and not a name that
exists.

Consumers today: `reports()` discloses `desires`, `desires_measured` and `worst_gap` into the
health series; `sensing:BeyondSurvivalShape` turns |gap| = 1 into a **warning** at boot — never
a refusal, because an agent past its envelope must be allowed to start precisely so it can do
something about it; and whoever holds the sensing provider may call `gaps()` or `current()` for the rows
themselves.

# What it is not

- **Not an aim.** A region is a range and an aim is a point inside it. The aim (`ag:aims`,
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

# Desires an agent did not source

The class was a class from the start because a second source was expected, and
[obligation](/domain/obligation.md) is it — what the agent owes because the society issued a claim
against its hardware, scored and pursued by this same machinery.

# The structure above these

Every want here is a node of a derived hierarchy — [root desire](/domain/root-desire.md) has
the levels above, and
[a-desire-is-a-forest-of-derived-roots](/decisions/a-desire-is-a-forest-of-derived-roots.md)
the argument.
