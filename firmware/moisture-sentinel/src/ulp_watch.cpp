// The sentinel's ULP watcher (#151), in its own unit so main.cpp stays about the wake cycle.
// Mirrors firmware/moisture-sensor/src/ulp_watch.cpp — projects are deliberately
// self-contained, so the machinery is repeated rather than shared. That is a decision with
// reasons and a stated expiry, not a habit: knowledge/decisions/firmware-repeats-rather-than-shares.md.
// Note the price it has already cost once — the ADC handover below was fixed HERE and the
// identical defect is still latent in the governed node's copy (#322).
//
// TWO RATES, and they answer different questions. PATROL (WATCH_PATROL_S) is how often the ULP
// asks "has anything changed"; CONFIRM (WATCH_CONFIRM_S) is how long it waits before deciding
// a suspicious look was real. Splitting them is what lets the patrol be cheap without making
// the confirmation slow: nothing is riding on the patrol interval except how soon a crossing is
// NOTICED, while the confirm interval is the whole cost of not trusting one ADC sample.
//
// WHAT THIS COSTS, stated plainly because the governed node's copy derives the opposite. That
// derivation is: soil moisture is an integrator, its fastest credible move is water arriving at
// percolation speed (~0.005 fraction/s on this bench), so a one-second look bounds the band
// overrun under a hundredth — which is why the period there sets detection LATENCY and never
// detection PROBABILITY. A 60-second patrol does not clear that bar. At the same slew the value
// can travel ~0.3 of a fraction between looks, wider than a typical band, so a pour can carry
// the pot clean through the window and settle before the ULP ever samples it. The promise
// weakens from "we will see it within a second" to "we will see where it ENDED UP within a
// minute" — fine for watching a pot drift, wrong for catching the act of watering.
//
// The energy this buys is small, and it is worth knowing which term dominates. By the README's
// own bench figures the vigil is ~3.6 mAh/day at one look per second and the radio is ~0.25 mAh
// per wake, so a 20-minute heartbeat (72 wakes/day, ~18 mAh) outweighs the entire watch budget
// several times over. Slowing the patrol saves at most ~3.5 mAh/day; the heartbeat is where the
// battery actually goes.
//
// COMPILE-UNTESTED HERE, like all firmware; the bench decides.
#include <Arduino.h>
#include "esp32/ulp.h"
// IDF 5.x: ulp_adc_init() replaces the adc1_config_* / adc1_ulp_enable dance. It exists
// BECAUSE the hand-rolled version is fragile — Espressif shipped it to do exactly the setup
// this file spent a whole bench session failing to get right on IDF 4.4, where the ULP's ADC
// did not survive deep sleep and four register-level fixes were measured to make no difference.
#include "ulp_adc.h"
#include "esp32-hal-periman.h"
#include "driver/rtc_io.h"
#include "soc/rtc_cntl_reg.h"
#include "soc/rtc_io_reg.h"
#include "soc/sens_reg.h"
#include <esp_sleep.h>

#include "config.h"
#include "ulp_watch.h"

#define ULP_MEM_LOW   0    // the too-wet count
#define ULP_MEM_HIGH  1    // the too-dry count
#define ULP_MEM_LOOKS 2    // consecutive breaching looks so far (#180)
#define ULP_MEM_LAST  4    // the ADC sample the ULP itself last saw — the only way to find out
                           // whether the coprocessor's view of the probe matches the CPU's
#define ULP_MEM_TICKS 3    // looks taken since the last arm — diagnostic only, never read by
                           // the program itself. A ULP that is not running leaves this at 0,
                           // which is the one fact a silent watcher cannot otherwise report.
#define ULP_PROG_START 8
#define ULP_ADC_CHANNEL 6  // GPIO34; if MOISTURE_PIN moves, check this row first

#ifndef WAKE_PERSIST_LOOKS
#define WAKE_PERSIST_LOOKS 2   // the society's figure, generated; this is only the fallback
#endif

