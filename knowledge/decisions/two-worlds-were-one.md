---
type: Decision
title: Two worlds were one, and the one that stays is the one that needs no hardware
description: society and simulation differed by 45 lines of ~230 with identical beliefs, so society went and simulation took its place as the deployment target. Keeping the flashed-board property meant simulation adopting sensing's device ids AND dropping its sim/ topic prefix, because matching ids alone would have made the test green and the property false. The prefix was safe to drop because each world runs its own broker; what it cost is legibility.
status: accepted
timestamp: 2026-08-11T00:00:00Z
---

# Context

Three worlds shipped: `society` (a market, real devices), `simulation` (the same market, every
device stood in for) and `sensing` (one real board, no market).

The first two were near-duplicates, and the measurement is the argument:

- **all four belief files were byte-identical**;
- after normalising the `sim/` topic prefix and the device-id naming, **~45 lines of ~230
  differed**, and every one of them was a simulated-device declaration (`orexis:simulatedBy`, five
  `ag:model*` parameters) or the air sensor added by [#88](https://github.com/ShishkinDmitriy/orexis/pull/88).

Two worlds that differ only in whether their devices are stood in for are one world with a flag
spelled as a directory.

# Decision — `society` goes, `simulation` is the deployment target

The world that can run without hardware is the one worth keeping. `simulation` composes its own
devices as containers, so `podman compose up` in it needs nothing on a bench; `society` needed
boards that only `sensing` actually describes.

`sensing` stays as it was: the world with a real board.

# What that cost, and the trap in paying it

`series-and-bus-isolation` deliberately made a **device credential name a device, not a
deployment** — `Principal(row["id"])`, with no world in it, where an agent's username is
`f"{world}-{agent_id}"`. The reason was that *one flashed board works in either world*, and the
pair that demonstrated it was `society` and `sensing`, which shared device ids and channels.

Removing `society` left no two worlds sharing a device, so
`test_two_worlds_that_share_a_device_share_its_credential` lost its subject — loudly, because it
carries `assert shared, "this test has lost its subject"`.

**Renaming `simulation`'s devices to match `sensing`'s would have made that test pass and the
property false.** The test compared *usernames*, and usernames are world-independent by
construction — so they would have matched even with entirely disjoint topics. A board flashed for
`sensing` publishes to `sensors/moisture_sensor_fern/reading`; `simulation`'s ACL would have
granted `sim/sensors/…`; the broker would authenticate it and deny its first publish. A green test
asserting a false property is the failure this project keeps finding in other forms, and it was
one edit away here.

So the topics had to move too.

## The `sim/` prefix was belt-and-braces, and here is what was checked

Dropping it needed the prefix to be doing no real work. It was not:

- **Each world runs its own broker**, in its own container, on its own ports — `simulation` on
  1885/8885, `sensing` on 1884/8884 — with its own ACL, its own passwd file and its own
  credentials. A topic string cannot collide across two brokers. AGENTS.md's leaked-publisher
  warning is about a stray process on the **same** broker, which is a different thing.
- **Nothing outside `world/simulation/world.ttl` referenced it.** The only other occurrences were
  two arbitrary strings in `tests/test_simulated_valve.py`, which invents its own topics as
  environment for a standalone process.
- **`onboarding/compose.py` keys off `sim:simulatedBy`**, not off ids or topics, so container
  names and `SIM_*` environment followed the rename without a line changing. Verified by
  regenerating rather than assumed.
- **Dashboards use the Influx measurement and its tags**, never a topic; **`orexis-firmware
  simulation` emits nothing**, because no board in that world states `mc:firmware`; **`infra/tests`
  mint their own probe topics.**

**What it cost is legibility.** Simulated traffic used to announce itself in the topic. It now
announces itself in the port, and someone tailing a broker has to know which one they are on.
That is a real loss and it is the price of the property below being true rather than asserted.

## So the property is preserved, and the test now checks the whole of it

`simulation` adopted `sensing`'s device ids — `sensor_fern` → `moisture_sensor_fern`,
`air_fern` → `air_temp_fern`, and the tomato and succulent probes likewise — and dropped the
prefix. The shared device is `moisture_sensor_fern`, and the assertion moved from the username to
the **grants**:

| | sensing | simulation |
|---|---|---|
| username | `moisture_sensor_fern` | `moisture_sensor_fern` |
| read `sensors/moisture_sensor_fern/command` | yes | yes |
| write `sensors/moisture_sensor_fern/reading` | yes | yes |
| read `actuators/valve_fern/status` | — | **yes** |

A **subset**, not an equality, and the extra grant is the interesting part: a stand-in reads the
valve status so its simulated soil can get wetter when the valve opens. A real probe just gets
wetter. Every topic the board actually uses is granted in both worlds; the stand-in needs one
more, and a board ignores it.

**What the property does not claim, and this is worth being exact about because the test's old
name overclaimed it:** *one flashed board works in either* is false, and
`series-and-bus-isolation` already said so — *"that argument died with the shared broker"*. Each
world mints its **own random password** for that username (`secrets.token_urlsafe(24)`, into
`world/<w>/secrets/`), and each broker listens on its own port. Both live in `config.h`, so
moving a board between worlds is a credential swap and a reflash.

What the property actually buys is that it is **only** that. The board is not re-modelled, not
re-identified and not re-granted: the same id, the same channels, the same ACL. That is a real
saving and a much smaller claim, and the test is named for what it checks now.

# Consequences

- **Tests fell by 15, and none was lost.** Every one is the `[society]` *instance* of a test
  parametrised over a world list — seven in `test_provenance`, four in `test_isolation`, and one
  each in `test_channels`, `test_inference`, `test_shapes` and `test_vocabulary`. The assertions
  all still run, over the worlds that remain. `test_shapes` trimmed itself, because it discovers
  worlds from disk rather than listing them.
- **Two tests had a premise nobody had noticed: *fern has exactly one sensor*.** True of
  `society`; false of a world where a probe and a thermometer share a board. Switching one sensor
  to `Push` left the other `Scheduled`, so the agent kept `Subscribing` and the test read as a
  failure while the design worked exactly as `who-holds-the-clock` describes. They state the
  premise they meant now — every sensor the agent polls — and one of them stopped hand-writing a
  derived fact to get there.
- **`test_the_simulated_world_derives_what_the_real_one_does` could not survive as an equality.**
  It compared two market worlds' ferns; the only world left with real devices has no market. It
  now pins the difference instead: everything `sensing`'s fern derives, `simulation`'s derives
  too, and the only thing the market world adds is `Bidding`. That still catches the failure it
  was written for — a simulated probe that stopped deriving `Subscribing` would fall out of the
  subset.
- **`test_two_sensors_on_different_properties_are_not_warned_about` had to change its property.**
  It added an `AirTemperature` sensor to fern to prove the duplicate-warning does *not* fire on
  distinct properties — and `simulation`'s fern already reads a temperature, so it fired
  correctly. It uses humidity now.

# Seams left open

- **Nothing in the repository describes a market world with real devices.** `society` was the
  only one, and it is gone. The wiring vocabulary and `orexis-firmware` are exercised by `sensing`
  alone, which has no market — so nothing checks that a market world's devices could be flashed.
- **The generated secrets for `simulation` are stale.** Device credentials are named after device
  ids, so `mqtt-sensor_fern.env` is now `mqtt-moisture_sensor_fern.env`; `orexis-mqtt simulation`
  has to run before that world starts again. Nothing warns — the world simply fails to
  authenticate, which is the shape of failure
  [#87](https://github.com/ShishkinDmitriy/orexis/issues/87) exists to make loud for belief bases
  and does not cover for credentials.
- **Simulated traffic is no longer self-describing.** Recorded above as the price of the property;
  if it turns out to matter, the answer is a per-world broker banner rather than a topic prefix,
  because the prefix is what made the property untrue.
