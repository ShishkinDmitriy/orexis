// Agora — ESP32 pump/valve node (the actuation edge).
//
// A *guarded* MQTT subscriber. On an executor command it opens the valve for a bounded
// time, then closes. It is dumb and stake-free, but because actuation is irreversible it
// enforces four things (see knowledge/domain/executor.md):
//   1. commands only from the executor topic (v1: trusted LAN; v2: signed grant / cert)
//   2. jti dedup — a redelivered command never double-waters
//   3. fail-safe watchdog — MAX_OPEN_SECONDS hard cap; close on lost connection
//   4. status publish — so the executor knows water actually flowed
//
//   subscribe: actuators/<PLANT_ID>/valve      {"jti","plant","ml","seconds",...}
//   publish:   actuators/<PLANT_ID>/valve/status

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

#include "config.h"

static const char *CMD_TOPIC = "actuators/" PLANT_ID "/valve";
static const char *STATUS_TOPIC = "actuators/" PLANT_ID "/valve/status";

WiFiClient wifi;
PubSubClient mqtt(wifi);

// Valve state + watchdog.
bool valveOpen = false;
unsigned long closeAtMs = 0;

// Small ring of recently-seen jtis for dedup.
static const int SEEN_N = 8;
String seenJti[SEEN_N];
int seenIdx = 0;

static void valveWrite(bool open) {
  int level = (VALVE_ACTIVE_HIGH ? (open ? HIGH : LOW) : (open ? LOW : HIGH));
  digitalWrite(VALVE_PIN, level);
}

static void closeValve(const char *reason) {
  valveWrite(false);
  if (valveOpen) {
    valveOpen = false;
    char msg[96];
    snprintf(msg, sizeof(msg), "{\"plant\":\"%s\",\"state\":\"closed\",\"reason\":\"%s\"}", PLANT_ID, reason);
    mqtt.publish(STATUS_TOPIC, msg);
    Serial.printf("valve closed (%s)\n", reason);
  }
}

static bool seenBefore(const String &jti) {
  for (int i = 0; i < SEEN_N; i++)
    if (seenJti[i] == jti) return true;
  seenJti[seenIdx] = jti;
  seenIdx = (seenIdx + 1) % SEEN_N;
  return false;
}

static void openValve(float seconds, const String &jti) {
  if (seconds > MAX_OPEN_SECONDS) seconds = MAX_OPEN_SECONDS; // hard edge cap
  if (seconds <= 0) return;
  valveWrite(true);
  valveOpen = true;
  closeAtMs = millis() + (unsigned long)(seconds * 1000.0);
  float ml = seconds * ML_PER_SECOND;
  char msg[128];
  snprintf(msg, sizeof(msg),
           "{\"plant\":\"%s\",\"state\":\"opening\",\"seconds\":%.2f,\"ml\":%.0f,\"jti\":\"%s\"}",
           PLANT_ID, seconds, ml, jti.c_str());
  mqtt.publish(STATUS_TOPIC, msg);
  Serial.printf("valve OPEN %.2fs (~%.0f ml) jti=%s\n", seconds, ml, jti.c_str());
}

static void onMessage(char *topic, byte *payload, unsigned int len) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, len)) {
    Serial.println("bad command payload");
    return;
  }
  String jti = doc["jti"] | "";
  float seconds = doc["seconds"] | 0.0;
  if (jti.isEmpty()) return;
  if (seenBefore(jti)) {                 // idempotency: ignore a redelivered command
    Serial.printf("dup jti=%s ignored\n", jti.c_str());
    return;
  }
  openValve(seconds, jti);
}

static void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
    closeValve("wifi-wait"); // fail-safe: never hold the valve open without a link
  }
  Serial.printf(" connected: %s\n", WiFi.localIP().toString().c_str());
}

static void connectMqtt() {
  while (!mqtt.connected()) {
    closeValve("mqtt-wait"); // fail-safe
    String clientId = String("agora-pump-") + PLANT_ID + "-" +
                      String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.print("MQTT...");
    // As itself: the broker refuses anonymous clients, and the ACL lets this valve hear its
    // own command topic and nothing else. See knowledge/decisions/series-and-bus-isolation.md.
    if (mqtt.connect(clientId.c_str(), MQTT_USER, MQTT_PASS)) {
      mqtt.subscribe(CMD_TOPIC, 1); // QoS 1
      Serial.printf("connected; subscribed %s\n", CMD_TOPIC);
    } else {
      Serial.printf("failed rc=%d; retry\n", mqtt.state());
      delay(1000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(VALVE_PIN, OUTPUT);
  closeValve("boot"); // valve closed by default
  valveOpen = false;
  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  // Watchdog: close the valve the instant its bounded time is up.
  if (valveOpen && (long)(millis() - closeAtMs) >= 0) {
    closeValve("done");
  }
}
