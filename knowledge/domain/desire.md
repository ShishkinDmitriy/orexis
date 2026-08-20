---
type: Domain Concept
title: Desire
description: What an agent is trying to bring about — for each property its subject states a need in, the region to hold that property inside and the envelope outside which the subject ends. Deduced at genesis by intersecting every operating range that applies, never authored; the band and the urgency every other capability reads come from here.
tags: [desire, bdi, ssn, capability, beliefs, sensing, market]
timestamp: 2026-08-13T00:00:00Z
---

# What it is

BDI's middle letter. Belief has a whole store — see [belief-base](/domain/belief-base.md) — and
desire is what the agent is trying to bring about with it: for each observable property its
subject states a need in, **a region to hold that property inside**, and **the envelope outside
which the subject does not merely sit badly but ends**.

An agent holds one per property. Which properties it holds them in is not its choice and not the
sovereign's to write down: it is whatever the thing it acts for states a range for.

# It is deduced, not authored

Nothing writes a desire. `packages/capability/desire/rules.ru` computes one at genesis by
**intersecting every operating range that applies** to the subject — the highest floor anyone
states, the lowest ceiling — and gathers the survival ranges the same way as the envelope. Two
bearers contribute: the subject itself (its own range, or its species' through the closure), and
any instrument that `sensing:monitors` it. A region an agent cannot witness itself inside is
not one it can hold.

The property is bound from the **subject's** conditions. An instrument may narrow a desire and
may never create one — a thermometer rated 0-50 °C states a fact about the thermometer, not an
ambition for the pot.

The result lives in a graph of its own, typed `ag:ConstraintGraph` and found by that type rather
than by name, so more than one source of desire is expressible without any code learning there is
a second. It is public and recomputed on every start, because it is a function of the ratified
files: a plant whose range is amended must not leave an agent holding the old region.

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

# The gap — the diff between desired and sensed

The package ships the question it exists to make askable, as SPARQL: `gap.rq` joins the public
regions against the agent's own sensed graph and yields, per property, a **signed** distance
normalised by the survival room on the side the value sits on — 0 at the region's point, the
sign saying which way out, |gap| = 1 at the edge of what the subject survives. |gap| *is*
`urgency`, by construction; the package's tests hold the query and the module to one definition.

A gap is a **verdict**: computed on every asking, stored nowhere — the same number is a crisis
for one agent and nothing for another. And a property with no observation yet produces **no row
rather than a zero**: at birth every desire is unmeasured, unmeasured must not read as
satisfied, and the first intention is always to look. That boot-order fact is what
[an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md)
builds the rest of BDI on.

# What am I pursuing — the whole list, with status

`goals.rq` is the question a sovereign and a model actually ask, shipped beside `gap.rq`: every
want this agent holds, hottest first, whoever sourced it. A stake and a duty appear in one list
because urgency is the common currency — a litre owed and a pot drying rank against each other
instead of running down two paths that never meet — and each row says what state its want is in:
a stake is `met`, `unmet` or `unmeasured`, a duty `standing`, `demanded` or `settled`.

Three deliberate differences from the diff above:

- **An unmeasured want is a row here, at urgency 1.0.** No row is right for a diff and wrong for
  a ranking: not knowing whether the pot is dying is at least as urgent as knowing it is
  uncomfortable, which is the answer `urgency(None)` has always given.
- **`side` says which way out a stake sits.** For moisture only the low side has a lever, so a
  drowning plant and a dying one are both `unmet` at urgency 1.00 and mean opposite things.
- **A count is about wanting, not about distance.** `unmet` means the reading sits outside the
  region, and `unactionable` means a want nothing can be done about — both read off the row's
  `state`. The first cut inferred them from urgency, which is zero only at a region's exact
  centre, so a barrel resting comfortably inside 1–5 reported one unmet and one unactionable
  goal and a calm society graphed as a stuck one. Ten minutes on the bench found it.
- **Whether anything can be DONE is not in the query.** That is the deliberator's answer — the
  menu is the union of what every loaded package contributes, and a copy of it inside a desire
  query would be free to disagree with the one the agent acts on. `pursued()` annotates each row
  by asking `propose_for`, and `series()` publishes the count, so a society drowning stops
  graphing like a society thirsty.

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
desire in a property the agent polls no sensor for — warns at the gate
(`desire:UnwatchedDesireShape`, the mirror of #111) and shows at runtime as `desires` and
`desires_measured` diverging.

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

# Obligations — the desires an agent did not source

BOID's O, and the second source the desire-graph class was reserved for: when the society
issues a claim against this agent's hardware, it OWES — recorded as a `ag:Obligation` in
a graph of its own, naming the counterparty, the claim that caused it, whether it has been
demanded yet, and when it was discharged. Kept after payment, because a debt paid and a debt
forgotten must not look alike.

Two levels, and the split is the point. **Whom I may owe is topology** — derived from the
wiring that says who may present to me, exactly as the broker ACL is derived, so a debt to an
agent the world does not declare is refused before it becomes a want. **What I owe now** is
runtime state, private like the intention ledger and disclosed the same way: the sovereign
asks. See
[an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md).
