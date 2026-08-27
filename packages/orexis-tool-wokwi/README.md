# Custom Wokwi boards

Wokwi's catalogue has no KY-015 and its RGB LED is not wired in the order ours is, so both are
defined by the packages that own those parts:

    packages/orexis-part-dht11/wokwi/     the KY-015 breakout
    packages/orexis-part-rgb-led/wokwi/   the KY-016 module

They live with their parts rather than in a tree of their own, which is the same rule the rest of
this project follows: a part's drawing is one of the things a part knows about itself, beside its
pins and its datasheet figures. Deleting `packages/orexis-part-rgb-led/` takes its board with it.

A Wokwi "board" turns out not to mean a microcontroller board — `ds18b20`, `lm35` and `bmp180`
are all in [wokwi/wokwi-boards](https://github.com/wokwi/wokwi-boards) — it means **a graphic, a
set of pin positions, and a delegation to a chip for behaviour**. That is exactly the shape a
sensor breakout has.

    board.json   the pins, in millimetres, and which chip pin each one reaches
    board.svg    the picture, sized in millimetres
    KY-0xx.svg   the original from Joy-IT, kept unmodified

## Loading one

    F1 → "Load custom board file…" → pick the part's `wokwi/` directory

**One at a time.** The test harness places a single part of type `wokwi-custom-board`, so a
diagram cannot use both of these until they are published upstream. Until then
`world/<world>/wokwi/diagram.json` goes on naming `wokwi-dht22` and `wokwi-rgb-led`, which is why
these are here rather than wired into the generator.

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

What is settled and what is guessed about each one is stated with that part, not here.
