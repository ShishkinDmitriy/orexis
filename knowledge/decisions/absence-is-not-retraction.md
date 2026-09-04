---
type: Decision
title: There is no belief update function — absence is not retraction, and validity is a window
description: >-
  Jason's `buf` is handed the whole percept set each cycle and deletes whatever is no longer
  perceived, which is how a fact stops being believed with nobody retracting it. Readings here
  arrive pushed and one at a time, so there is no snapshot to diff and silence means nothing.
  Decided that we hold no belief update function at all — a reading is upserted and never
  expires, and NOT-CURRENT is a want rather than an absence — and that a fact which stops being
  true by the clock gets one of three treatments, chosen by whether its absence is itself
  evidence.
status: accepted
timestamp: 2026-08-26T22:30:00Z
---

# What the other half of the split does

[a-hook-is-a-term](/decisions/a-hook-is-a-term.md)'s neighbour in the literature is Jason's pair.
`brf` performs one update and reports what changed — that is the seam
[layered-by-timescale-and-interruptibility](/decisions/layered-by-timescale-and-interruptibility.md)
calls the interface, and `packages/orexis-agent-deliberation/reviser.py` is ours. `buf` is the other one: handed the
**complete current percept set** every cycle, it adds what is perceived and not believed and
**deletes what is believed and not perceived**. Snapshot semantics — how *the block is no longer
on the table* happens without anyone sending a retraction.

# What is decided

**We hold no belief update function, and could not.** A reading is a message, pushed, one
property at a time; there is no moment at which this agent holds everything true right now. If
silence were retraction, a board that missed one publish would delete its pot's moisture and the
agent would believe **nothing** where it had believed something old — strictly worse, because a
stale value carrying its instant is still evidence and a hole is not.

**So not-current is a want, not an absence.** The observation is upserted — `sensed_writer`
deletes only the node it is about to rewrite — and stays on disk for ever; what changes when a
board goes quiet is that the freshness want stops being met
([the-stake-is-sensings-want](/decisions/the-stake-is-sensings-want.md)). That is why a dead
probe's last reading survives and the agent still knows it is blind: staleness is a first-class
fact rather than a missing one, and it can be planned about, ranked, and repaired by looking.

**A fact that stops being true by the CLOCK gets one of three treatments, and which one is not
a style question.** Ask whether the fact's absence is itself evidence:

| treatment | when | here |
|---|---|---|
| **retract** | the absence says nothing worth keeping | a round past its `closesAt` — a bidder is never told a round closed, so the clock ends the row (`rounds.sweep_expired`) |
| **keep and mark** | the absence IS evidence | an [obligation](/domain/obligation.md) past `orexis:expiresAt` — a debt nobody presented is a fact about a counterparty, so it is `lapsed` and unpursuable, never deleted |
| **keep and let a want go cold** | the fact is still the best evidence there is | a reading past its horizon — kept, with its instant, and the want about knowing goes unmet |

**Which rules out the tempting generalisation.** A single sweeper that retracted anything past
its validity window would be wrong twice over: it would delete a lapsed debt, which is exactly
the evidence a creditor wants, and it would delete a stale reading, leaving an agent that cannot
tell *dry an hour ago* from *never measured*. Three words in three namespaces —
`market:closesAt`, `orexis:expiresAt`, `sensing:staleAfterS` — are not duplication; each belongs to
the owner that knows which treatment its fact deserves.

# What this does not solve

A fact that becomes false for a reason other than the clock — somebody else watered the pot — is
detectable only by looking. That is what the expectation machinery is for
([an-intention-stands-until-the-world-answers](/decisions/an-intention-stands-until-the-world-answers.md)),
and it is the same reason looking is an [act](/domain/act.md) with a cost rather than a
background refresh.

# Seams left open

- **The nearest thing to a snapshot is a retained message**, delivered on connect, and nothing
  treats it specially: it arrives as an ordinary reading with the instant it was published. A
  reconnect is therefore the one moment a buf-shaped diff would be possible, and we do not take
  it.
- ~~**The round sweep runs on one agent's one event.**~~ Closed (#398). Retracting what the
  clock has ended is a choir hook, `orexis:sweep`, asked on the agent's own housekeeping tick —
  the one clock every agent has, because keeping your own house is not a capability. The
  kernel asks and never sweeps: which fact expires, and which of the three treatments it
  deserves, stays with its owner. What the tick guarantees is BOUNDEDNESS rather than
  promptness — it is hourly, and a bidder still sweeps on an offer because a round beginning
  with yesterday's rows standing reads oddly in a trace.
- **No belief carries its own validity in the kernel's words.** `progression:notAfter` exists for an
  ACT, and the same shape would fit a fact; nothing needs it yet, and inventing it before a
  third treatment appears would be the generalisation this record refuses.
