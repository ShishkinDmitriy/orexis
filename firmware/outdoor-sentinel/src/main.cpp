// Orexis — the OUTDOOR SENTINEL (sensing:PushProcedure + sensing:AlarmProcedure).
//
// A COPY of firmware/moisture-sentinel/src/main.cpp with these departures — a BME280 read in
// every payload, the FireBeetle 2 ESP32-E's own WS2812 as the lamp, dark-before-sleep, the
// battery's voltage off the board's own divider, and the probe's RAW COUNT published rather than
// a fraction — kept in step with the original by hand where they share (#461). What follows is
// the sentinel's own account.
//
// THE RAW COUNT, because a calibration is the agent's belief and not the board's: the count in
// dry air and in water is one probe in one bed, it drifts, and a board that scaled with it
// needed retrieving to be recalibrated. The agent scales the count by the two points it believes
// (sensing:TwoPoint), and is told what the probe reads now to revise them. So nothing here knows
// what dry or wet is; the ULP watches counts, and its window is counts wide.
//
// The second firmware, and the inverse temperament of the first. The moisture-sensor node is
// governed: the agent commands its cadence and its band, and the board keeps them. A sentinel
// is autonomous: it takes NO orders — no command topic, no subscribe, nothing to parse — so
// its agent derives sensing:Listening and can only receive. What it does instead:
//
//   - the ULP watches for MOVEMENT — the last published value plus/minus WAKE_DELTA — patrolling
//     for microamps while everything else deep-sleeps, and confirming a suspicious look before
//     it believes it;
//   - a crossing wakes the radio and publishes, marked "wake":"alarm" — something happened, so
//     the world hears it, rather than waiting out the rest of the heartbeat;
//   - a slow HEARTBEAT wake publishes regardless, so silence stays distinguishable from death:
//     the agent's Listening freshness rule (sensing:maxReadingAgeS) is an absolute, and the
//     heartbeat is generated to fit under it.
//
// Sampling is not reporting: the patrol's looks die in a register — no observation, no
// testimony — and only a crossing or a heartbeat becomes a published reading.
//
//   publish:   MOISTURE_TOPIC   {"moisture_raw":2412,"sensor":"<SENSOR_ID>"}       heartbeat
//              MOISTURE_TOPIC   {"moisture_raw":1830,"sensor":"<SENSOR_ID>",
//                                "wake":"alarm"}                             the news
//              — and, on a board the world gives a BME280 (BME280_SDA_PIN), the same
//              message carries "temperature", "humidity" and "pressure" beside the
//              count, each picked out by its own sensing:readingPointer; absent, never
//              zero, when the part does not answer; and where the board states its battery
//              divider (BATTERY_PIN), "battery" in volts.
//
// No sleep_s in the payload, deliberately: the ack is a receipt for a commanded cadence, and
// nothing commands this board. A push device that acked would invite its agent to hold a
// freshness rule the vocabulary says it may not have — the same reason the simulator's push
// mode omits it.
//
// COMPILE-UNTESTED HERE, like all firmware: the bench has the last word.

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <esp_sleep.h>

#include "config.h"

// The watch lives in ulp_watch.cpp. It is a DEVIATION alarm: the window is the last published
// value plus/minus WAKE_DELTA, and the operating range is not consulted — the heartbeat says
// where the value is, the ULP says that it moved. The two-rate patrol/confirm is written there.
#include "ulp_watch.h"

#ifndef HEARTBEAT_S
#define HEARTBEAT_S 600         // generated from the polling agent's own freshness rule
#endif
#ifndef MQTT_TRIES
// THREE, not ten. A failed wake is the expensive one: ten attempts at ~11s each is 110 seconds
// of radio at ~100mA — about 3 mAh against 0.25 for a wake that works, so two failures cost
// more than a whole day of heartbeats. A board that cannot reach the broker should sleep and
// try on its own clock rather than hold the radio open arguing with the network.
#define MQTT_TRIES 3
#endif
#ifndef WIFI_TIMEOUT_MS
#define WIFI_TIMEOUT_MS 20000
#endif

#ifndef OBSERVE_S
#define OBSERVE_S 0     // bench aid: seconds of live probe readout at boot. 0 disables it.
#endif

