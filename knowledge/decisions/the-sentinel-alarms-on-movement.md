---
type: Decision
title: The sentinel alarms on movement, not on range
description: >-
  Watching the operating range as well as the deviation made the sentinel's ULP alarm
  continuously whenever a pot sat outside its range — a slow fact the heartbeat already
  reports — and the intersection went empty exactly when the plant was thirsty, waking the
  radio every patrol forever. The band is dropped from what the coprocessor watches and kept
  as what SIZES the trigger. Supersedes in part the band half of the-alarm-answers-to-the-last-report.
status: accepted
timestamp: 2026-08-23T22:05:00Z
---

# The sentinel alarms on movement, not on range

[the-alarm-answers-to-the-last-report](/decisions/the-alarm-answers-to-the-last-report.md) gave
the alarm two halves and a clean division of labour: the deviation limit catches the
between-reports event, and **the band catches what creeps** — HI/LO fixed in world terms, never
re-anchoring, so a month-long dry-down still alarms at the edge however gently it got there. The
ULP watched the intersection of the two, which makes "outside the band OR moved more than delta"
one comparison and costs the coprocessor nothing.

The reasoning was sound and the third bullet was wrong, on the bench, for the sentinel.

# What the band half actually did

A sentinel takes no orders, so its band is compiled in at flash time from the world's operating
range. Point one at a pot whose value sits **outside** that range — a thirsty plant, which is the
case the whole society exists to notice — and every look breaches. The board wakes, publishes,
re-arms, breaches again a patrol later, forever. The intersection with the deviation window then
goes literally empty: the ceiling lands below the floor, no sample can satisfy both, and the arm
line prints a window backwards.

So the band half alarmed hardest precisely when it had least to say. That a pot is outside its
range is **slow** news, already carried by every heartbeat, and the agent — which holds the range
— is far better placed to judge it than a board that cannot be told anything.

# The decision

**The ULP watches the last published value plus or minus `WAKE_DELTA`, clamped to the physical
0..1 of a saturation fraction, and the operating range does not appear in the comparison at all.**

The division of labour that replaces it is one line: **the heartbeat says where the value is; the
ULP says that it moved.** Slow drift is never invisible — each scheduled report carries the
drifted value — and a between-reports jolt still wakes the radio within a patrol and a confirm.

**The band is not gone; it moved up a level.** `WAKE_DELTA` is `sensing:alarmDeltaFraction` of the
band's *width*, resolved to a number by `render_sentinel` at generation time, so a fussy plant
still gets a tight trigger and a tolerant one a loose trigger. The range still decides *how much
change matters*. It no longer decides *where the value must sit*.

# What this costs, stated plainly

A sentinel no longer enforces anything the world wrote. Its README's claim — "a board that takes
no orders can still keep a promise the world wrote" — was the sharpest thing about the design and
it is now false. What is left is a board that reports movement fast and leaves every judgment to
the agent, which is a smaller promise honestly kept rather than a larger one kept only while the
plant is comfortable.

Two things fall out that are worth having. The empty-window pathology is structurally impossible:
one window, always well-formed. And the alarm no longer needs the calibration to agree with
anyone — a deviation in raw counts means the same thing whatever `ADC_DRY`/`ADC_WET` say — which
sits well with moving the interpretation to the agent
([#26](https://github.com/ShishkinDmitriy/orexis/issues/26)).

# Two rates, because patrolling and confirming are different jobs

Not part of the same decision, but landed with it and cheap to state. The ULP now chooses its own
next interval from the path it takes through its own program: an in-window look asks for the slow
patrol, a breaching look asks for the fast confirm. Nothing rides on the patrol interval except
how soon a crossing is *noticed*; the confirm interval is the whole cost of not trusting one ADC
sample. The ESP32 ULP has five sleep-period registers and `I_SLEEP_CYCLE_SEL` picks between them,
so this costs one instruction per path.

The honest consequence: at a 60-second patrol the value can travel far more than a band width
between looks, so the promise weakens from "we will see it within a second" to "we will see where
it ENDED UP within a minute". Good for watching a pot drift, wrong for catching the act of
watering.

# Seams left open

- **`render_sentinel` still generates `WAKE_BAND_LOW`/`HIGH`** and the firmware no longer reads
  them. It still needs the operating range to size the delta, so the query stays; the two
  `#define`s should go.
- **Only the sentinel changed.** The governed node still watches band ∩ delta, because it is
  *told* its band by an agent that can retract it — so the pathology above cannot arise there in
  the same way. Whether the two firmwares should agree is a real question this record does not
  answer.
- **Nothing re-picks `WAKE_DELTA` for a sentinel.** `sensing:alarmDeltaFraction` is a revisable
  belief, and a board that takes no orders freezes whatever the society believed at flash time.
