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
#ifndef WIFI_TIMEOUT_MS
#define WIFI_TIMEOUT_MS 20000   // stop holding the radio up for a network that is not there
#endif

uint32_t sleep_s = DEFAULT_SLEEP_S;

static float lastRaw = 0.0f; // kept for the serial line: calibration needs the RAW number

// Did this wake achieve the one thing it exists for. Read once, on the way to sleep — the lamp
// reports an OUTCOME rather than narrating progress, so nothing lights until this is settled.
static bool published = false;

// ---------------------------------------------------------------------------------------------
// The status LED. Compiled out entirely unless the world says this board carries one — a board
// with no LED must not drive whatever GPIO 0 happens to be, since that is a strapping pin and
// holding it would leave the board in bootloader mode at the next reset.
//
// ONE signal per wake, at the end, and dark the rest of the time — including the whole sleep.
//
//   one blink    the reading went out. Its COLOUR is the agent's verdict, which arrived on the
//                retained command message: red LOW, blue HIGH, green OK or no verdict offered.
//   three red    never reached the wifi
//   three mag.   reached the wifi; the broker refused the connection or the publish
//
// The colour is not this board's opinion — it never computes a band. The count is: one means an
// outcome, three means a fault, which is what keeps a thirsty plant (one red) from reading like
// a board that never found the network (three red).
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

static void ledOff() { led(0, 0, 0); }

// Dark, and dark is the resting state — not amber, not anything.
//
// The lamp says one thing per wake, at the end, when there is something to report. It used to
// narrate: amber on boot, red flashing throughout the wifi association. Both were describing
// the ORDINARY case, which is the one nobody needs telling about, and a lamp that is lit during
// normal operation has no way left to mean "look at me". Associating is not a fault; failing to
// associate is.
static void ledBegin() {
  pinMode(LED_RED_PIN, OUTPUT);
  pinMode(LED_GREEN_PIN, OUTPUT);
  pinMode(LED_BLUE_PIN, OUTPUT);
  ledOff();
}

static void ledBlink(bool r, bool g, bool b, int times) {
  for (int i = 0; i < times; i++) {
    led(r, g, b); delay(140);
    ledOff();     delay(140);
  }
}

// What one wake ended up meaning. Green until something says otherwise, so a board that gets
// all the way through with nobody's opinion about it still reports plainly that it worked.
static bool okR = 0, okG = 1, okB = 0;

// LOW / OK / HIGH are the agent's bands — a verdict about ITS pot against ITS OWN limits, which
// is why the same number is LOW for a fern and OK for a succulent. The board only paints it,
// and paints it once, on the way out.
static void ledBand(const char *band) {
  if      (!strcmp(band, "LOW"))  { okR = 1; okG = 0; okB = 0; }  // thirsty
  else if (!strcmp(band, "HIGH")) { okR = 0; okG = 0; okB = 1; }  // wetter than it wants
  else                            { okR = 0; okG = 1; okB = 0; }  // OK, or one we do not know
}

// ONE blink: the wake worked. Its colour is the agent's verdict if one arrived, green if not.
static void ledWorked() { ledBlink(okR, okG, okB, 1); }

// THREE blinks: it did not. The count is what separates a fault from a verdict, because LOW is
// also red — one red blink is a thirsty plant reported correctly, three is a board that never
// reached the wifi, and those must not be confusable from across the room.
static void ledFault(bool r, bool g, bool b) { ledBlink(r, g, b, 3); }

#else
static void ledBegin() {}
static void ledBand(const char *) {}
static void ledWorked() {}
static void ledFault(bool, bool, bool) {}
static void ledOff() {}
static void led(bool, bool, bool) {}
#endif

