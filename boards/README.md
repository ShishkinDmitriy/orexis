# Custom Wokwi boards for the parts on this bench

Wokwi's catalogue has no KY-015 and its RGB LED is not wired in the order ours is, so both are
defined here. A Wokwi "board" turns out not to mean a microcontroller board — `ds18b20`, `lm35`
and `bmp180` are all in [wokwi/wokwi-boards](https://github.com/wokwi/wokwi-boards) — it means
**a graphic, a set of pin positions, and a delegation to a chip for behaviour**. That is exactly
the shape a sensor breakout has.

    board.json   the pins, in millimetres, and which chip pin each one reaches
    board.svg    the picture, sized in millimetres
    KY-0xx.svg   the original from Joy-IT, kept unmodified

## Loading one

    F1 → "Load custom board file…" → pick this directory

**One at a time.** The test harness places a single part of type `wokwi-custom-board`, so a
diagram cannot use both of these until they are published upstream. Until then
`world/<world>/wokwi/diagram.json` goes on naming `wokwi-dht22` and `wokwi-rgb-led`, which is
why these are here rather than wired into the generator.

## Where the numbers came from

Nothing was measured. A 0.1 inch header is **2.54 mm by definition**, so finding the header in
the drawing and dividing gives the scale for everything else:

| | header pitch in the SVG | scale | board |
|---|---|---|---|
| KY-015 | 103.2 units (three round pads in a row) | 0.024612 mm/unit | 14.69 × 26.61 mm |
| KY-016 | 85.24 units (four leg rectangles) | 0.029800 mm/unit | 14.63 × 32.21 mm |

Both SVGs draw their pads inside transformed groups, so the raw `cx`/`cy` are not the positions
on the page — the transforms have to be composed down the tree first. The KY-016's legs are thin
tall `<rect>`s rather than circles, which is why they do not look like pads at a glance.

The Joy-IT originals carry `width="1920" height="1017"`, a render size that matches neither the
viewBox nor the part. `board.svg` is the same drawing with those replaced by the millimetres
above, because Wokwi scales a board by what its SVG claims to be.

## What is settled and what is not

**KY-016 is certain.** Its order is `R G B GND` left to right, read off the module. Wokwi's
`wokwi-rgb-led` calls its common leg `COM`, and `target` is precisely the mechanism for
re-mapping — which is the whole reason this module needed a board of its own. It is common
cathode, which agrees with what `world/sensing` already states.

**KY-015's outer two pins are a guess.** The middle pin of a three-pin KY module is VCC by
convention — that is what makes the module survive being plugged in backwards — so only `S` and
`GND` are in question, and this file has `S` on the left. If the LED and the sensor come up with
their signal and ground swapped, that is this line and nothing else.

**The KY-015 delegates to `wokwi-dht22`, and that is fine here.** These boards exist to be a
visual model of the bench, not to simulate it, so the delegation only has to supply pin NAMES for
`target` to map onto — and `wokwi-dht22` has `VCC`, `SDA` and `GND`, which is what the KY-015
needs. What is drawn and labelled is our own board.

It would NOT be fine if anything ran. DHT11 and DHT22 do not encode alike: a DHT11 sends integer
bytes with zero decimals, a DHT22 sends 16-bit values scaled by ten with a signed temperature.
The firmware asks for `DHT11`, so a simulation would fail its checksum and `logAir()` would report
no answer. Making that truthful needs a `chip-ky-015` implementing DHT11 framing — worth knowing
the day someone wants the simulator, and worth nobody's afternoon before then.
