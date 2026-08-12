---
type: Decision
title: A pin is a piece of metal, a role is abstract, and a wire is the thing you get wrong
description: Why the core vocabulary split into a stand plus a package per protocol and per part, and why a pin assignment became three objects instead of one — which is what made the rail-voltage fault sayable at all.
tags: [vocabulary, hardware, pins, wires, shacl, packages, seams]
timestamp: 2026-08-07T00:00:00Z
---

# Two subjects were sharing a file

`packages/core/agora/ontology.ttl` had grown to 205 lines holding agents, capabilities, the world
and its versions, named graphs, simulated devices, boards, pins, pin roles, and the three
peripherals that happen to be on this bench. Two of those are the same subject and the rest are
not: **what a society IS** and **what is screwed to the windowsill** change for different
reasons, at different rates, prompted by different people.

The tell is that adding a temperature sensor edited the file that defines what an agent is.

It now splits along the seam the loader already provided — a directory under `vocabulary/` is a
package, found by looking and never listed, exactly like a capability:

```
packages/core/agora/            agents, capabilities, world, hosts, naming, graphs   (205 -> ~115)
packages/part/microcontroller/  boards, peripherals, pins, wires, roles       mc:
packages/bus/onewire/          a protocol                                    onewire:
packages/bus/i2c/              a protocol                                    i2c:
packages/part/dht11/            a part, and the shapes that refuse it wired wrong   dht11:
packages/part/rgb_led/          a part                                        rgbled:
packages/part/moisture_probe/   a part                                        probe:
packages/plant/water/            the domain, unchanged
```

**Adding a part is adding a directory.** Nothing registers it; nothing imports it.

## Why one-wire is not a transport

`packages/transport/` looked like the obvious home and is the wrong one. Those describe how an
**agent** reaches a device, and each has Python behind it. Nothing in this repository speaks
one-wire — the *board* does, in firmware, and the agent never sees it. A transport package with
no driver would be a promise the runtime cannot keep.

## The hardware layer keeps its own namespaces

Every module here used to declare an `owl:Ontology` IRI and then put all its terms in `ag:` —
the ontology IRI and the term namespace disagreed, which reads as an error and was a
convention: one namespace, many documents.

The hardware packages now have namespaces of their own, and the reason is economy rather than
tidiness. This is the layer that grows a term per pin. With one shared namespace every term has
to carry its board's name to stay unambiguous — `ag:Esp32Gpio34` — and with its own it does not:
`esp32:Gpio34Pin`. The prefix is already saying which board.

**It can afford this because no runtime code names these terms.** An agent never queries a pin.
`agent/ontology.py`'s `term()` mints `AG + name` and every capability's `terms.py` depends on
that, so moving the *society* vocabulary would be a large and risky change for no benefit —
but the hardware vocabulary is read only by `onboarding/firmware.py` and by the shapes, which
spell IRIs in full anyway. Three files, none of them the runtime.

The society kernel, the capabilities and the domain stay in `ag:`. Two conventions in one
bundle is a cost, and the line between them is exactly the line the code already draws.