// ---------------------------------------------------------------------------------------------
// The air sensor — SERIAL ONLY, deliberately.
//
// Nothing publishes these numbers yet and nothing should. One device reports two properties
// down one line, and both the model (a sensor observes one property) and the runtime (one
// reading per message, first sensor that owns the topic wins) assume one — so wiring it to MQTT
// today would deliver temperature OR humidity and silently drop the other. That is the same
// failure keying an observation by subject alone produced, and it is tracked as its own issue.
//
// So this exists to answer one question: is the sensor alive and are its numbers sane. It goes
// where a person can read it and nowhere an agent can.
// ---------------------------------------------------------------------------------------------
#ifdef AIR_SENSOR_PIN
#include <DHT.h>

// The KY-015 breakout carries the pull-up, so the line needs nothing added.
static DHT dht(AIR_SENSOR_PIN, DHT11);

static void airBegin() { dht.begin(); }

static void logAir() {
  // Called AFTER the network is up on purpose: a DHT11 needs roughly a second from power-on
  // before it will answer, and connecting has already spent several. Reading it first would
  // mean sleeping for a second to no purpose on every single wake.
  float c = dht.readTemperature();
  float rh = dht.readHumidity();
  if (isnan(c) || isnan(rh)) {
    // Almost always the wiring rather than the part: a missing ground, or the data leg on a
    // pin that cannot drive. The sensor answers with silence either way.
    Serial.printf("air sensor on GPIO %d: no answer\n", AIR_SENSOR_PIN);
    return;
  }
  // Humidity printed as a FRACTION as well as a percentage, because the fraction is the form
  // it would take on the wire — and it is the form that makes the hazard obvious: 0.46 is
  // indistinguishable from a soil moisture by inspection, and lands inside the bands agents
  // hold. Nothing in the number says which it is; only the property does.
  Serial.printf("air sensor: %.1f C, %.0f%% RH (%.3f as a fraction) — logged only, not published\n",
                c, rh, rh / 100.0f);
}
#else
static void airBegin() {}
static void logAir() {}
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
  published = mqtt.publish(MOISTURE_TOPIC, payload);
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
    // Bounded, which it was not. The loop had no exit but success, so a board out of range sat
    // here with the radio up forever — the most expensive state it can be in, and the one it
    // would reach precisely when it could least afford it. It also meant "wifi did not
    // connect" was not an outcome anything could report, LED or otherwise.
    if (millis() - began > WIFI_TIMEOUT_MS) {
      Serial.printf("\nno wifi after %ums — sleeping %us and trying again\n",
                    millis() - began, sleep_s);
      ledFault(1, 0, 0); // three red: never reached the network
      ledOff();
      esp_sleep_enable_timer_wakeup((uint64_t)sleep_s * 1000000ULL);
      esp_deep_sleep_start();
    }
    delay(300);
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
    // Give up eventually rather than spinning on a wall forever: a board that cannot reach
    // the broker should sleep and retry on its own clock, not hold the battery open.
    if (attempt >= MQTT_TRIES) {
      Serial.printf("giving up for now — sleeping %us and trying again\n", sleep_s);
      // Three magenta: wifi worked and the broker refused us, which is a credential or an ACL
      // problem and wants a different person than a red light does.
      ledFault(1, 0, 1);
      ledOff();
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
  airBegin();

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
  logAir();  // serial only — see above

  // 2. listen briefly for the agent's cadence (a retained cmd is delivered on subscribe)
  unsigned long until = millis() + CMD_WAIT_MS;
  while (millis() < until) mqtt.loop();

  // 3. say how it went, once, and sleep. Everything before this point is silent: a lamp that
  //    narrates the ordinary case has nothing left to mean "look at me".
  //      one blink   it worked, coloured by the agent's verdict (green if it offered none)
  //      three red   never reached the wifi
  //      three mag.  reached the wifi, the broker would not have us, or refused the publish
  published ? ledWorked() : ledFault(1, 0, 1);
  ledOff();

  // 4. deep-sleep for the agent-set cadence, then the board wakes and repeats setup()
  Serial.printf("sleeping %us\n", sleep_s);
  mqtt.disconnect();
  delay(50);
  esp_sleep_enable_timer_wakeup((uint64_t)sleep_s * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {} // never reached — deep sleep restarts from setup()
