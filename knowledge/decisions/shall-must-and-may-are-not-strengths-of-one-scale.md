---
type: Decision
title: SHALL, MUST and MAY are not strengths of one scale
description: >-
  The sovereign's taxonomy of the mind's attitudes — SHALL, SHALL NOT, MUST, MUST NOT, MAY,
  explicitly not the RFC synonyms — mapped term by term against what exists. SHALL is the
  desire, already built; deontic MUST is the obligation, breakable by definition; the
  unbreakable MUST and MUST NOT are not stronger duties but a different logic, alethic,
  living in the ratified shapes and the planner's refusal; the envelope prices SHALL rather
  than enforcing MUST NOT; and MAY is not a modality at all but the plan library, the
  amortisation tower's missing middle. What is refused is a force term ranking wants on one
  deontic scale — the sources differ in logic, urgency stays the unranked common currency,
  and the character seam stays open. Two gaps survive, each with an issue — a want met by
  absence (#468), and remembered plans (#469).
  A follow-up sitting added the provenance axis — the moods compose with WHOSE, and internal
  barely exists here — and refused mood classes and mood stores both, because modality decides
  the store, provenance the graph, and severity the force. The second cut ruled mood and
  provenance orthogonal — a Desire is my MUST, an Obligation someone's — gave each mood its
  behaviour in the search, and sent the subclass itself away as a flag (#471). The last
  ruling brought the scope axis IN — severity narrows to two, a want states its scope in
  PDDL's words, and orexis:ShouldBecome, older than the reified desire and made redundant by
  it, retires (#472).
status: accepted
timestamp: 2026-08-31T17:36:56Z
---

# SHALL, MUST and MAY are not strengths of one scale

The sovereign's taxonomy, in its own words (2026-08-30,
[#467](https://github.com/ShishkinDmitriy/orexis/issues/467)), and explicitly NOT the RFC 2119
synonyms: **SHALL** — what we want to do, closest to the existing desire; **SHALL NOT** — states
to avoid if we have alternatives; **MUST / MUST NOT** — the same, but mandatory; **MAY** —
already-prepared plans, maybe used before, as a reference — you may use one, or find better.

Five words that LOOK like one scale of force with a permission at the bottom. The standing
principle refuses the look — **desire is bouletic, obligation deontic, affordance alethic,
freshness epistemic: different logics rather than strengths of one** — and holding each word to
it, most of the taxonomy turns out to exist under the house's names:

| the sovereign's word | what it is here | its logic | state |
|---|---|---|---|
| SHALL | a [desire](/domain/desire.md) — the [region](/domain/region.md), the [aim](/domain/aim.md) picked inside it, a met-shape and a declared measure | bouletic | built |
| SHALL NOT | per property, the region's own side shapes; in general, a want met by ABSENCE | bouletic | half-built — [#468](https://github.com/ShishkinDmitriy/orexis/issues/468) |
| MUST | an [obligation](/domain/obligation.md) — a desire someone else sourced, with a deadline | deontic | built |
| MUST, unbreakable | not a stronger duty — the ratified shapes, the gates, the planner's refusal | alethic | built |
| MUST NOT | the same split — the alethic half built (shapes, mandate), the deontic half without a customer | alethic / deontic | built / waiting |
| MAY | not a modality — the plan library | none; a cost model | [#469](https://github.com/ShishkinDmitriy/orexis/issues/469) |

This table maps the moods onto the class names that existed when it was drawn, and the same
sitting then cut deeper: the names dissolve into cells of mood × provenance, and the subclass
between them goes — the second cut, below.

## Why the principle decides it, in the machinery's own terms

Watch what *violated* means in each row, because that is where the logics refuse to be one
scale. An unmet SHALL is a [gap](/domain/gap.md) — a distance and an urgency, legitimate while
a plan runs. A broken deontic MUST is a breach — a counterparty defaulted on, kept on the books
because a debt paid and a debt forgotten must not look alike. A broken alethic MUST is nothing
at all — not a bad world but an illegitimate one, refused by the gates at ratification and by
the planner at commitment: `REFUSED` in `packages/orexis-agent-deliberation/planner.py` is a
plan with no steps, and legality is asked once, of the world the winning plan would actually
reach ([a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md)).
Three *violateds* that share no arithmetic and no consumer are not three strengths of one
thing.

The alternative weighed and refused: a **force term on the want** — the RFC scale imported as
data, ranking SHALL below MUST. Three reasons, each already paid for elsewhere:

- **Urgency is the common currency, and the deliberately unranked meeting point.** A stake and
  an obligation compare by heat, never by kind, and
  [an-obligation-is-a-desire-someone-else-sourced](/decisions/an-obligation-is-a-desire-someone-else-sourced.md)
  records the failure a rank would reintroduce: an obligation pinned above every stake is the
  honoured mode returning, outranking a plant that is dying.
- **Where force is real, severity already carries it** — a violation refuses, a warning notes,
  a gap motivates ([a-desire-is-a-shape](/decisions/a-desire-is-a-shape.md)). A second force
  vocabulary beside severity would be two owners of one claim.
- **The override order is the character seam, and this must not close it by accident.** BOID's
  answer — how far obligation outranks desire IS the agent's character, sovereign-bounded,
  agent-picked — stays where the obligation record left it, open.

## SHALL — built, and the envelope is its scale, not a MUST NOT

The want, its region, its aim and its measure are the pages linked in the table;
[a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md) has the
current mechanics. One sharpening the taxonomy forces: the natural reading "MUST NOT partially
exists per property, as the envelope beside the region" is half right, and the wrong half
matters. The envelope is deliberately NOT a refusal — it reports `sh:Warning` at the gates,
because a plant past tolerating is a fact about the world rather than an illegitimate world,
and an agent past its envelope must be allowed to start precisely so it can act. What the
envelope actually does is PRICE the shall: [urgency](/domain/urgency.md) is distance from the
aim scaled by the survival room on that side, so the envelope is the denominator of every want
about the property. It serves SHALL's arithmetic, not MUST NOT's enforcement.

## SHALL NOT — one gap, and it covers the deontic MUST NOT too

Per property, the two directions of leaving the region are already avoidances with a named
side (`orexis:violationIs`, [region](/domain/region.md)). And "if we have alternatives" is
satisficing, which the search already is: a move is taken only when the world it reaches beats
standing still, and NOT_BETTER is an answer, not a failure. What has no expressible form is a
GENERAL avoidance — a state to steer away from that is not a band in one observed property.
The met-shape machinery would carry it, since SHACL states absence natively and the side
shapes are that very form; what is missing is a **source** (deduced or ratified, never
authored — and an avoidance has no ranges to intersect) and a **measure** (conformance is
boolean, a want has distance). That is
[#468](https://github.com/ShishkinDmitriy/orexis/issues/468).

The same issue is the deontic MUST NOT's seat when a customer arrives: a breakable prohibition
owed to a peer is a want met by absence whose source is a claim rather than the world — and
differing only in provenance is already exactly how desire and obligation differ. One gap, not
two.

The alethic MUST NOT needs nothing: shapes refuse a world at the gates, the mandate refuses a
revision (`validate_agent`, the same call the agent makes at boot —
[self-review-is-a-capability](/decisions/self-review-is-a-capability.md)), and the planner
refuses commitment to a world the society would not accept.

## MAY — not a modality, and folding it in is the conflation the principle names

The sovereign's own words describe a cache with the freedom not to use it, and
freedom-not-to-use is what separates it from every row above: nothing is wanted, owed or
forbidden about a remembered plan. Folding "cheaper to reuse than to search" into a deontic
scale would be pricing a caching concern in obligation's currency — the strengths-of-one-logic
conflation, verbatim.

Where it lives is the amortisation tower. An
[intention is an amortised deliberation](/decisions/an-intention-is-an-amortised-deliberation.md)
— one decision spanning events; a
[habit is a compiled one](/decisions/a-habit-is-a-compiled-deliberation.md) — the decision
gone from the loop, answering before the search. MAY is the missing middle: weaker than a
habit, because it is a suggestion the search tries first and may reject — *you may use one, or
find better* is the contract, literally — and stronger than re-deriving from nothing. The
storage tension resolves the way habits resolved it: what is stored is a suggestion whose
every use re-verifies against current premises, so it cannot outlive them in effect, and the
[imaginarium](/domain/imaginarium.md) stays required to be lost, because what is kept is steps
to re-try, never a possible world. The price signal that makes reuse rational is
[#466](https://github.com/ShishkinDmitriy/orexis/issues/466)'s: without costs, search is free
in the ranking and a library buys nothing. That is
[#469](https://github.com/ShishkinDmitriy/orexis/issues/469).

One line for the reading the sovereign explicitly set aside: RFC 2119's MAY — a permission —
also has an owner here, the mandate and its latitude, and nothing in this record licenses
importing the RFC meanings into these five words.

## One axis, not two taxonomies — the moods compose with provenance

Asked by the sovereign on reading the mapping: *we also have internal and external
(someone's) distinctions.* The axis exists, it is PROVENANCE, and it is orthogonal to the
moods: force says how a crossed line binds, the source says whose line it is, and the two
compose rather than multiplying into new words. The first draft of this section offered the
ontology as proof — `orexis:Obligation rdfs:subClassOf orexis:Desire`, its comment reading
*what differs is only where it came from, which is what prov says* — and the sovereign turned
the evidence against the witness: if provenance is the ONLY difference and prov already says
it, the subclass is a FLAG — the kind-is-read-never-flagged rule, applied one level up, to a
class. The axiom goes: [#471](https://github.com/ShishkinDmitriy/orexis/issues/471).

| source | its SHALL | its SHALL NOT | crossed means |
|---|---|---|---|
| the subject — whom I act for | the stake, a region from its stated ranges | the region's own side shapes | a gap — bouletic |
| a peer — a counterparty | an obligation | the deontic prohibition, [#468](https://github.com/ShishkinDmitriy/orexis/issues/468)'s future seat | a breach — deontic |
| the sovereign, ratifying a want | a world-stated root | a ratified avoidance, #468's door | a gap — bouletic |
| the sovereign, as law | — | the shapes and the mandate | illegitimate — alethic |
| the agent itself | only the aim — a pick inside room, never a want | nothing, by design | — |

The last row is the axis's sharpest fact: **internal barely exists here, on purpose.** An
agent authors no wants — the self-satisfaction loophole is shut in both directions — it only
picks inside room others gave. So the working test is not internal against external but the
one [the-mind-is-six-graphs](/decisions/the-mind-is-six-graphs.md) already stated: **is there
someone to be wronged?** Yes — deontic, a breach with a counterparty and a deadline. No, but
ratified as law — alethic, refused. No, and merely stated as a need — bouletic, a gap,
priced.

## The second cut: a want is a cell, and the class names dissolve into it

Ruled in the sitting's second pass: axis one is the MOOD — SHALL, SHALL NOT, MUST, MUST NOT —
and axis two is PROVENANCE, and the existing class names are cells rather than moods: **a
Desire is my MUST, and an Obligation is someone's MUST.** The first table mapped the moods
onto class names because those were the surfaces that existed; this cut is deeper and
simpler, and it is the one the implementation follows.

And the house had already split along the mood line without naming it: **met is the label,
urgency is the motive**
([a-desire-states-its-own-measure](/decisions/a-desire-states-its-own-measure.md)). One want
carries BOTH a MUST — its met-shape, the boolean the plan is for — and a SHALL — its declared
measure, the gradient that prefers one world over another inside *not met yet*. The region is
the MUST half and the aim's gradient the SHALL half of the same node. The sovereign's four
moods are that met/measure split crossed with polarity: a negative want carries a forbidding
shape (its MUST NOT) and a penalty gradient (its SHALL NOT). Nothing has to be invented for
SHALL — it is the measure, already built, and *prefer a SHALL state over neutral over a SHALL
NOT state* is what one continuous score does, generalised from a three-way ordering to a
gradient.

## What each mood does to the search

The sovereign's rulings, term by term — with the lookup named, per the plan record's own
discipline, so the next widening is a lookup rather than a re-derivation: this is PDDL3
re-derived from inside — hard at-end goals, hard trajectory constraints, soft preferences
with violation costs.

| mood | in the search | carrier |
|---|---|---|
| MUST | **the goal** — what the plan is FOR; the sovereign's *just the final state* is PDDL3's at-end. Deontic, so best-effort stays representable: a plan that only nears it reports IMPROVED, and the gap or breach stays visible, never silent | the met-shape |
| MUST NOT | **a constraint on EVERY state** — a valid plan contains no state matching one, so a child world failing a violation-severity shape is discarded at expansion: never extended, never a candidate. The next-best LEGAL plan then wins by construction | violation-severity shapes — #468 |
| SHALL | **a graded preference** — prefer the world that scores better; no new mechanism | the declared measure |
| SHALL NOT | **a penalty plus bounded extra effort** — the search may end in one, but spends budget looking for better first: *avoid if we have alternatives* means alternatives are SEARCHED FOR, not merely compared among candidates already found; the budget is #466's to price | a measure penalty — #468, #466 |

Two consequences worth stating before anyone builds. **The ranking must widen from the
pursued want to the world**: today a candidate is scored by one want's urgency alone, and a
SHALL NOT that is not the pursued want can bite only if the score aggregates the avoidance
wants a candidate world violates — one more reason the measure, not a new class, is SHALL
NOT's carrier. **And moving MUST NOT to expansion is a cost decision as much as a semantic
one**: only violation-severity shapes run per node, the full rulebook stays at the gates, and
the per-node price is measured on the Pi before it ships — both halves carried on #468's
definition of done.

**The sovereign's own image for it: a magnet.** A SHALL state attracts, a SHALL NOT repels —
one field, opposite polarity — and the literature name is potential-field planning (Khatib's
artificial potential fields): the measure IS a scalar field over worlds, zero at the aim, 1.0
at the envelope, and a penalty is a repulsive bump on it. Two sharpenings keep the image
honest. **MUST NOT is a wall, not a strong magnet** — a repulsor, however strong, can be
crossed when the attraction behind it pays enough, which is exactly what the every-state
ruling refuses, so the hard moods live in the TOPOLOGY (the goal test, the pruning) and never
in the field; polarity is for the soft moods only. And **fields fail by local minima** — a
hollow where attraction and repulsion balance and a gradient-follower stalls short of the
goal. This house already answers that: the search does not follow the gradient, it simulates
and ranks whole worlds — which is how the absorbed reflex's own defect was cured, a greedy
direction-follower being a field-follower and watering a drowning plant. The field ranks; the
search sees.

## Scope is the third axis, and it is adopted lazily

Asked by the sovereign on meeting PDDL3's trajectory constraints: are they better than the
moods? Not better — ORTHOGONAL, and the decomposition is exact. PDDL3's own structure is
operator × force: any scope operator (`at-end`, `always`, `always ¬`, `sometime`,
`at-most-once`, `sometime-before`, `within`) may be hard or a preference. So a fully
decomposed want is **force × provenance × scope**, polarity folding into the formula — and
the four moods are force × polarity with the scope DEFAULTED: MUST is hard `at-end`, MUST NOT
is hard `always ¬`, the SHALLs the same two soft. Scope cannot replace mood, because scope
says nothing deontic: `always ¬` does not say who is wronged when it fails.

The other operators wait for customers, and the audit says most never get one here.
Maintenance (`always φ`) is delivered by the LOOP, not the plan: re-deliberation converts it
into repeated achievement, and a-sensing-action-ends-a-plan keeps plans too short for
within-plan scope to say much. Ordering (`sometime-before`) EMERGES from simulation — the
premise-that-cannot-bind mechanism produced acquire-then-apply from two rules that never
mention each other, where PDDL3 needs the operator because its goals are weaker than
effects-plus-search. And the two per-state operators are exactly the two already ruled; the
rest (`sometime`, `at-most-once`, `sometime-before`) need memory along the path — PDDL3
compiles them to automata tracked during search — which is machinery with no customer. A term
nobody reads is annotation: an operator is adopted when a want needs it.

## The shipped mind, in coordinates

Asked by the sovereign: how would our desires look on the three axes? Projected rather than
sketched — every row below is a want a shipped world holds today — and the punchline is that
NOTHING NEW IS STORED: force is which carrier a want already has (met-shape hard, measure
soft, severity for law), provenance is the premise PROV already names, and scope is defaulted
by kind. The axes are how to READ the mind, not a migration.

| want | force | provenance | scope |
|---|---|---|---|
| a property inside its region | MUST — the met-shape; SHALL — the measure toward the aim | region: the subject's ranges; aim: THE AGENT | `always`, delivered by the loop — `at-end` per pass |
| the envelope beside it | neither — the SHALL's denominator, and a warning to the operator | the subject | — |
| freshness, per instrument | MUST — the met-shape; measure boolean today | the wiring, ratified | `always` via the loop; the horizon re-arms it |
| an obligation | MUST — the discharged-pattern | a peer's claim | `at-end`; `within(t)` is the seam above |
| the conduct picks — cadence, patience, offer, reserve | soft, inside room | the agent, inside sovereign mandates | — |
| the mandate | MUST NOT, hard | the sovereign, as law | `always` — each revision, each boot |
| the constitution's shapes | MUST NOT, hard | the sovereign, as law | `always` — now every planned state |
| an avoidance ([#468](https://github.com/ShishkinDmitriy/orexis/issues/468)) | SHALL NOT — a penalty | sovereign ratifying, or a peer | `always` |
| a remembered plan ([#469](https://github.com/ShishkinDmitriy/orexis/issues/469)) | none — MAY | the agent's own past, or a model | — |

Two findings fall out of doing the projection, and neither was designed:

- **The agent's own column is soft-only.** Everywhere the agent appears as a source — the aim,
  every conduct pick — the force is soft; hard comes exclusively from outside, the subject's
  ranges, a peer's claim, the sovereign's law. The agent may prefer and may never bind, which
  is [control-the-derivative](/decisions/control-the-derivative-not-the-value.md) restated as
  an invariant of the axes, and it holds in every shipped world.
- **The scope column is nearly constant — `always`, delivered by the loop** — which is why
  scope never needed vocabulary here: re-deliberation each tick IS the always-operator,
  implemented as repeated at-end. The one cell that will ever need a written operator is the
  debt's `within(t)`, already a seam.

## One owner per axis, and the mood is computed like a band

Asked by the sovereign, third and most concretely: do the axes need terms — a `pddl3:Always`,
a `pddl3:AtEnd`, a `modality:Shall`, a `modality:MustNot`? No, and the reason has a sharper
form than the no-new-classes section above: **each axis gets exactly ONE owner, and two of
the three already have theirs.** Force is owned by SEVERITY — `sh:Violation`, `sh:Warning`,
`orexis:ShouldBecome` — and the custom severity is the precedent that shows the mechanism:
when force needed a new value, the house extended the severity vocabulary, not a class
hierarchy, and a future hard avoidance is one more severity IRI, never a class. One
correction the sovereign's reading surfaced, worth pinning: the trio marks WHO REACTS, not
the moods one-to-one. `sh:Violation` is refused — MUST NOT. `sh:Warning` is the OPERATOR'S
row, not SHALL NOT: the envelope lives there, legitimate, worth a person's notice, pursued by
nobody. `orexis:ShouldBecome` is the agent's row and carries BOTH SHALLs, polarity in the
shape's content — the region's own side shapes are per-property SHALL NOTs minted at that
severity. And the custom IRI earns its place three ways, all lived: an unmet want must never
stop a boot, so `conforms()` filters by it; the human report must hide the forty at-birth
gaps while showing a crossed envelope, which one IRI for both cannot do; and *should hold* is
a claim about now where *should become* is pursued TOWARD, tolerating being unmet while the
plan runs — the reason intentions exist. A
`modality:MustNot` beside `sh:Violation` would be two owners of one claim — the thing the
domain gate refuses in prose, arriving in the T-Box. Provenance is owned by PROV and the
premises, and a class flagging it is the mistake
[#471](https://github.com/ShishkinDmitriy/orexis/issues/471) is deleting, rotated ninety
degrees. Scope has no owner because it has ONE value — `always`, via the loop — and a
vocabulary whose every instance says the same thing is a term nobody reads.

**The mood of a want is therefore COMPUTED, never asserted — like a band.** A want with a
`orexis:metWhen` has a MUST half; a kind with a declared measure has a SHALL half; a shape at
violation severity is law. A dashboard or the ask channel that wants to print "MUST,
someone's, always" derives the label from the carriers on demand, and it can never disagree
with the data beside it because it IS the data beside it. Even polarity needs no term: an
avoidance's measure is high when the pattern is present and zero when it is absent — the
gradient's own arithmetic is the polarity.

**And no `pddl3:` namespace, ever** — naming PDDL is not proposing to parse it, and the
carriers stay SHACL, SPARQL and PROV. The nicest case is `within(t)`, which may need ZERO
vocabulary when its day comes: `orexis:expiresAt` is already on the obligation, and the change
is the planner reading it as plan-validity — the simulated clock checked against it — rather
than only as heat. A semantics change, not a term. The ontology's trajectory out of this
sitting is net NEGATIVE: #471 removes a class, and the three axes add none.



## No new classes, and no new stores — asked and refused

The sovereign asked both directly, and both dissolve against rules already paid for.

**Concepts: the two that exist are enough.** `orexis:Desire`, with `orexis:Obligation` its
subclass, and the KIND of a want read off the premises it has and the others do not — a stake
carries a reading, an obligation a claim and a counterparty, an epistemic want its instrument
— because a flag that can disagree with the data beside it is a flag that eventually does
([desire](/domain/desire.md)). A mood class beside them — a Shall, an Avoidance, a
Prohibition — would be exactly such a flag, and one nothing reads: the met-shape gives the
state, the declared measure gives the urgency, the search minimises it, and an avoidance
differs only in what its shape and measure SAY. A term nobody reads is annotation. What #468
and [#469](https://github.com/ShishkinDmitriy/orexis/issues/469) genuinely need they mint in
their owner's namespace in the change that builds it, promoted to `orexis:` only when several
packages must speak it — the standing promotion test.

**Stores: neither four nor one — the question dissolves, because a store is a modality and
the four moods are not four modalities**
([a-store-is-a-modality](/decisions/a-store-is-a-modality.md)). SHALL, SHALL NOT and the
deontic MUST are all *would like*: ONE desires store, already built to take contributions
from every loaded package's `desires.ru` and from the records — the obligations among them —
rebuilt from premises and read-only to the runtime, so a new source of want is a new
contributor to the build and no reader learns the count. The alethic MUST NOT is not a mental
state at all: it lives where law lives, the ratified world and its shapes, public. MAY's
plans, when #469 builds them, are the agent's own past — recorded, beside the ledger, not a
want. Splitting the desires store by force would put severity where provenance belongs;
merging the modalities into one store would repay the split for nothing.

**And packages already contribute per mood, through doors that exist**: `desires.ru` for
wants — bouletic or deontic, the premise decides; `shapes.ttl` for law — every package's
shapes already gate validation; #469 adds the library door. A package that speaks a new mood
edits nothing outside its directory, which is rule 2's mechanic doing what it always does.

## The axis is ruled in: a want states its scope, and ShouldBecome retires

The sovereign put the scope axis a second time — *we lack these PDDL scopes; keep only
`sh:Violation` and `sh:Warning`, and add a scope axis for desire, in PDDL terms* — and the
probe that came with it (*is ShouldBecome at-end?*) found the ground under the lazy-adoption
position dissolved. `orexis:ShouldBecome` PREDATES the reification: it was minted when a
desire WAS a bare `sh:NodeShape` and needed marking apart from law, and a want being a node
(`orexis:Desire`, `orexis:metWhen`) made the mark redundant without anyone noticing. Its
severity said who reacts, which the node's type now says; its time-meaning was implicit,
which an explicit scope says better. So ruled, and filed as
[#472](https://github.com/ShishkinDmitriy/orexis/issues/472):

- **severity keeps TWO values** — `sh:Violation`, law, refused; `sh:Warning`, the operator's
  notice — both claims about *now*, on shapes;
- **a desire carries `orexis:scope`** — `orexis:Always`, `orexis:AtEnd`, `orexis:Within` —
  PDDL's WORDS in the kernel's namespace, because every derivation writes one and the
  planner reads it, which is the promotion test met; never a `pddl3:` import;
- **the shipped assignments close a seam on arrival**: region → `Always`, freshness →
  `Always`, obligation → `Within` reading `orexis:expiresAt` — the deadline stops being only
  heat, and the within seam below is struck through rather than waited on;
- **the planner branches on scope**: `Always` judged at every state of a candidate plan,
  `AtEnd` at the end-world, `Within` as validity against the simulated clock;
- **the severity's three lived jobs re-plumb onto the `metWhen` linkage** — boot survives
  unmet wants, the report hides at-birth gaps and shows crossed envelopes — carried on #472.

What survives of the overridden position, so nobody over-reads the reversal: members still
arrive by customer (`Sometime`, `at-most-once`, `sometime-before` stay unminted); the MOOD is
still computed and never asserted; and the one-value claim for scope is corrected rather than
mourned — the values were three all along, once the obligation's deadline is read as scope
rather than heat.

# Seams left open

- **The override order (character)** stays the obligation record's seam. This record adds one
  constraint for whoever closes it: character ranks SOURCES of desire, and must never re-type
  wants onto a single force scale.
- **A deontic MUST NOT has no customer.** Nothing shipped is a prohibition anyone could
  breach; the day one arrives, it is #468's machinery with a peer's provenance, and this line
  is where that argument starts.
- ~~**A deadline is heat today, not plan validity.**~~ CLOSED by the scope ruling, faster
  than the seam expected: the obligation's scope is `orexis:Within`, reading
  `orexis:expiresAt`, and the validity check on the simulated plan's clock rides with
  [#472](https://github.com/ShishkinDmitriy/orexis/issues/472) — the
  [#250](https://github.com/ShishkinDmitriy/orexis/issues/250) neighbourhood (patience
  against landing time) is where its test case lives.
- **The nouns are deliberately unminted.** "Avoidance" and "plan library" appear here as
  descriptions, not terms — a word enters the dictionary in the same change that builds its
  thing, and both issues carry that requirement.

- ~~**Restriction is at commitment, not during search.**~~ Ruled and CLOSED in the same
  sitting, more strongly than the seam proposed: MUST NOT constrains every state, checked at
  expansion, so the next legal candidate wins by construction and
  [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md)'s
  no-fallback seam RETIRES rather than being implemented. Mechanics and the per-node cost
  measurement are carried on #468's definition of done — struck through rather than removed,
  because the ruling only makes sense against what it overruled.

# Issues this emits

[#468](https://github.com/ShishkinDmitriy/orexis/issues/468) — a want met by absence: the
general avoidance, and the deontic prohibition's future seat.
[#469](https://github.com/ShishkinDmitriy/orexis/issues/469) — remembered plans: the library,
tried before searching, re-verified on every use.
[#471](https://github.com/ShishkinDmitriy/orexis/issues/471) — retire the Obligation
subclass: one class of want, whose it is read from provenance.
[#472](https://github.com/ShishkinDmitriy/orexis/issues/472) — a want states its scope in
PDDL's words, and `orexis:ShouldBecome` retires.
It engages [#466](https://github.com/ShishkinDmitriy/orexis/issues/466) rather than emitting
it: costs are what make MAY's economics real.
