// The ULP watcher (#151) — the governed node's variant: the band arrives RETAINED beside the
// cadence and survives deep sleep in RTC memory, so a wake that hears no fresh command keeps
// watching what it was last told. See ulp_watch.cpp for the machinery and for how the watch
// period is derived from the worst credible slew.
#pragma once

#ifdef WAKE_ON_CROSSING
// The band, as fractions. Set by onCmd from {"watch":{"/value":[lo,hi]}}; negative means
// "never commanded", and the watch stays unarmed exactly as unflashed firmware would.
extern float rtc_wake_below;
extern float rtc_wake_above;

void armUlpWatch();      // load thresholds + program, start the once-a-second look
bool wokeByCrossing();   // did THIS wake happen because the value moved
#else
inline void armUlpWatch() {}
inline bool wokeByCrossing() { return false; }
#endif
