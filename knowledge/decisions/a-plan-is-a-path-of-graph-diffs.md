---
type: Decision
title: A desire could be a graph, and a plan a path of diffs — the widening, mapped before it is needed
description: The sovereign's question re-derived STRIPS from inside the graph, and this
  architecture is already its degenerate case — menu rows are action schemas, the Reflex a
  depth-1 planner, intentions committed steps, verification the monitoring. The widening is
  effects on the menu row, deduced goal patterns, and a bounded Planning member; its guardrails
  are the two standing principles, and its first honest customer is the supplier's empty barrel.
---

# A desire could be a graph, and a plan a path of diffs

Asked by the sovereign in three steps that are one idea: desire as a whole graph rather than
one aim fact ("now the value is this, the desired value is another"); generalised past
datatype properties to a generic graph diff; and plans whose every step is defined by what it
adds to the graph and what it deletes, so that a diff remains and a path must be found. That
is classical planning — STRIPS — lifted to RDF, and the useful discovery is that this
architecture is already its degenerate case:

| planning concept | already here |
|---|---|
| action schema: preconditions | a menu row's WHERE clause — the plumbing walk IS one |
| action schema: effects | `market:direction` — a one-bit effect ("this property rises") |
| goal state | the region and the aim — a goal over one datatype property |
| planner | the Reflex — greedy, depth 1 |
| committed plan step | an intention, lifecycle and patience included |
| execution monitoring | the verification arc — expected effect vs observed, UNMET and false-knowledge |

So the generalisation is a WIDENING, not a rebuild — and one precedent makes "desire as a
graph" less exotic than it sounds: **SHACL shapes are already desired graphs.** The sovereign
holds them about worlds and validation is gap detection; a desiring agent holding a deduced
pattern about the world-state is the same machinery pointed at runtime.

## One formalism, a modality axis

Asked next by the sovereign, and it is the sharpest formulation of the whole idea: are these
just two KINDS of shape — one validating a world, unviolable, and one desired? Yes — and the
axis already has two points in the house, with the third legal by SHACL's own rules:

| modality | severity | violated means | who reacts | when |
|---|---|---|---|---|
| must hold | `sh:Violation` | illegitimate — refused | a human, at the gates | ratification, boot, each revision |
| should hold | `sh:Warning` | legitimate, worth noticing | an operator | the gates |
| should become | a custom severity (`sh:severity` is any IRI) | legitimate, unsatisfactory — a GAP | the agent, through its levers | continuously |

Three asymmetries keep the kinds from collapsing. WHO THEY BIND: a validating shape is the
society's, everyone held identically; a desired shape is a stake, deduced per agent — and
neither may be weakened by the agent, which is the symmetry that matters. DEGREE AND TIME:
conformance is boolean now; a want has signed distance (what urgency, bidding and the alarm
bands consume — the violation must carry its measure) and is pursued TOWARD, tolerating being
unmet while the plan runs, which is the entire reason intentions exist. THE REACTION PATH:
violation refuses, warning notes, desire feeds the menu — which is where this record's
machinery clicks in: gap, affordance rows, lever or plan.

## The guardrails, which are the two standing principles

**A desire answers to something public.** The region is deduced from stated ranges precisely
so an agent cannot want less and call itself satisfied
([the-range-is-the-plants-and-the-pick-is-the-agents](/decisions/the-range-is-the-plants-and-the-pick-is-the-agents.md)).
A desired GRAPH must come from the same discipline — deduced or ratified patterns, never
privately authored goals — or the self-satisfaction loophole returns at graph scale.

**Control the derivative.** Effects flow through levers the graph authorises: every plan edge
is a menu row, precondition-checked as Acquire walks the plumbing. A plan is a path through
the AFFORDANCE graph, never arbitrary surgery an agent imagines onto the world.

## The first honest customer

Multi-step planning is not needed by anything shipped — heat beside water is two parallel
one-steps — with one real exception: **the supplier's empty barrel**. "Water fern" dead-ends
when the tank is dry; the true plan is *refill, then sell* — two steps with a genuine
dependency, expressible only with effects ("refilling makes `lotCapacity > 0` true, which is
every bidder's Acquire precondition"). The float switch the terrace build adds makes the
precondition observable. Depth 2 suffices; that is the scale to build for.

## The path in, when it is wanted

1. **Effects join the menu row** — [#127](https://github.com/ShishkinDmitriy/agora/issues/127)
   gave direction; the row grows its add/delete template, owned where direction is owned: the
   lever's meaning states what applying it makes true.
2. **Goal patterns are deduced** from the same statements the regions come from — a region
   becomes a one-pattern goal, and plants notice nothing.
3. **A `Planning` member joins the deliberation family** — the seat the family was built to
   offer: Reflex (depth 1), Planning (bounded search, depth 2–3), Consulting above both, where
   the model PROPOSES a plan and the effect machinery VERIFIES each step's preconditions —
   deterministic-bid applied to plans: the model picks, code checks.
4. **Monitoring is already built**: an intention chain whose step's expected diff fails to
   appear is the unconfirmed-dose logic, generalised.

# Seams left open

- **Implemented at depth 2, when the trigger fired.** The city mains (#201) made the supplier
  refillable, and the Planning member took its seat: granted by the dealer premise (acting
  for a source it offers, refillable from a source another offers — levers that compose),
  subsuming the reflex, adding exactly ONE deduced goal past the region — the hosted lot must
  be serveable, which is every downstream buyer's silent Acquire precondition. The other half
  landed in the host: rounds are sized by the vessel's own freshest reading (the bench had
  sold 2 L lots from a barrel at 0.000 — phantom water, conservation violated live), and a
  LOW nobody can serve DEFERS the round, reopening the moment the witness reports the refill
  — acquire-then-offer, the two-step held by the market and observable in the logs. The plan
  is also data: `plan_for` returns the two rows through the two venues, the Consulting
  member's substrate. What was NOT built of the sketch: the add/delete template on menu rows
  (the serveability goal is deduced in the planner, not stated as row effects — sufficient at
  depth 2, revisit if depth grows) and goal patterns as shapes (one deduced goal exists; the
  severity-axis machinery stays future). `intention:Offer` is declared for plans to name and
  adopted by nobody — a host keeps no gap ledger, per the family's own boundary.
- **The convening gap is the planner's ceiling.** A dealer may want stock the upstream will
  not yet sell: the city convenes on LOW alone, so a planner pursuing serveability at
  stock 1.5 has no round to bid in until the region floor is crossed. That is
  [the-lot-is-the-hosts-standing-offer](/decisions/the-lot-is-the-hosts-standing-offer.md)'s
  recorded seam ("half the lot can be wanted by agents none of whom can convene a round"),
  reached now from the buy side — the fix is a convening shock beyond the demand shock
  (market.md names four), not a deeper planner.
- **Plan search is bounded by construction**, not by hope: depth 2–3 over menu rows whose
  preconditions are SPARQL, never open-ended STRIPS search. If a domain ever wants more, that
  is a different decision, taken then.
- **Who ratifies a goal pattern** beyond the deduced ones is the same question as who ratifies
  an affordance the model proposes — answered by the consulted-at-the-edge record's split:
  present sovereign ratifies at genesis, absent sovereign means private adoption plus review.
