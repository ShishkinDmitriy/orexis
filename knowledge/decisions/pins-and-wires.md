---
type: Decision
title: A pin is a piece of metal, a role is abstract, and a wire is the thing you get wrong
description: Why the core vocabulary split into a stand plus a package per protocol and per part, and why a pin assignment became three objects instead of one — which is what made the rail-voltage fault sayable at all.
tags: [vocabulary, hardware, pins, wires, shacl, packages, seams]
timestamp: 2026-08-07T00:00:00Z
---

# Two subjects were sharing a file

`vocabulary/agora/ontology.ttl` had grown to 205 lines holding agents, capabilities, the world
and its versions, named graphs, simulated devices, boards, pins, pin roles, and the three
peripherals that happen to be on this bench. Two of those are the same subject and the rest are
not: **what a society IS** and **what is screwed to the windowsill** change for different
reasons, at different rates, prompted by different people.

The tell is that adding a temperature sensor edited the file that defines what an agent is.

It now splits along the seam the loader already provided — a directory under `vocabulary/` is a
package, found by looking and never listed, exactly like a capability:

```
vocabulary/agora/            agents, capabilities, world, naming, graphs   (205 -> 108 lines)
vocabulary/stand/            hosts, boards, peripherals, pins, wires, roles
vocabulary/onewire/          a protocol
vocabulary/i2c/              a protocol
vocabulary/dht11/            a part, and the shapes that refuse it wired wrong
vocabulary/rgb-led/          a part
vocabulary/moisture-probe/   a part
vocabulary/water/            the domain, unchanged
```

**Adding a part is adding a directory.** Nothing registers it; nothing imports it.

## Why one-wire is not a transport

`agent/transports/` looked like the obvious home and is the wrong one. Those describe how an
**agent** reaches a device, and each has Python behind it. Nothing in this repository speaks
one-wire — the *board* does, in firmware, and the agent never sees it. A transport package with
no driver would be a promise the runtime cannot keep.

# A pin assignment was one node doing two objects' work

The old form fused two facts:

```turtle
ag:probe ag:pin [ ag:pinRole ag:AnalogIn ; ag:gpio 34 ] .
```

`ag:AnalogIn` is a fact about the **probe's** leg — what that leg is for. `34` is a fact about
the **board's** leg — which line it is on the silkscreen. One blank node, two devices, and no
way to tell which end anything belonged to.

That fusion made a whole class of statement impossible. A peripheral could not describe a leg
that was not connected to anything. It could not say which rail it was powered from. It could
not be moved to a second board without being redescribed. And the model could not represent the
one thing on a breadboard that people actually get wrong, which is the wire.

Now there are three objects and the wire is one of them:

```turtle
ag:air_vcc a ag:Pin ; ag:pinRole ag:PowerPinRole .
ag:pin_3v3 a ag:Pin ; ag:pinRole ag:PowerPinRole ; ag:railVolts 3.3 ; skos:notation "3V3" .
[] a ag:Wire ; ag:joins ag:air_vcc , ag:pin_3v3 .
```

**An instance of `ag:Pin` is a piece of metal. An instance of `ag:PinRole` is abstract — it has
no metal anywhere.** `ag:pinRole` links them, and a pin *plays* a role rather than *being* one.
That distinction is why the roles are named `ag:RedPinRole` and not `ag:RedPin`: a term ending in
"Pin" that is typed as a role is a category error sitting in plain sight, and it will be copied.

`skos:notation` carries what is **printed** next to the leg, which is not the number. On a
DevKitC, GPIO 36 and 39 are silkscreened VP and VN — the number appears nowhere on the board, so
"put it on 36" is an instruction you cannot follow without a datasheet. A label is for a human
reading the graph; a notation is a code you match against the silkscreen with a jumper in your
hand.

# What became checkable

Three faults that the old model could not express, now refusable by `agora-validate`:

- **A leg no wire reaches.** Previously impossible to state — a pin *was* its connection, so an
  unconnected leg was invisible rather than wrong. A floating ground is the commonest reason a
  three-legged sensor answers with silence, and it looks exactly like a dead part.
- **The wrong rail.** A three-legged sensor carries a pull-up to its own VCC, so its data line
  idles at whatever it is powered from. On VIN that is 5 V presented to an input that is not 5 V
  tolerant — which does not fail, it degrades over weeks and looks like a flaky sensor. There was
  nowhere to say which rail a device was on, so there was nothing to check.
- **A part that does not name all its legs.** A DHT stating only its data line was the old
  model's best effort. It is precisely the other two that go wrong.

The generic rules — flash pins, ADC2, input-only 34-39, one line one leg — moved onto the
**wire**, because that is where the two facts finally meet. Neither end knows the other until
something joins them.

# Two bugs found by building it

**A `rdfs:domain` turned a class into a device.** `ag:logicVolts` carries `rdfs:domain ag:Device`,
so stating it on `ag:Dht11` made the *class* infer as a Device and get held to `DeviceShape`,
which demands a `localId`. A class does not have one. Domain axioms are inference rules, not type
declarations, and this is the second time that has cost something here.

**The input-only rule had no bound.** Rewritten onto the wire, it matched every driven leg on
every GPIO rather than only 34-39 — the `FILTER` had not come across. It failed loudly, which is
the only reason it was cheap.

# Seams left open

- **Only the sensing world has a stand.** Society and simulation declare no boards, so the whole
  of this is exercised by one world and the test stand.
- **`ag:gpio` still implies the ESP32.** The ranges 0-39, 6-11 and 34-39 are that family's, stated
  in the stand rather than per board model. A second family of board would need them keyed on
  something — probably `ag:model`, which nothing derives behaviour from today by explicit choice.
- **A wire is untyped.** Nothing distinguishes a jumper from a solder joint from a PCB trace, and
  nothing needs to yet.
- **Nothing checks a rail can supply the current drawn.** Every peripheral here draws milliamps;
  the day one does not, this model has the shape to say so and no vocabulary for it.
