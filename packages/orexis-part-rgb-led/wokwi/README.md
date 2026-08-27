# KY-016 as a Wokwi board

The 4-pin RGB LED module drawn as a custom Wokwi board. What a custom board IS, how to load one,
and where the millimetres came from:
[`packages/orexis-tool-wokwi/README.md`](../../../tool/wokwi/README.md).

Source: [KY-016.svg](https://sensorkit.joy-it.net/files/files/sensors/KY-016/KY-016.svg), kept
unmodified. Details at [sensorkit.joy-it.net](https://sensorkit.joy-it.net/de/sensors/ky-016).

## This one is certain

Its order is `R G B GND` left to right, read off the module. Wokwi's `wokwi-rgb-led` calls its
common leg `COM`, and `target` is precisely the mechanism for re-mapping — **which is the whole
reason this module needed a board of its own.** It is common cathode, which agrees with what
`world/sensing` already states.

Its legs are thin tall `<rect>`s in the source SVG rather than circles, which is why they do not
look like pads at a glance — relevant if the geometry is ever re-derived.
