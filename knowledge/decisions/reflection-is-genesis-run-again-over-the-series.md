---
type: Decision
title: Reflection is genesis run again, over the series, and it reads the history and never the beliefs
status: accepted
timestamp: 2026-10-04T21:00:00Z
description: >-
  The sovereign's ruling of 2026-10-04 on where a model may stand in Agent 0.2.0, taking over the
  seam three 0.1.0 records left when the kernel was replaced. The daily routine is BDI and no model
  is in a pass. Reflection - how well do I work, what desire or action is missing, what wants
  recalibrating - is a slow process run from the sovereign's side as genesis is, over the agent's
  series alone, its history and its metrics; it never opens the volume. It answers a fixed set of
  questions first, a model optional, and its output is a proposal in the world's own words that the
  sovereign ratifies into the world as a draft is; the agent adopts nothing privately, and what a
  proposal names the agent's own act revises. Refused - private adoption bounded by shapes, a model
  in the pass, a reader of the beliefs, and a reflection package inside the agent. Measured: what the
  series holds today, and the two things the fixed questions need that it does not yet carry.
---

# What was true

Agent 0.1.0 had a place for a model in three records, each superseded whole by
[agent-0-2-0-replaced-the-kernel](/decisions/agent-0-2-0-replaced-the-kernel.md) and none taken over
since. [llm-heavy-deliberation](/decisions/0.1.0/llm-heavy-deliberation.md) put one call over beliefs,
transcript and wallet at the centre of deliberating, and an intention was how the call was
amortised. [self-review-is-a-capability](/decisions/0.1.0/self-review-is-a-capability.md) made
reviewing one's own settings a family of two members, a reckoning by rules and a `review:Consulting`
reserved for a model, granted where a mandate left room to move.
[the-model-is-consulted-at-the-edge-of-knowledge](/decisions/0.1.0/the-model-is-consulted-at-the-edge-of-knowledge.md)
made the model a teacher asked once per novel gap, and split who approves its answer by TIME: the
sovereign at genesis, and once the society runs the agent alone, adopting the answer privately,
bounded by shapes and wrong at its own cost.

The 0.2.0 tree has no model anywhere. [roadmap](/decisions/roadmap.md) says the member 0.1.0
declared was never built and no seam is reserved for one; the pass is the derivation, a budgeted
search and the executor's walk, and [measure-a-pass](/runbooks/measure-a-pass.md) puts a quiet pass of
the greenhouse's grower at 96 ms and the cold dry bed at 254 ms on the development container. What a
person watches of an agent is its [series](/domain/kernel/series.md): a history of every observation
and every step taken and answered, and metrics of what each pass searched, exhausted, reached nothing
and failed, written by two parts that hear every signal and import no package
([metrics-and-history-are-what-events-say](/decisions/metrics-and-history-are-what-events-say.md)).

The sovereign, 2026-10-04, on what the 0.1.0 idea had been: *in 0.1.0 the idea was to keep the
agent's daily task BDI, and sometimes the agent would think what actions or desires to add, or maybe
initiate calibration. So the LLM was only to reflect on themselves — how well do I work — not the
daily routine.* And on the one objection raised, that a reflection reading no belief cannot know
which calibration to name: *agree, only history, never beliefs. But it should know what to calibrate
— it's beliefs.*

# The claim

**The daily routine is BDI and no model is in a pass.** Nothing changes in the mind: desires derive
wants, the search finds plans, the executor walks them, and every one of those is measured in
milliseconds and runs on every reading.

**Reflection is genesis run again.** [genesis](/decisions/genesis.md) is the sovereign narrating, a
model drafting, the sovereign ratifying and the ratified draft becoming `world/<name>/`. Reflection is
the same four steps with a different first input: instead of the sovereign's story of a world that
does not exist yet, the record of a world that has run. It is a separate, slow process, run from the
[sovereign](/domain/kernel/sovereign.md)'s side on the sovereign's clock — a season, a month, a visit —
over the agent's **series alone**, its history and its metrics. It never opens the agent's volume.

**It answers a fixed set of questions first, and a model is optional.** Each is a reading of the
series that names something in the world's own words:

