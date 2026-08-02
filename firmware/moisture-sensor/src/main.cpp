// Agora — ESP32 soil-moisture sensor node (pull-based).
//
// Inverted from a fixed-interval pusher: the *agent* owns the cadence (policy), the board
// provides the mechanism (sense + sleep). Each wake it reads, publishes, briefly listens for
// an agent-set cadence, then deep-sleeps. Realizes knowledge/decisions/agent-centric-epistemics.md
// (agent-driven sensing) and the connection/authorization model in knowledge/domain/gateway.md.
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

static float readMoisture() {
  const int samples = 16;
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(MOISTURE_PIN);
    delay(5);
  }
  float raw = sum / (float)samples;
  float frac = (ADC_DRY - raw) / (float)(ADC_DRY - ADC_WET); // dry->high, wet->low
  if (frac < 0.0f) frac = 0.0f;
  if (frac > 1.0f) frac = 1.0f;
  return frac;
}

static void publishMoisture() {
  char payload[96];
  snprintf(payload, sizeof(payload), "{\"value\":%.3f,\"sensor\":\"%s\"}", readMoisture(), SENSOR_ID);
  mqtt.publish(MOISTURE_TOPIC, payload);
  Serial.printf("%s %s\n", MOISTURE_TOPIC, payload);
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

static void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.printf(" %s\n", WiFi.localIP().toString().c_str());
}

static void connectMqtt() {
  while (!mqtt.connected()) {
    String clientId = String("agora-sensor-") + PLANT_ID + "-" + String((uint32_t)ESP.getEfuseMac(), HEX);
    if (mqtt.connect(clientId.c_str())) {
      mqtt.subscribe(CMD_TOPIC); // retained cadence command arrives here on subscribe
    } else {
      delay(1000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12); // 0..4095

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
