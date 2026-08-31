---
type: Decision
title: One word for one relation, and a term of ours earns its place by answering a different question
description: A subclass axiom is a claim that our term means something more, so where it does not, ours is a synonym with an unenforced comment. mc:carries, sensing:Sensor, actuation:Actuator and sensing:seconds went; orexis:Device, sensing:senseMode and review:Revision stayed, and the reasons are the deliverable. The test that emerged is not whether a standard has a similar word but whether it is answering the same question — SOSA's axis is functional, ours is substrate, and terms on different axes cut across each other rather than duplicating.
status: accepted
timestamp: 2026-08-11T00:00:00Z
---

# Context

Six places declared `ourTerm rdfs:subClassOf standardTerm`, and a subclass axiom is a **claim**:
it says the narrower term means something the wider one does not. Where that is true the term
earns its keep. Where it is not, we are paying for a specialisation nobody collects on — two
words for one relation, and every reader having to learn which of them a query wants.

[every-term-in-its-own-house](every-term-in-its-own-house.md) audited this once and asked *is it
ours at all*. It answered by kind — intersection, narrowing, genuinely ours — and stopped there.
This pass asks the harder question: **is the distinction checked?**

# The test that emerged

Not *does a standard have a similar word*. **Is the standard answering the same question?**

SOSA's axis is **functional**. `sosa:Platform` asks *where is it mounted* — its own examples run
to buoys, ships, satellites and humans — and `ssn:System` asks *what implements the procedure*.
Neither is about what a thing is made of, and the spec is explicit that all its major classes may
be virtual, a correction it made deliberately after the first SSN handled software sensors badly.

`device:Device`'s axis is **substrate**: a physical node with legs, interchangeable with a
stand-in. That is a different question, so a term answering it necessarily cuts **across** their
classes rather than duplicating one — `mc:Microcontroller` is a Platform, a sensor is a System,
and `mc:hasPin` and `mc:logicVolts` take `device:Device` as their domain. Boards have pins.

That is why `device:Device` survives an audit that retired the classes sitting directly on top of
it. (AMENDED. Two things this passage said are no longer true. The word is not the kernel's —
[the-substrate-is-not-the-minds](/decisions/the-substrate-is-not-the-minds.md). And
`sim:simulatedBy` does NOT take it as its domain: a stand-in is the ABSENCE of a device, so it
hangs off the role instead, which is
[a-stand-in-is-not-a-device](/decisions/a-stand-in-is-not-a-device.md).)

# What went