WiFiClient wifi;
PubSubClient mqtt(wifi);

static float lastRaw = 0.0f;

// The probe's raw count, averaged over sixteen looks: what is published, and what the ULP's window
// is centred on. Unscaled and unclamped — dry and wet are the agent's to say.
static float readMoisture() {
  const int samples = 16;
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(MOISTURE_PIN);
    delay(5);
  }
  lastRaw = sum / (float)samples;
  return lastRaw;
}

// ---------------------------------------------------------------------------------------------
// THE BATTERY, where the board states a divider on its battery port (BATTERY_PIN, and the ratio
// BATTERY_DIVIDER): the FireBeetle 2 ESP32-E halves the cell's voltage onto GPIO34 through 1 MΩ +
// 1 MΩ. Read in millivolts with the factory calibration the ESP32 carries in its eFuses
// (analogReadMilliVolts), since a raw count on this ADC is not linear enough to be a voltage, then
// scaled back up. Taken after ulpStop(), like every analogRead, since the ULP owns ADC1 until then.
#ifdef BATTERY_PIN
static float battV = -1.0f;

static void readBattery() {
  const int samples = 16;
  uint32_t sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogReadMilliVolts(BATTERY_PIN);
    delay(2);
  }
  battV = (sum / (float)samples) * BATTERY_DIVIDER / 1000.0f;
  Serial.printf("battery: %.3f V\n", battV);
}

// Appended as the air fields are: the closing brace becomes ",\"battery\":...}".
static void appendBattery(char *payload, size_t size) {
  if (battV < 0.0f) return;
  size_t n = strlen(payload);
  if (n == 0 || payload[n - 1] != '}') return;
  snprintf(payload + n - 1, size - (n - 1), ",\"battery\":%.3f}", battV);
}
#else
static void readBattery() {}
static void appendBattery(char *, size_t) {}
#endif

// ---------------------------------------------------------------------------------------------
// The outdoor air sensor: a BME280 over I2C, where the world's wiring states one. The sentinel
// had no air sensor at all until the terrace (#323); this is the governed node's contract
// carried over — the values ride the moisture message, each pointed at by its sensor in the
// world, OMITTED rather than zero when the part does not answer, because "0.0 C" is a
// plausible number in a way silence is not. The ULP watches none of this: it hangs off a bus
// the coprocessor cannot speak, and the world says so by never typing these channels with
// the alarm promise.
//
// Pressure is read and published too. No world points at it yet — no domain property names
// it — but the part produces all three in ONE forced conversion, and a value the board already
// holds is one pointer away from being wanted.
// ---------------------------------------------------------------------------------------------
#ifdef BME280_SDA_PIN
#include <Wire.h>
#include <Adafruit_BME280.h>

static Adafruit_BME280 bme;
static bool airValid = false;
static float airC = 0.0f, airRh = 0.0f, airHpa = 0.0f;   // RH as a FRACTION on the wire

static void readAir() {
  airValid = false;
  Wire.begin(BME280_SDA_PIN, BME280_SCL_PIN);
  if (!bme.begin(BME280_ADDR, &Wire)) {
    Serial.printf("BME280 not found at 0x%02X (SDA %d, SCL %d) — check the wiring, and the "
                  "SDO strap against i2c:address in the world\n",
                  BME280_ADDR, BME280_SDA_PIN, BME280_SCL_PIN);
    return;
  }
  // Forced mode, full oversampling — the part's ForcedModeCapability in the ontology. One
  // conversion per wake with the die idle otherwise, so self-heating never reaches the
  // temperature; the board deep-sleeps between wakes and the part sleeps with it.
  bme.setSampling(Adafruit_BME280::MODE_FORCED,
                  Adafruit_BME280::SAMPLING_X16,   // temperature
                  Adafruit_BME280::SAMPLING_X16,   // pressure
                  Adafruit_BME280::SAMPLING_X16,   // humidity
                  Adafruit_BME280::FILTER_OFF);
  if (!bme.takeForcedMeasurement()) { Serial.println("BME280: no answer"); return; }
  float c = bme.readTemperature(), rh = bme.readHumidity(), hpa = bme.readPressure() / 100.0F;
  if (isnan(c) || isnan(rh) || isnan(hpa)) { Serial.println("BME280: read returned NaN"); return; }
  airValid = true; airC = c; airRh = rh / 100.0f; airHpa = hpa;
  Serial.printf("air: %.2f C, %.1f%% RH (%.3f as a fraction), %.1f hPa\n", c, rh, airRh, hpa);
}

