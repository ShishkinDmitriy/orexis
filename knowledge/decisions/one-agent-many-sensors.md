---
type: Decision
title: One agent, many sensors — what collides and what does not
description: An agent may hold several sensors, and every combination now works. Both failures were triggered by adding a second kind of sensor to a subject; this records what broke, why, what was done, and why the strictest reading is a warning rather than a refusal — which turned out to require changing what conformance means here.
status: accepted
timestamp: 2026-08-07T00:00:00Z
---

# What is measured, not assumed

An agent's sensors are per-sensor throughout: topics hang off the sensor (`mqtt:readingTopic`), a
driver is chosen per sensor, and cadence is tracked per sensor. So the obvious worry — that two
sensors share machinery — is unfounded. Driven through the real module with two `sensing:ScheduledProcedure`
sensors on one agent:

```
subscribes to: sensors/basil/moisture, sensors/fern/moisture
  RECORD  moisture_sensor_fern   0.2      PUBLISH sensors/fern/cmd   {'sleep_s': 10}
  RECORD  moisture_sensor_basil  0.9      PUBLISH sensors/basil/cmd  {'sleep_s': 10}
```

One capability — `sensing:Subscribing` is derived once, not once per sensor — routing each message to
the right sensor and each cadence to its own command topic.

| one agent, two sensors | |
|---|---|
| same mode, different subjects | **works**, as above |
| same mode, same subject, same property | works; they share one record, last writer wins — warned about, and curable by a `sosa:Sample` each (#98) |
| same mode, same subject, **different property** | **fixed** — see below |
| **different modes** | **fixed** — see below |

The mode is not what broke. Both failures were triggered by the same event: giving one subject a
*second kind* of sensor.

# An observation was keyed by its subject alone

`sensed_writer.py` named the observation node `ag:obs_<subject_id>` and deleted it before each
insert. The property observed was written *into* the node but was not part of its identity.

So a subject with a moisture probe and a temp/humidity board had one record the sensors took
turns destroying. Losing data was the smaller half: lookups were by subject, so whoever asked
for moisture could be handed something else — a number in the wrong unit, which is the worst
shape a failure can take, because a market can act on it.

**How much it costs depends on the unit, and that is worth stating precisely**, because the
first test written for this proved nothing and looked like it did. A *temperature* mistaken for
a moisture fraction reads as 21.0 — far above any target — so the agent concludes it is
comfortable, cedes, and quietly loses the round. That is a fault, but a cheap one, and an
assertion about the resulting cadence passes whether or not the bug is present. *Humidity* is
the dangerous half of the same board: it is a fraction, so 0.10 lands inside the bands agents
actually hold and reads as a parched plant. The agent then bids real money for water because
the **air** was dry, and nothing downstream can tell — a bid is private, and that one is
perfectly well-formed.

**The fix: an observation is keyed by subject AND property**, and `current_reading` takes the
property it wants. It is a required argument rather than an optional one, because an omitted
default would silently restore exactly the defect: a caller that cannot name the property does
not know what it is asking.

That reached further than the writer. Everything that carried "a reading of a subject" now
carries the property too — `reading_recorded`, `on_reading_recorded`, `annotate`, `urgency`,
`stale_after_s`, `sensor_for`, and the agent's public announcement, which now names the property
because one event topic carries two kinds of number. A stake is held in a *property*, so a
module handed a temperature answers `None` rather than judging it against the only scale it
owns; the distinction that matters there is **no opinion versus an opinion of zero**.

# How a bidder knows which property is its business — and why not from the market

The market package must not name a domain property: `water:SoilMoisture` in market code would be
the domain leaking into the protocol. So it is derived. The question is *derived from what*, and
the first answer was wrong.

**The first answer put it on the market**: a market is `market:marketFor` a resource, and the
resource's class states which property it `ag:relieves`. It reads plausibly and it is wrong
twice. A market is a **lot** — 1L of water is 1L of water whether or not anyone's soil is dry —
so making a market carry a property means a market for something no instrument measures (a time
slot, a right of way, a share of attention) cannot be declared at all. And it puts a fact about
one *bidder's* valuation on the *venue*, which every participant would then have to share.

**The property-shaped thing is the stake.** A target of 0.55 is 0.55 *of* something; the bands
are in the same unit; and `water:litresPerFraction` — "litres needed to raise moisture by 1.0" — is
exactly the exchange rate between the lot and the property, which is where the coupling honestly
lives. Until this was written down, that 0.55 was dimensionless, and the agent got away with it
only because it had one kind of reading to compare against.

So the domain states `market:aboutProperty` on the desire term itself:

```turtle
water:hasTarget market:aboutProperty water:SoilMoisture .
```

The bidder follows that link from `water:hasTarget`, which its own beliefs block already names, so
no domain property is written in market code and no world restates anything. A bidder whose
desire names no property **refuses to start** — the only alternative left is judging whichever
reading arrived last, which is the defect being fixed.

Winning still changes the property. That is a consequence of the lot, not the identity of the
market.

# Two sensors, one property: a warning, not a refusal

Strictly, this case should not arise. A sensor observes a property *of a feature of interest*,
and two probes in one pot observe different features — the soil by the left wall and the soil by
the right. Same property, different subject. Modelling it otherwise is under-modelling — and the
word for the right modelling turned out to be SOSA's own, one step past where this paragraph
used to stop (#98): each patch is a **`sosa:Sample`** of the pot, *"representative of a
FeatureOfInterest that is not fully accessible"*, which a pot's soil is exactly. A probe may now
state its patch (`sensing:samples`), the observation is keyed by the patch, and the two records
both survive; the pot answers with the newest witness among its patches — a choice of witness,
deliberately not an aggregation.

For a houseplant that strictness is often not worth it, and declaring the pot to be one object
stays a legitimate simplification: absent a sample, the subject is the feature, the two sensors
share one record and the last writer wins, which is what "these are one object" means. Someone
has to JUDGE that two probes sit in two patches rather than one, and no shape can make that
judgement — which is why the sample is optional and the default is unchanged.

So `orexis-validate` says so at **`sh:Warning`** rather than `sh:Violation` — two sensors
observing one property of one subject may mean two subjects, and the world still conforms. That
is an honest use of validation: it carries the judgement without refusing a world whose author
simplified on purpose. The day zone-level watering is wanted, the tool has already pointed at the
place the model was thin.

**Averaging them would be an opinion**, and opinions belong to capabilities rather than the
kernel. Last-writer-wins is the right default precisely because it asserts nothing.

## Writing a warning meant changing what conformance means here

`sh:Warning` did nothing on its own, and the reason is in the spec rather than in pySHACL: SHACL
defines conformance as *no validation results at all*, so a warning sets `conforms: false`
exactly as a violation does. Adding one immediately failed a world that was fine — and the only
thing `sh:Warning` had changed was a word in the report. A severity that cannot be survived is
not a severity.

So the verdict is now ours: `agent.validate.conforms` inspects the results graph and returns
false only for `sh:Violation`. Everything else is printed and passed over, and nothing is
hidden — the full report, warnings included, is what the caller prints.

It also cost a duplicate. `tests/test_shapes.py` had its own copy of the pySHACL call, which was
harmless while the two agreed and stopped being harmless the moment they diverged: the tests
failed a world `orexis-validate` accepted. It now calls the real function. Two ways to decide
whether a world holds is one too many, and the one that ships is the one to test.

# Mixed sense modes: the capabilities split, the sensors do not

An agent with one `sensing:ScheduledProcedure` and one `sensing:PushProcedure` sensor derives both `sensing:Subscribing` and
`sensing:Listening`. Both modules then take **every** sensor the agent has:

```python
def handle(self, topic, payload):
    for sensor in self.me.sensors:      # all of them, whatever their mode
```

`Agent._on_message` returns after the first module that handles a message, so nothing is ingested
twice — an earlier note in this repo claimed double ingest and was wrong. What happens instead is
quieter. Modules are ordered by `sorted(capabilities)`, `sensing:Listening` sorts before
`sensing:Subscribing`, and listening's `on_reading` is a deliberate no-op — so **the scheduled sensor's
cadence is never re-aimed**. The board keeps whatever interval it last had, indefinitely. In the
other direction, subscribing publishes `{"sleep_s": N}` at a push device that takes no orders.

The root cause was one line of absence: `Sensor` carried no sense mode. `_sensors_q` never selected
`sensing:senseMode`, so the runtime could not partition what the derivation already separated. It does
now, and each module declares the mode it serves beside the capability it already declares.

**And the combination was not merely unhandled — it was unvalidatable.** Two shapes, each written
for a pure agent, contradicted each other on a mixed one: the subscribing shape demanded an
interval and the listening shape forbade it. So a perfectly ordinary rig — a plant with a scheduled
moisture probe and a push thermometer — could not be expressed at all, and nothing said so. The
prohibition was an accident of two rules meeting, not a decision anyone made.

The listening prohibition now applies only to an agent that listens **and does not subscribe**,
which is what it always meant. A sensor's mode is a fact about the device; the agent's capabilities
are derived from the sensors it holds; and holding one kind never forbids holding another.

**The fix**: select it, carry it on `Sensor`, and have each module declare the mode it serves —
`SENSE_MODE` beside the `CAPABILITY` it already declares — and take only those sensors. That
states the mode↔capability pairing in Python as well as in `rules.ru`; the alternative is
introspecting a SPARQL update to recover it, which is worse. Both are T-Box terms, which the
first rule in AGENTS.md permits in code.

# Why neither was caught

Nothing in the suite gave one agent two sensors. Every ratified world wires one sensor per agent,
so the combination was unexercised rather than untested-by-oversight — the tests were honest
about what the worlds contain. All three cases are in the suite now: two of one mode, two of
different modes, and two observing different properties of one subject. Each guard was verified
by breaking the fix and watching it fail, which is the only way to know a guard works; one of
them had to be rewritten when it turned out to pass with the fix removed.

# Seams left open

- **Nothing aggregates.** Two sensors on one property overwrite rather than combine, deliberately.
- ~~**No ratified world wires two sensors to one agent.**~~ **Closed.** `world/sensing` now wires
  three to `fern` — the capacitive probe, and the KY-015's temperature and humidity — so the
  behaviour this record describes is exercised by a shipped world rather than only by worlds
  built in a temporary directory. The board is flashed and publishing all three. What made that
  possible was giving the two air channels a way to say which value in the shared message is
  theirs; see
  [a-reading-is-one-value-so-it-is-pointed-at](a-reading-is-one-value-so-it-is-pointed-at.md).
- **A desire is about exactly one property.** `market:aboutProperty` is read as a single value, so an
  agent whose stake spans two — wanting both moisture and nutrient held — has no representation.
  Nothing depends on this yet, and widening it is one query and a loop.
- **The link is on the term, so every agent in a domain shares it.** Two agents in one world
  cannot denominate their desires differently. That is right for a domain where a target *means*
  soil moisture, and it is the thing to revisit if a second kind of bidder appears in the same
  society rather than in a second world.
- **The warning is per sensor, not per pair.** Two probes on one property produce two warnings,
  one from each end. Harmless, and mildly noisy at four probes.
