---
type: Decision
title: An observation is a percept, and the mind reads only what belief revision makes of it, in the domain's words
description: >-
  The sovereign, 2026-10-09 - an observation is not a belief; it is what a sensor said. Decided - an
  observation is a percept, sensing's own, named per reading, linked to the one before it, kept as
  deep as sensing's rules read and handed to no reader of the mind. Belief revision makes of the
  latest percept of a key ONE belief, in the domain's words - the bed is dry - and no number,
  replacing the belief before it whole, and judging the percept beside that belief, so a state is
  held by the belief itself and the hysteresis needs no previous observation. One rule judges every
  range with its margin and the domain names the states. A predicted number becomes a predicted
  belief the same way, beside the belief before it. Stuck is a rule over the last percepts kept.
  Desires, preconditions and effects speak the belief, an action takes the subject and not a
  reading, and the number is read off the percept by its two readers at the boundary alone,
  prediction and a command sizing its step when it is taken; planning's and execution's code are
  untouched. Amended the next day - the belief holds no value. Refused - the observation as the
  belief, summaries a writer carries onto the present, a side re-derived from the last N numbers,
  the hold read off the previous percept, a predicted number judged bare, and a hold written once
  per property.
status: superseded-in-part
superseded-by: a-transition-changes-the-state-and-an-inference-only-concludes
timestamp: 2026-10-09T20:00:00Z
---

> **Superseded in part, 2026-10-10: the domain's transition makes the belief, and no rule of
> sensing's judges every range.** What stands: an observation is a percept, the mind reads beliefs
> in the domain's words, and a state is held by the belief it replaces. What goes: one rule of
> sensing's judging every range with the domain naming the states, and the refusal of a hold written
> per property — [a-transition-changes-the-state-and-an-inference-only-concludes](/decisions/a-transition-changes-the-state-and-an-inference-only-concludes.md)
> makes the belief a domain's transition, triggered once by the observation arriving, deleting the state
> before and inserting the new one, and engages that refusal there.

