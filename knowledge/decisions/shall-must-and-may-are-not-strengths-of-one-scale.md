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
  the store, provenance the graph, and severity the force.
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
compose rather than multiplying into new words. The proof is already structural — MUST is
SHALL from outside, and the ontology says so: `orexis:Obligation` is a subclass of
`orexis:Desire`, in its own comment's words *because everything that reads desire should read
this too; what differs is only where it came from, which is what prov says.*

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

# Seams left open

- **The override order (character)** stays the obligation record's seam. This record adds one
  constraint for whoever closes it: character ranks SOURCES of desire, and must never re-type
  wants onto a single force scale.
- **A deontic MUST NOT has no customer.** Nothing shipped is a prohibition anyone could
  breach; the day one arrives, it is #468's machinery with a peer's provenance, and this line
  is where that argument starts.
- **The nouns are deliberately unminted.** "Avoidance" and "plan library" appear here as
  descriptions, not terms — a word enters the dictionary in the same change that builds its
  thing, and both issues carry that requirement.

- **Restriction is at commitment, not during search.** A world failing law is refused after
  the search has picked it, and a refused winner yields NO plan rather than the next legal
  candidate — [a-plan-is-a-path-of-graph-diffs](/decisions/a-plan-is-a-path-of-graph-diffs.md)'s
  recorded seam, untriggerable while no shape refuses a state a lever can reach. The moment
  #468's source mechanism lets a sovereign ratify at violation severity — a true MUST NOT
  over a reachable state — it becomes triggerable, and the same change must close it the way
  that record already names: ask the next candidate. Carried on #468's definition of done.

# Issues this emits

[#468](https://github.com/ShishkinDmitriy/orexis/issues/468) — a want met by absence: the
general avoidance, and the deontic prohibition's future seat.
[#469](https://github.com/ShishkinDmitriy/orexis/issues/469) — remembered plans: the library,
tried before searching, re-verified on every use.
It engages [#466](https://github.com/ShishkinDmitriy/orexis/issues/466) rather than emitting
it: costs are what make MAY's economics real.
