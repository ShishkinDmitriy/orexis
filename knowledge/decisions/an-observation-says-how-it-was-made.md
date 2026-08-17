---
type: Decision
title: An observation says how it was made, and a procedure is named for what it does
description: A reading now carries sosa:usedProcedure — the sensor's sense mode — because whether a missing reading means a late board or a quiet one was recoverable only by joining back to the sensor. The three modes are renamed to read as procedures rather than states, since #95 made them sosa:Procedure instances and a Procedure is a plan. The rename crossed seven spellings, one of which left the process and would have silently changed a simulated device's behaviour, and one of which arrived on another branch after the sweep was complete.
status: accepted
stage: v1
tags: [sensing, ontology, naming, provenance, reuse]
timestamp: 2026-08-12T00:00:00Z
---

# Context

[one-word-for-one-relation](one-word-for-one-relation.md) typed the three sense modes as
`sosa:Procedure` alongside `sensing:SenseMode`, and deliberately kept the *relation* ours.
It left two things it did not look at.

**Nothing cited a procedure.** `agent/sensed_writer.py` writes a complete `sosa:Observation` —
feature of interest, observed property, simple result, result time, made-by sensor, world
version, author — and never said by what method. The W3C's own worked example does, and
`sosa:usedProcedure` was the one predicate of theirs we had no answer for.

**And the names read as states.** `sosa:usedProcedure sensing:Scheduled` says an observation
used a procedure called *Scheduled*, which is an adjective. A `sosa:Procedure` is a **plan** —
*"a workflow, protocol, plan, algorithm, or computational method specifying how to make an
Observation."*

# Decision — the modes are named for what they do

| was | is | agent capability |
|---|---|---|
| `sensing:Pull` | `sensing:PolledProcedure` | `sensing:Polling` |
| `sensing:Scheduled` | `sensing:ScheduledProcedure` | `sensing:Subscribing` |
| `sensing:Push` | `sensing:PushProcedure` | `sensing:Listening` |

Each keeps its mode word. That was the constraint, not decoration: the pairing in
[who-holds-the-clock](who-holds-the-clock.md) is what the whole family is about, and a name that
lost the tie to its capability would have cost more than the elliptical reading did.

This record shipped them as `…Sensing` — SOSA's own word, free, and used by nothing else here.
That spelling has since been superseded by `…Procedure`, for a reason this record could not have
seen: it did not yet have a use site where the name is read aloud. See
[a-sensor-implements-its-procedure](a-sensor-implements-its-procedure.md), and the amendment
table in [who-holds-the-clock](who-holds-the-clock.md), which is where these spellings are
tracked. The table above shows today's names against the ones this record replaced.

## The first names were wrong, and the reason generalises

They were `ScheduledSampling`, `PushReporting` and `PolledSampling`, and both compounds were
taken:

- **`Sampling` is `sosa:Sampling`** — *"an act of Sampling carries out a sampling Procedure to
  create or transform one or more samples."* It produces a `sosa:Sample`: a specimen removed and
  examined. Our probes sit in the soil and remove nothing, so the name imported a concept we
  deliberately do not model — and one that is the subject of an open issue.
- **`Reporting` is ours.** `capabilities/reporting/` was created eight commits earlier for
  telemetry an agent emits *about itself* — `reporting:Storing`, `reporting:Announcing`. A
  sensing procedure called `PushReporting` is a second sense of that word, in one codebase,
  introduced the same day.

**The root word was checked and the compound was not.** *Procedure*, *sensing* and *mode* were all
weighed against SOSA and against our namespaces; `Sampling` and `Reporting` arrived as suffixes
and were never asked the same question. That is the third time this project has been caught by a
name that read cleanly in isolation — after `matching` against `provider(family)` and
`calibration` against the procedure that produces one — and the first where the collision was with
a term this repository had itself created that week.

A compound is a new name. Check it whole.

**`sensing:SenseMode` stays, and it is not a synonym for `sosa:Procedure`.** It is the
constrained subset. `sensing:senseMode`'s range being `SenseMode` is what stops a sensor
naming any procedure at all, and the derivation is guarded on exactly these three; `sosa:Procedure`
is too wide to say that with. The same reasoning kept the *relation* ours in the record above.