`ComputeHost`, `lanAddress` and `runsOn` went back to the kernel while this was being done.
They describe where agents execute; they are not electronics and never had pins.

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
ag:air_vcc a mc:Pin ; mc:pinRole mc:PowerPinRole .
ag:pin_3v3 a mc:Pin ; mc:pinRole mc:PowerPinRole ; mc:railVolts 3.3 ; skos:notation "3V3" .
[]         a mc:Wire ; mc:joins ag:air_vcc , ag:pin_3v3 .
```

**An instance of `mc:Pin` is a piece of metal. An instance of `mc:PinRole` is abstract — it has
no metal anywhere.** `mc:pinRole` links them, and a pin *plays* a role rather than *being* one.
That distinction is why the roles are named `rgbled:RedPinRole` and not `rgbled:RedPin`: a term
ending in "Pin" that is typed as a role is a category error sitting in plain sight, and it gets
copied.

`skos:notation` carries what is **printed** next to the leg, which is not the number. On a
DevKitC, GPIO 36 and 39 are silkscreened VP and VN — the number appears nowhere on the board, so
"put it on 36" is an instruction you cannot follow without a datasheet. A label is for a human
reading the graph; a notation is a code you match against the silkscreen with a jumper in your
hand.

# It is also now runnable

`agora-wokwi <world>` writes `world/<world>/wokwi/diagram.json` — the stand as a
[wokwi.com](https://wokwi.com) project. Every part, every wire, coloured by what it carries.

Two other renderings were tried and dropped, and the reasons are the useful part. **Grafana's
node graph** could not express the one thing that makes a wiring diagram legible, which is that
pins sit INSIDE their device: 21 nodes came out as a hairball, with no grouping, no per-node
position and no control over size. Force-directed layout is the wrong shape for a thing whose
arrangement is already known. **Mermaid** fixed that with subgraphs and was genuinely readable, and Wokwi was chosen over it
because it **runs** — the same trick `world/simulation` plays a layer up with containers speaking
the real protocol.

**That argument has since been withdrawn, and the choice survives it.** Simulation is not what
this is for: it is a visual model of the bench. What Wokwi still gives that Mermaid cannot is
PHYSICAL accuracy — the real DevKit graphic with its real header, the parts drawn as the parts,
each leg where it actually sits. Boxes and lines answer "what is connected to what"; this answers
"which hole does this go in", which is the question you have while holding a jumper. It is a
closer call than the original reasoning made it, and worth saying so rather than resting on an
argument that no longer applies.

One consequence of dropping simulation: the chip a custom board delegates to only has to supply
pin NAMES for `target` to map onto. So `wokwi-dht22` standing in for a DHT11 costs nothing here,
and would cost everything the day anything runs — see boards/README.md.

**A part says how it draws in its own package.** `packages/part/dht11/` already states what a DHT11
is and what legs it has; that it draws as `wokwi-dht22` with SDA/VCC/GND is the same kind of
fact. Adding a part stays "adding a directory". A part that says nothing about Wokwi is reported
and omitted rather than guessed at.

**Two naming systems, neither derived from the other, both stated.** `skos:notation` is what is
PRINTED beside a leg — for a person with a jumper in their hand. `wokwi:name` is what the
simulator calls it. The tidy version of this — that one authority would do, since both name the
same physical header — was written into a commit and is wrong:

    printed      D34      GND      GND      GND      3V3
    wokwi         34    GND.1    GND.2    GND.3     3V3

Wokwi names a general-purpose leg by its bare number, and disambiguates the three ground legs
that the board prints identically — so the silkscreen does not even identify a pin uniquely.
**They agree on 3V3 and nothing else**, which is how it went unnoticed: that was the single wire
that drew, and the result looked like a sparse circuit rather than a broken generator.

The bare number was then briefly *computed* from `mc:gpio`. That gave the right answer and was
the wrong shape — a rule about Wokwi's naming conventions living in Python, where nothing in the
graph shows it and nothing contradicts it the day they change it. A leg with no `wokwi:name` is
now reported and omitted, which is the same treatment a part with no `wokwi:part` gets.

A generated picture can go stale in the one way a hand-drawn one cannot be saved from, so
`tests/test_wokwi.py` regenerates and compares. A stale drawing looks exactly like a current
one, which is why trusting the author to remember was not an option.

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

The unwired-leg rule needed two exemptions, and telling them apart is the useful part. A leg that
connects to nothing INSIDE the part — a bare 4-pin DHT11's third position, where the package has
more pins than the die uses — is intrinsic, so `mc:NotConnectedPinRole` is a role. (Nothing on
this bench has one: the KY-015 breakout exposes three legs and all three are wired. Wokwi's model
of the part has one, which is where the example came from, and it was mistaken for ours.) A board leg this build simply did not use is not intrinsic
at all: an ESP32 has thirty legs, a world wires seven, and the same board in another world uses
different ones. That is `mc:unused` on the pin, and it is deliberately not a role — a role
travels with the component, and filing "unwired here" inside the description of a component puts
a fact about one breadboard where every future build of that part will read it.

**Neither is derivable, for different reasons.** A not-connected leg is *inherited* — once a
part's legs are declared on its type ([#55]) a world states nothing and gets it from the part.
An unused one cannot be derived at all: the graph already shows a pin with no wire, and what it
cannot show is whether anyone MEANT that. Intent is not a consequence of other facts, so stating
it is not bookkeeping — it is the entire content.

Both cost a line, which is the point: silence must go on meaning *I have not thought about this
leg*. A checker that could be quietened for free would be quietened everywhere.

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

- **Only the sensing world has a board.** Society and simulation declare no boards, so the whole
  of this is exercised by one world and the test stand.
- **`mc:gpio` still implies the ESP32.** The ranges 0-39, 6-11 and 34-39 are that family's,
  written as literals into the shapes rather than described per board model. The next step is a
  `packages/part/esp32/` package where each position is a class — `esp32:Gpio34Pin` carrying
  `mc:gpio 34`, its silkscreen notation and whether it can be driven — so the rules read the
  board's own description and stop knowing any numbers. That is also how a world says a board has
  ONLY those pins: every position subclasses `esp32:Pin`, and one SHACL constraint refuses
  anything else.
- **A wire is untyped.** Nothing distinguishes a jumper from a solder joint from a PCB trace, and
  nothing needs to yet.
- **Nothing checks a rail can supply the current drawn.** Every peripheral here draws milliamps;
  the day one does not, this model has the shape to say so and no vocabulary for it.
