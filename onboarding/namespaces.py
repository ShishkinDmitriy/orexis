"""The namespaces onboarding interpolates and the kernel does not speak.

Onboarding legitimately knows packages and their vocabularies: it reads the ratified files
directly, to mint a credential per sensor, a dashboard per observed property, a config.h per
board. The kernel does not — it is a BDI engine, and what a reading looks like is sensing's
(the-stake-is-sensings-want). So a namespace the generators need and the kernel has no use for
is declared here, where it is consumed, rather than in the kernel vocabulary (`packages/orexis-progression-patience/ontology.py`), where it read as
the kernel's word. `SOSA` moved first (#378); the twelve package namespaces followed, which
closed the ratchet's KIND 3.

These are NOT a prefix registry — `agent.loader` reads those off each ontology, and a package
listed here still owns its own vocabulary. They are the handful of namespaces the sovereign's
tooling builds full IRIs in, by interpolation rather than by prefix, because it queries the
ratified files directly and not through a `Store` carrying `store.PREFIXES`. That is a way to
name a term a rename cannot see — an interpolated `bidsIn` went on compiling and matching
nothing for four merged PRs once market owned `market:bidsIn` — which is why
`tests/test_kernel_namespaces.py` resolves every term the kernel names, and why onboarding's
should get the same guard one day.
"""

SOSA = "http://www.w3.org/ns/sosa/"

# The hardware: `packages/part/` and `packages/bus/` ship no Python, so there is no `terms.py`
# of their own to hold these — a knowledge-only package being knowledge.
MC = "http://example.org/orexis/microcontroller#"
ONEWIRE = "http://example.org/orexis/onewire#"
I2C = "http://example.org/orexis/i2c#"
DHT11 = "http://example.org/orexis/dht11#"
RGBLED = "http://example.org/orexis/rgb-led#"
PROBE = "http://example.org/orexis/moisture-probe#"
ESP32 = "http://example.org/orexis/esp32#"

# And the capability packages the generators read across.
MARKET = "http://example.org/orexis/market#"
MQTT = "http://example.org/orexis/mqtt#"
SENSING = "http://example.org/orexis/sensing#"
ACTUATION = "http://example.org/orexis/actuation#"
REVIEW = "http://example.org/orexis/review#"

# What stands in for hardware nobody built — `packages/orexis-sim-standin/`, which the generators read
# to give a stand-in a container and a credential (a-stand-in-is-not-a-device). The SUBSTRATE
# vocabulary beside it, `device:`, is not here: the generators build an inventory and a harness
# from `mc:`, and never ask what anything is made of.
SIM = "http://example.org/orexis/sim#"
