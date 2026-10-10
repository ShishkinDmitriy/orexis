---
type: Domain Concept
title: Region
description: >-
  A range a subject needs a property to stay inside, in SSN-System's words - an operating range
  it does well in, a survival range it lives through - stated by the world and minted by nobody.
  Sensing's rules say which side of each range a reading is on, a domain's transition judges a
  subject belief against the operating one, and the prediction package calculates when a reading
  will cross a bound.
---

# What it is

```turtle
:fern ssn-system:hasOperatingRange [
    ssn-system:inCondition [ ssn:forProperty climate:SoilMoisture ;
                             schema:minValue 0.30 ; schema:maxValue 0.60 ] ] .
```

`ssn-system:hasOperatingRange` for where the subject does well, `ssn-system:hasSurvivalRange` for
where it merely lives, each with the property it is about and two bounds. A world states them on
the subject or on an instrument that watches it; nothing derives or picks one.

# What reads it

- **Sensing's three rules** conclude, of every observation of the property, `sensing:below`,
  `sensing:inside` or `sensing:above` the range, bounds inclusive — a revision, one triple per
  observation and range. A side is the bare comparison of one reading with the bounds, and
  remembers nothing.
- **A domain's transition** — climate's, for the soil and the air — judges the subject's state against
  its OPERATING range alone, beside the [subject belief](/domain/belief/transition.md) it replaces:
  the bound crossed at itself from another state, and a held state left only past the
  [margin](/domain/sensing/margin.md) the range's condition states. None judges a survival range.
- **A desire's met-test** reads the state that transition makes, never a side: a grower wants no
  bed it acts for believed dry, and a dose's effect predicts it will be moist (#944). Sensing's sides
  are read by nothing of the mind, and stand until they retire.
- **The prediction package** places every crossing of a bound where its accumulated rates reach it,
  so a stretch begins where the side changes.

Membership is crisp: a reading is inside or it is not, and how far it is from a bound is the
command's business when it sizes a dose, never the met-test's.