// TWO RATES, because patrolling and confirming are different jobs (see the header note).
// The ESP32 ULP has five sleep-period registers and I_SLEEP_CYCLE_SEL picks which one governs
// the NEXT wakeup, so the program chooses its own next interval from the path it took:
// in-window ends by asking for the patrol rate, a breach ends by asking for the confirm rate.
#ifndef WATCH_PATROL_S
#define WATCH_PATROL_S 60      // between looks when nothing is wrong
#endif
#ifndef WATCH_CONFIRM_S
#define WATCH_CONFIRM_S 10     // between a suspicious look and the one that settles it
#endif
// The diagnostics that found the ADC-ownership bug (#151 bench, Aug 2026) are kept, not
// deleted — they are the only reason it was found, and the next hard question about this
// coprocessor will want them. ULP_VERBOSE 1 turns them all back on in one move.
#ifndef ULP_VERBOSE
#define ULP_VERBOSE 0
#endif

#define ULP_TIMER_PATROL  0    // SENS_SLEEP_CYCLES_S0 — the default the timer starts on
#define ULP_TIMER_CONFIRM 1    // SENS_SLEEP_CYCLES_S1

// ---------------------------------------------------------------------------------------------
// THE VIGIL LAMP — lit while the board is SUSPECTING and has not yet spoken.
//
// The window this shows is the persistence count (#180): the ULP has seen the value leave the
// armed window on at least one look, and is waiting to see whether it stays out. That is the
// board deciding whether it has news worth a radio wake — and it happens entirely with the SoC
// in deep sleep, which is the whole reason this cannot use the governed node's `analogWrite`
// idiom. The main CPU is not running. The ULP must drive the pin itself.
//
// So the lamp is an RTC GPIO written from inside the ULP program: one instruction on the
// breaching path, one on the in-window path. It costs the vigil two instructions and no
// wakeups, which is the only budget that matters here.
//
// WHAT IT MEANS, in one line each:
//   lit     the value is outside the window and the board is counting looks to be sure
//   dark    the last look was inside the window — nothing to say
//   lit through a wake  the count reached N, this wake is an alarm, and the publish is
//                       off-heartbeat news rather than the slow "still alive"
//
// It stays lit across the wake deliberately: the ULP leaves it on when it raises I_WAKE, and
// nothing clears it until the watch is re-armed at the end of setup(). So the lamp is on for
// the whole boot-connect-publish sequence of an alarm wake and dark for the whole of a
// heartbeat wake, which makes the two visibly different from across the room without the main
// CPU computing anything. Re-arming sets it low; if the value is still out of band the very
// next look lights it again, so a pot parked outside its range reads as a lamp that flickers
// once per re-arm rather than one that lies.
//
// ON/OFF ONLY. The ULP has no PWM, so this is full duty where the governed node's lamp is
// dimmed to LED_BRIGHTNESS — it will look considerably brighter than that board's. If that is
// unpleasant on a windowsill, the fix is a larger series resistor, not this file.
//
// NOT A BAND VERDICT. The governed node spends colours on the agent's opinion (one red thirsty,
// one blue too wet). This board never learns an opinion — it has no command channel — so the
// lamp says only "deciding", and the colour below is whichever leg is wired, not a meaning.
// ---------------------------------------------------------------------------------------------
// VIGIL_LED_DISABLE removes the lamp entirely — no rtc_gpio_init, no register writes inside the
// ULP program — so deep sleep can be tested with nothing but the ADC touching the RTC domain.
#ifndef VIGIL_LED_DISABLE
#define VIGIL_LED_DISABLE 0
#endif
#if !defined(VIGIL_LED_PIN) && defined(LED_BLUE_PIN) && !VIGIL_LED_DISABLE
#define VIGIL_LED_PIN LED_BLUE_PIN
#endif

#ifdef VIGIL_LED_PIN
// GPIO number -> RTC GPIO number, for the ESP32 pins that can be OUTPUTS in the RTC domain.
// The ULP addresses the RTC index, not the GPIO index, and they are not the same numbering —
// getting this wrong lights a different leg, or nothing, with no error anywhere. 34-39 are
// absent on purpose: they are input-only, so a lamp on one is a wiring mistake worth failing on.
static constexpr int rtcGpioOf(int gpio) {
  return gpio ==  0 ? 11 : gpio ==  2 ? 12 : gpio ==  4 ? 10 :
         gpio == 12 ? 15 : gpio == 13 ? 14 : gpio == 14 ? 16 : gpio == 15 ? 13 :
         gpio == 25 ?  6 : gpio == 26 ?  7 : gpio == 27 ? 17 :
         gpio == 32 ?  9 : gpio == 33 ?  8 : -1;
}
static_assert(rtcGpioOf(VIGIL_LED_PIN) >= 0,
              "VIGIL_LED_PIN is not an RTC-capable output pin; the ULP cannot drive it");

