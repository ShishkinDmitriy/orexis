// The ULP watcher (#151) — the sentinel's variant: the band is COMPILED IN from the world's
// operating range (WAKE_BAND_LOW/HIGH in config.h), because a board that takes no orders can
// still keep a promise the world wrote. See ulp_watch.cpp for the machinery and the derivation
// of the one-second internal cadence.
#pragma once

void armUlpWatch();
bool wokeByCrossing();