// The air fields, appended to a payload that already ends in a closing brace: the brace is
// replaced by ",...}" so the heartbeat and the alarm shapes above stay exactly as written.
static void appendAir(char *payload, size_t size) {
  if (!airValid) return;
  size_t n = strlen(payload);
  if (n == 0 || payload[n - 1] != '}') return;
  snprintf(payload + n - 1, size - (n - 1),
           ",\"temperature\":%.1f,\"humidity\":%.3f,\"pressure\":%.1f}", airC, airRh, airHpa);
}
#else
static void readAir() {}
static void appendAir(char *, size_t) {}
#endif

// Print what the probe is actually doing, so a band is set from a measurement rather than from
// an assumption about what "grabbing it" does to a capacitive sensor. Costs a boot delay and
// nothing else; OBSERVE_S 0 removes it.
static void observeProbe() {
  if (OBSERVE_S <= 0) return;
  Serial.printf("observing %ds — hold the probe in air, then in water, and watch the count move\n", OBSERVE_S);
  uint32_t until = millis() + (uint32_t)OBSERVE_S * 1000UL;
  float seenLo = 4095.0f, seenHi = 0.0f;
  while ((int32_t)(until - millis()) > 0) {
    float r = readMoisture();
    if (r < seenLo) seenLo = r;
    if (r > seenHi) seenHi = r;
    // The pin's voltage beside the count, by the factory calibration: a probe that is unpowered or
    // whose ground and signal are swapped shows a voltage no capacitive probe gives — roughly 1.2 V
    // in water to 2.5 V in air on 3.3 V — where the count alone only says "low".
    Serial.printf("  raw %6.0f   %4lu mV\n", r, (unsigned long)analogReadMilliVolts(MOISTURE_PIN));
    delay(400);
  }
  Serial.printf("observed counts %0.0f..%0.0f over %ds\n", seenLo, seenHi, OBSERVE_S);
}

// ---------------------------------------------------------------------------------------------
// THE STATUS LAMP, mirroring firmware/moisture-sensor — same colours, same counts, so one habit
// reads both boards. What a sentinel cannot borrow is the VERDICT: the governed node blinks one
// red for "the agent says LOW" and one blue for HIGH, and this board has no command channel and
// therefore no agent opinion to paint. So single blinks mean nothing here, and only the count-3
// faults and the connect signals survive.
//
//   one magenta   a broker attempt failed — one per attempt, up to MQTT_TRIES of them
//   TWO green     a broker attempt got in; this wake is going to work
//   three red     never reached the wifi
//   three magenta reached the wifi; the broker refused the connection, or the publish did
//
// A SUCCESSFUL SEND IS SILENCE after the green, deliberately and exactly as on the other board:
// the green already said the wake was working, and blinking again a second later to say "yes,
// still fine" is a lamp repeating itself, which teaches you to stop reading it. Nothing after
// the green means it published. (If you would rather have an explicit success blink, it is one
// line — but it costs the lamp the property that any blink after the green is bad news.)
//
// This lamp shares GPIO27 with the ULP's vigil lamp, which owns the pad in the RTC domain
// between wakes, so ledBegin() takes it back before the first analogWrite.
// ---------------------------------------------------------------------------------------------
#ifdef LED_RED_PIN

#ifndef LED_BRIGHTNESS
#define LED_BRIGHTNESS 20   // of 255. Firmware, not world: how this code behaves, not what the
#endif                      // board IS. Raise it if the pot sits in daylight.

static void led(bool r, bool g, bool b) {
  analogWrite(LED_RED_PIN,   r ? LED_BRIGHTNESS : 0);
  analogWrite(LED_GREEN_PIN, g ? LED_BRIGHTNESS : 0);
  analogWrite(LED_BLUE_PIN,  b ? LED_BRIGHTNESS : 0);
}
static void ledOff() { led(0, 0, 0); }