// Common CATHODE is assumed, as on the governed node: a high leg sources current and lights.
// Define VIGIL_LED_ACTIVE_LOW for a common-anode part, where the complement is true and the
// symptom is a lamp that appears stuck ON — because the in-window state, which is most of the
// time, is the one driving it.
#ifdef VIGIL_LED_ACTIVE_LOW
#define VIGIL_ON_LEVEL  0
#define VIGIL_OFF_LEVEL 1
#else
#define VIGIL_ON_LEVEL  1
#define VIGIL_OFF_LEVEL 0
#endif

#define VIGIL_RTC_BIT (RTC_GPIO_OUT_DATA_S + rtcGpioOf(VIGIL_LED_PIN))
#define VIGIL_LIT()   I_WR_REG_BIT(RTC_GPIO_OUT_REG, VIGIL_RTC_BIT, VIGIL_ON_LEVEL),
#define VIGIL_DARK()  I_WR_REG_BIT(RTC_GPIO_OUT_REG, VIGIL_RTC_BIT, VIGIL_OFF_LEVEL),
#else
#define VIGIL_LIT()
#define VIGIL_DARK()
#endif

static uint16_t fracToRaw(float frac) {
  float raw = ADC_DRY - frac * (float)(ADC_DRY - ADC_WET);
  if (raw < 0) raw = 0;
  if (raw > 4095) raw = 4095;
  return (uint16_t)raw;
}

RTC_DATA_ATTR static float rtc_last_reported = -1.0f;

void noteReported(float frac) { rtc_last_reported = frac; }

