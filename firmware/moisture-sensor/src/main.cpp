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
//   publish:   sensors/<PLANT_ID>/moisture   {"value":0.183,"sensor":"<SENSOR_ID>"}
//   subscribe: sensors/<PLANT_ID>/cmd         {"sleep_s":N}  and/or  {"sense":true}   (retained)
//
// The board emits *numbers* only; the agent judges (band) and asserts them. Cadence ≠ content:
// the agent chooses *when* to look, but the reading is what the sensor measured.

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <esp_sleep.h>

#include "config.h"

static const char *MOISTURE_TOPIC = "sensors/" PLANT_ID "/moisture";
static const char *CMD_TOPIC = "sensors/" PLANT_ID "/cmd";

WiFiClient wifi;
PubSubClient mqtt(wifi);

uint32_t sleep_s = DEFAULT_SLEEP_S;

static float lastRaw = 0.0f; // kept for the serial line: calibration needs the RAW number

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
    if (mqtt.connect(clientId.c_str())) {
      Serial.printf("MQTT %s:%d connected as %s\n", MQTT_HOST, MQTT_PORT, clientId.c_str());
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
  delay(50);
  esp_sleep_enable_timer_wakeup((uint64_t)sleep_s * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {} // never reached — deep sleep restarts from setup()
