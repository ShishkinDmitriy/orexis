// Agora — ESP32 soil-moisture sensor node.
//
// Reads a capacitive moisture sensor, maps the raw ADC reading to a 0..1 fraction
// using per-board calibration, and publishes it to MQTT for the gateway:
//
//   topic:   sensors/<PLANT_ID>/moisture
//   payload: {"value":0.183,"sensor":"<SENSOR_ID>"}
//
// The board is a dumb, stake-free transducer: it emits *numbers* only. The
// numeric->qualitative judgement (band, provenance, attestation) lives on the Pi,
// never here — recalibrate thresholds in backend/config/plants.yaml, no reflash.
// See knowledge/domain/gateway.md.

#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

#include "config.h"

static const char *TOPIC = "sensors/" PLANT_ID "/moisture";

WiFiClient wifi;
PubSubClient mqtt(wifi);

static void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.printf(" connected: %s\n", WiFi.localIP().toString().c_str());
}

static void connectMqtt() {
  while (!mqtt.connected()) {
    String clientId = String("agora-") + PLANT_ID + "-" +
                      String((uint32_t)ESP.getEfuseMac(), HEX);
    Serial.print("MQTT...");
    if (mqtt.connect(clientId.c_str())) {
      Serial.println("connected");
    } else {
      Serial.printf("failed rc=%d; retry in 1s\n", mqtt.state());
      delay(1000);
    }
  }
}

// Average several ADC samples and map to a 0..1 moisture fraction.
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

void setup() {
  Serial.begin(115200);
  analogReadResolution(12); // 0..4095
  connectWifi();
  mqtt.setServer(MQTT_HOST, MQTT_PORT);
}

void loop() {
  connectWifi();
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  float value = readMoisture();
  char payload[96];
  snprintf(payload, sizeof(payload), "{\"value\":%.3f,\"sensor\":\"%s\"}", value, SENSOR_ID);

  bool ok = mqtt.publish(TOPIC, payload);
  Serial.printf("%s %s %s\n", TOPIC, payload, ok ? "ok" : "PUBLISH FAILED");

  delay(PUBLISH_INTERVAL_MS);
}
