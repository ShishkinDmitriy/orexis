# KY-015 as a Wokwi board

The DHT11 breadboard module drawn as a custom Wokwi board, so a diagram of this bench shows the
part that is actually on it. What a custom board IS, how to load one, and where the millimetres
came from: [`packages/tool/wokwi/README.md`](../../../tool/wokwi/README.md).

Source: [KY-015.svg](https://sensorkit.joy-it.net/files/files/sensors/KY-015/KY-015.svg), kept
unmodified. Details at [sensorkit.joy-it.net](https://sensorkit.joy-it.net/de/sensors/ky-015).

## Its outer two pins are a guess

The middle pin of a three-pin KY module is VCC by convention — that is what makes the module
survive being plugged in backwards — so only `S` and `GND` are in question, and `board.json` has
`S` on the left. **If the LED and the sensor come up with their signal and ground swapped, that is
this line and nothing else.**

## It delegates to `wokwi-dht22`, and that is fine here

These boards exist to be a visual model of the bench, not to simulate it, so the delegation only
has to supply pin NAMES for `target` to map onto — and `wokwi-dht22` has `VCC`, `SDA` and `GND`,
which is what the KY-015 needs. What is drawn and labelled is our own board.

**It would NOT be fine if anything ran.** DHT11 and DHT22 do not encode alike: a DHT11 sends
integer bytes with zero decimals, a DHT22 sends 16-bit values scaled by ten with a signed
temperature. The firmware asks for `DHT11`, so a simulation would fail its checksum and
`logAir()` would report no answer. Making that truthful needs a `chip-ky-015` implementing DHT11
framing — worth knowing the day someone wants the simulator, and worth nobody's afternoon before
then.
