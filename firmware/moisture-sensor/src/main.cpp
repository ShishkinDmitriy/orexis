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
//   publish:   MOISTURE_TOPIC   {"value":0.183,"sensor":"<SENSOR_ID>",
//                               "temperature":21.4,"humidity":0.463}
//              one message for the whole board — one client, one credential, one
//              channel. Each sensor in the world picks its own value out with an
//              ag:readingPointer; the air fields are absent if the part did not answer.
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
// Dark except while something is being attempted or reported, and dark through the whole sleep.
//
//   one magenta   a broker attempt failed — one per attempt, up to MQTT_TRIES of them
//   TWO green     a broker attempt got in; the wake is going to work
//   one red       the agent says LOW: this plant is thirsty
//   one blue      the agent says HIGH: wetter than it wants
//   three red     never reached the wifi
//   three magenta reached the wifi; the broker refused the connection or the publish
//
// Green is doubled so that a SINGLE blink always means the agent's verdict and never the
// board's own progress. The two are separated in time by the whole publish, but they are the
// two things you would be looking at the lamp for at once, and a lone green among lone reds
// and blues invited reading it as a third band.
//
// A green and then nothing is the ordinary healthy wake: it worked, and nobody is worried. OK
// is not a colour, because saying so a second later would only repeat the green — and a lamp
// that repeats itself is one you stop reading.
//
// The colour is not this board's opinion; it never computes a band. The COUNT is: one means an
// outcome, three means a fault, which is what keeps a thirsty plant (one red) from reading like
// a board that never found the network (three red).
// ---------------------------------------------------------------------------------------------
#ifdef LED_RED_PIN

// Common cathode: current out of a leg lights it. If yours is common anode, every colour here
// comes out as its complement — which is the visible symptom, and the fix is the world's
// `ag:model` being wrong rather than this file.
//
// Driven at a fraction of full duty rather than hard on. A modern indicator LED at 3.3V through
// a 220R is unpleasant to look at across a room, and this one sits on a windowsill rather than
// in a rack. LED_BRIGHTNESS is firmware, not world: it is a property of how this code behaves,
// not of what the board IS, so it is not generated. Raise it if the pot is in daylight.
//
// Red will still look brighter than green and blue at equal duty — its forward voltage is lower,
// so more current flows. If that bothers you, split this into three constants.
#ifndef LED_BRIGHTNESS
#define LED_BRIGHTNESS 20   // of 255
#endif

static void led(bool r, bool g, bool b) {
  analogWrite(LED_RED_PIN,   r ? LED_BRIGHTNESS : 0);
  analogWrite(LED_GREEN_PIN, g ? LED_BRIGHTNESS : 0);
  analogWrite(LED_BLUE_PIN,  b ? LED_BRIGHTNESS : 0);
}

static void ledOff() { led(0, 0, 0); }

// Dark, and dark is the resting state — not amber, not anything.
//
// It used to narrate: amber on boot, red flashing throughout the wifi association. Both were
// describing the ORDINARY case, which is the one nobody needs telling about, and a lamp lit
// during normal operation has no way left to mean "look at me". Associating is not a fault;
// failing to associate is.
static void ledBegin() { ledOff(); }  // analogWrite attaches the pad itself

static void ledBlink(bool r, bool g, bool b, int times) {
  for (int i = 0; i < times; i++) {
    led(r, g, b); delay(140);
    ledOff();     delay(140);
  }
}

// LOW / OK / HIGH are the agent's bands — a verdict about ITS pot against ITS OWN limits, which
// is why the same number is LOW for a fern and OK for a succulent. The board only paints it.
//
// OK is deliberately NOT a colour. Getting in already blinked green, and blinking green again a
// second later to say the plant is fine is the lamp repeating itself — which trains you to stop
// reading it. Silence after the green IS "OK": the wake worked and nobody is worried.
static bool haveBand = false;
static bool bandR = 0, bandG = 0, bandB = 0;

static void ledBand(const char *band) {
  if      (!strcmp(band, "LOW"))  { haveBand = 1; bandR = 1; bandG = 0; bandB = 0; }
  else if (!strcmp(band, "HIGH")) { haveBand = 1; bandR = 0; bandG = 0; bandB = 1; }
  else                              haveBand = 0;  // OK, or a band this firmware cannot read
}

// One blink per broker attempt, as it happens. The exception to reporting only outcomes, and a
// deliberate one: a broker that will not have us costs ten attempts and a socket timeout each,
// which is a long time for a board to look exactly like one that is asleep. While it is failing,
// reaching the broker is not the ordinary case — it is the thing being watched.
static void ledAttemptFailed() { ledBlink(1, 0, 1, 1); }
static void ledAttemptOk()     { ledBlink(0, 1, 0, 2); }

// ONE blink, and only when the agent said something worth adding: red thirsty, blue too wet.
static void ledVerdict() { if (haveBand) ledBlink(bandR, bandG, bandB, 1); }

