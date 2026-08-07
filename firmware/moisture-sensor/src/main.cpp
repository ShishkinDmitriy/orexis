// Agora — ESP32 soil-moisture sensor node (ag:Scheduled -> the agent holds ag:Subscribing).
//
// Inverted from a fixed-interval pusher: the *agent* owns the interval (policy), the board
// keeps to it (mechanism: sense + sleep). Each wake it reads, publishes, briefly listens for a
// new interval, then deep-sleeps. Realizes knowledge/decisions/agent-centric-epistemics.md
// (agent-driven sensing) and the connection/authorization model in knowledge/domain/gateway.md.
//
// This is deliberately NOT ag:Polling. Between wakes the board is unreachable, so it cannot be
// asked for a reading — it can only be told, in advance, how often to take one. The retained
// cadence command is what makes that reliable; `sense` is best-effort and lands only inside
// the CMD_WAIT_MS window. See knowledge/domain/sensing.md.
//
//   publish:   MOISTURE_TOPIC   {"value":0.183,"sensor":"<SENSOR_ID>"}
//   subscribe: CMD_TOPIC        {"sleep_s":N, "band":"LOW"}  and/or  {"sense":true}  (retained)
//
// Both topic names come from config.h and are the world's own, so they are not spelled out
// here — they used to be, as "sensors/<PLANT_ID>/moisture", which was already wrong.
//
// The board emits *numbers* only; the agent judges (band) and asserts them. Cadence ≠ content:
// the agent chooses *when* to look, but the reading is what the sensor measured. The band comes
// BACK on the command topic purely so the LED can show it — the board never computes one, and
// stripping the LED out changes nothing about what this node means.

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <esp_sleep.h>
#include <driver/gpio.h>
#include <string.h>   // strcmp, for the band names — Arduino.h usually pulls this in, and
                      // "usually" is not a thing to depend on across toolchain versions

#include "config.h"

// The topics come from config.h, which `agora-firmware` generates from the world's own
// ag:readingTopic and ag:commandTopic. They used to be built here as "sensors/" PLANT_ID
// "/moisture" — which assumed a topic SHAPE the world states explicitly, and would have gone
// quietly wrong the day a world named a topic differently.

WiFiClient wifi;
PubSubClient mqtt(wifi);

// These are properties of the FIRMWARE, not of this deployment, so they are not generated:
// changing one changes how the board behaves, not what it is. config.h may still override them.
#ifndef DEFAULT_SLEEP_S
#define DEFAULT_SLEEP_S 60      // cadence until the agent sets one
#endif
#ifndef MQTT_TRIES
#define MQTT_TRIES 10           // give up and sleep rather than hold the battery open
#endif
#ifndef CMD_WAIT_MS
#define CMD_WAIT_MS 1500        // listen window after publishing, to catch a retained cadence
#endif

uint32_t sleep_s = DEFAULT_SLEEP_S;

static float lastRaw = 0.0f; // kept for the serial line: calibration needs the RAW number

// ---------------------------------------------------------------------------------------------
// The status LED. Compiled out entirely unless the world says this board carries one — a board
// with no LED must not drive whatever GPIO 0 happens to be, since that is a strapping pin and
// holding it would leave the board in bootloader mode at the next reset.
//
// The colour is NOT this board's opinion. It shows the agent's verdict, which arrives on the
// same retained command message as the cadence, so a board waking from deep sleep is told what
// its agent currently thinks before it does anything else. The board contributes only the
// things the agent cannot know: that the wifi failed, that the broker refused it.
// ---------------------------------------------------------------------------------------------
#ifdef LED_RED_PIN

// Common cathode: a leg HIGH lights it. If yours is common anode, every colour here comes out
// as its complement — which is the visible symptom, and the fix is the world's `ag:model`
// being wrong rather than this file.
static void led(bool r, bool g, bool b) {
  digitalWrite(LED_RED_PIN, r);
  digitalWrite(LED_GREEN_PIN, g);
  digitalWrite(LED_BLUE_PIN, b);
}

static void ledBegin() {
  // Release the pads first: if the previous cycle held a colour through deep sleep, the hold
  // is still latched and digitalWrite would appear to do nothing at all.
  //
  // gpio_hold_* and NOT rtc_gpio_hold_*, which is the pairing that matters and which I got
  // wrong first: rtc_gpio_hold_en applies to a pad brought up as an RTC IO through
  // rtc_gpio_init. These are driven with pinMode/digitalWrite, i.e. through the digital IO
  // mux, and the digital half of the API is what holds those. The two compile identically and
  // the wrong one simply does not latch.
  gpio_deep_sleep_hold_dis();
  gpio_hold_dis((gpio_num_t)LED_RED_PIN);
  gpio_hold_dis((gpio_num_t)LED_GREEN_PIN);
  gpio_hold_dis((gpio_num_t)LED_BLUE_PIN);
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);
  led(1, 1, 0); // amber: awake, and nobody has told me anything yet
}