void armUlpWatch(float nowFrac) {
  // A DEVIATION alarm, and only that. The window is the last value the agent HEARD, plus and
  // minus WAKE_DELTA, clamped to the physical 0..1 of a saturation fraction — the operating
  // range does not appear here at all.
  //
  // Why the band is gone. Watching it too meant the ULP alarmed whenever the pot sat outside
  // its range, which is a SLOW fact the heartbeat already reports and the agent — who holds the
  // range — is better placed to judge. Worse, it made the intersection empty exactly when the
  // plant was thirsty, so a pot that needed water woke the radio every patrol forever. The two
  // jobs separate cleanly: the heartbeat says where the value IS, the ULP says that it MOVED.
  //
  // The band still sizes the trigger, upstream: WAKE_DELTA is sensing:alarmDeltaFraction of the
  // band width, so a fussy plant gets a tight delta and a tolerant one a loose delta. That
  // arrives already resolved to a number, which is why nothing below mentions a range.
  //
  // The reference is what was last PUBLISHED, not last sampled — a drift is measured from what
  // the agent believes, so an unheard reading cannot silently re-centre the window. Before the
  // first successful publish there is no such value, and the current sample stands in: arming
  // around something is better than a board that cannot alarm until it has managed to speak.
  float ref = (rtc_last_reported >= 0) ? rtc_last_reported : nowFrac;
  float lo = ref - WAKE_DELTA, hi = ref + WAKE_DELTA;
  // THE CLAMP IS IN FRACTIONS AND THE COMPARISON IS IN COUNTS, and reconciling the two is this
  // firmware's job. A fraction is defined by the calibration: 1.0 means "as wet as ADC_WET", not
  // "as wet as it gets". Water is wetter than a calibration point — the probe reads about 1100
  // where ADC_WET is 1300 — so readMoisture() clamps to 1.000 and hides it, while the ULP, which
  // compares raw counts and knows nothing of clamping, sees a sample below the wet threshold and
  // breaches on every look. Seen on the bench as an alarm every ~23 seconds for as long as the
  // probe stayed in the glass: re-arm, immediate breach, confirm, wake, publish, repeat. The dry
  // end is the same defect mirrored, for a pot drier than ADC_DRY.
  //
  // So an edge that has reached a PHYSICAL limit is opened to the hardware limit rather than
  // pinned to the calibration point. An open edge cannot fire: no 12-bit sample exceeds 4095,
  // and none is below 0.
  bool openDry = (lo <= 0.0f);   // the window already includes "drier than calibration knows"
  bool openWet = (hi >= 1.0f);   // ... and likewise wetter
  if (lo < 0.0f) lo = 0.0f;
  if (hi > 1.0f) hi = 1.0f;

  RTC_SLOW_MEM[ULP_MEM_HIGH] = openDry ? 4095 : fracToRaw(lo);  // drier than the floor
  RTC_SLOW_MEM[ULP_MEM_LOW]  = openWet ? 0    : fracToRaw(hi);  // wetter than the ceiling
  // Every word the ULP writes carries its PC in bits 31:21 and the address register in 17:16
  // (see I_ST in ulp.h), so a CPU-side read is meaningless without this mask. Reading one raw
  // is how "2746843456 looks" happened.
  static RTC_DATA_ATTR uint32_t rtc_magic;
  if (rtc_magic != 0x0BE71CE5) {          // power-on: RTC memory is whatever it was
    rtc_magic = 0x0BE71CE5;
    RTC_SLOW_MEM[ULP_MEM_TICKS] = RTC_SLOW_MEM[ULP_MEM_LOOKS] = RTC_SLOW_MEM[ULP_MEM_LAST] = 0;
#if ULP_VERBOSE
    Serial.println("first boot — ULP counters zeroed, nothing to report yet");
#endif
  } else {
    // ONE line, kept at normal verbosity: it is the whole health of the watcher. Zero looks
    // means the coprocessor stopped, which is silent in every other way.
    Serial.printf("ULP: %u looks, %u breaching, last sample %u\n",
                  (unsigned)(RTC_SLOW_MEM[ULP_MEM_TICKS] & 0xFFFF),
                  (unsigned)(RTC_SLOW_MEM[ULP_MEM_LOOKS] & 0xFFFF),
                  (unsigned)(RTC_SLOW_MEM[ULP_MEM_LAST]  & 0xFFFF));
  }
  RTC_SLOW_MEM[ULP_MEM_TICKS] = 0;
  RTC_SLOW_MEM[ULP_MEM_LOOKS] = 0;              // every arming starts the vigil over

  ulp_adc_cfg_t adcCfg = {
      .adc_n    = ADC_UNIT_1,
      .channel  = (adc_channel_t)ULP_ADC_CHANNEL,
      .atten    = ADC_ATTEN_DB_12,        // was ADC_ATTEN_DB_11, a deprecated alias for this
      .width    = ADC_BITWIDTH_12,
      .ulp_mode = ADC_ULP_MODE_FSM,
  };
  // RELEASE ADC1 FROM ARDUINO FIRST. analogRead() owns the unit through the oneshot driver, and
  // ulp_adc_init() is refused while it does — "adc1 is already in use", ESP_ERR_NOT_FOUND. This
  // is almost certainly the whole bug, and IDF 4.4 hid it: adc1_ulp_enable() returned success
  // with Arduino still holding the unit, so the ULP piggybacked on a configuration that lived
  // only as long as the CPU was awake, and lost it the moment the board slept. Every symptom
  // fits — correct samples awake, 4095 asleep, and no register we forced ever helping.
  //
  // Clearing the pin's bus runs Arduino's own detach handler, which deletes the oneshot unit
  // once no channel is left using it (esp32-hal-adc.c: adcDetachBus). GPIO34 is our only one.
  perimanClearPinBus(MOISTURE_PIN);
  esp_err_t adcErr = ulp_adc_init(&adcCfg);
  // Only worth a line when it FAILS — and it will, loudly, if anything ever takes ADC1 back:
  // "adc1 is already in use" is what a whole evening of this looked like before it was found.
  if (adcErr != ESP_OK) Serial.printf("ulp_adc_init FAILED: %s\n", esp_err_to_name(adcErr));
#if ULP_VERBOSE
  else Serial.println("ulp_adc_init: ESP_OK");
#endif

  // FOUR REGISTER-LEVEL "FIXES" LIVED HERE, and every one was measured on the bench to make no
  // difference: clearing analogRead's software-force bits, forcing SENS_FORCE_XPD_SAR,
  // RTC_CNTL_CKGEN_I2C_PU, and the analog bias pair — plus, briefly, an always-on CK8M that was
  // itself a defect. None of them was the problem. The coprocessor simply did not own ADC1, and
  // no amount of powering a peripheral helps while someone else holds it. Deleted rather than
  // kept, because a wrong explanation sitting in a file is worse than none:
  // see knowledge/decisions/two-owners-of-one-peripheral.md.

#if ULP_VERBOSE
  Serial.printf("ADC1 handed to ULP (DATA_INV %s)\n",
                REG_GET_BIT(SENS_SAR_READ_CTRL_REG, SENS_SAR1_DATA_INV_M) ? "set" : "clear");
#endif

#ifdef VIGIL_LED_PIN
  // Hand the leg to the RTC domain and start it dark. This is also what clears a lamp the ULP
  // left lit through an alarm wake: arming is the moment the board has finished saying its
  // piece, so it is the honest moment to stop suspecting out loud.
  rtc_gpio_init((gpio_num_t)VIGIL_LED_PIN);
  rtc_gpio_set_direction((gpio_num_t)VIGIL_LED_PIN, RTC_GPIO_MODE_OUTPUT_ONLY);
  rtc_gpio_set_level((gpio_num_t)VIGIL_LED_PIN, VIGIL_OFF_LEVEL);
#endif
  // NOT the lamp's, though it lived inside the lamp's #ifdef until now: the SAR ADC is an RTC
  // peripheral and needs this domain up in sleep whether or not a leg is wired. Scoped to the
  // lamp, "disable the lamp" silently also meant "power down the ADC" — which would have made
  // the experiment below lie about its own result.
  esp_sleep_pd_config(ESP_PD_DOMAIN_RTC_PERIPH, ESP_PD_OPTION_ON);
  // The program and its four data words live here. Enabling ULP wakeup is supposed to imply
  // this, but "supposed to" is what we are currently testing.
  esp_sleep_pd_config(ESP_PD_DOMAIN_RTC_SLOW_MEM, ESP_PD_OPTION_ON);

#if ULP_MINIMAL_TEST
  // THE BISECT, in levels, because the real program adds three things to a bare counter and any
  // one of them could be what dies in deep sleep. Each level adds exactly one. Flash, sleep once,
  // read the ULP @boot line: ticks climbing by ~6 means that level survives deep sleep.
  //
  //   1  count only ................ is the ULP running in sleep at all?
  //   2  + I_SLEEP_CYCLE_SEL ....... does the two-rate instruction stop the timer?
  //   3  + I_ADC .................... does sampling stall on a converter with no power?
  //
  // Level 2 is a real suspect and not a formality: selecting a sleep-cycle register is the one
  // instruction here that touches the timer the ULP depends on to run again, and it is the piece
  // this firmware added most recently. Level 3 isolates the ADC with no branches around it.
#if ULP_MINIMAL_TEST >= 3
  const ulp_insn_t program[] = {
      I_MOVI(R3, 0),
      I_ADC(R0, 0, ULP_ADC_CHANNEL),
      I_ST(R0, R3, ULP_MEM_LAST),
      I_LD(R1, R3, ULP_MEM_TICKS),
      I_ADDI(R1, R1, 1),
      I_ST(R1, R3, ULP_MEM_TICKS),
      I_SLEEP_CYCLE_SEL(ULP_TIMER_PATROL),
      I_HALT(),
  };
#elif ULP_MINIMAL_TEST == 2
  const ulp_insn_t program[] = {
      I_MOVI(R3, 0),
      I_LD(R1, R3, ULP_MEM_TICKS),
      I_ADDI(R1, R1, 1),
      I_ST(R1, R3, ULP_MEM_TICKS),
      I_SLEEP_CYCLE_SEL(ULP_TIMER_PATROL),
      I_HALT(),
  };
#else
  const ulp_insn_t program[] = {
      I_MOVI(R3, 0),
      I_LD(R1, R3, ULP_MEM_TICKS),
      I_ADDI(R1, R1, 1),
      I_ST(R1, R3, ULP_MEM_TICKS),
      I_HALT(),
  };
#endif
  Serial.printf("*** ULP_MINIMAL_TEST level %d — not the real watcher ***\n", ULP_MINIMAL_TEST);
#else
  const ulp_insn_t program[] = {
      I_ADC(R0, 0, ULP_ADC_CHANNEL),   // R0 = one 12-bit sample
      I_MOVI(R3, 0),                   // base address for every load/store
      I_ST(R0, R3, ULP_MEM_LAST),      // what the COPROCESSOR saw, not what the CPU saw
      I_LD(R1, R3, ULP_MEM_TICKS),     // "I ran" — before any branch, so every path counts
      I_ADDI(R1, R1, 1),
      I_ST(R1, R3, ULP_MEM_TICKS),
      I_LD(R1, R3, ULP_MEM_HIGH),
      I_SUBR(R2, R1, R0),              // high - sample; borrow => sample > high (too dry)
      M_BXF(1),
      I_LD(R1, R3, ULP_MEM_LOW),
      I_SUBR(R2, R0, R1),              // sample - low; borrow => sample < low (too wet)
      M_BXF(1),
      VIGIL_DARK()                     // in window: nothing to say, so say nothing
      I_MOVI(R1, 0),                   // in window: the vigil starts over
      I_ST(R1, R3, ULP_MEM_LOOKS),
      I_SLEEP_CYCLE_SEL(ULP_TIMER_PATROL),   // nothing wrong: go back to the slow patrol
      I_HALT(),                        // hand back to the timer for the next look
      M_LABEL(1),                      // breached this look — news only if it persists
      VIGIL_LIT()                      // suspecting, out loud, from the first look
      I_LD(R0, R3, ULP_MEM_LOOKS),     // into R0, because JUMPR can compare only R0
      I_ADDI(R0, R0, 1),
      I_ST(R0, R3, ULP_MEM_LOOKS),     // durable across runs; registers are not
      M_BGE(2, WAKE_PERSIST_LOOKS),    // R0 >= N: the Nth consecutive breach is real
      I_SLEEP_CYCLE_SEL(ULP_TIMER_CONFIRM),  // suspicious: come back soon and settle it
      I_HALT(),
      M_LABEL(2),
      I_MOVI(R0, 0),                   // the alarm is spent: the NEXT one needs N fresh breaches
      I_ST(R0, R3, ULP_MEM_LOOKS),     // without this the count keeps climbing past N and every
                                       // further look re-wakes the radio — an alarm storm for as
                                       // long as the value stays out. The self-test showed it
                                       // going 1,2,3,4 while the CPU was up to ignore the wakes.
      VIGIL_DARK()                     // confirmed: the lamp's job is over. It marks the WAIT —
                                       // breached once, not yet believed — and nothing else, so
                                       // it goes out at the moment of decision rather than
                                       // staying lit through the wake and the publish.
      I_WAKE(),                        // raise the SoC's wakeup signal
      I_SLEEP_CYCLE_SEL(ULP_TIMER_PATROL),   // said our piece; the host re-arms in a moment
      I_HALT(),                        // waking the host does not stop the watcher
  };
#endif
  size_t size = sizeof(program) / sizeof(ulp_insn_t);
  ulp_process_macros_and_load(ULP_PROG_START, program, &size);
  ulp_set_wakeup_period(ULP_TIMER_PATROL,  (uint32_t)WATCH_PATROL_S  * 1000000UL);
  ulp_set_wakeup_period(ULP_TIMER_CONFIRM, (uint32_t)WATCH_CONFIRM_S * 1000000UL);
  ulp_run(ULP_PROG_START);
  esp_sleep_enable_ulp_wakeup();
  ulpDumpAdcRegs("arm");
#ifdef VIGIL_LED_PIN
  const int lampPin = VIGIL_LED_PIN;
#else
  const int lampPin = -1;   // no leg wired; the vigil is silent
#endif
  Serial.printf("watching %0.3f+-%0.3f = %0.3f..%0.3f (counts %u..%u), "
                "patrol %ds confirm %ds x%d, lamp %d\n",
                ref, (float)WAKE_DELTA, lo, hi, (unsigned)RTC_SLOW_MEM[ULP_MEM_LOW],
                (unsigned)RTC_SLOW_MEM[ULP_MEM_HIGH],
                WATCH_PATROL_S, WATCH_CONFIRM_S, WAKE_PERSIST_LOOKS, lampPin);
}

