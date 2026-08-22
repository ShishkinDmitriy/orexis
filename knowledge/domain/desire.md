---
type: Capability
title: Desire
description: What an agent is trying to bring about — for each property its subject states a need in, the region to hold that property inside and the envelope outside which the subject ends. Deduced at genesis by intersecting every operating range that applies, never authored; the band and the urgency every other capability reads come from here.
---

# What it is

BDI's middle letter. Belief has a whole store — see [belief-base](/domain/belief-base.md) — and
desire is what the agent is trying to bring about with it.

The capability produces two things and holds a third. It deduces a [region](/domain/region.md) per
property its subject needs, with an envelope beside it; the agent then picks an
[aim](/domain/aim.md) inside each; and it answers *what am I pursuing* across both of those and
the [obligations](/domain/obligation.md) it did not source.

# It is deduced, not authored

Nothing writes a desire. `packages/capability/desire/rules.ru` computes one at genesis from what
the subject and its instruments state, and the result is a [region](/domain/region.md) — that page
has the intersection, the two kinds of bearer, and why a graph found by TYPE rather than by name
is what makes a second source of desire possible.

What this capability adds is the DEDUCING: it is granted by a stake, `ag:actsFor` a subject that
states what it needs. An agent advancing nobody's interest wants nothing, which is why the sensing
world's agent has three sensors and no desires at all.

# What the rest of the society asks it

Four questions, and none of the askers imports this package — they arrive through the hooks
every module has (`agent/module.py`) or through `agent.provider(DESIRE)`.

| question | who asks | what it does with it |
|---|---|---|
| `band(property, value)` — LOW / OK / HIGH | [sensing](/domain/sensing.md), for the announcement | a host hears that a participant is in trouble, never how wet it is |
| `urgency(property, value)` — 0.0 to 1.0 | sensing, for the cadence | attention follows need: the closer to trouble, the closer it watches — and asked with NO value, the answer is maximal: ignorance in a wanted property is a need too (#137) |
| `region(property)` | anything that needs the range itself | the numbers |
| `aim(property)` — the pick inside the region | a bidder, at bid time, for the point a deficit is priced against | None is an answer: with no aim there is no deficit, and the bidder cedes rather than inventing one |

**The band is the region; urgency is measured from its centre toward the survival bound on that
side.** So urgency rises *inside* the region rather than waiting for the edge — an agent at the
edge of comfortable is already worth watching more closely than one in the middle — and it is
asymmetric per subject for free, because the room on each side is whatever that subject's two
ranges leave. See
[desire-is-deduced-from-the-ranges-the-world-states](/decisions/desire-is-deduced-from-the-ranges-the-world-states.md).

# The gap it is measured against

A region states where a subject should be. How far outside it something sits, and what that
distance is worth, is [gap](/domain/gap.md)'s.

# What am I pursuing — the whole list, with status

`goals.rq` is the question a sovereign and a model actually ask, shipped beside `gap.rq`: every
want this agent holds, hottest first, whoever sourced it. A stake and a duty appear in one list
because urgency is the common currency — a litre owed and a pot drying rank against each other
instead of running down two paths that never meet — and each row says what state its goal is in:
a stake is `met`, `unmet`, `stale` or `unmeasured`, a duty `standing`, `demanded` or
`settled`.

Three deliberate differences from the diff above:

- **A reading that went cold is its own want** (#240). `stale` sits beside `met` and `unmet`
  because a number past its horizon is not wrong, it has stopped being EVIDENCE — so it is
  reported at urgency 1.0, the same as never having looked, and for the same reason: ranking an
  agent by a distance it no longer trusts would rank it by something it does not know. The last
  reading is still carried on the row, because "this is what it said, and that was too long ago"
  is more useful than silence.
- **Freshness is about the INSTRUMENT, not the stake.** A want exists for every property this
  agent polls a sensor for — including one pointed at something it does not act for, which
  `world/loner`'s gardener does with its water butt. If an agent went to the trouble of polling
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
  region, and `unactionable` means a goal nothing can be done about — both read off the row's
  `state`. The first cut inferred them from urgency, which is zero only at a region's exact
  centre, so a barrel resting comfortably inside 1–5 reported one unmet and one unactionable
  goal and a calm society graphed as a stuck one. Ten minutes on the bench found it.
- **Whether anything can be DONE is not in the query.** That is the deliberator's answer — the
  menu is the union of what every loaded package contributes, and a copy of it inside a desire
  query would be free to disagree with the one the agent acts on. `pursued()` annotates each row
  by asking `propose_for`, and `series()` publishes the count, so a society drowning stops
  graphing like a society thirsty.

**The horizon is published, not recomputed.** `stale_after_s` works it out from the rhythm in
force — the board's own acknowledgement where it gives one, the agent's intent where it does
not — and none of that was ever written down: both were dicts on a module, lost at every restart
and invisible to `agora-ask`. A shape cannot run a method, so freshness would have needed either
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
of its own: it is an `sh:sparql` constraint sitting inside `desire:BeyondSurvivalShape`, whose
name and comment describe a survival check that moved into the deduction and is no longer
there ([#275](https://github.com/ShishkinDmitriy/agora/issues/275)). An earlier version of this
page called it `desire:UnwatchedDesireShape`, which is the name it deserves and not a name that
exists.

Consumers today: `reports()` discloses `desires`, `desires_measured` and `worst_gap` into the
health series; `desire:BeyondSurvivalShape` turns |gap| = 1 into a **warning** at boot — never
a refusal, because an agent past its envelope must be allowed to start precisely so it can do
something about it; and whoever holds `provider(DESIRE)` may call `gaps()` or `current()` for
the rows themselves.

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
