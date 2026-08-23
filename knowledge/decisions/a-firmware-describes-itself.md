---
type: Decision
title: A firmware describes itself, and a board just says which one it runs
description: >-
  firmware/<name>/ontology.ttl is a third T-Box source beside packages/ — the sense mode, the
  implemented procedures and the generator's dispatch name are the flashed image's facts,
  stated once as a class with hasValue restrictions and entailed onto every board typed with
  it. a-part-is-described-once-and-fitted-many-times applied to code instead of silicon; issue
  #175.
status: accepted
timestamp: 2026-08-15T16:33:30Z
---

> **Current statement: [model-and-unit](/domain/model-and-unit.md).** This record is one
> application of a principle four of them share; the domain concept states the principle
> and the mechanism once.

# A firmware describes itself, and a board just says which one it runs

# Context

Two firmwares exist since #151, and the worlds restated per device what the flashed image
determines: `sensing:senseMode` (who holds the clock IS the code — the derivation rules' own
comment always said *"reflash a board from push to scheduled and the agent gains an
interval"*), `ssn:implements sensing:AlarmProcedure` where the image cannot be flashed without
it, and `mc:firmware`, the string the generator dispatches on. Every board of a kind repeated
its kind's facts, and nothing could refuse a board that contradicted its own image.

# Decision

**`firmware/<name>/ontology.ttl` is a third T-Box source.** `loader.ontology_files()` merges
it beside `packages/`, prefixes flow through unchanged, and the description is a class —
`governed:Node`, `sentinel:Node` — carrying the image's facts as `owl:hasValue` restrictions
that the closure's existing rule 5 entails onto every typed board. This is
[a-part-is-described-once-and-fitted-many-times](a-part-is-described-once-and-fitted-many-times.md)
applied to code instead of silicon: one image, one set of promises, however many boards run it.

The sensing world's board now states neither fact. `world.ttl` types the connecting device
`governed:Node`; the mode and the firmware name follow, the runtime and the shapes read the
conclusions, and `orexis-firmware` reaches the name through the hosting the deployment already
produces (`?board sosa:hosts ?bearer . ?bearer mc:firmware ?fw` — either spelling satisfies
the query, so a world stating the string directly stays legal).

**Only the connecting device is typed, and the refusal that taught us is worth keeping.** The
board node and its bus principal are one physical board wearing two roles (#81). Typing the
bare microcontroller too entails a sense mode onto a node with no command channel, and the
instructable shape rightly refuses it — the class describes the SPEAKING role.

# What stays where it was

- **The deployment half stays the world's**: subject, topics, pins, calibration, bus — the
  boundary `deploy-dht22.ttl` draws for parts, drawn here for code.
- **The governed node's alarm moved onto the class after all** (#181). This bullet used to
  argue it stayed per channel because the promise was true only of a board flashed with the
  define — but the generator reads the promise to decide whether to emit the define, so
  putting the promise on the class makes the claim self-keeping: every image emitted for a
  `governed:Node` carries the watch, and the entailment lands on the CONNECTING device alone,
  which IS the per-channel truth — the typed device is the analog channel, and the DHT
  channels riding the same stream are never typed. What holds the promise to the silicon is
  no longer authorship but wiring: the board's class states which pin roles its sleep-watcher
  reaches (`mc:watcherReachesRole`, esp32's ULP → analog only), and
  `mc:WatchedChannelWiringShape` refuses a watched channel wired past that reach. A stand-in
  still states its promises by hand — it has no pins and no watcher, and its constitution is
  that it reports what its world says.
- **Simulated devices run no firmware and are never typed**: `ag:simulatedBy` is their
  kind-statement, and a stand-in wearing a firmware class it does not run would be a new way
  to lie. The simulation world keeps its direct statements.
- **No volume migration**: everything that moved lives in public graphs, refreshed from files
  at every boot. Asserted here because #175's done-when asked for it to be checked: it was,
  and the vocabulary gained terms without renaming any.

# Seams left open

- **The channel structure is not yet described by the class.** Which pointers the one message
  carries is the image's fact too, but channels are world instances; describing them needs
  classes the world instantiates per channel, which is a second step this record does not
  take.
- **wokwi/wireviz still read what they read.** The generator's union covers `orexis-firmware`;
  the drawing generators were not swept and keep working off the hardware description, which
  states no firmware fact at all.