static void ledBegin() {
  vigilLampRelease();   // the ULP had the blue leg; take it back for the digital matrix
  ledOff();
}

static void ledBlink(bool r, bool g, bool b, int times) {
  for (int i = 0; i < times; i++) {
    led(r, g, b); delay(140);
    ledOff();     delay(140);
  }
}

// One blink per broker attempt, as it happens — the one place this lamp reports progress rather
// than an outcome, and deliberate: a broker that will not have us costs MQTT_TRIES attempts and
// a DNS or socket timeout each, which is a long time for a board to look exactly like one that
// is asleep. While it is failing, reaching the broker IS the thing being watched.
static void ledAttemptFailed() { ledBlink(1, 0, 1, 1); }
static void ledAttemptOk()     { ledBlink(0, 1, 0, 2); }

// THREE blinks. The count is what separates a fault from anything else, and it is why the
// governed node's single red (a thirsty plant) can never be confused with three red (a board
// that never found the wifi) from across the room.
static void ledFault(bool r, bool g, bool b) { ledBlink(r, g, b, 3); }

#elif defined(STATUS_LED_WS2812_PIN)
// The board's OWN lamp — a FireBeetle 2 ESP32-E carries a WS2812 on GPIO 5 by construction, so
// the world wires nothing and the generator reads the pin off the board's class. The same
// vocabulary as above, word for word: doubled green for a wake that got in, one magenta per
// refused broker attempt, three of a colour for a fault, nothing after the green when it
// published. Driven through the ESP32 core's RMT path (rgbLedWrite) rather than a library.
//
// It exists for BATTERY BRING-UP: a node meant to stay dark for months is hard to trust until
// it has been seen to wake and get in. Once it has, the board's low-power solder pad is cut
// (DFRobot: ~500 µA static; the LED then lights only on USB) — a knife, no reflash — and this
// code keeps writing to a lamp that draws nothing. No vigil lamp: the ULP's RTC-domain blink
// needs a bare GPIO, and a WS2812 needs a bit-stream the coprocessor cannot produce.
#ifndef LED_BRIGHTNESS
#define LED_BRIGHTNESS 20   // of 255, as for the discrete LED; a WS2812 at full is a torch
#endif

static void led(bool r, bool g, bool b) {
  rgbLedWrite(STATUS_LED_WS2812_PIN, r ? LED_BRIGHTNESS : 0, g ? LED_BRIGHTNESS : 0,
              b ? LED_BRIGHTNESS : 0);
}
static void ledOff() { led(0, 0, 0); }
static void ledBegin() { ledOff(); }

static void ledBlink(bool r, bool g, bool b, int times) {
  for (int i = 0; i < times; i++) {
    led(r, g, b); delay(140);
    ledOff();     delay(140);
  }
}
static void ledAttemptFailed() { ledBlink(1, 0, 1, 1); }
static void ledAttemptOk()     { ledBlink(0, 1, 0, 2); }
static void ledFault(bool r, bool g, bool b) { ledBlink(r, g, b, 3); }

#else
// A board the world gives no LED compiles all of this away — every one of them must exist,
// including those called only from the connect path.
static void ledBegin() {}
static void ledAttemptFailed() {}
static void ledAttemptOk() {}
static void ledFault(bool, bool, bool) {}
static void ledOff() {}
#endif

static bool connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  uint32_t began = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - began > WIFI_TIMEOUT_MS) {
      Serial.printf("no wifi after %ums\n", millis() - began);
      return false;
    }
    delay(300);
  }
  return true;
}

static bool connectMqtt() {
  String clientId = String("orexis-sentinel-") + SENSOR_ID + "-"
                    + String((uint32_t)ESP.getEfuseMac(), HEX);
  for (unsigned attempt = 1; attempt <= MQTT_TRIES; attempt++) {
    if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) { ledAttemptOk(); return true; }
    Serial.printf("MQTT attempt %u failed (state %d)\n", attempt, mqtt.state());
    ledAttemptFailed();
    delay(1000);
  }
  return false;
}