static void ledBlink(bool r, bool g, bool b, int times) {
  for (int i = 0; i < times; i++) {
    led(r, g, b); delay(120);
    led(0, 0, 0); delay(120);
  }
}

// LOW / OK / HIGH are the agent's bands — a verdict about ITS pot against ITS OWN limits, which
// is why the same number is LOW for a fern and OK for a succulent. The board only paints it.
static void ledBand(const char *band) {
  if      (!strcmp(band, "LOW"))  led(1, 0, 0);   // thirsty
  else if (!strcmp(band, "OK"))   led(0, 1, 0);
  else if (!strcmp(band, "HIGH")) led(0, 0, 1);   // wetter than it wants
  else                            led(1, 1, 0);   // a band this firmware does not know
}

// Hold the colour across deep sleep, so the state is readable at a glance rather than only
// during the few seconds the board is awake. This COSTS the deep sleep: an LED is 5-15 mA
// against a ~10 uA sleep budget, so on a battery node it would be the dominant drain by three
// orders of magnitude. It is deliberate here because this board is on USB. Anything on a
// battery should call led(0,0,0) instead and accept that the colour is only a flash.
static void ledHoldThroughSleep() {
  gpio_hold_en((gpio_num_t)LED_RED_PIN);
  gpio_hold_en((gpio_num_t)LED_GREEN_PIN);
  gpio_hold_en((gpio_num_t)LED_BLUE_PIN);
  gpio_deep_sleep_hold_en();
}

#else
static void ledBegin() {}
static void ledBlink(bool, bool, bool, int) {}
static void ledBand(const char *) {}
static void ledHoldThroughSleep() {}
static void led(bool, bool, bool) {}
#endif

static float readMoisture() {
  const int samples = 16;
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(MOISTURE_PIN);
    delay(5);
  }
  lastRaw = sum / (float)samples;
  float frac = (ADC_DRY - lastRaw) / (float)(ADC_DRY - ADC_WET); // dry->high, wet->low
  if (frac < 0.0f) frac = 0.0f;
  if (frac > 1.0f) frac = 1.0f;
  return frac;
}

static void publishMoisture() {
  char payload[96];
  float frac = readMoisture();
  snprintf(payload, sizeof(payload), "{\"value\":%.3f,\"sensor\":\"%s\"}", frac, SENSOR_ID);
  mqtt.publish(MOISTURE_TOPIC, payload);
  // The raw ADC goes to the serial line and NOT on the wire. Calibration is a fact about this
  // board's wiring, not something any agent should reason about — an agent reads a 0..1
  // fraction and would have no business knowing an ADC exists. But you cannot set ADC_DRY and
  // ADC_WET without seeing it, and a clamped 0.000 or 1.000 tells you nothing about how far
  // outside the range you are.
  Serial.printf("%s %s   [raw %.0f, calibrated dry=%d wet=%d%s]\n",
                MOISTURE_TOPIC, payload, lastRaw, ADC_DRY, ADC_WET,
                (frac <= 0.0f || frac >= 1.0f) ? "  <- CLAMPED, recalibrate" : "");
}

// The agent sets the cadence (sleep_s) and can ask for an extra reading while we're awake.
static void onCmd(char *topic, byte *payload, unsigned int len) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, len)) return;
  if (doc["sleep_s"].is<uint32_t>()) {
    uint32_t s = doc["sleep_s"];
    if (s < MIN_SLEEP_S) s = MIN_SLEEP_S;
    if (s > MAX_SLEEP_S) s = MAX_SLEEP_S; // constitutional cadence floor
    sleep_s = s;
    Serial.printf("cadence set: sleep %us\n", sleep_s);
  }
  // The agent's verdict, riding the same retained message as the cadence rather than a topic
  // of its own — the board is already subscribed here, and the ACL already grants it.
  if (doc["band"].is<const char *>()) {
    const char *band = doc["band"];
    Serial.printf("agent says: %s\n", band);
    ledBand(band);
  }
  if (doc["sense"] | false) {
    publishMoisture();
  }
}

// How strong the link is, in words. A board that cannot reach the broker looks identical
// whether the address is wrong or the signal is too weak to carry a TCP handshake — and the
// second is far more common on a battery node stuck behind a plant pot.
static const char *signalQuality(int rssi) {
  if (rssi >= -55) return "strong";
  if (rssi >= -67) return "good";
  if (rssi >= -75) return "weak — expect retries and dropped readings";
  return "very weak — move the board or add an antenna";
}

