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
#define ULP_MEM_LOOKS 2    // consecutive breaching looks so far (#180)
#define ULP_PROG_START 8
#define ULP_ADC_CHANNEL 6  // GPIO34; if MOISTURE_PIN moves, check this row first

#ifndef WAKE_PERSIST_LOOKS
#define WAKE_PERSIST_LOOKS 2   // the society's figure, generated; this is only the fallback
#endif

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
  RTC_SLOW_MEM[ULP_MEM_LOOKS] = 0;   // every arming starts the vigil over

  // ADC1 in RTC-controlled mode, so the ULP may read it while everything else sleeps.
  adc1_config_width(ADC_WIDTH_BIT_12);
  adc1_config_channel_atten((adc1_channel_t)ULP_ADC_CHANNEL, ADC_ATTEN_DB_11);
  adc1_ulp_enable();

  // The persistence counter (#180): a breach visible in exactly one look is an ADC glitch,
  // not physics — the same argument that derived the one-second period. A breaching look
  // increments a count in RTC memory, an in-window look resets it, and only the Nth
  // consecutive breach wakes the radio: N-1 seconds of latency, inside the overshoot
  // allowance the period already carries, for never paying a radio wake on a glitch.
  //
  // HOW TO READ THE MACHINE this program runs on, because it is small enough to hold whole.
  // The ULP-FSM is a four-register 16-bit accumulator machine: R0-R3, an ALU, no stack, no
  // interrupts. Its only memory is RTC_SLOW_MEM — 8 KB of 32-bit words that stay powered in
  // deep sleep, shared between this program (loaded at word ULP_PROG_START) and its data
  // (words 0..2 here); I_LD/I_ST move the LOW 16 bits of the word at [reg + offset], which is
  // why R3 is pinned to zero as a base address. The timer runs the program from the top every
  // wakeup period; nothing survives a run except what was stored to RTC_SLOW_MEM, which is
  // exactly why the looks-counter lives there and not in a register.
  //
  // Two comparison idioms, because the ISA has two:
  //   - I_SUBR sets the ALU overflow flag on BORROW, so "A - B then M_BXF" reads as
  //     "branch if B > A" — an unsigned compare of two registers, used for sample-vs-band
  //     because both sides are runtime values;
  //   - M_BGE branches when R0 >= an IMMEDIATE (it wraps JUMPR, which can only compare R0),
  //     used for count-vs-N because N is a compile-time constant — and it is why the count
  //     is loaded into R0 rather than a scratch register.
  //   - I_WAKE raises the wakeup signal to the sleeping SoC; I_HALT ends THIS run and hands
  //     back to the ULP timer for the next look. Every path must end in I_HALT, including
  //     the one after I_WAKE — waking the host does not stop the coprocessor.
  const ulp_insn_t program[] = {
      I_ADC(R0, 0, ULP_ADC_CHANNEL),          // R0 = one 12-bit SAR sample of the soil
      I_MOVI(R3, 0),                          // R3 = 0, the base every load/store hangs off
      I_LD(R1, R3, ULP_MEM_HIGH),             // R1 = RTC_SLOW_MEM[1]: the too-dry count
      I_SUBR(R2, R1, R0),                     // R2 = high - sample; borrow => sample > high
      M_BXF(1),                               // borrowed: crossed dry-wards -> a breaching look
      I_LD(R1, R3, ULP_MEM_LOW),              // R1 = RTC_SLOW_MEM[0]: the too-wet count
      I_SUBR(R2, R0, R1),                     // R2 = sample - low; borrow => sample < low
      M_BXF(1),                               // borrowed: crossed wet-wards -> a breaching look
      I_MOVI(R1, 0),                          // in window: the vigil starts over
      I_ST(R1, R3, ULP_MEM_LOOKS),            // RTC_SLOW_MEM[2] = 0
      I_HALT(),                               // this run is over; timer looks again in a second
      M_LABEL(1),                             // breached THIS look — is it news yet?
      I_LD(R0, R3, ULP_MEM_LOOKS),            // R0 = looks so far (R0, because JUMPR reads R0)
      I_ADDI(R0, R0, 1),                      // one more consecutive breaching look
      I_ST(R0, R3, ULP_MEM_LOOKS),            // remembered across runs, or a glitchy pair of
                                              // looks a minute apart would count as two
      M_BGE(2, WAKE_PERSIST_LOOKS),           // R0 >= N: the Nth consecutive breach is real
      I_HALT(),                               // one look is a glitch; look again first
      M_LABEL(2),
      I_WAKE(),                               // the world changed and STAYED changed; say so
      I_HALT(),                               // waking the host does not stop the watcher
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
