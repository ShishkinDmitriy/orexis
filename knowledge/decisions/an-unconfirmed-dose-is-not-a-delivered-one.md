---
type: Decision
title: An unconfirmed dose is not a delivered one, and it stays spent anyway
description: The status channel a valve has always published on had no listener, so a dose that never happened looked exactly like one that did. Actuation now waits for the device to say what it dispensed, on a deadline derived from that dose's own duration plus a stated grace. An unconfirmed dose is reported and counted but never re-sent — the device refuses replays itself, and over-watering is irreversible where a missed round is not. Getting there needed the runtime to stop handing a message to only the first module that wanted it.
status: accepted
timestamp: 2026-08-11T00:00:00Z
---

# Context

`firmware/pump-valve` has always published what it dispensed, and PR #34 granted the actuating
agent the right to read it. **Nothing did.** So the agent published a dose and assumed it
happened, and three quite different outcomes were indistinguishable from where it stood:

- a valve that never received the command;
- a valve that received it and refused the signature;
- a valve that dispensed exactly as asked.

The device was already telling the truth. `firmware/simulated-valve` publishes on the status
topic after dispensing and stays **silent** when it refuses — signature, replay, nothing to
dispense — so silence is its refusal, deliberately. The only thing missing was a listener.

**[settlement-speaks-rea](settlement-speaks-rea.md) had already named the gap without anyone
noticing it was open.** A claim is a `vf:Commitment`; the valve opening is the
`vf:EconomicEvent` that fulfils it; and REA defines an economic event as an **observed** flow.
Nothing here observed anything. We marked a commitment fulfilled on the strength of having
asked.

# First, the runtime had to stop swallowing the message

`_on_message` returned as soon as a module's `handle` came back true. That read as an
optimisation and was a defect — a second module subscribed to the same topic never saw the
message at all — and it is exactly what [#51](https://github.com/ShishkinDmitriy/orexis/issues/51)
fixed one level down, where `SensingModule.handle` returned after the first *sensor* owning a
topic and a board's second channel went unread.

The module-level version survived because nothing yet wanted one topic twice. This change wants
it: a supplier runs actuation beside hosting, and the old loop would have handed a valve's status
to whichever module happened to come first in the list.

So a message is now offered to **every** module. `handled` means at least one *took* it, not that
every module was asked — the distinction is the whole value of the warning below the loop, which
is what makes a topic disagreement visible and which offering-to-everyone would otherwise silence
for ever. `reading_recorded` immediately above had always worked this way; the two agree now.

`Module.handle`'s own docstring said *"so no other module sees it"* — true, and the defect stated
as the contract. So did `tests/test_runtime.py`, which asserted `len(seen) == 1`.

# The deadline is derived, not picked

A dose is commanded and then confirmed, separated by however long the pour takes plus however
long the bus needs. **The agent already knows the first**: it computed the open-seconds itself,
from the device's own `actuation:mlPerSecond`. So the only thing left to state is the second.

`actuation:doseGraceS` is that slack, and the deadline is `this dose's seconds + the grace`.

This is the same shape as `sensing:readingGraceS`, and for the same stated reason. There the
agent chooses the interval, so staleness has to be relative to it — *"it cannot both decide that
600s between looks is acceptable and refuse a 120s-old number."* Here the agent chooses the dose,
so lateness has to be relative to that: it cannot ask a valve for a ninety-second pour and then
call it late at thirty. An absolute deadline would contradict the agent's own instruction.

Being relative is also what keeps a **slow valve** and a **silent** one apart, which is the whole
distinction being drawn.

# It stays spent, which is the opposite of what the issue proposed

[#36](https://github.com/ShishkinDmitriy/orexis/issues/36) asked for *"at minimum log it; better,
do not treat the claim as spent."* The better option is the wrong one, for two reasons.

**The device refuses replays itself.** `firmware/simulated-valve` keeps its own spent set and
`_refuse("replay", …)` is one of the paths it stays silent on. A re-sent command is therefore
refused rather than poured — so un-spending buys nothing at all, and costs this agent its own
guard.

**And the failures are not symmetric.** If the water flowed and the report was lost, re-sending
risks watering twice. If it never flowed, the plant misses this round and bids again in the next
one — the market self-corrects, which is what a market is for. **Over-watering is irreversible
and a missed round is not**, so the safe direction is to keep the jti spent and say loudly that
nobody confirmed it.

What comes out instead is a number. `doses_unconfirmed` is the honest thing an agent can offer
about a dose it cannot see the end of: it does not know whether the water flowed, and it stops
pretending it does.

# Consequences

- **A valve with no status channel is a deployment, not an error.** `mqtt:statusTopic` is
  optional on an actuator, nothing goes pending without one, and the permanent zeroes in
  `reports()` are themselves the reading — the same argument
  [self-review-is-a-capability](self-review-is-a-capability.md) makes for the absence of revision
  lines.
- **A report for a dose the agent has forgotten is not an error either.** A restarted agent has
  lost its pending set, and the device is right to report anyway.
- **The actuating agent gained its first belief.** Everything that decides how much water flows
  is on the device, because that is a fact about hardware; how long to *wait* is a judgement, and
  judgements are beliefs here.

# Seams left open

- **Nothing reconciles a confirmed dose against what was asked.** The report carries the millilitres
  the device says it dispensed, and this compares nothing — a valve reporting half of what it was
  told would confirm happily. The number is there; using it is not designed.
- **`doses_unconfirmed` counts, and nothing acts on it.** No agent bids differently because its
  valve has gone quiet, and clearing does not learn that a settled trade never landed. Whether an
  unconfirmed dose should reach the market at all is a governance question with no mechanism.
- **The pending set does not survive a restart.** It is in memory, so an agent restarted mid-pour
  neither confirms nor counts that dose. Persisting it would mean deciding what a belief base owes
  an operation still in flight, which nothing else here has needed.
- **The sweep interval is a constant** where the deadline is derived. Five seconds decides only how
  coarsely lateness is noticed, not what counts as late, so it is a resolution rather than a
  policy — but it is the one number here that nobody stated.
