---
type: Decision
title: An intention is an amortised deliberation, and the gap is what deliberation is about
description: BDI's three letters, mapped honestly — beliefs are the store, desire is the region-plus-aim, and intention was proto only, existing as a pending bid, a held claim and a commanded cadence with no name, no lifecycle and no way to be queried. The plan in four phases — make the desired/sensed gap a query, move the aim into desire, reify the intention, then extract the welded reflex chain into a deliberation capability whose second member is an LLM. The ordering is the argument: intentions exist to SAVE deliberation, so for an LLM planner they are the cost model — an intention is an amortised LLM call, and the commitment policy is what keeps the planner affordable. Reflex ships first, so the LLM drops into a seam that provably exists.
status: accepted
stage: v1
tags: [bdi, desire, intention, deliberation, llm, planning, capability, roadmap]
timestamp: 2026-08-14T00:00:00Z
---

# The question

[desire-is-deduced-from-the-ranges-the-world-states](/decisions/desire-is-deduced-from-the-ranges-the-world-states.md)
gave BDI's middle letter a package. That immediately sharpened the question the older records
kept deferring: *what is the third letter here, and where does the LLM sit?*
[llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) says one LLM call produces a
stance; [the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md)
records *"intention is still unnamed"* as a seam and declines to settle whether that is a gap or
a happy absence. It is a gap, and this record says why and what to do about it.

# The mapping, honestly

| BDI | agora | state |
|---|---|---|
| **Beliefs** | the store: public graphs, private beliefs, `:sensed` | done |
| **Desires** | `desire:Desire` regions, plus the aim inside one | region done; aim still `water:hasTarget` |
| **Goals** | implicit — the worst gap wins attention | unnamed, deliberately |
| **Intentions** | **proto only**: a pending bid, a held claim, a commanded cadence | no name, no lifecycle |
| **Interpreter** | hardwired: reading → band → LOW → announce → bid → claim → actuate | welded; it IS the planner |

Two observations drive everything below.

**The gap is why an agent looks at all.** At birth there is a desired state and an empty sensed
graph, so the first intention is always *observe* — sensing is not upstream of deliberation, it
is deliberation's first product. The cadence machinery already whispers this (urgency drives
polling) as a special case; making the gap first-class makes it the general one.

**An intention is an amortised deliberation.** The sharpest lesson in the BDI literature
(Bratman; Kinny & Georgeff on reconsideration) is that intentions exist to *save* deliberation:
an agent that re-decides on every sensing is a reflex machine wearing a planner's name. Here
that is not philosophy but a cost model — an LLM call is expensive, so an intention is an
amortised LLM call, and the commitment policy (when to reconsider) is exactly what keeps an LLM
planner affordable. This is why intention is reified BEFORE any LLM is consulted: without a
persisted commitment the model would be asked per reading, which is both expensive and thrashy.

# What was decided

Four phases, each independently shippable, each an issue. The decision here is the shape and the
ordering; the issues carry what is left to do.

## 1. The gap becomes a query, and a gap is a verdict

Desired and sensed are both graphs now, so *how far am I from what I want* stops being Python
inside a module and becomes a SPARQL query the packages ship: per property, the current value,
the region, and the signed distance normalised by the survival room on that side — the urgency
arithmetic, expressed where any consumer can run it. Three consumers exist the moment it does:
metrics reports the gap, a shape can refuse an agent that has sat outside its region for N
windows, and a `review.rq` can finally *justify* an aim against gap history — the seam
[the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md)
has carried since it was written.

**A gap is computed and never stored**, exactly as a band is: it is a verdict, and the same
number is a crisis for one agent and nothing for another. What may be stored is a *summary* of
it, which is review's existing pattern and needs no new mechanism.

## 2. The aim moves into desire

