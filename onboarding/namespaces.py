"""The hardware namespaces onboarding interpolates and the agent does not speak.

`orexis-firmware` reads a world's `hardware.ttl` to write a board's config.h — its pins, the part
on each bus — and that vocabulary is one no agent has a use for, so it is declared here, where it
is consumed, as the handful of IRIs the generator builds full terms in. A term interpolated this
way is one a rename cannot see, which is why each is kept to what the generator actually reads.
"""

MC = "http://example.org/orexis/microcontroller#"
ONEWIRE = "http://example.org/orexis/onewire#"
I2C = "http://example.org/orexis/i2c#"
DHT11 = "http://example.org/orexis/dht11#"
RGBLED = "http://example.org/orexis/rgb-led#"
PROBE = "http://example.org/orexis/moisture-probe#"
ESP32 = "http://example.org/orexis/esp32#"
BME280 = "http://example.org/orexis/bme280#"