> **Amended 2026-10-10 (#947): the belief is the state, and holds no number.** As first decided, the
> belief carried the subject's value beside its state — "its moisture is 0.3001" — so that a command
> could size a dose and a drift a rate from it. Nothing in planning reads a number: the met-tests,
> the preconditions, the effects and the costs read the side. The number's readers are a command,
> sizing a step when it is taken, and prediction's drifts, an estimator's rates — the effectoric and
> the perceptual side of the boundary, neither of them the mind. So the number stays the percept's,
> and they read it there. Copied into the belief it was the percept's testimony said twice, and it
> moved the belief, and with it the mind's present, on every reading that wobbled inside its state.
> The body below is amended to that.

# The question

#944 began as a side flipping on a reading's noise, and three builds answered it in a day: a
hysteresis held by the want, then by sensing with the side before carried onto the observation in
the kernel's words, then the same with the words in sensing and a prediction reading no margin. The
last left an agent with no pump committing waits for a stretch ahead that read inside while the
present read below — the same number judged twice, once with a memory and once without.

The sovereign named what the three had in common: they all treat the observation as the belief.
An observation is what a sensor said at an instant. What the agent believes — the bed is dry — is
what revision makes of it, and the mind should read that and nothing else, in the words of the
domain the agent acts in, abstracted from how any sensor is wired.

# What the tree held, read on 2026-10-09

- **One observation per sensor, replaced in place.** A sensor's latest observation is one node,
  `observation_by(sensor)` in `agent/sensing/ontology.py`, in one graph the next reading replaces
  whole (`agent/sensing/received.py`). Its sides are revisions of that graph.
- **The mind reads that node directly.** The greenhouse's desire (`world/greenhouse/desires.ttl`)
  and both allotment growers walk `orexis:actsFor` back along `sosa:hasFeatureOfInterest` to it and
  ask `sensing:below`. The dose, the heat and the market's claim-and-dose
  (`domains/actuation/actions.ttl`, `domains/climate/actions.ttl`, `domains/market/actions.ttl`)
  take it as their `$reading` parameter: the precondition asks its side, `landsAfter` reads its
  sensor's cadence through `sosa:madeBySensor`, the effect deletes `sensing:below` and constructs
  `sensing:inside` on it, and the command sizes the dose from its `sosa:hasSimpleResult`. The soil's
  drying (`domains/actuation/drifts.ttl`) takes its rate from the reading's number, and rain
  (`domains/climate/drifts.ttl`) from a forecast observation's band. Prediction
  (`agent/prediction/predict.py`) reads the observation in hand and writes a predicted
  `sosa:Observation` per stretch, which the rules judge and the planner reads.
- **Planning's and execution's code name no SOSA word.** They are generic over triples; the reading
  enters them through the domains' texts alone.
- **History was carried as summaries, because only one observation was kept.** The run of an
  unchanged number rides on each observation as `sensing:unchangedSince` (#462), and #946's build,
  unmerged, carried the side the reading before was judged on as `sensing:wasBelow` and
  `sensing:wasAbove`.
- **The world's hash takes an IRI by identity** and only a blank node by its content
  (`agent/hash_named_graph.py`), so anything the mind reads needs a name that does not change with
  every reading.
- **A rule concludes beside its source and never deletes** (`agent/belief/revise.py`), and what
  replaces a conclusion is its source rewritten.
- **The stack already had the row this skipped.** [the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md)
  draws translation, then BRF — "what counts as a belief change" — then the mind. The tree wired
  translation's output straight into the mind.

# The decision

**An observation is a percept, and it is sensing's own.** Each reading is its own node, named when
it arrives, linked to the one before it (a `previous` link of sensing's), and sensing keeps as many
of a sensor's percepts as its rules read — the last few for stuck — and forgets the oldest as a new
one comes. A percept is testimony, kept as the premise
([a-situated-instance-is-kept-only-when-it-is-testimony](/decisions/a-situated-instance-is-kept-only-when-it-is-testimony.md)),
and it is concluded from the number the sensor gave exactly as
[an-observation-is-concluded-from-the-number-a-sensor-gave](/decisions/an-observation-is-concluded-from-the-number-a-sensor-gave.md)
says. What changes is who reads it: a percept is a graph of a kind no reader of the mind is handed
— not the planner, not a desire, not the imaginarium, not the hash — so a name per reading costs
the mind nothing, and several percepts of one sensor leave no doubt about which is the present.

**Belief revision makes of the latest percept of a key one belief, in the domain's words, and the
mind reads nothing else.** For a key — a subject and a property — the belief says what the agent
holds true of the subject: its state, which the domain names (the bed is dry), and no number. It is
about the subject, whose IRI does not change, and it speaks no SOSA: the domain's words only. A
desire asks "the bed is not dry"; the dose takes the bed, not a reading, and its effect turns dry into
its state inside the range. The number stays the percept's [reading](/domain/sensing/reading.md),
read there by the two readers at the boundary: the dose's command, sizing it when it is taken, and
the drying drift, prediction's rate — the effectoric and the perceptual interface, neither of them
the mind, which compares triples and interprets no literal. The world's description of which sensor
a subject hosts and the ranges it states stays in SOSA and SSN, since it is sensing's
configuration and not an observation.

**A belief is replaced whole, by what the rules conclude from the percept beside the belief it
replaces — and that is where a state is held.** The memory a hysteresis needs is the state judged
before, and the belief IS that state. A range's condition states one margin, the world's figure for
its probe's noise; a value coming from another state crosses at the bound, and a state held stays
until the value clears the bound by the margin. So the bed believed dry stays dry at 0.3001 against
a floor of 0.30 and a margin of 0.0002, because the belief it replaces is dry — no previous
observation is read, no side is carried, and no rule remembers anything the store does not hold.

**One rule judges every range, and the domain names the states.** The judgment — the bounds, the
margin, the state before — is written once, by sensing, which speaks SOSA, SSN and the margin; the
domain declares which of its words says each side of which property. The judgment cannot drift
between properties, and a domain adds a property by naming three states.

**A predicted number becomes a predicted belief the same way, beside the belief before it.**
Prediction stays the estimator it is: it reads the percept in hand and the drifts, cuts the horizon
where the number crosses a bound, and writes a number per stretch, reading no margin. Revision
judges each stretch's number into a predicted belief beside the belief before it — the present
belief for the first stretch, the stretch before for the rest — so a bed believed dry and resting at
0.3001 is foreseen dry, and the planner waits for no stretch that the present will never show. A
predicted number carries no instrument's noise; the state it is judged into is held, as every
state is.

**Stuck is a rule over the percepts kept.** Sensing keeps a sensor's last `sensing:stuckAfter`
percepts, and a rule says the sensor stuck when every one of them carries the same raw number. The
run's start carried onto each observation (`sensing:unchangedSince`) and the code that counts it
in `received` go.

# Why

**A percept is what a sensor said, and a belief is what the agent holds — two things, kept apart.**
Merged, the mind reads SOSA and sensing's side words, so a desire depends on how a bed's sensor is
wired, and the one node per sensor forced every scrap of history the rules needed to be copied onto
the present by its writer. Apart, the mind speaks the domain, and sensing keeps what its own rules
need of the past, honestly, as the percepts themselves.

**A Schmitt trigger's state is its output, not its last input.** The hold needs the state judged
before, and the state judged before depends on the state before it, all the way back. The belief
is that state, and keeping it is keeping the whole history in one triple; nothing older is needed.

**The belief is written, not re-derived, and that is its difference from a side.** A side today is
a revision, concluded beside its observation and re-derivable from it. A held state is not
re-derivable from the latest percept, since one of its premises is the state it replaced; so the
belief is revision's state, kept and replaced whole, as the intentions are the executor's. That is
the one conclusion kept beside testimony, and it is kept because a premise of it is gone.

**One judgment for the present and the foreseen.** Judged two ways — the present beside its
history, a predicted number bare — the forecast contradicted the present on a number that had not
moved, and the planner believed the forecast: three waits in an hour of readings held at 0.3001,
two in the straying case, twelve in thirty cadences of the noisy simulator, each sending nothing,
measured on #946's build. Judged one way, there is nothing to contradict.

# What was refused

- **The observation as the belief** — the tree as it stood. It made the mind speak SOSA and
  sensing's side words, gave an action a reading for a parameter where the subject is what it acts
  on, and allowed one observation per sensor, so history had to travel as summaries.
- **Summaries a writer carries onto the present** — `sensing:unchangedSince` (#462) and #946's
  `sensing:wasBelow` and `sensing:wasAbove`. Each is the writer copying a fact about the past onto
  a fact about now, in a word that exists only to be copied. The hold is the belief's and stuck is
  the percepts', so neither needs one.
- **A side re-derived from the last N numbers.** Readings of 0.2990, 0.3001, 0.3001, 0.3001 against
  a floor of 0.30 and a margin of 0.0002 are below four times. Re-derived from the last two numbers,
  the third is judged beside a 0.3001 that has lost its own predecessor, reads inside, and the hold
  is gone after one reading in the band; from the last N, after N. No depth of numbers recovers a
  state that has been held longer than the depth.
- **The hold read off the previous percept's side** — the link and the side the percept before was
  judged on. It works, since that side was concluded while its own predecessor stood, but it asks a
  percept for what the belief already says, and keeps a percept for every key for the hold alone.
- **A predicted number judged bare** — #946's last build, with the waits measured above.
- **A hold written per property** — each domain's rule holding its own states by its own margin.
  The judgment is one thing, and written per property it is written again and drifts; the domain's
  part is the names.
- **Sensing's side words in the mind** — `sensing:below` in a desire and an effect. They tie what an
  agent wants to how a reading is judged, where the domain's state says what the agent wants it
  about.

# Consistent with, and named so it is not mistaken for a reversal

- **[a-belief-is-crisp-and-an-estimator-may-reason-with-probability](/decisions/a-belief-is-crisp-and-an-estimator-may-reason-with-probability.md)**
  stands for what a belief is — a crisp triple, never a probability a reader weighs. Its hysteresis,
  held by sensing with the side carried and a prediction judged bare, is superseded here.
- **The rules run on the present only**, a percept when it arrives and a prediction when it is
  predicted, never in a search; an effect still writes its own conclusion, now in the domain's words.
- **A world is hashed within what is read**, and what is read is now beliefs about subjects, whose
  names hold still.

# Seams left open

- **The words.** Which state words each domain declares, per property, is the first slice's, and
  each gets its page before it is used.
- **A state change foreseen out of a held state is placed early.** Prediction cuts a stretch where
  the number crosses the bare bound, so a bed rising from dry is foreseen inside from the floor,
  where the present will say so only past the floor and the margin — early by the time the number
  takes to cross the margin. The trigger is a plan placed on that instant and failing at its landing.
- **When a dose lands is still read through the world's description.** `landsAfter` finds the
  sensor a subject hosts and its cadence in SOSA's words, since no belief says when it is next
  revised. A belief stating that would remove the last SOSA word from the domains' actions.
- **Stuck counts readings, not time.** A sensor that misses readings is said stuck later than one
  that never misses; `sensing:stuckAfter` keeps its unit of cadences, and the percepts kept are that
  many.
- **How deep sensing keeps percepts** is what its deepest rule reads, stuck today; a rule reading
  further back widens it, and a percept is never a series — a series is watched, never believed.
