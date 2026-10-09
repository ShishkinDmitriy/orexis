---
type: Domain Concept
title: Region
description: >-
  A range a subject needs a property to stay inside, in SSN-System's words - an operating range
  it does well in, a survival range it lives through - stated by the world and minted by nobody.
  Sensing's rules judge which side of each range the subject is on, given the instrument's noise;
  the prediction package calculates when a reading will cross a bound.
---

# What it is

```turtle
:fern ssn-system:hasOperatingRange [
    ssn-system:inCondition [ ssn:forProperty climate:SoilMoisture ;
                             schema:minValue 0.30 ; schema:maxValue 0.60 ] ] .
```

`ssn-system:hasOperatingRange` for where the subject does well, `ssn-system:hasSurvivalRange` for
where it merely lives, each with the property it is about and two bounds. A world states them on
the subject or on an instrument that watches it; nothing derives or picks one. A condition may
state a [margin](/domain/kernel/margin.md) beside its bounds, and a range that does is named, since
the side an observation carries names it.

# What a side is

Sensing's three rules conclude, of every observation of the property, `sensing:below`,
`sensing:inside` or `sensing:above` the range — a revision, one triple per observation and range.
A side is sensing's **judgment of the subject against its range, given the instrument's noise**,
not a bare comparison of one number: a reading coming from inside is below once it is under the
floor and above once it is over the ceiling, bounds inclusive, and a reading coming from beyond a
bound stays on that side until it has cleared the bound by the range's margin. Each rule reads the
observation's own facts — its reading, the bounds, the margin, and the side the reading before it
was judged on, carried onto it — and nothing else, so no rule remembers: where the range states no
margin, a side is exactly the comparison it always was.

# What reads it

- **A desire's met-test** reads the side: a plant wants its soil `inside` its operating range, and
  a dose's effect predicts it will be.
- **The prediction package** places every crossing where its accumulated rates reach a bound — or,
  leaving a side, the bound and its margin — so a stretch begins where the side changes.

Membership is crisp: a reading is inside or it is not, and how far it is from a bound is the
command's business when it sizes a dose, never the met-test's.
