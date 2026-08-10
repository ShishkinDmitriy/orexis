"""How a device is REACHED — one directory per protocol, discovered by looking.

The same plug-in mechanism as a capability, borne by a BINDING rather than by an agent: which
protocol a device speaks is something only the device can say, so a driver is chosen at runtime
from what the sensor declares and nothing is derived onto an agent. Inside `agent/` for the same
reason capabilities are — only an agent loads a driver. Its two neighbours in the reading
pipeline, `codecs/` and `calibrations/`, work the same way.
"""