**`mc:carries` → `sosa:hosts`.** [#79](a-board-is-a-platform.md) declared it a subproperty, which
was honest at the time. Its `rdfs:domain mc:Microcontroller` and `rdfs:range mc:Peripheral` were
never enforced — neither is in `agent/inference.py`'s closure and no shape read them — so
board-to-part was a comment. **The narrowing survives as `orexis:ABoardCarriesPartsShape` and is
checked for the first time**: a board hosting a non-peripheral is refused now and was accepted
before. A term was given up and a rule was gained.

**`sensing:Sensor` and `actuation:Actuator` → `sosa:Sensor`, `sosa:Actuator`.** These were
intersections — `orexis:Device ∧ sosa:X` — which is why earlier audits kept them. True, and beside
the point: a named class is not the only way to state an intersection. An instance carries both
types, and the one shape that enforced the conjunction states it as two `sh:class` values.

(AMENDED, and this is the half that was wrong: **the conjunction should not have been preserved
at all.** Keeping it meant a sensor had to be hardware, in a project whose simulated worlds
contain no hardware and whose own defence of the word is that SOSA's classes may be virtual. The
shapes ask for the role alone now, and `actuation:Valve` narrows `sosa:Actuator` and nothing
else — see [a-stand-in-is-not-a-device](/decisions/a-stand-in-is-not-a-device.md). What this
record got right was the method: ask whether the standard answers the same question. What it got
wrong was assuming the intersection it found was one worth keeping.)

**`sensing:seconds` → `schema:value` + `schema:unitCode`.** The W3C's own worked example of
the DHT22 — the KY-015's sibling, written by the people who wrote SSN — says a frequency as a
number and a unit. Its `rdfs:range xsd:integer` was never enforced either; there is a shape now,
and it checks something the old spelling **could not express**: that the figure is in seconds. A
frequency in milliseconds was previously unsayable rather than refused, and would have raised an
agent's floor a thousandfold from a well-formed graph.

**`mc:Peripheral ⊑ sosa:Platform` → `ssn:System`.** Both of SSN's restrictions agree: a Platform's
hostees must be Systems, and a System's sub-systems must be Systems. A peripheral is hosted and
has channels, so it is a System twice over and a Platform for no reason — nothing is mounted on a
KY-015.

The W3C's deployment example of that part shows all three cases in one chain, and they are
**orthogonal rather than alternatives** — which neither relation's definition makes obvious:

| | relation | why |
|---|---|---|
| wall → board | `sosa:hosts` only | placed, but not a component of the wall |
| board → part | **both** | placed *and* a component — *when the mounting is permanent* |
| part → channel | `ssn:hasSubSystem` only | never placed at all; it is what the part is made of |

Their own comment licenses the middle row: *PCB Board 1 hosts DHT22 #4578 permanently, one can
say it has it as one of its subsystems.* **Permanence is what earns the second relation**, and
hosting is the trace of an act — `sosa:hosts` is entailed from
`owl:propertyChainAxiom ( ssn:inDeployment ssn:deployedSystem )`, and a Deployment is of systems
*for a particular purpose*.

**Here the board states `sosa:hosts` alone.** Ours are plausibly soldered — the wiring says so in
prose — but nothing in the graph records whether a mounting is permanent or socketed, and
asserting `hasSubSystem` would be inferring permanence from the absence of a socket. That is a
fact about hardware, which means it belongs in the wiring, stated once by whoever knows it, with
the relation derived from it. `mc:Wire` is where it would go: a mounting is closer to a wire than
to a part, and `mc:Wire` already exists with `mc:joins` and `mc:colour`. Left as a stated gap
rather than guessed.

# What stayed, and why each is a different reason

| term | why it stays |
|---|---|
| `device:Device` | different **axis** — substrate, where SOSA's is functional. No capability asks for it |
| `sensing:senseMode` | different **cardinality** — `sh:maxCount 1`, which `ssn:implements` cannot say |
| `review:Revision` | different **kind** — a deliberation, where PROV's is a derivation |
| `actuation:Actuation` | different **kind** — a capability, where SOSA's is an event |
| `sensing:polls`, `monitors` | no equivalent — SOSA puts feature-of-interest on the Observation |
| `actuation:mlPerSecond` | no equivalent — a calibration constant, not a range of results |

The two marked *different kind* are the ones worth dwelling on, because both are **homonyms** and
a tidy-minded reader would align them.

**`review:Revision` against `prov:wasRevisionOf`.** PROV's revision relates two artefacts —
`rdfs:domain prov:Entity`, `rdfs:range prov:Entity` — and is defined as *a derivation for which
the resulting entity is a revised version of some original*. Half of what ours records is a
decision to change **nothing**, and a decline produces no newer entity to hang the relation from.
An agent's eleven declines are exactly the signal that the problem is elsewhere, and PROV cannot
say them at all.

**`actuation:Actuation` against `sosa:Actuation`.** Ours is `a orexis:Capability` — the agent may
drive actuators it owns. SOSA's is an **event**: *an Actuation carries out a Procedure to change
the state of the world using an Actuator*, sibling to `sosa:Observation`, its example being the
activity of closing a window. An act and a permission share a word and nothing else.

The general shape, stated once: **SOSA models the instrument and the observation; we model the
agent's dealings with them.** Of 27 terms across `sensing` and `actuation`, three defer.

# Consequences

- **A subclass axiom is now something to justify, not something to add.** Declaring one says the
  narrower term means more; if nothing checks the difference, it means the same and costs a word.
- **Instances assert what they used to entail.** `a sensing:Sensor` entailed both halves; a
  sensor now states both. Two tests were about that entailment and had to find another —
  `test_provenance`'s spanning pattern is `ssn:System`, which is entailed through the axiom
  [#94](a-board-says-what-it-can-honour.md) restated, so it now exercises the borrowed-axiom
  bridge rather than one of our own subclass edges.
- **A term is still named in ways a sweep cannot see.** A full IRI inside a `sh:sparql` string
  survived every prefix-aware pass — the first time
  [every-term-in-its-own-house](every-term-in-its-own-house.md)'s *seven ways* finding has been
  met since it was written down. And `onboarding/firmware.py` held three call sites nobody had
  listed, because every generator that walks a board starts from the hosting relation.

# Seams left open

- **`ssn:Deployment` is available and untaken.** `sosa:hosts` is entailed from
  `owl:propertyChainAxiom ( ssn:inDeployment ssn:deployedSystem )`, so asserting hosting directly
  states a conclusion without its premise. Deployment is where *for a particular purpose* and a
  lifetime would live — this board, in this pot, from this date.
- **`sosa:Actuation` is available for a thing we do not model.** A dose that happened has no node;
  [#36](https://github.com/ShishkinDmitriy/orexis/issues/36)'s pending set is in memory. If a
  redemption ever becomes a fact in the graph, SOSA already has the class for it.
- **`ssn-system:ActuationRange` fits `maxDoseMl` and was not taken.** It is *the set of values the
  Actuator can return as the Result of an Actuation*, which a dose ceiling is and a flow rate is
  not — so the pair `mlPerSecond`/`maxDoseMl` splits, and doing half of it was not worth a commit
  on its own.
- **Platform and System are not disjoint.** SSN declares no disjointness anywhere, so a thing may
  be both — the ESP32 arguably is, carrying peripherals and implementing the publishing
  procedure. Typing it as a Platform alone is a simplification of ours and **not** a rule to
  enforce with a shape.
- **Neither hosting nor sub-system carries cardinality.** Nothing forbids a System being hosted by
  two Platforms and nothing makes sub-systems exclusive. The distinction between them is
  semantic, and no shape should be expected to enforce an exclusivity the vocabulary never
  claimed.