void ulpDumpAdcRegs(const char *when) {
  // Measure, do not guess. Called once at boot (before anything reconfigures the ADC) and once
  // at the end of arm (right after we set it up), the two dumps DIFF to show precisely what
  // deep sleep did to the SAR. Every field below is one we either set or depend on.
#if !ULP_VERBOSE
  (void)when; return;
#else
  uint32_t w2  = READ_PERI_REG(SENS_SAR_MEAS_WAIT2_REG);
  uint32_t st1 = READ_PERI_REG(SENS_SAR_MEAS_START1_REG);
  uint32_t rd  = READ_PERI_REG(SENS_SAR_READ_CTRL_REG);
  uint32_t pwc = READ_PERI_REG(RTC_CNTL_PWC_REG);
  uint32_t ana = READ_PERI_REG(RTC_CNTL_ANA_CONF_REG);
  uint32_t op0 = READ_PERI_REG(RTC_CNTL_OPTIONS0_REG);
  Serial.printf("ADCREG @%-4s xpd_sar=%u start_force=%u pad_force=%u dig_force=%u "
                "data_inv=%u rtc_pd_en=%u ckgen_i2c=%u bias_nosleep=%u bias_i2c=%u\n", when,
                (unsigned)((w2 >> SENS_FORCE_XPD_SAR_S) & SENS_FORCE_XPD_SAR_V),
                (unsigned)((st1 & SENS_MEAS1_START_FORCE_M) ? 1 : 0),
                (unsigned)((st1 & SENS_SAR1_EN_PAD_FORCE_M) ? 1 : 0),
                (unsigned)((rd  & SENS_SAR1_DIG_FORCE_M) ? 1 : 0),
                (unsigned)((rd  & SENS_SAR1_DATA_INV_M) ? 1 : 0),
                (unsigned)((pwc & RTC_CNTL_PD_EN) ? 1 : 0),
                (unsigned)((ana & RTC_CNTL_CKGEN_I2C_PU_M) ? 1 : 0),
                (unsigned)((op0 & RTC_CNTL_BIAS_FORCE_NOSLEEP_M) ? 1 : 0),
                (unsigned)((op0 & RTC_CNTL_BIAS_I2C_FORCE_PU_M) ? 1 : 0));
#endif
}