`water:hasTarget` is two things fused: the point an agent aims at inside its region (desire's)
and the input a litre-deficit is priced from (the market's). They split: `desire:aims` is
private, per property, checked against the region it picks inside; bidding reads the aim through
`agent.provider(DESIRE)` and keeps only its value curve (`litresPerFraction`,
`maxValuePerL`). The old term migrates through the vocabulary successor mechanism, so a running
store follows.

The aim stays **picked, not deduced** — it is the one thing left that an agent decides about its
own ends, it is what review may legitimately move, and it is **required wherever something acts
on it** rather than defaulted to the region's centre. A missing belief is an error, not a
default; this repo refuses fabricated beliefs everywhere else and an aim is not the exception.

## 3. Intention is named, by reifying what already exists

No new behaviour. The three proto-intentions get one name and one lifecycle:
`intention:Intention` is a commitment to reduce a named gap by a named means — *observe* (a
cadence command), *acquire* (a bid, satisfied by a claim), *apply* (a redemption) — with
states adopted → active → satisfied | dropped and a `becauseOf`, the same PROV-flavoured shape
`review:Revision` already has.

**Intentions are private.** They live in a graph the capability owns, like `revisions/`, because
an intention disclosed is strategy leaked: the *bid* is the public face of the intention, never
the intention itself. The market sees what you do, not what you are trying to bring about.

**The commitment policy is a belief with a shaped floor**, not kernel: how stubborn to be —
"reconsider when the gap doubles", "never mid-auction" — is an opinion an agent may hold and
review may move, bounded the way cadences are bounded.

## 4. Deliberation becomes a family, and Reflex is its first member

The welded chain (LOW → announce → bid) is extracted into a capability family — something that
turns a gap and the standing intentions into the next intention. It passes rule 2's test
cleanly: the *how* genuinely differs.

- **Reflex** — the current chain, as code. Deterministic, free, always a valid fallback. Ships
  first, so the family exists with one member and the loop runs LLM-free end to end.
- **an LLM member** — one call over beliefs + T-Box + the gap + standing intentions, emitting an
  intention **from a menu of affordances**, never free text-to-action. The formal layer holds
  it: the intention validates against shapes or is not adopted, an intention outside the mandate
  fails the same check every belief fails, and the bid *number* stays deterministic —
  [deterministic-bid](/decisions/deterministic-bid.md) stands, the model picks *whether and
  when*, code computes *how much*.

The granting premise, since each capability names its own: **a desire plus at least one lever**
— a market position, an actuator, or cadence latitude. An agent that wants but cannot act has
nothing to plan with; an agent with levers and no wants has nothing to plan for.

# What this amends

[llm-heavy-deliberation](/decisions/llm-heavy-deliberation.md) says the LLM's output is a
*stance*. This record narrows that without reversing it: **the intention is the stance, made
checkable**. Prose remains how the model reasons; what it *commits* is a typed intention the
shapes can refuse. The consequence section of that record — the formal layer is load-bearing
precisely because deliberation is persuasive — is exactly the mechanism phases 3 and 4 lean on,
so this is that decision growing teeth rather than changing course.

# Seams left open

- **Goals stay unnamed.** BDI distinguishes desires (all wants) from goals (the consistent
  subset pursued now). Here the worst gap wins attention and that is the whole selection.
  Naming goals earns its place when two desires genuinely conflict — nothing yet does.
- **Desire is denominated in observable properties of the subject, and only those.** An agent
  cannot want anything about *itself* — "keep my balance above 20", "spend less electricity
  looking" — because `ssn:forProperty` points at what its subject exhibits, not at what the
  agent's own operation costs. The concrete trigger for revisiting: an energy budget. Every
  sensor wake is paid for, and today the paying is spread across three mechanisms with no
  region to answer to — urgency interpolates the cadence, review re-picks `slowSleepS` when the
  instrument is quiet, and the metabolic cost debits the wallet. A self-directed desire with a
  stated range (a spend the agent tries to keep inside) would give those three one thing to
  answer to, the same move that gave the target a region. What blocks it is honest: the agent's
  own spend is not a `sosa:ObservableProperty` of its plant, so this needs either the agent as
  a feature of interest of its own metering or a second denomination for desire — a modelling
  decision, not an edit.

  **The third arrival, and the strongest evidence yet.** The sovereign has now reached this
  seam three times from three directions — the energy budget above, the two-forces framing
  that became #137, and, after #135, the observation that the cadence loop has quietly become
  a complete BDI miniature about the agent itself. The isomorphism is exact and nobody
  designed it:

  | desire (about the plant) | cadence (about the board) |
  |---|---|
  | region — deduced from the plant's stated ranges | the constitution's `minSleepS`/`maxSleepS`, plus the board's own `ssn-system:Frequency` |
  | aim — the pick inside, private | the commanded cadence — the agent's pick inside the bounds |
  | observation — what the sensor reports | the ack — what the board says it actually runs (#135) |
  | gap — observed against aim | the mismatch — acked against commanded |
  | unmet after the deadline | disputed after two consecutive mismatches |
  | the act toward the gap — a bid | the re-send of the command |
  | mandate bounds the re-pick | the same mandate, on `slowSleepS` — already there |

  Every row exists in shipped code; only the vocabulary is missing. The ack even behaves as an
  observation in everything but form — testimony, arrival-stamped, judged against intent — and
  is kept out of `:sensed` for exactly this seam's reason: its feature of interest would be the
  board, and the agent does not act for its board. A pattern that reassembles itself
  unprompted, three times, in a subsystem nobody was thinking about desire in, is a pattern
  asking to be named. When someone opens the second-denomination conversation, this table is
  where it starts.
- **No composite distance.** The gap is per property; `max()` of normalised gaps ranks troubles,
  and the envelope already carries the weighting a `desire:weight` triple would duplicate. A
  scalar "wellness" number tells nobody which lever to pull, so it waits for a consumer.
- **Regimes still unexpressed.** A second `desire:DesireGraph` is where a seasonal regime would
  land; the selection mechanism is still missing, unchanged from
  [the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md).
- ~~**Which model, and what context window**~~ — the *when* and the *what-becomes-of-the-answer*
  are now settled by
  [the-model-is-consulted-at-the-edge-of-knowledge](/decisions/the-model-is-consulted-at-the-edge-of-knowledge.md):
  consulted at the edge of knowledge, answer written down as affordance facts, approval split by
  time because the interface is genesis-only. What stays open there is the residue that was open
  here — endpoint as environment, the prompt as a menu derived per #127.

Amended by [a-habit-is-a-compiled-deliberation](/decisions/a-habit-is-a-compiled-deliberation.md):
the amortisation this record names has one rung above it — a stable environment lets the
deliberation itself compile into policy, and review is what compiles and retires it.
