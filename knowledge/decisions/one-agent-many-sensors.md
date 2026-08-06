---
type: Decision
title: One agent, many sensors — what collides and what does not
description: An agent may hold several sensors, and three of the four combinations work. The two that do not are both triggered by adding a second kind of sensor to a subject; this records what breaks, why, and the fix, including why the strictest reading is a warning rather than a refusal.
tags: [perception, sensors, observations, sense-mode, shacl, seams]
timestamp: 2026-08-06T00:00:00Z
---

# What is measured, not assumed

An agent's sensors are per-sensor throughout: topics hang off the sensor (`ag:readingTopic`), a
driver is chosen per sensor, and cadence is tracked per sensor. So the obvious worry — that two
sensors share machinery — is unfounded. Driven through the real module with two `ag:Scheduled`
sensors on one agent:

```
subscribes to: sensors/basil/moisture, sensors/fern/moisture
  RECORD  moisture_sensor_fern   0.2      PUBLISH sensors/fern/cmd   {'sleep_s': 10}
  RECORD  moisture_sensor_basil  0.9      PUBLISH sensors/basil/cmd  {'sleep_s': 10}
```

One capability — `ag:Subscribing` is derived once, not once per sensor — routing each message to
the right sensor and each cadence to its own command topic.

| one agent, two sensors | |
|---|---|
| same mode, different subjects | **works**, as above |
| same mode, same subject, same property | works; they share one record, last writer wins |
| same mode, same subject, **different property** | **broken** — see below |
| **different modes** | **broken** differently — see below |

The mode is not what breaks. Both failures are triggered by the same event: giving one subject a
*second kind* of sensor.

# An observation is keyed by its subject alone

`agora/sensed_writer.py` names the observation node `ag:obs_<subject_id>` and deletes it before
each insert. The property observed is written *into* the node but is not part of its identity.

So a subject with a moisture probe and a temperature sensor has one record that the two take
turns destroying. Worse than losing data: lookups are by subject, so whoever asks for moisture
can be handed a temperature — a plausible number in the wrong unit, which is the worst shape a
failure can take. A market can act on it.

**The fix is to key an observation by subject AND property**, and to make the reading lookup name
the property it wants. That is wider than it sounds: `current_reading` is used by bidding and
urgency, which currently assume one reading per subject.

# Two sensors, one property: a warning, not a refusal

Strictly, this case should not arise. A sensor observes a property *of a feature of interest*,
and two probes in one pot observe different features — the soil by the left wall and the soil by
the right. Same property, different subject. Modelling it otherwise is under-modelling.

For a houseplant that strictness is not worth it, and declaring the pot to be one object is a
legitimate simplification. Keying by subject and property makes it behave sensibly on its own:
the two sensors share one record and the last writer wins, which is what "these are one object"
means.

So `agora-validate` should say so at **`sh:Warning`** rather than `sh:Violation` — two sensors
observing one property of one subject may mean two subjects, and the world still conforms. That
is an honest use of validation: it carries the judgement without refusing a world whose author
simplified on purpose. The day zone-level watering is wanted, the tool has already pointed at the
place the model was thin.

**Averaging them would be an opinion**, and opinions belong to capabilities rather than the
kernel. Last-writer-wins is the right default precisely because it asserts nothing.

# Mixed sense modes: the capabilities split, the sensors do not

An agent with one `ag:Scheduled` and one `ag:Push` sensor derives both `ag:Subscribing` and
`ag:Listening`. Both modules then take **every** sensor the agent has:

```python
def handle(self, topic, payload):
    for sensor in self.me.sensors:      # all of them, whatever their mode
```

`Agent._on_message` returns after the first module that handles a message, so nothing is ingested
twice — an earlier note in this repo claimed double ingest and was wrong. What happens instead is
quieter. Modules are ordered by `sorted(capabilities)`, `ag:Listening` sorts before
`ag:Subscribing`, and listening's `on_reading` is a deliberate no-op — so **the scheduled sensor's
cadence is never re-aimed**. The board keeps whatever interval it last had, indefinitely. In the
other direction, subscribing publishes `{"sleep_s": N}` at a push device that takes no orders.

The root cause is one line of absence: `Sensor` carries no sense mode. `_sensors_q` never selects
`ag:senseMode`, so the runtime cannot partition what the derivation already separated.

**The fix**: select it, carry it on `Sensor`, and have each module declare the mode it serves —
`SENSE_MODE` beside the `CAPABILITY` it already declares — and take only those sensors. That
states the mode↔capability pairing in Python as well as in `rules.ru`; the alternative is
introspecting a SPARQL update to recover it, which is worse. Both are T-Box terms, which the
first rule in AGENTS.md permits in code.

# Why neither was caught

Nothing in the suite gives one agent two sensors. Every world here wires one sensor per agent, so
the combination is unexercised rather than untested-by-oversight — the tests are honest about
what the worlds contain. A fix for either should bring the case into the suite: two sensors of
one mode, two of different modes, and two observing different properties of one subject.

# Seams left open

- **Nothing aggregates.** Two sensors on one property overwrite rather than combine, deliberately.
- **`current_reading` is per subject.** Until it takes a property, a subject can hold exactly one
  kind of reading, which is the bug above rather than a design.
- **The warning does not exist yet.** It is described here and not implemented, so a world can
  still under-model a pot in silence.
