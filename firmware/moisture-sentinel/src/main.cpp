// Orexis — ESP32 soil-moisture SENTINEL (sensing:PushProcedure + sensing:AlarmProcedure).
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
//   publish:   MOISTURE_TOPIC   {"moisture":0.183,"sensor":"<SENSOR_ID>"}          heartbeat
//              MOISTURE_TOPIC   {"moisture":0.391,"sensor":"<SENSOR_ID>",
//                                "wake":"alarm"}                             the news
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
#define MQTT_TRIES 10
#endif
#ifndef WIFI_TIMEOUT_MS
#define WIFI_TIMEOUT_MS 20000
#endif

#ifndef OBSERVE_S
#define OBSERVE_S 0     // bench aid: seconds of live probe readout at boot. 0 disables it.
#endif

WiFiClient wifi;
PubSubClient mqtt(wifi);

static float lastFrac = 0.0f;
static float lastRaw = 0.0f;

static float readMoisture() {
  const int samples = 16;
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(MOISTURE_PIN);
    delay(5);
  }
  lastRaw = sum / (float)samples;
  float frac = (ADC_DRY - lastRaw) / (float)(ADC_DRY - ADC_WET);
  if (frac < 0.0f) frac = 0.0f;
  if (frac > 1.0f) frac = 1.0f;
  return frac;
}

// Print what the probe is actually doing, so a band is set from a measurement rather than from
// an assumption about what "grabbing it" does to a capacitive sensor. Costs a boot delay and
// nothing else; OBSERVE_S 0 removes it.
static void observeProbe() {
  if (OBSERVE_S <= 0) return;
  Serial.printf("observing %ds — grab the probe and watch the fraction move\n", OBSERVE_S);
  uint32_t until = millis() + (uint32_t)OBSERVE_S * 1000UL;
  float seenLo = 1.0f, seenHi = 0.0f;
  while ((int32_t)(until - millis()) > 0) {
    float f = readMoisture();
    if (f < seenLo) seenLo = f;
    if (f > seenHi) seenHi = f;
    Serial.printf("  raw %6.0f   frac %0.3f\n", lastRaw, f);
    delay(400);
  }
  Serial.printf("observed %0.3f..%0.3f over %ds — the band must contain the RESTING value "
                "and exclude the triggered one\n", seenLo, seenHi, OBSERVE_S);
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
  lastFrac = readMoisture();
  Serial.printf("\norexis moisture sentinel  %s\nmoisture %.3f  [raw %.0f]  wake: %s\n",
                SENSOR_ID, lastFrac, lastRaw, crossing ? "crossing" : "heartbeat");

  observeProbe();
  lastFrac = readMoisture();   // publish what is true after observing, not before

  ledBegin();
  bool network = connectWifi(), published = false;
  if (network) {
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
    if (connectMqtt()) {
      char payload[192];
      if (crossing) {
        // An alarm carries the PRIOR QUIET SAMPLE, and it is the difference between a graph
        // that tells the truth and one that does not. Two points half an hour apart — 0.15 and
        // 1.00 — are drawn as a straight line by every consumer, which claims a gradual
        // half-hour soak where there was a 25-second jump. The board knows better: it took
        // ~120 looks in that window and every one before the breach was in-window. So it says
        // so, and the agent can place that point at its own instant.
        //
        // `prev` mirrors the reading's own shape, so the same pointer reaches it one level
        // down: a sensor reading `/moisture` finds its prior at `/prev/moisture`.
        float prevFrac; uint32_t prevAge;
        if (priorQuietSample(&prevFrac, &prevAge)) {
          snprintf(payload, sizeof(payload),
                   "{\"moisture\":%.3f,\"sensor\":\"%s\",\"wake\":\"alarm\","
                   "\"prev\":{\"moisture\":%.3f,\"age_s\":%lu}}",
                   lastFrac, SENSOR_ID, prevFrac,
                   (unsigned long)(prevAge + millis() / 1000));  // age at THIS instant, not at
                                                                 // the wake: connecting took time
        } else {
          snprintf(payload, sizeof(payload),
                   "{\"moisture\":%.3f,\"sensor\":\"%s\",\"wake\":\"alarm\"}",
                   lastFrac, SENSOR_ID);
        }
      } else {
        snprintf(payload, sizeof(payload), "{\"moisture\":%.3f,\"sensor\":\"%s\"}",
                 lastFrac, SENSOR_ID);
      }
      bool sent = published = mqtt.publish(MOISTURE_TOPIC, payload);
      if (sent) noteReported(lastFrac);
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
  armUlpWatch(lastFrac);
#ifdef ULP_SELFTEST_S
  ulpSelfTest(ULP_SELFTEST_S);
#endif
  esp_sleep_enable_timer_wakeup((uint64_t)HEARTBEAT_S * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}  // never reached — deep sleep restarts from setup()
