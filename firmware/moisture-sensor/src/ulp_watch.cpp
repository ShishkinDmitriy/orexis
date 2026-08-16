// The ULP watcher (#151), in its own translation unit so main.cpp stays about the wake cycle.
//
// The coprocessor samples the moisture ADC while the main core and the radio deep-sleep at
// microamps, compares the count against the commanded band, and wakes the board the moment the
// value leaves it. Sampling is not reporting: the per-second looks die in a register, and only
// a crossing is promoted to a full wake and a published reading marked "wake":"alarm".
//
// WHY ONE SECOND — the internal cadence, derived rather than guessed. The watch period is
// bounded by  tolerable_overshoot / worst_credible_slew.  Soil moisture is an integrator:
// between events it moves at drying speed (~10^-6/s, irrelevant here), and its fastest
// credible move is water ARRIVING — bounded by percolation, not by the pour, and measured on
// this bench at the valve's own rate: ~10 ml/s through 2 L-per-fraction is 0.005 fraction/s.
// Allowing the value to overrun a band edge by at most ~0.01 (a twentieth of a typical
// region) gives a period of about two seconds; one second clears it with margin to spare, and
// a hand-pour absorbed twice as fast still stays inside the allowance. What CANNOT be caught
// at any period is a transient that enters and leaves the band within one look — and for soil
// that transient is not physics: water does not leave in a second. So the period sets
// detection LATENCY, never detection probability, which is what makes one second safe rather
// than merely fast. (Pricing that microamp vigil against the radio wakes it saves is the
// energy-budget seam's business, recorded on #151.)
//
// Follows the canonical esp-idf ulp_adc example (ULP-FSM macro assembly). GPIO34 is ADC1
// channel 6, RTC-capable. COMPILE-UNTESTED HERE, like all firmware: the bench has the last word.
// config.h BEFORE the guard, because config.h is where WAKE_ON_ALARM is defined: testing it
// first compiled this whole file to nothing, and the linker — not any test — was what said so.
#include "config.h"

#ifdef WAKE_ON_ALARM

#include <Arduino.h>
#include "esp32/ulp.h"
#include "driver/adc.h"
#include "soc/rtc_cntl_reg.h"
#include "soc/sens_reg.h"

#include "ulp_watch.h"

#define ULP_MEM_LOW   0    // the too-wet count (fractions invert into counts; see below)
#define ULP_MEM_HIGH  1    // the too-dry count
#define ULP_PROG_START 8
#define ULP_ADC_CHANNEL 6  // GPIO34; if MOISTURE_PIN moves, check this row first

// The band, remembered across deep sleep the way sleep_s is not: RTC memory survives, so a
// wake that hears no fresh command keeps watching the band it was last told.
RTC_DATA_ATTR float rtc_wake_below = -1.0f;
RTC_DATA_ATTR float rtc_wake_above = -1.0f;
RTC_DATA_ATTR float rtc_wake_delta = -1.0f;
RTC_DATA_ATTR static float rtc_last_reported = -1.0f;

void noteReported(float frac) { rtc_last_reported = frac; }

static uint16_t fracToRaw(float frac) {
  // The probe reads high when dry: frac = (ADC_DRY - raw) / (ADC_DRY - ADC_WET), so the
  // fraction FLOOR becomes the count CEILING and vice versa.
  float raw = ADC_DRY - frac * (float)(ADC_DRY - ADC_WET);
  if (raw < 0) raw = 0;
  if (raw > 4095) raw = 4095;
  return (uint16_t)raw;
}

void armUlpWatch() {
  if (rtc_wake_below < 0 && rtc_wake_above < 0 && rtc_wake_delta < 0)
    return;  // nothing commanded; plain schedule
  // The armed window is the INTERSECTION of the band and last-report±delta, so the deviation
  // alarm costs the ULP nothing: one window, tightened here by arithmetic. Leaving the window
  // means either the band broke or the value jolted — the agent reads which from the value.
  float lo = (rtc_wake_below >= 0) ? rtc_wake_below : 0.0f;
  float hi = (rtc_wake_above >= 0) ? rtc_wake_above : 1.0f;
  if (rtc_wake_delta >= 0 && rtc_last_reported >= 0) {
    float dlo = rtc_last_reported - rtc_wake_delta;
    float dhi = rtc_last_reported + rtc_wake_delta;
    if (dlo > lo) lo = dlo;
    if (dhi < hi) hi = dhi;
  }
  uint16_t count_when_too_dry = fracToRaw(lo);
  uint16_t count_when_too_wet = fracToRaw(hi);
  RTC_SLOW_MEM[ULP_MEM_HIGH] = count_when_too_dry;
  RTC_SLOW_MEM[ULP_MEM_LOW]  = count_when_too_wet;

  // ADC1 in RTC-controlled mode, so the ULP may read it while everything else sleeps.
  adc1_config_width(ADC_WIDTH_BIT_12);
  adc1_config_channel_atten((adc1_channel_t)ULP_ADC_CHANNEL, ADC_ATTEN_DB_11);
  adc1_ulp_enable();

  const ulp_insn_t program[] = {
      I_ADC(R0, 0, ULP_ADC_CHANNEL),          // R0 = one sample of the soil
      I_MOVI(R3, 0),
      I_LD(R1, R3, ULP_MEM_HIGH),             // too-dry count
      I_SUBR(R2, R1, R0),                     // high - sample; overflow set if sample > high
      M_BXF(1),                               // crossed dry-wards -> wake
      I_LD(R1, R3, ULP_MEM_LOW),              // too-wet count
      I_SUBR(R2, R0, R1),                     // sample - low; overflow if sample < low
      M_BXF(1),                               // crossed wet-wards -> wake
      I_HALT(),                               // in band: sleep until the next look
      M_LABEL(1),
      I_WAKE(),                               // the world changed; say so
      I_HALT(),
  };
  size_t size = sizeof(program) / sizeof(ulp_insn_t);
  ulp_process_macros_and_load(ULP_PROG_START, program, &size);
  ulp_set_wakeup_period(0, 1000 * 1000);      // the derived period above: one look per second
  ulp_run(ULP_PROG_START);
  esp_sleep_enable_ulp_wakeup();
  Serial.printf("watching band %.3f..%.3f (counts %u..%u), one look per second\n",
                rtc_wake_below, rtc_wake_above,
                (unsigned)RTC_SLOW_MEM[ULP_MEM_LOW], (unsigned)RTC_SLOW_MEM[ULP_MEM_HIGH]);
}

bool wokeByAlarm() {
  return esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_ULP;
}

#endif  // WAKE_ON_ALARM
