---
type: Decision
title: Firmware repeats itself rather than sharing
description: >-
  Each firmware project is self-contained and duplicates machinery — the ULP watcher twice,
  the RGB lamp twice — where the rest of this repository would extract. The reason is that a
  shared library is a shared reflash across boards that are physically hard to retrieve, and
  that what looks duplicated is usually the mechanism while the MEANING differs per board.
  Recorded because it was a real choice made only in C++ comments, and because the trigger for
  changing it is worth writing down before someone hits it.
status: accepted
timestamp: 2026-08-23T23:30:00Z
---

# Firmware repeats itself rather than sharing

Two firmwares now carry near-identical machinery twice over. `ulp_watch.cpp` exists in
`moisture-sensor` and `moisture-sentinel` with the same instruction sequence, the same
persistence counter and the same RTC-memory layout. The RGB lamp exists in both with the same
`led()`, `ledOff()` and `ledBlink()`. Everywhere else in this repository that would be a package
— rule 2 exists precisely to name an ability whose implementations could differ.

The choice to duplicate was made and never written down except as a sentence inside the code
it explains ("projects are deliberately self-contained, so the machinery is repeated rather
than shared"). **A default chosen in a comment is an unrecorded decision**, which is the same
trigger [bytes-become-a-quantity-in-stages](/decisions/bytes-become-a-quantity-in-stages.md)
acted on. This record makes it a decision, and — more usefully — says when it stops being one.

# The decision

**A firmware project is one directory that compiles on its own.** It shares no C or C++ with any
other firmware, and no package carries firmware source.

# Why, in the order the reasons actually matter

**A shared library is a shared reflash.** Every other kind of code here is deployed by rebuilding
a container. Firmware is deployed by physically retrieving a board out of a pot, which is the
cost this project has already paid three times for a port change, a credential rotation and a
calibration — the whole reason `orexis-firmware` exists. A library shared by two firmwares turns
a fix for one board into a re-flash of every board, and the blast radius of a mistake stops being
proportional to the change.

**What looks duplicated is the mechanism; the MEANING differs.** The lamp is the clean example.
Stripped of comments the two blocks are 24 and 19 lines and nearly identical. But the governed
node blinks one red for "the agent says this plant is thirsty" and one blue for "wetter than it
wants", and the sentinel has no command channel, therefore no agent verdict, therefore no single
blinks at all. The colours mean different things on the two boards. Extracting the mechanism
would leave the interesting half — which colour means what, and why — behind in both files
anyway, and would invite a future editor to add a verdict to a board that cannot have one.

**Packages carry knowledge, not firmware behaviour.** `packages/part/rgb_led/` is
`ontology.ttl` + `shapes.ttl` + `wokwi/`, and there is no C or C++ anywhere under `packages/`.
`agent.loader` reads Python; it would never see a header. So putting driver code there does not
extend the existing mechanic — it invents a second one, and couples `platformio.ini` to the
package tree in a direction nothing else uses. The right reading of AGENTS.md's "an omission is
a statement" is that a part package omits code because a part has no behaviour *a runtime* could
load; firmware is not loaded by any runtime here.

**What IS shared is shared already, and it is the part worth sharing.** Both boards read the same
world graph, are described by the same part ontologies, are drawn from the same `wokwi/` assets,
are held to the same shapes, and take their per-instance facts from the same generator. The
duplication is confined to the layer that touches silicon.

# When this stops being right

Written down deliberately, so the next person does not have to re-derive the argument:

- **A third consumer.** Two copies is a coincidence; three is a pattern, and the case for a
  shared lamp gets much stronger the moment a board other than these two has an RGB LED.
- **The two firmwares landing on one platform.** They are currently on different ones — the
  sentinel is pinned to pioarduino/IDF 5 and the governed node is still on IDF 4.4, which
  [#322](https://github.com/ShishkinDmitriy/orexis/issues/322) will resolve. A shared library
  cannot even be attempted until they agree, and once they do, one obstacle is gone.
- **A divergence that is a BUG rather than a difference.** The ULP watcher's two copies are the
  thing to watch. `two-owners-of-one-peripheral` fixed the ADC handover in one of them and left
  the identical defect latent in the other — which is exactly the failure duplication is supposed
  to be paid for avoiding. If that happens a second time, the price has been paid twice and the
  argument above is worth less than it reads.

That last one is the honest counter-argument and it is already partly true. This record is not a
claim that duplication is free; it is a claim that it is currently cheaper than the alternative,
with the receipts on both sides.

# Seams left open

- **Nothing detects drift between the two copies.** No test compares `moisture-sensor/src/ulp_watch.cpp`
  with `moisture-sentinel/src/ulp_watch.cpp`, so a fix to one silently leaves the other behind —
  and has, once. A guard that fails when they diverge without a comment saying why would make the
  duplication honest rather than merely intended.
- **The lamp's colour vocabulary is a convention held in prose.** "One blink is a verdict, three is
  a fault" is stated in both files and enforced by neither, and it is what keeps a thirsty plant
  (one red) from reading like a dead network (three red).
- **This says nothing about the simulated devices.** `simulated-sensor`, `simulated-valve` and
  `simulated-meddler` are Python in containers and share nothing with these two, which is a
  different situation with different economics and no reflash cost at all.