// THREE blinks: it did not. The count is what separates a fault from a verdict, because LOW is
// also red — one red blink is a thirsty plant reported correctly, three is a board that never
// reached the wifi, and those must not be confusable from across the room.
static void ledFault(bool r, bool g, bool b) { ledBlink(r, g, b, 3); }

#else
// A board the world gives no LED compiles all of this away. Every one of these must exist,
// including the ones only called from the connect path — that is the half I forgot, and it
// would have failed to build on exactly the boards that have no lamp to test it with.
static void ledBegin() {}
static void ledBand(const char *) {}
static void ledAttemptFailed() {}
static void ledAttemptOk() {}
static void ledVerdict() {}
static void ledFault(bool, bool, bool) {}
static void ledOff() {}
static void led(bool, bool, bool) {}
#endif

// ---------------------------------------------------------------------------------------------
// The air sensor — published in the SAME message as the moisture.
//
// One board is one MQTT client with one credential, so it publishes once however many
// peripherals it carries. The world names three sensors on this one topic and each says which
// value is its own with an ag:readingPointer (RFC 6901): the probe takes `/value`, and the
// KY-015's two channels take `/temperature` and `/humidity`. Nothing new is granted — the
// payload grew, the channel did not.
//
// This used to be serial-only, because the model gave a sensor one property and the runtime
// took one reading per message. Both are fixed; see issue #51.
// ---------------------------------------------------------------------------------------------
#ifdef AIR_SENSOR_PIN
#include <DHT.h>

// The KY-015 breakout carries the pull-up, so the line needs nothing added.
static DHT dht(AIR_SENSOR_PIN, DHT11);

static bool airValid = false;
static float airC = 0.0f, airRh = 0.0f;   // RH as a FRACTION, which is what goes on the wire

static void airBegin() { dht.begin(); }

static void logAir() {
  // A DHT11 needs roughly a second from power-on before it will answer. The moisture read and
  // the serial banner ahead of this have already spent it, so nothing here sleeps to wait.
  float c = dht.readTemperature();
  float rh = dht.readHumidity();
  if (isnan(c) || isnan(rh)) {
    // Almost always the wiring rather than the part: a missing ground, or the data leg on a
    // pin that cannot drive. The sensor answers with silence either way.
    //
    // The fields are then OMITTED from the payload rather than sent as zero or as NaN. A
    // pointer that finds nothing makes its agent record nothing and say so; a zero would be
    // recorded as a measurement, and "0.0 C" is a plausible number in a way silence is not.
    airValid = false;
    Serial.printf("air sensor on GPIO %d: no answer\n", AIR_SENSOR_PIN);
    return;
  }
  // Humidity travels as a FRACTION, which is the form that makes the hazard obvious: 0.46 is
  // indistinguishable from a soil moisture by inspection, and lands inside the bands agents
  // hold. Nothing in the number says which it is; only the property does — which is why the
  // agent keys an observation by subject AND property, and why these are two sensors.
  airValid = true;
  airC = c;
  airRh = rh / 100.0f;
  Serial.printf("air sensor: %.1f C, %.0f%% RH (%.3f as a fraction)\n", c, rh, airRh);
}
#else
// A board with no air sensor wired says nothing about air: the fields are absent, exactly as
// they are when the part fails to answer. A world for such a board names no air sensors, so
// nothing points at them and nothing is missed.
static const bool airValid = false;
static const float airC = 0.0f, airRh = 0.0f;
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

// SENSING AND REPORTING ARE SEPARATE, and keeping them together was a real fault rather than
// an untidiness. Both early exits — no wifi, no broker — deep-sleep from inside the function
// that failed, so everything after them was unreachable. The moisture line and the air line
// both lived after them. The board therefore said nothing at all about what it had measured on
// exactly the wakes where it could not report: the ones you are holding a serial cable for.
//
// So it senses first, prints first, and only then goes looking for a network.
static float lastFrac = 0.0f;

static void senseMoisture() {
  lastFrac = readMoisture();
  // The raw ADC goes to the serial line and NOT on the wire. Calibration is a fact about this
  // board's wiring, not something any agent should reason about — an agent reads a 0..1
  // fraction and would have no business knowing an ADC exists. But you cannot set ADC_DRY and
  // ADC_WET without seeing it, and a clamped 0.000 or 1.000 tells you nothing about how far
  // outside the range you are.
  Serial.printf("moisture %.3f   [raw %.0f, calibrated dry=%d wet=%d%s]\n",
                lastFrac, lastRaw, ADC_DRY, ADC_WET,
                (lastFrac <= 0.0f || lastFrac >= 1.0f) ? "  <- CLAMPED, recalibrate" : "");
}

