"""The namespaces onboarding interpolates and the agent does not speak.

Onboarding reads the world's documents to mint a credential per principal, a dashboard per
observed property and a config.h per board, and some of what it reads — a board's pins, a part's
bus — is vocabulary no agent has a use for. Those namespaces are declared here, where they are
consumed, as the handful of IRIs the sovereign's tooling builds full terms in by interpolation.
A term interpolated this way is one a rename cannot see, which is why each is kept to what a
generator actually reads.
"""

SOSA = "http://www.w3.org/ns/sosa/"

# The hardware, as a world's hardware.ttl states it.
MC = "http://example.org/orexis/microcontroller#"
ONEWIRE = "http://example.org/orexis/onewire#"
I2C = "http://example.org/orexis/i2c#"
DHT11 = "http://example.org/orexis/dht11#"
RGBLED = "http://example.org/orexis/rgb-led#"
PROBE = "http://example.org/orexis/moisture-probe#"
ESP32 = "http://example.org/orexis/esp32#"
BME280 = "http://example.org/orexis/bme280#"

# And the capability packages the generators read across.
MARKET = "http://example.org/orexis/market#"
MQTT = "http://example.org/orexis/mqtt#"
SENSING = "http://example.org/orexis/sensing#"
ACTUATION = "http://example.org/orexis/actuation#"
REVIEW = "http://example.org/orexis/review#"

# What the simulator plays, which a generator gives a container and a credential.
SIM = "http://example.org/orexis/sim#"