| the series says | reflection names |
|---|---|
| a want stood `unreachable`, pass after pass, under a desire | an action the world lacks, or a scope that cannot reach the want |
| a step's `landing` timed out, or landed late by a stretch, for one action | a landing band declared wrong, or an instrument past its calibration |
| a desire never read unmet over a season — no `search` tagged with it | dead weight, a desire to retire |
| every `search` under a desire ended `exhausted`, the budget spent | a budget too small or an estimate too weak |
| a probe's history sat past a calibration point for stretches in soil never flooded, or its raw count has not moved for days | a recalibration to schedule |

That list is what an `orexis-explain` would be — an operator command gathering one agent's figures
from the series into a report that answers these — and it is the model's tool before it is the
person's: a model asked to reflect reads that report, not the buckets. What the fixed set answers
without a model is the first tool's done-when; what needs a model is whatever the fixed set cannot.

**Its output is a PROPOSAL in the world's own words**, and only that: a desire with its met-test, an
action with its precondition and effect, a recalibration to schedule, a budget to raise. The sovereign
ratifies it into `world/<name>/` exactly as a genesis draft is ratified, and a running agent re-reads an
updated public document at its next boot as it does any amendment. The agent adopts nothing privately.

**Reflection names; the agent's own act revises.** A proposal says WHICH probe, WHICH action, WHICH
desire. It changes no belief. What it names is then changed by the one door every belief changes by:
a document the sovereign ratified, or a step the agent takes whose effect writes the new fact. The
sovereign's objection is answered by what the history is tagged with — every observation point is
tagged `sensor` and `feature`, every step `action` and `want` — so a probe is named by its tag and
no belief is read to find it.

Two consequences follow, and both bind.

**A. The history must carry enough to judge the agent without its beliefs.** Anything reflection
would need and cannot get from the series is a GAP IN WHAT THE AGENT REPORTS, never a licence to read
the beliefs. Measured on this tree, two of the five questions above already find one:

- `agent/sensing/events.py` writes an observation's point with one field, `value`, which
  `agent/sensing/create.py` reads off `sosa:hasSimpleResult` — the reading, after the scaling and the
  calibration the world states. The raw count (`sensing:rawResult`) is on no point. So "a raw count
  that has not moved for days" cannot be asked of the history today, and "past a calibration point"
  can only be asked of the reading, which a past-the-point count makes read past 1.0 — askable, but
  through the very scaling under doubt. The raw count beside the reading is the first thing the
  history must gain.
- Sensing says `sensing:stuckSince` and `sensing:silentSince` in the agent's state graphs, and reports
  on the metrics one level, `silence`, how MANY sensors are silent now (`Silence` in
  `agent/sensing/events.py`); nothing says which, and a sensor said stuck is on no metric and no point.
  A reflection asking which probe went quiet can infer it from the gaps in that probe's history, which
  is the honest reading; a flag per sensor is the second gap.

**B. "Is a recalibration due" has two homes, and that is not a duplicate.** #862's first step is a
desire of the agent's whose met-test reads a recalibration due off its own beliefs — fast, in the
pass, the agent's judgment, answered by a want and a plan walked with a person. Reflection asks the
same question over months of history — slow, outside the pass, the sovereign's, answered by a
document offered back. One is a judgment in the pass and the other a proposal outside it; they differ
in the clock they run on, the data they read and who acts on the answer, and a desire that the agent
could not author for itself — because it does not yet know what a drift over a season looks like — is
exactly what a proposal would hand it.

**What the calibration IS today, since the proposal has to be in the world's words.** The brief this
record was written from said the points had become the agent's belief under #861, revised by an
`orexis-calibrate` tool. That is not what landed: #861 built that and struck it, and
[an-observation-is-concluded-from-the-number-a-sensor-gave](/decisions/an-observation-is-concluded-from-the-number-a-sensor-gave.md)
records the refusal. A probe's [scaling](/domain/sensing/scaling.md) and a thermometer's
[calibration](/domain/sensing/calibration.md) are objects the WORLD states beside the sensor —
`world/terrace/world.ttl` holds the terrace's `sensing:TwoPointScaling` — and recalibrating is two
numbers edited and the agent restarted ([calibrate-a-probe](/runbooks/calibrate-a-probe.md)). So a
recalibration proposal is, today, exactly a genesis amendment: an edit to the world the sovereign
ratifies. When #862 lands and the points are written by a `calibrate` step's effect, the proposal
becomes the desire that step is walked under. Either way reflection names the probe and writes
nothing, which is the claim.