void setup() {
  Serial.begin(115200);
  delay(200);
  analogReadResolution(12);

  bool crossing = wokeByAlarm();
  // BEFORE readMoisture(), which calls analogRead() and takes ADC1 straight back off the ULP.
  // Whatever this prints was produced entirely during deep sleep.
  ulpStop();          // before ANY analogRead: the ULP still holds ADC1 from the last arm
  ulpReport("boot");
  ulpDumpAdcRegs("boot");
  readMoisture();
  Serial.printf("\norexis moisture sentinel  %s\nmoisture raw %.0f  wake: %s\n",
                SENSOR_ID, lastRaw, crossing ? "crossing" : "heartbeat");

  observeProbe();
  readMoisture();              // publish what is true after observing, not before
  readBattery();               // the board's own divider, where it states one
  readAir();                   // the BME280, where the world wires one; silent otherwise

  ledBegin();
  bool network = connectWifi(), published = false;
  if (network) {
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
    if (connectMqtt()) {
      char payload[256];   // room for the air fields beside the prior sample
      if (crossing) {
        // An alarm carries the PRIOR QUIET SAMPLE, and it is the difference between a graph
        // that tells the truth and one that does not. Two points half an hour apart — 0.15 and
        // 1.00 — are drawn as a straight line by every consumer, which claims a gradual
        // half-hour soak where there was a 25-second jump. The board knows better: it took
        // ~120 looks in that window and every one before the breach was in-window. So it says
        // so, and the agent can place that point at its own instant.
        //
        // `prev` mirrors the reading's own shape, so the same pointer reaches it one level
        // down: a sensor reading `/moisture_raw` finds its prior at `/prev/moisture_raw`.
        // The age comes off the RTC clock at THIS instant, so it already includes the time
        // spent connecting — and, across a failed attempt, the sleeps since. Nothing to add.
        float prevRaw; uint32_t prevAge;
        if (priorQuietSample(&prevRaw, &prevAge)) {
          snprintf(payload, sizeof(payload),
                   "{\"moisture_raw\":%.0f,\"sensor\":\"%s\",\"wake\":\"alarm\","
                   "\"prev\":{\"moisture_raw\":%.0f,\"age_s\":%lu}}",
                   lastRaw, SENSOR_ID, prevRaw, (unsigned long)prevAge);
        } else {
          snprintf(payload, sizeof(payload),
                   "{\"moisture_raw\":%.0f,\"sensor\":\"%s\",\"wake\":\"alarm\"}",
                   lastRaw, SENSOR_ID);
        }
      } else {
        snprintf(payload, sizeof(payload), "{\"moisture_raw\":%.0f,\"sensor\":\"%s\"}",
                 lastRaw, SENSOR_ID);
      }
      appendAir(payload, sizeof(payload));       // heartbeat and alarm alike: one message, all of it
      appendBattery(payload, sizeof(payload));
      bool sent = published = mqtt.publish(MOISTURE_TOPIC, payload);
      if (sent) noteReported(lastRaw);
      Serial.printf("%s %s   %s\n", MOISTURE_TOPIC, payload, sent ? "sent" : "REFUSED");
      mqtt.disconnect();
    }
  }

  // Say how it went, once, and only if it went badly. Everything before this point is silent
  // except the connect signals: a lamp that narrates the ordinary case has nothing left to mean
  // "look at me". Silence here is the good outcome — it published.
  if      (!network)   ledFault(1, 0, 0);   // three red: never reached the wifi
  else if (!published) ledFault(1, 0, 1);   // three magenta: no broker, or the publish refused
  ledOff();

  // Watch, then sleep until the value MOVES or the heartbeat comes due — whichever first.
  delay(50);
  // Dark before the sleep, again and last. A WS2812 HOLDS its colour with no further clocking,
  // so a lamp lit at the wrong moment would stay lit through a whole heartbeat on battery —
  // the discrete LED goes dark when its pins do, and never needed this.
  ledOff();
  armUlpWatch(lastRaw);
#ifdef ULP_SELFTEST_S
  ulpSelfTest(ULP_SELFTEST_S);
#endif
  esp_sleep_enable_timer_wakeup((uint64_t)HEARTBEAT_S * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}  // never reached — deep sleep restarts from setup()