void vigilLampRelease() {
#ifdef VIGIL_LED_PIN
  // The lamp pin has two owners, exactly as ADC1 does. armUlpWatch() hands it to the RTC domain
  // so the coprocessor can drive it in deep sleep; the status blinks need it back on the digital
  // matrix for analogWrite. Without this the blue leg is dead to analogWrite after the first
  // sleep — and since magenta is red+blue, every fault colour would silently come out red.
  rtc_gpio_deinit((gpio_num_t)VIGIL_LED_PIN);
#endif
}

void ulpStop() {
  // THE COPROCESSOR AND THE CPU CANNOT BOTH OWN ADC1. On wake the ULP is still running from the
  // previous arm, and the first analogRead() of setup() takes the unit back from under it — its
  // next I_ADC then blocks forever on a SAR it no longer owns, which is exactly the hang seen on
  // every second cycle. Stopping the timer before the CPU touches the ADC removes the overlap.
  // The short wait covers a look already in flight when the timer is cleared.
  CLEAR_PERI_REG_MASK(RTC_CNTL_STATE0_REG, RTC_CNTL_ULP_CP_SLP_TIMER_EN_M);
  delay(20);
}

void ulpReport(const char *when) {
  // Read-only, and deliberately callable BEFORE anything touches the ADC. Called at the very
  // top of setup() it answers the one question the arm-time report cannot: what the coprocessor
  // did while the CPU was in deep sleep, uncontaminated by analogRead() taking ADC1 back.
#if !ULP_VERBOSE
  (void)when; return;
#endif
  Serial.printf("ULP @%s: ticks %u  breaching %u  last sample %u\n", when,
                (unsigned)(RTC_SLOW_MEM[ULP_MEM_TICKS] & 0xFFFF),
                (unsigned)(RTC_SLOW_MEM[ULP_MEM_LOOKS] & 0xFFFF),
                (unsigned)(RTC_SLOW_MEM[ULP_MEM_LAST]  & 0xFFFF));
}

void ulpSelfTest(int seconds) {
  if (seconds <= 0) return;
  // Watch the coprocessor from the CPU, awake, with no deep sleep in the way. Deliberately does
  // NOT call analogRead: that would take ADC1 straight back off the ULP and destroy the thing
  // being measured. The CPU's own reading is on the boot line above for comparison.
  Serial.printf("ULP self-test: %ds awake. Expect ticks to climb once per %ds.\n",
                seconds, WATCH_PATROL_S);
  for (int i = 1; i <= seconds; i++) {
    delay(1000);
    Serial.printf("  t+%2ds  ticks %-4u sample %-5u breaching %u\n", i,
                  (unsigned)(RTC_SLOW_MEM[ULP_MEM_TICKS] & 0xFFFF),
                  (unsigned)(RTC_SLOW_MEM[ULP_MEM_LAST]  & 0xFFFF),
                  (unsigned)(RTC_SLOW_MEM[ULP_MEM_LOOKS] & 0xFFFF));
  }
}

bool wokeByAlarm() {
  return esp_sleep_get_wakeup_cause() == ESP_SLEEP_WAKEUP_ULP;
}