// One message carrying everything this board read, because it is one client with one
// credential and one channel. Each value is picked out by the pointer its sensor states in the
// world; a field that is absent is simply not read, and its agent says so rather than
// recording a zero.
static void publishReading() {
  char payload[160];
  int n = snprintf(payload, sizeof(payload), "{\"value\":%.3f,\"sensor\":\"%s\"",
                   lastFrac, SENSOR_ID);
  if (airValid && n > 0 && n < (int)sizeof(payload)) {
    n += snprintf(payload + n, sizeof(payload) - n, ",\"temperature\":%.1f,\"humidity\":%.3f",
                  airC, airRh);
  }
  if (n > 0 && n < (int)sizeof(payload)) {
    snprintf(payload + n, sizeof(payload) - n, "}");
  }
  published = mqtt.publish(MOISTURE_TOPIC, payload);
  Serial.printf("%s %s   %s\n", MOISTURE_TOPIC, payload,
                published ? "sent" : "REFUSED by the broker — check the ACL for this topic");
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
    senseMoisture();   // a nudge asks for a LOOK; republishing the last one would be a lie
    logAir();          // and the air with it, or the nudge would send a stale temperature
    publishReading();
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

// Both connect functions REPORT rather than act. They used to deep-sleep from inside
// themselves the moment they gave up, which made them the only exit from a wake and meant
// everything after them was unreachable — a board with no broker never reached the end of its
// own cycle. There is one exit now, at the bottom of setup(), and it is always taken.
static bool connectWifi() {
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
      Serial.printf("\nno wifi after %ums\n", millis() - began);
      return false;
    }
    delay(300);
    Serial.print(".");
  }
  int rssi = WiFi.RSSI();
  // Association time is the other half of the picture: a strong signal that takes ten seconds
  // to associate is a congested channel, not a distance problem.
  Serial.printf(" %s  rssi %d dBm (%s), associated in %ums\n",
                WiFi.localIP().toString().c_str(), rssi, signalQuality(rssi), millis() - began);
  return true;
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

static bool connectMqtt() {
  String clientId = String("agora-sensor-") + SENSOR_ID + "-" + String((uint32_t)ESP.getEfuseMac(), HEX);
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
      ledAttemptOk();
      return true;
    }
    Serial.printf("MQTT %s:%d attempt %u failed (state %d): %s\n",
                  MQTT_HOST, MQTT_PORT, ++attempt, mqtt.state(), mqttError(mqtt.state()));
    ledAttemptFailed();
    // Give up eventually rather than spinning on a wall forever: a board that cannot reach
    // the broker should sleep and retry on its own clock, not hold the battery open.
    if (attempt >= MQTT_TRIES) {
      Serial.printf("giving up on the broker for this wake\n");
      return false;
    }
    // NOTE: every exit from this function is inside the loop, which is why the compiler warns
    // that control can reach the end — the one path it cannot rule out is the loop condition
    // being false on entry, i.e. a session already up. That is not reachable today (the client
    // is disconnected before every sleep), and falling off the end of a bool function is
    // undefined behaviour rather than a tidy false, so it is answered explicitly below.
    delay(1000);
  }
  return mqtt.connected();  // already up on entry: report what is actually true
}

void setup() {
  Serial.begin(115200);
  delay(200); // let the USB serial attach, or the first lines are lost on a fresh boot
  analogReadResolution(12); // 0..4095
  ledBegin();
  airBegin();

  // Say what this build actually is. Checking a board against the world is otherwise
  // guesswork, and the ids here must match genesis/<world>/world.ttl exactly.
  Serial.printf("\nagora moisture sensor\n  sensor    %s\n"
                "  broker    %s:%d\n  publishes %s\n  listens   %s\n",
                SENSOR_ID, MQTT_HOST, MQTT_PORT, MOISTURE_TOPIC, CMD_TOPIC);

  // 1. read the instruments and say what they said. FIRST, and unconditionally: this needs no
  //    network, and the wakes where the network is missing are exactly the ones somebody is
  //    watching the serial line for.
  senseMoisture();
  logAir();  // both instruments, before anything is sent — see publishReading

  // 2. try to report it. Neither of these aborts the wake — the readings above are already on
  //    the serial line, and a board that cannot reach anyone is still a working sensor with
  //    nowhere to send. It finishes its cycle, says so, and sleeps like any other wake.
  bool network = connectWifi();
  bool broker = false;
  if (network) {
    mqtt.setServer(MQTT_HOST, MQTT_PORT);
    mqtt.setCallback(onCmd);
    broker = connectMqtt();
  }

  if (broker) {
    // The same numbers already printed above, not a second look.
    publishReading();
    // Then listen briefly: a retained cadence and verdict arrive the moment we subscribe.
    unsigned long until = millis() + CMD_WAIT_MS;
    while (millis() < until) mqtt.loop();
  }

  // 3. say how it went, once. Everything before this point is silent: a lamp that narrates the
  //    ordinary case has nothing left to mean "look at me".
  if (!network)        ledFault(1, 0, 0);  // three red: never reached the wifi
  else if (!published) ledFault(1, 0, 1);  // three magenta: no broker, or the publish refused
  else                 ledVerdict();       // silent unless the agent had something to add
  ledOff();

  // 4. deep-sleep for the agent-set cadence, then the board wakes and repeats setup()
  Serial.printf("sleeping %us\n", sleep_s);
  mqtt.disconnect();
  delay(50);
  esp_sleep_enable_timer_wakeup((uint64_t)sleep_s * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {} // never reached — deep sleep restarts from setup()
