---
type: Decision
title: A stand-in reports what its world says it does, and the message finally happened
description: The simulator published one value while the real firmware published three, so the multi-value path was argued in unit tests and never travelled a wire. It now reports a value per property at the pointers its world declares, each drifting in its own range. Two shapes had to stop assuming every value is a fraction and every device holds a credential — both assumptions the hardware world had already disproved. Running it found a stale belief volume that no gate can see.
status: accepted
timestamp: 2026-08-11T00:00:00Z
---

# Context

Everything for a board reporting several properties was built and **no such message had ever
been published by anything.**

`world/sensing` states the shape — three sensors, one reading topic, one message — and its
firmware reads a KY-015 and sends `{"value":…,"temperature":21.4,"humidity":0.463}`. But
`main.cpp` has never been compiled here and the board has never been flashed with it.
`world/simulation` had three stand-ins on three topics, one value each. The unit test fed a
payload to `handle()` directly.

So the path was argued and never travelled, and the simulator's own claim about itself had gone
false without anything noticing:

> **The whole claim is that nothing downstream can tell.** So this publishes what the real board
> publishes, byte for byte — `{"value": 0.183, "sensor": "..."}`

The real board stopped publishing that when the KY-015 landed. Nothing failed, because no world
had asked the simulator for more than one value.

# Decision — the stand-in reports a value per property, and a world says which

`SIM_VALUES` lists what a device reports and where each value goes in its document. A part
reporting two properties down one line is a list of two; a probe is a list of one, and not a
special case. One message carries all of them, because that is what a board does: it wakes once,
reads what it is wired to, and spends one transmission on the lot.

**The ranges come from each sensor's own model, not from a shared default.** `0..1` was never a
fact about sensing — only about soil moisture — and a board reporting degrees beside a fraction
is describing two kinds of number down one wire. Each value drifts in its own range from its own
start, so a room warms while a pot dries.

**Water moves only the value a litre is worth something to.** `litresPerFraction` is joined
through the *property* the domain's valuation is denominated in — `water:hasTarget
market:aboutProperty water:SoilMoisture` — and not through the subject. Three sensors on one board
can monitor one plant, so the subject cannot say which reading a dose moves. Without that join a
litre of water warmed the thermometer, which would have taught an agent something false about the
world.

# Two shapes had to stop assuming what the hardware world already disproves

Both were right when written and both had been overtaken by `world/sensing`.

**`orexis:SimulatedDeviceShape` demanded `mqtt:onBus` of everything stood in for.** Its reasoning was
sound — without a credential nothing publishes for it, and a permanently silent sensor reads like
hardware that is not there. But the premise is satisfied another way now: a neighbour publishes on
the same wire. `orexis:air_temp_fern` has no bus at all on the real board, because a second credential
for a client that never connects is what that world refuses. Demanding it here would have forced
the simulation to model something no board does. The shape tests **reachability** now — on a bus,
or sharing the reading topic of something that is.

**`orexis:DeviceModelShape` held every initial value to `0..1`**, "a fraction of the observed
property". True of everything modelled until a thermometer arrived, and 21.4 is not a fraction of
anything. It is held to the model's **own** range now, which still catches the slip it was written
for — 45 where 0.45 was meant, in a model that says it runs 0..1 — and catches it in a thermometer
too, where a rule spelling `0..1` could not look.

## And a grant that belonged to the wrong thing

`_SIM_DOSE_Q` keyed on `orexis:simulatedBy` alone, so the second sensor on a board minted a principal
of its own holding a single dose grant — for a client that never connects. Measured before it was
fixed, then guarded on `mqtt:onBus`: **the grant belongs to whatever connects.** That is
[#81](https://github.com/ShishkinDmitriy/orexis/issues/81) one level down, and it is the third time
this project has found a credential attached to something that does not open a socket.

# What running it proved that the tests could not

The world was brought up and the message captured on the wire:

```
sim/sensors/sensor_fern/reading {"sensor": "sensor_fern", "temperature": 21.15, "value": 0.39}
```

and the agent's log for the same message:

```
sensor_fern: SoilMoisture   0.410  band=OK
air_fern:    AirTemperature 21.100
```

and the series store, two points per message, ~25 ms apart:

```
13:22:25  0.41   SoilMoisture    sensor_fern
13:22:25  21.1   AirTemperature  air_fern
```

Three things that had only ever been argued are now observed: `handle()` offers one message to
every sensor on the channel; a pointer picks the right field out of a **real** payload rather than
a fixture; and a temperature lands tagged `AirTemperature` beside a fraction instead of becoming
a third moisture reading — the hazard the series writer added the tag to prevent.

The band is on the moisture and not on the temperature, which is the protection against judging a
humidity against a moisture band working in a running society rather than in a unit test.

## And one thing only running it could find

**Every agent crash-looped on first boot, and no gate could have seen it.** A belief base is
authored once at birth and never touched by start or stop, so the volumes held terms spelled the
way they were before the namespace sweep — `ag:hasTarget` where the code now asks for
`water:hasTarget`. The tests build a fresh store every time and never meet a volume older than the
code.

Nothing in this change caused it and nothing in this change fixes it: it is a property of that
sweep meeting a deployed world, and it is filed rather than patched here. Re-authoring is dropping
the volume and letting the world seed it again, which is what was done.

# Consequences

- **The simulation world exercises the multi-value path**, so a regression in `handle()`,
  in a pointer, or in the property tag now shows up in a world that runs rather than only in a
  fixture.
- **The simulator's claim about itself is true again**, and it is true because a world states what
  the device reports rather than because someone kept two files in step.
- **Adding a sensor to an existing topic adds no grant and no principal**, proved rather than
  asserted — the payload grew and the channel did not.

# Seams left open

- **The real firmware is still uncompiled.** `main.cpp` reads the DHT and publishes three values
  and has never been built here; `tests/test_firmware.py` checks the generated `config.h` only.
  What this change proves is that everything *downstream* of the board is right, which is most of
  the risk and not all of it.
- **`subscriptions()` returns one topic per sensor**, so an agent with two sensors on one channel
  subscribes twice — visible in its log. Harmless to MQTT and a duplication the channel could
  remove now that it is a node.
- **`ag:modelDryRate` is named for the first thing this project modelled** and means "how far it
  moves per tick" for everything since. A thermometer states a negative one to warm.
- **A deployed belief volume older than a vocabulary change breaks its agent at boot**, and
  nothing warns. Found here by accident, and the only reason it was found at all is that this
  change had to run a world.