# What was refused

- **The 0.1.0 clause that let the agent adopt a model's answer privately, bounded by shapes, once
  the sovereign is absent.** It rested on the interface being a genesis-time thing, so that at runtime
  nobody could be asked. In 0.2.0 the world is documents, a running agent re-reads an updated public
  document, and beliefs are the agent's and authored once at birth
  ([where-the-belief-base-lives](/decisions/where-the-belief-base-lives.md)) — so there IS a channel
  that needs nobody present, the world's directory, and the sovereign is absent only from the pass,
  not from the society. An answer the agent adopts privately is a belief nobody ratified, in a store
  nobody but the agent opens, which nothing can diff against the world and no second agent would
  share; it is the one kind of fact this project has no provenance for.
- **A model in the pass**, the direction `llm-heavy-deliberation` set. The pass is measured in
  milliseconds and runs on every reading; a model call is seconds and a cost per call. In 0.1.0 an
  intention existed to amortise the call, and in 0.2.0 the pass needs no model to amortise — the
  search is bounded by a budget in the unit it spends and continued by the next pass. A model that
  the pass waits on makes every reading cost what the slowest call costs.
- **Reflection reading the beliefs**, by opening the volume as the struck `orexis-calibrate` did.
  Rule 4 says there is no shared store and the volume is the agent's; a reader of the volume is a
  second writer waiting to happen — the struck tool stopped the agent to read and write it; and the
  series exists precisely so that what a person watches is never what the agent believes — a series
  read back is no longer a series, as its page says. The sovereign's objection, that reflection must
  know what to calibrate, is met by the tags the history carries and by consequence A, not by a read.
- **A reflection package inside the agent.** To read every package's events it would import every
  package, which `metrics-and-history-are-what-events-say` refuses for the two parts that already
  hear them; and it would run on the agent's clock, in the agent's process, when the question is the
  sovereign's and the clock is a season's. A package that asks how well the agent works is not a
  package of the agent any more than the dashboards are.

# What it emits

An issue for the first tool: an operator command, beside the onboarding commands and outside
`agent/` as they are, that gathers one agent's figures from its history and metrics buckets into a
report answering the fixed questions above, model-less, measured on the simulated greenhouse at a
fast pace (`OREXIS_TIME_PACE`, which `agent/clock.py` reads) so a season is an afternoon. Its
done-when carries consequence A's two gaps — the raw count on the observation's point, and a sensor
said stuck or silent named on the series — since the tool cannot answer the fifth question without
the first. Filed as [#894](https://github.com/ShishkinDmitriy/orexis/issues/894) once the sovereign had read
this record.

# Seams left open

- **The model is optional and no model is wired.** The fixed set is answered by queries over two
  buckets; where a model is wanted, what it is handed is the report, and its endpoint is environment
  per rule 5. Nothing here declares a term for it, and the vocabulary a proposal is written in is the
  world's own, so no reflection vocabulary is needed until a proposal cannot be said in it.
- **Which questions the fixed set answers** is the first tool's done-when and will grow with the
  worlds; a question added is a row in the table above and a query in the tool, and a question the
  series cannot answer is a gap in the history by consequence A.
- **How a proposal is ratified** is undecided: a pull request against `world/<name>/` the sovereign
  merges, or a chat with the sovereign as #862 sketches for the recalibration plan, or both. Either
  is genesis's ratify step with a different carrier, and the choice waits on the first proposal worth
  carrying.
- **A proposal about a desire's RANGE reaches down a level.** "The fern keeps hitting rot at your
  stated range — narrow it?" is a proposal about a value, and the ratifier must refuse it or own that
  it is the sovereign picking, which the sovereign may; what reflection may propose on its own
  authority is what is missing or wrong — an action, a desire, a band, a calibration — never a
  figure inside a desire ([control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md)).
- **Whether an agent's own word about itself is what reflection reads about the agent.** #876 would
  give the agent a document of its own stances — its patience, its budget, its silence limit. Those
  are beliefs, so by this record reflection does not read them; but a budget exhausted every pass is
  a proposal ABOUT one, and a stance is authored in the world, so the proposal is an edit to a world
  document as any other is. Whether the tool is handed the world's documents as well as the series
  — public, ratified, nobody's belief — is open, and the honest default is that it is, since the
  world is what the proposal is written against.
