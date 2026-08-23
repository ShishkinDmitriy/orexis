// The ULP watcher (#151) — the sentinel's variant, now a pure DEVIATION alarm: the ULP watches
// the last published value plus/minus WAKE_DELTA and wakes the radio when the reading leaves
// it. The operating range is not watched; it only sized WAKE_DELTA, upstream at generation.
// See ulp_watch.cpp for that argument and for the two-rate patrol/confirm machinery.
#pragma once

// The reference for the deviation window: what was last published if anything has been, and
// this reading otherwise. See ulp_watch.cpp for why the operating range is not consulted.
void armUlpWatch(float nowFrac);
// Stay awake and report what the coprocessor is doing, second by second. Diagnostic only.
void ulpSelfTest(int seconds);

// Print the ULP's counters without touching them or the ADC. Safe at the top of setup().
// Hand the vigil lamp's pin back to the digital matrix so analogWrite can drive it. The next
// armUlpWatch() reclaims it for the coprocessor.
void vigilLampRelease();

// Stop the ULP timer. MUST be called before the CPU uses ADC1, or the two fight over the unit.
void ulpStop();

void ulpReport(const char *when);

// Dump the ADC/RTC registers the ULP depends on. Diff boot against arm to see what sleep did.
void ulpDumpAdcRegs(const char *when);

// The last sample taken while the value was still inside the window, and how long before the
// wake it was taken. False when the window broke on its first look and there is no such sample.
bool priorQuietSample(float *frac, uint32_t *ageAtWakeS);

bool wokeByAlarm();
void noteReported(float frac);   // the deviation limit drifts from what was last heard