# And an observation cites one

```turtle
ag:obs_fern_SoilMoisture a sosa:Observation ;
    sosa:hasFeatureOfInterest ag:fern ;
    sosa:observedProperty water:SoilMoisture ;
    sosa:hasSimpleResult "0.183"^^xsd:decimal ;
    sosa:resultTime "…"^^xsd:dateTime ;
    sosa:madeBySensor :moisture_sensor_fern ;
    sosa:usedProcedure sensing:ScheduledProcedure ;
    ag:underWorldVersion 1 ;
    prov:wasGeneratedBy :fern_agent .
```

**What it buys is what a *missing* reading means.** These are different claims, and the number
cannot tell them apart:

- *"0.183 at 13:22, on the interval the agent asked for"* — silence afterwards means the board is late
- *"0.183 at 13:22, because the board chose that moment"* — silence may mean nothing happened worth reporting

Until now that was knowable only by joining an observation back to its sensor. One join away from
nobody making it, and this project has found more than one fact that lived exactly there.

## It is the clock, not the whole method

The sense mode is *when* a reading was taken. The codec, the pointer and the scaling are also how
that number came to be. SOSA asks for *"a relation to link to **a** re-usable Procedure"*, not the
complete method, so a partial answer is a legitimate one — but it is partial, and worth saying so:
if the whole pipeline is ever modelled as a Procedure, this predicate gets **re-pointed** rather
than a second one added beside it.

Some of the rest of the method is now named — a one-wire transaction, a combined read, an MQTT
publish — and named on the systems that perform them rather than on the observation. Nothing
re-points yet, because an observation citing a procedure is a claim about *this reading* and
`ssn:implements` is a claim about the equipment; joining the two is what
[a-procedure-belongs-to-whatever-performs-it](a-procedure-belongs-to-whatever-performs-it.md)
leaves open.

# The rename crossed seven spellings, and one left the process

[every-term-in-its-own-house](every-term-in-its-own-house.md) recorded that a term is named seven
ways here and that six of them fail silently. This is the second live case, and it is the first
where a spelling crossed a **process boundary**.

`onboarding/compose.py` built the simulator's environment by lowercasing the IRI's local name:

```python
mode = (row.get("senseMode") or "").rsplit("#", 1)[-1].lower() or "scheduled"
```

`firmware/simulated-sensor/simulator.py` compares that against `"push"`. Renaming would have sent
`SIM_SENSE_MODE: "pushreporting"` to a container that then quietly kept an interval instead of
clocking itself. **Nothing would have failed**: the world validates, the container starts, and the
only symptom is a self-clocked stand-in behaving like the other kind — in a world where every
shipped device is scheduled, so the push branch is exercised by nothing.

The mapping is stated now. **The env word is the simulator's contract and the IRI is the society's
vocabulary**, and they are allowed to differ; deriving one from the other is what let a rename
reach across the boundary. Saying it once, in one dict, is what stops the next one.

The other five: prefixed TTL and SPARQL, a `term()` builder, a Python constant, a full IRI inside
a `sh:sparql` `VALUES` clause in `transports/mqtt/shapes.ttl` — the form `tests/test_store.py`'s
scan cannot see — and prose still spelling them `ag:` from before the namespace sweep.

One of those prose copies is in `onboarding/compose.py`, four lines above the `_SIM_MODE` lookup,
and it is **emitted into every generated `compose.yaml`**. So the rename changes a generated
grant: `world/simulation/compose.yaml` differs from `main` in three identical comments and in
nothing else — no value moved, `SIM_SENSE_MODE` included. A comment is the safest thing that
could have differed there, and it is worth knowing that anything in that file can.

## The seventh arrived after the sweep, from another branch

The enumeration above was complete when it was made, and was **stale by the time it merged**.
[their-descriptions-are-our-fixtures](their-descriptions-are-our-fixtures.md) landed on `main`
while this branch was in flight, bringing `tests/fixtures/w3c-ssn/deploy-dht22.ttl` — the
deployment half this project writes to sit beside a vendor's part description, and it names a
sense mode twice. Rebasing produced no conflict in that file, because nothing on this branch had
ever touched it; it simply began failing.

