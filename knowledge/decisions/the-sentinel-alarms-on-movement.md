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

# The clamp is in fractions and the comparison is in counts

The sentence above — "clamped to the physical 0..1 of a saturation fraction" — is true and was a
trap, because **a fraction is defined by the calibration and the ULP is not**. `1.0` means "as wet
as `ADC_WET`", not "as wet as it gets", and real water is wetter than a calibration point. So a
probe in a glass reads about 1100 counts where `ADC_WET` is 1300; the CPU clamps the fraction to
1.000 and hides it, while the coprocessor — comparing raw counts, knowing nothing of clamping —
sees a sample below its wet threshold and breaches on every look.

On the bench that was an alarm every ~23 seconds for as long as the probe stayed in the water:
re-arm, immediate breach, confirm, wake, publish, repeat. The series store shows it plainly —
four sends 23 seconds apart where the heartbeat had been landing every twenty minutes. The dry
end is the same defect mirrored, for a pot drier than `ADC_DRY`.

The fix is to open an edge that has reached a physical limit rather than pin it to the calibration
point: no 12-bit sample exceeds 4095 and none is below 0, so an open edge cannot fire. The window
in water becomes "alarm if it gets drier", which is exactly the remaining news.

Worth naming as a class, because this project will meet it again: **whenever a value crosses
between units, a clamp applied in one of them is invisible in the other.** The same seam is why
[#26](https://github.com/ShishkinDmitriy/orexis/issues/26) wants the interpretation moved to the
agent — a deviation expressed in raw counts needs no calibration to agree with anyone.

# Silence is information, and the series store cannot hold it

The design's own claim is that **silence means nothing crossed** — that is what makes a generous
heartbeat safe. A time-series store cannot represent that. Two points half an hour apart, 0.15 and
1.00, are interpolated by every consumer into a straight line, so a graph and every query over
that window report a gradual half-hour soak where there was a jump of twenty-five seconds. The
information the design earns is converted into a falsehood by the act of storing it.

The device knows which it was. At a fifteen-second patrol it took about a hundred and twenty looks
in that window, and every one before the breach was in-window. So **a crossing report carries the
last quiet sample and its age**, the agent places that point at the instant it was taken, and the
corner lands where it belongs: flat until T−25s, then near-vertical.

Three details make it cheap rather than clever. The ULP already runs an in-window path on every
quiet look — resetting the counter — so remembering the sample there is one store instruction. The
age is exact rather than estimated: a quiet look sets the patrol rate and the breach that follows
switches to the confirm rate, so the last quiet sample is one patrol plus (N−1) confirms before the
alarm. And `prev` mirrors the reading's own shape, so a sensor that reads `/moisture` finds its
prior at `/prev/moisture` — which is what keeps a shared topic working, three sensors each finding
their own.

**The prior is written to the series and NOT to the belief base**, and the asymmetry is the point.
What an agent believes is what it last heard; this is evidence about the SHAPE of a change it has
already been told about. Recording it as a current observation would let an older value overwrite
a newer one — the sensed store upserts one observation per subject-property — and would re-trigger
everything downstream of a reading for a value the agent has already superseded.

What this does NOT do is let the device assert the quiet interval itself. It repairs the edge of
each gap, not the gap. A board that could say "in-window from T₁ to T₂" would make silence a claim
rather than a hole, and that needs a vocabulary term and an agent that records a span rather than
a point.

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