static void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  uint32_t began = millis();
  while (WiFi.status() != WL_CONNECTED) {
    // Red while trying. A board stuck here is otherwise indistinguishable from one asleep, and
    // "stuck associating" is the single most common failure on this bench — see the −80 dBm.
    ledBlink(1, 0, 0, 1);
    delay(60);
    Serial.print(".");
  }
  int rssi = WiFi.RSSI();
  // Association time is the other half of the picture: a strong signal that takes ten seconds
  // to associate is a congested channel, not a distance problem.
  Serial.printf(" %s  rssi %d dBm (%s), associated in %ums\n",
                WiFi.localIP().toString().c_str(), rssi, signalQuality(rssi), millis() - began);
}

// PubSubClient reports failures as a number and nothing else. Silence here is the worst
// possible symptom — a board that has WiFi and then says nothing looks identical whether the
// broker refused it, the address is wrong, or the network dropped. Name it.
static const char *mqttError(int state) {
  switch (state) {
    case -4: return "timeout — broker did not answer in time";
    case -3: return "connection lost";
    case -2: return "cannot reach the broker (wrong MQTT_HOST? not listening on the LAN?)";
    case -1: return "disconnected";
    case  1: return "broker rejected the protocol version";
    case  2: return "broker rejected the client id";
    case  3: return "broker unavailable";
    case  4: return "bad credentials";
    case  5: return "not authorised";
    default: return "unknown";
  }
}

static void connectMqtt() {
  String clientId = String("agora-sensor-") + PLANT_ID + "-" + String((uint32_t)ESP.getEfuseMac(), HEX);
  unsigned attempt = 0;
  while (!mqtt.connected()) {
    // The board connects AS ITSELF. The broker refuses anonymous clients and holds an ACL
    // derived from the world, so this credential is what entitles it to publish its own
    // readings and to hear its own cadence — and nothing else on the bus.
    if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
      Serial.printf("MQTT %s:%d connected as %s (user %s)\n", MQTT_HOST, MQTT_PORT,
                    clientId.c_str(), MQTT_USER);
      mqtt.subscribe(CMD_TOPIC); // retained cadence command arrives here on subscribe
      Serial.printf("subscribed %s\n", CMD_TOPIC);
      return;
    }
    Serial.printf("MQTT %s:%d attempt %u failed (state %d): %s\n",
                  MQTT_HOST, MQTT_PORT, ++attempt, mqtt.state(), mqttError(mqtt.state()));
    // Magenta from the FIRST failure, not from the last. It used to light only once the board
    // gave up, which is ten attempts and — with PubSubClient's socket timeout on an
    // unreachable broker — can be minutes of a board that looks perfectly fine. The whole
    // reason to have a lamp is to see the fault while it is happening.
    led(1, 0, 1);
    // Give up eventually rather than spinning on a wall forever: a board that cannot reach
    // the broker should sleep and retry on its own clock, not hold the battery open.
    if (attempt >= MQTT_TRIES) {
      Serial.printf("giving up for now — sleeping %us and trying again\n", sleep_s);
      // Held through the sleep, so the fault is still visible on a board that is now idle.
      // WiFi worked and the broker refused us: a credential or an ACL problem, which wants a
      // different person than a red LED does.
      ledHoldThroughSleep();
      esp_sleep_enable_timer_wakeup((uint64_t)sleep_s * 1000000ULL);
      esp_deep_sleep_start();
    }
    delay(1000);
  }
}

void setup() {
  Serial.begin(115200);
  delay(200); // let the USB serial attach, or the first lines are lost on a fresh boot
  analogReadResolution(12); // 0..4095
  ledBegin();

  // Say what this build actually is. Checking a board against the world is otherwise
  // guesswork, and the ids here must match genesis/<world>/world.ttl exactly.
  Serial.printf("\nagora moisture sensor\n  subject   %s\n  sensor    %s\n"
                "  broker    %s:%d\n  publishes %s\n  listens   %s\n",
                PLANT_ID, SENSOR_ID, MQTT_HOST, MQTT_PORT, MOISTURE_TOPIC, CMD_TOPIC);

  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onCmd);
  connectMqtt();

  // 1. sense + publish
  publishMoisture();

  // 2. listen briefly for the agent's cadence (a retained cmd is delivered on subscribe)
  unsigned long until = millis() + CMD_WAIT_MS;
  while (millis() < until) mqtt.loop();

  // 3. deep-sleep for the agent-set cadence, then the board wakes and repeats setup()
  Serial.printf("sleeping %us\n", sleep_s);
  mqtt.disconnect();
  ledHoldThroughSleep(); // whatever colour the agent last asked for stays lit
  delay(50);
  esp_sleep_enable_timer_wakeup((uint64_t)sleep_s * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {} // never reached — deep sleep restarts from setup()