**A rename is not a closed set of files, it is a claim about a whole tree at one instant.** No
sweep can cover a file that does not exist yet, so the guard cannot be diligence — it is that a
stale spelling is *refused*. It was, and by the two tests that had most recently been written
about something else entirely.

## Their reading cites a procedure, and is still refused

`<observation/1087>` is the one node in the fixture set that answers `sosa:usedProcedure` —
`<DHT22#Procedure>`, their own. Our shape rejects it anyway, on `sh:class` rather than
`sh:minCount`: it is a `sosa:Procedure` and not one of the three `sensing:SenseMode`
instances.

That is the constrained-subset argument above, arriving from outside as evidence rather than as
reasoning. Had `senseMode`'s range been `sosa:Procedure`, a vendor's illustrative procedure would
have satisfied a shape whose entire purpose is to guard a derivation keyed on three specific
instances — and it would have derived nothing, silently. The residue is unchanged because that
node was already refused for six other reasons; no expectation moved.

## A record about a rename had to be repaired by hand

`who-holds-the-clock` recounts an **earlier** rename of these same modes: *"`sensing:Pull` is
now `sensing:Scheduled`"*. Renaming mechanically turned that into *"`PolledSampling` is now
`ScheduledSampling`"* — false, since those are two distinct current terms. The sentence now names
the spelling it means, and the record carries an amendment table.

A find-and-replace over a document that is *about* naming will falsify it. Worth knowing before
the next one — which arrived immediately, and then a third time. Each rename has had to **add a
column** to that table rather than rewrite it, and to walk the sentence recounting the first
change forward by hand: *"two renames"*, then *"three spellings"*, now *"four"*. The third pass
falsified this very paragraph, which had recorded the second one in the past tense.

**The later renames are also what proved the `_SIM_MODE` fix.** Renaming `PushReporting` to
`PushSensing`, and then to `PushProcedure`, changed the dict's keys twice and left its values —
`"push"`, `"scheduled"`, `"pull"` — untouched both times, because the simulator's contract is not
the society's vocabulary. Under the old derivation each of those would have sent `"pushsensing"`
and then `"pushprocedure"`, breaking a device twice more in the same silent way.

# Consequences

- **A shape requires the citation**, so a sensor with no sense mode never reaches the writer —
  the world is refused first. Proved by mutation: an observation lacking it is refused, with its
  own message.
- **The stale spelling is refused rather than ignored.** Putting `sensing:Scheduled` back into
  a world fails validation on `senseMode`'s range, which is the difference between a rename that
  is caught and one that silently derives nothing.
- **Prose from before the namespace sweep is corrected.** `ag:Scheduled` survived in the README
  and the firmware documentation; those lines had to change anyway.

# Seams left open

- **The mode is still the sensor's, and it describes a board.** Its own definition says *"this is
  what a deep-sleeping battery board is"*, and all three of the fern board's sensors state it
  independently — so an observation cites a fact copied three times. That is
  [#96](https://github.com/ShishkinDmitriy/agora/issues/96); when the mode moves to the board, an
  observation will cite the board's procedure, which is more accurate still, since the firmware
  holds the clock and the sensing element does not.
- ~~**`ssn:implements` is the standard relation and we do not use it.**~~ **Half-closed, and the
  half matters.** It is in use — a DHT11 states two procedures with it — and it is still not the
  relation between a sensor and its sense mode, for the reason given above: it is wider than
  `senseMode`, which carries `sh:maxCount 1` and guards a derivation. What changed is that the
  two predicates now visibly answer different questions rather than one appearing to be a
  home-made stand-in for the other. See
  [a-procedure-belongs-to-whatever-performs-it](a-procedure-belongs-to-whatever-performs-it.md).
- **`sensing:PolledProcedure` is still reserved.** No rule maps it, so no observation can cite
  it, and the shape would accept one that did.
