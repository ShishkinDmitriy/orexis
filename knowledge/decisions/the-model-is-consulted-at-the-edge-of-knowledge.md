---
type: Decision
title: The model is consulted at the edge of knowledge, and its answer is written down
description: The LLM is not a decider in the loop — it is a teacher consulted when no written-down plan connects a gap to a lever, and its whole output is one or two graph facts that are then held to shapes and never asked for again. The reflex handles everything the graph already knows, free and forever; the model appears when the world surprises, and periodically through review to propose improvements. Who approves the answer splits by TIME, not by kind, because the approval interface itself is a genesis-only thing — while the world is being designed the sovereign is present and ratifies; once the society runs, the sovereign is absent, so the agent adopts privately, bounded by shapes, wrong at its own cost. Emits the affordance issue - the graph must state which direction a lever moves a property - as the substrate the whole design stands on.
status: accepted
stage: v1
tags: [llm, deliberation, bdi, affordance, genesis, sovereignty, capability]
timestamp: 2026-08-14T00:00:00Z
---

# The question

[an-intention-is-an-amortised-deliberation](/decisions/an-intention-is-an-amortised-deliberation.md)
opened the seam: `deliberation:Consulting`, the LLM member, declared with its constraints fixed —
a move from the menu, never free text-to-action, numbers deterministic, consultations bounded by
the keeper's patience. What it did not settle is *when the model is consulted and what becomes of
its answer* — and behind that, a question the constraints only gestured at: **where does the
knowledge live that connects a gap to a lever at all?**

That second question has a concrete hole. "To raise moisture, bid for water" is spread across
the world graph (which market, which source, which pot), the T-Box (bids are priced in
`SoilMoisture`), one causal constant (`litresPerFraction`) — and one piece that is written
NOWHERE: the *direction*. Nothing in any graph says water raises moisture rather than lowering
it. The reflex knows it because `deficit = aim - value` hardcodes it, which is harmless with one
lever and one domain and unwritable the moment a model needs a menu that says what each act
*does*.

# What was decided

**The model is a teacher at the edge of knowledge, not a decider in the loop — and its whole
output is graph facts.**

```
gap appears
   │
   ├─ the graph connects it to a lever?  ──► Reflex handles it. Deterministic. Free. Forever.
   │
   └─ no connection?  ──► consult the model once
                           └─► its answer is one or two TRIPLES — an affordance,
                               the same fact a human would have authored, arriving late
                               └─► held to shapes like everything else, written down,
                                    and never asked for again
```

Three consequences, in order of how much they change:

**The reflex generalises one step and stays free.** Today it is *below the aim → Acquire*
because the direction is hardcoded. Over affordance facts it becomes *gap in property P, plus a
lever the graph says moves P the right way → the move* — still deterministic, still no model in
the loop, and now correct for a lever nobody hardcoded. This is the substrate, and it is
[#127](https://github.com/ShishkinDmitriy/agora/issues/127): the graph must state which
direction a lever moves a property, so the menu is *derived* rather than written into a prompt.

**Consultation happens at the rate the world surprises, not the rate sensors tick.** The
trigger is a gap with no affordance connecting it to any lever the agent holds — a genuinely
novel situation, once per situation. The keeper's patience already bounds re-asking about the
same standing question; the affordance bounds re-asking about the same *kind* of question. That
completes the amortisation ladder the roadmap was named for:

| layer | amortises | horizon |
|---|---|---|
| an intention | one decision | seconds to minutes |
| a written-down affordance | a class of decisions | the agent's lifetime |
| a review arising | re-opening either | bounded by its own clock, on evidence |

**Periodic improvement is review's, and review already works this way.** "Propose changes when
the environment shifts" is not a new mechanism — `capabilities/review/` wakes on its own clock,
reads evidence summaries, re-picks a belief within its mandate and records why.
`review:Consulting` has been declared-and-reserved since that capability was built; a model
proposing a better aim from gap history is that member, inside the same mandate every re-pick
answers to.

# Who approves the answer: split by time, because the interface is

The obvious governance split — domain facts need the sovereign, private tunings do not — is by
*kind*. It is the wrong split, because it assumes an approval channel that exists whenever
needed, and here it does not: **the interface between the user and the society is a genesis-time
thing.** While a world is being designed, the sovereign is present, the conversation is open,
and asking is cheap — the genesis process is *already* "the LLM drafts, the sovereign ratifies".
Once the society starts, the user disappears; strictly speaking the interface disappears. An
agent that queued a proposal for synchronous approval would wait on a channel with nobody at the
other end.

So the split is by **when**:

- **At genesis** — the model proposes affordances into the draft, the sovereign approves or
  corrects, and what is ratified lands in the world like every other authored fact. Most
  affordances should be born here: "water raises moisture" is knowable at design time.
- **At runtime** — the agent decides alone. A model-authored affordance is adopted **privately**,
  into the agent's own beliefs, held to the same shapes as everything else — and wrong at the
  agent's own cost, which is the market's own discipline: an agent that believes something false
  about what a lever does loses money, and review, reading the gap history, is the mechanism
  that notices the belief is not paying.

What keeps the runtime path honest is everything already built: a privately adopted fact lives
in the agent's graph and says so ([who-put-the-fact-there](/decisions/who-put-the-fact-there.md)),
shapes bound what it may claim, `deterministic-bid` keeps numbers out of the model's hands, and
nothing an agent believes privately reaches another agent's store.

# Seams left open

- **The affordance vocabulary itself** — [#127](https://github.com/ShishkinDmitriy/agora/issues/127),
  the emitted issue, now CLOSED: the domain states its direction once (`market:Raises` on the
  valuation term, demanded by a shape), the Reflex reads the sign instead of hardcoding it, and
  the menu is derived. Strengthened past the issue on the sovereign's ask — the Acquire row is
  *deduced along the plumbing*: the market's host holds an actuator, the actuator is plumbed to
  this agent's own pot, so opening it puts the good where the agent is, and only the physics
  atom ("water raises moisture") is stated, because no topology can derive a law of nature. A
  market whose deliveries cannot reach your pot is, for you, no lever at all — which is what
  keeps the menu honest the day two markets move two properties. Cost-shape and side-effects
  remain speculation until that second lever exists.
- **A runtime interface, later.** The sovereign is absent, not abolished: a world can already be
  amended and picked up on restart (`refresh_public`), so an asynchronous channel — the agent
  writes proposals somewhere the sovereign reads at the next amendment, private adoption in the
  meantime, promotion or veto when a human next looks — is buildable on existing mechanics. Not
  designed here; the trigger for designing it is the first privately-adopted affordance worth
  promoting to the ratified world.
- **Which member answers when both exist** — unchanged from the parent record. The selection
  rule between Reflex and Consulting is the last piece to add, not the first; the edge-of-
  knowledge trigger (no affordance found) is the natural candidate and is recorded here as the
  intent.
- **The model's context and endpoint** — environment, per the no-config rule; the prompt as a
  derived affordance menu. Mechanics belong to the implementing change.
