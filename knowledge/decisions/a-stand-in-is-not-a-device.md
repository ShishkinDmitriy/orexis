---
type: Decision
title: A stand-in is not a device, and observing is not something only a built thing can do
description: >-
  Sensing's shape demanded that a polled sensor be a physical device, and actuation's demanded
  it of an actuator — the intersection left behind when two of our classes were retired in
  favour of SOSA's. So every simulated world declared a physical edge node and denied it in the
  next line, and a W3C-conformant vendor description had to be told it was hardware before our
  shapes would take it. Decided that a role asks for the role alone, that what a thing is made
  of and whether it has a referent at all are two more questions with two more vocabularies,
  and that the wire name follows the role rather than the body.
status: accepted
timestamp: 2026-08-27T12:00:00Z
---

# What was true before

[one-word-for-one-relation](/decisions/one-word-for-one-relation.md) retired `sensing:Sensor` and
`actuation:Actuator` in favour of `sosa:Sensor` and `sosa:Actuator`. Both had been intersections —
*a device that observes*, *a device that acts* — and the audit preserved the conjunction into the
shape that had enforced it:

```turtle
sh:path sensing:polls      ; sh:class sosa:Sensor   , ag:Device .
sh:path actuation:hasActuator ; sh:class sosa:Actuator , ag:Device .
```

`actuation:Valve` repeated it a level up, as `rdfs:subClassOf ag:Device , sosa:Actuator`. Three
statements, one belief: **a thing that observes or acts is a thing somebody built.**

# What was wrong

The sovereign put it plainly — *sensing should not require physical embodiment* — and the repo
had already been paying for the opposite in three places.

- **The simulated worlds contradicted themselves.** `world/simulation` and `world/loner` contain
  no board, no pin and no `mc:` triple of any kind, and every sensor in them read
  `a sosa:Sensor , ag:Device` followed by `ag:simulatedBy`. The world asserted a physical edge
  node and denied its existence two lines later. The type was there to pass the shape and for
  nothing else, which is the definition of ceremony.
- **A conformant description was refused.** `tests/fixtures/w3c-ssn/` holds the W3C's own DHT22
  document. Its two channels are `sosa:Sensor , ssn:System` — typed by the people who wrote SSN —
  and our deployment overlay had to add `ag:Device` to them. A vendor's file being told by us
  what it is made of, in order to be a sensor, is the clearest evidence the demand was wrong.
- **The word contradicted its own defence.** The audit's argument for keeping our substrate term
  was that SOSA's classes may be VIRTUAL. That argument says a `sosa:Sensor` need not exist; the
  shape said it must.

# What is decided

**A role asks for the role.** `sensing:polls` takes a `sosa:Sensor` and `actuation:hasActuator`
takes a `sosa:Actuator`; neither asks what it is made of. `actuation:Valve` narrows
`sosa:Actuator` and nothing else — every valve this project has ever run is stood in for, so a
class asserting a physical node made each of those worlds contradict itself.

**Three questions, three vocabularies, and only the first is a capability's business.**

| the question | the word | who asks |
|---|---|---|
| what does it DO | `sosa:Sensor`, `sosa:Actuator`, `ssn:System` | sensing, actuation — and nothing else |
| what is it MADE OF | `device:Device` | `mc:hasPin`, `mc:logicVolts`, the harness, the inventory |
| does it EXIST at all | `sim:simulatedBy` | onboarding, when it gives a stand-in a container |

**A stand-in is the absence of a device, not a fake one**, which is why the two are separate
packages rather than one. `sim:simulatedBy` takes `ssn:System` as its domain — the thing playing
the role — and says the role has no referent: nobody built it, a process supplies its behaviour.
Hanging that off a physical class was what produced the self-contradicting worlds, and putting
the two words in one package would have kept them looking like halves of one idea.
`packages/sim/standin/` holds the mark, `sim:Model` and the physics a stand-in computes; the
`model` prefix each of those properties wore to fake a namespace inside `ag:` came off with the
move, because `sim:losesPerDay` on a `sim:Model` needs no such help.

**And a domain axiom is a demand too.** `sensing:senseMode` — who holds the clock — was declared
`rdfs:domain device:Device`, which is the same claim made quietly: every stand-in in
`world/simulation` states a sense mode, so the axiom entailed a physical edge node onto exactly
the nodes that deny having one. Its domain is `ssn:System` now, which is what actually holds —
keeping a clock is implementing a procedure. `tests/test_shapes.py::test_no_capability_asks_what_a_thing_is_made_of`
is what found it, by reading the machine-read part of every capability's Turtle and ignoring
prose; the two audits in sensing's and actuation's ontologies name the word and are meant to.

**The wire name follows the role.** `ag:localId` used to be required by `device:DeviceShape`, so
a sensor stated one because it was a device. But `onboarding/dashboards.py` names a row from
every polled sensor's `localId` and `orexis-mqtt` writes the ACL from every reporting valve's, in
worlds where three of the four valves are stood in for. So `sensing:SensorShape` requires it of a
sensor and `actuation:ActuatorShape` of an actuator, each for its own stated reason;
`device:DeviceShape` keeps it for boards. That closes a hole rather than moving one: a real
sensor typed only `sosa:Sensor` would have reached the dashboard generator with no name and
matched nothing, silently, which is the empty-result trap the repo already knows by heart.

# What did not change

- **`device:Device` survives, and its argument survives with it.** SOSA's axis is functional and
  this one is substrate; boards have pins. What changed is only who is entitled to ask.
- **`world/sensing` still says `device:Device`,** on three sensors that are genuinely a probe and
  a KY-015 wired to an ESP32. That is the contrast case: the type is a claim now rather than a
  formality, and the worlds that cannot honestly make it no longer do.
- **The simulation runs identically.** The generators read the same physics through the same
  queries; only the namespace changed.

# Seams left open

- **Nothing yet requires a `sosa:Sensor` to be reachable.** A sensor states a name and what it
  watches; that it can be spoken to is the transport's business, and mqtt's shapes ask it of a
  stand-in and of a device on a bus. A sensor that is neither is not refused, because no world
  has one.
- **`ssn:System` is a wide domain for `sim:simulatedBy`.** A world could mark a `sosa:Platform`
  or a whole board as stood in for, and nothing would object; the physics assumes one value per
  stand-in, so a simulated BOARD is not a thing the generators would know how to write today.
