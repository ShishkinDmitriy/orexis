---
type: Domain Concept
title: Margin
term:
  - http://example.org/orexis/sensing#margin
  - http://example.org/orexis/sensing#wasBelow
  - http://example.org/orexis/sensing#wasAbove
description: >-
  How far past a bound a reading must go to leave the side the reading before it was judged on -
  one number on a range's condition, beside the bounds it widens, sized from the instrument's
  noise. Its memory is the side `received` carries onto each observation, so the rules concluding
  a side read the observation's own facts and remember nothing. A predicted reading is the model's
  number, with no instrument's noise, and carries no side.
---

# What it is

```turtle
:bed_operating ssn-system:inCondition [ ssn:forProperty climate:SoilMoisture ;
    schema:minValue 0.30 ; schema:maxValue 0.60 ; sensing:margin 0.0002 ] .

# the probe's next observation, after one the rules judged below the range
:obs_probe sensing:rawResult 0.3001 ; sensing:wasBelow :bed_operating .
```

A **margin** widens a bound for a reading coming from beyond it, and for no other. A reading whose
predecessor was judged below a range stays below until it reaches the floor and the margin; one
whose predecessor was judged above stays above until it falls to the ceiling less the margin; one
coming from inside crosses at the bound itself, so a real drop reads below at once and nothing is
noticed late. One number serves both ends of one range for one property. A condition stating none
has a margin of nought, and its sides are the bare comparison they always were.

It is hysteresis in value against the instrument's noise, which SSN-System's conditions have no
word for, so the word is sensing's: sensing speaks SOSA and SSN and declares what they lack. What a
side then means is the [region](/domain/sensing/region.md) page's to say.

# The side carried

`sensing:wasBelow` and `sensing:wasAbove` name the range the reading before this observation's was
judged below or above. That is the whole of the memory hysteresis needs, and it is a fact of the
observation, as `sensing:unchangedSince` carries the run of an unchanged number: the side rules read
it beside the reading and the bounds, and keep no state of their own. It is carried only for a range
stating a margin, since for no other could it change a side.

[Sensing](/domain/sensing/sensing.md)'s `received` writes it, from what the rules concluded of the
observation it replaces, before that observation goes. A silence between the two carries it still —
the observation before the silence stands until replaced — and so does a restart, the sides being
revisions the volume keeps. Where those revisions say nothing — a revision its budget cut short —
nothing is carried and the reading is judged alone, as a range with no margin judges every reading:
the store is never handed a side it holds no evidence for, and what the gap costs is one flip of the
kind the margin exists to stop. Several readings in one message are each judged against the side the
store last concluded, since no rule runs between them.

# A predicted reading reads none

The noise a margin holds a side against is the instrument's, and a predicted reading has none: it is
the model's number, and its doubt is the [corridor](/domain/prediction/corridor.md). So
[prediction](/domain/prediction/prediction.md) reads no margin and writes no side carried; a
predicted observation is judged by its number alone. Where a reading is held below inside the margin
and nothing moves the subject, the stretch ahead reads inside while the present reads below. The want
is minted by the present and kept by it, and nothing the stretch ahead says withdraws it; the
[planner](/domain/planning/planner.md), holding no act that reaches the want, plans a
[wait](/domain/planning/wait.md) toward that stretch, which lands and leaves the want standing.

Where no drift moves a key at all, prediction carries the observation in hand forward whole, and the
side it carries goes with it.

# How big

The instrument's whole spread: twice what a reading strays either way. A value resting exactly at
the floor is read anywhere within the noise on both sides of it, so a margin of the one-way figure is
cleared by one extreme draw of a value that never moved, and the side flips back; the whole spread
is cleared only once the value itself has left the floor's noise. The greenhouse's probe strays a
count of the four places it is published to and its thermometer a hundredth of a degree, so its soil
states 0.0002 and its air 0.02.

`orexis-onboard` refuses three margins (`onboarding/reading.py`, `unholdable`): a negative one, which
widens nothing, so the rules would read as nought a figure the world stated; one of half its range's
width or more, since every act here aims at the middle of the range and a dose landing there would
still be held below; and one on a range with no IRI, since the side carried names its range.
