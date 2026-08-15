// The sentinel's ULP watcher (#151), in its own unit so main.cpp stays about the wake cycle.
// Mirrors firmware/moisture-sensor/src/ulp_watch.cpp — projects are deliberately
// self-contained, so the machinery is repeated rather than shared; the governed node's copy
// carries the full derivation of the one-second period from the worst credible slew, and it
// holds here unchanged: soil moisture is an integrator, its fastest credible move is water
// arriving at percolation speed (~0.005 fraction/s on this bench), and one look per second
// bounds the band overrun well under a hundredth. The period sets detection LATENCY, never
// probability — water does not leave in a second. COMPILE-UNTESTED HERE; the bench decides.
#include <Arduino.h>
#include "esp32/ulp.h"
#include "driver/adc.h"
#include "soc/rtc_cntl_reg.h"
#include "soc/sens_reg.h"

#include "config.h"
#include "ulp_watch.h"

#define ULP_MEM_LOW   0    // the too-wet count
#define ULP_MEM_HIGH  1    // the too-dry count
#define ULP_PROG_START 8
#define ULP_ADC_CHANNEL 6  // GPIO34; if MOISTURE_PIN moves, check this row first

static uint16_t fracToRaw(float frac) {
  float raw = ADC_DRY - frac * (float)(ADC_DRY - ADC_WET);
  if (raw < 0) raw = 0;
  if (raw > 4095) raw = 4095;
  return (uint16_t)raw;
}

RTC_DATA_ATTR static float rtc_last_reported = -1.0f;

void noteReported(float frac) { rtc_last_reported = frac; }

void armUlpWatch() {
  // Band ∩ last-report±delta: the deviation alarm (in-band jolts — a stranger's water on a
  // comfortable pot, a leak still in-range) costs the ULP nothing but this arithmetic.
  float lo = WAKE_BAND_LOW, hi = WAKE_BAND_HIGH;
#ifdef WAKE_DELTA
  if (rtc_last_reported >= 0) {
    float dlo = rtc_last_reported - WAKE_DELTA, dhi = rtc_last_reported + WAKE_DELTA;
    if (dlo > lo) lo = dlo;
    if (dhi < hi) hi = dhi;
  }
#endif
  RTC_SLOW_MEM[ULP_MEM_HIGH] = fracToRaw(lo);   // drier than the tightened floor
  RTC_SLOW_MEM[ULP_MEM_LOW]  = fracToRaw(hi);   // wetter than the tightened ceiling

  adc1_config_width(ADC_WIDTH_BIT_12);
  adc1_config_channel_atten((adc1_channel_t)ULP_ADC_CHANNEL, ADC_ATTEN_DB_11);
  adc1_ulp_enable();

  const ulp_insn_t program[] = {
      I_ADC(R0, 0, ULP_ADC_CHANNEL),
      I_MOVI(R3, 0),
      I_LD(R1, R3, ULP_MEM_HIGH),
      I_SUBR(R2, R1, R0),      // high - sample; overflow set if sample > high (too dry)
      M_BXF(1),
      I_LD(R1, R3, ULP_MEM_LOW),
      I_SUBR(R2, R0, R1),      // sample - low; overflow set if sample < low (too wet)
      M_BXF(1),
      I_HALT(),
      M_LABEL(1),
      I_WAKE(),
      I_HALT(),
  };
  size_t size = sizeof(program) / sizeof(ulp_insn_t);
  ulp_process_macros_and_load(ULP_PROG_START, program, &size);
  ulp_set_wakeup_period(0, 1000 * 1000);   // the derived period: one look per second
  ulp_run(ULP_PROG_START);
  esp_sleep_enable_ulp_wakeup();
  Serial.printf("watching %0.3f..%0.3f (counts %u..%u)\n", lo, hi,
                (unsigned)RTC_SLOW_MEM[ULP_MEM_LOW],
                (unsigned)RTC_SLOW_MEM[ULP_MEM_HIGH]);
}

bool wokeByAlarm() {
  return esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_ULP;
}
