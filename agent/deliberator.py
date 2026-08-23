"""The deliberator: given where the agent stands against what it wants, the next move.

**This is the mind's WHETHER, and it is the kernel's because a mind is not plug-in-able.** It
was `deliberation:Reflex` and `deliberation:Planning`, two members of a family, and the family
does not survive its own evidence: `PlanningModule` subclassed `ReflexModule`, called
`super().propose()` first, and added one branch whose `_my_shop_needs` returns None for any
agent that is not a dealer. A member that literally CONTAINS the other, with its extra branch
inert everywhere else, is not an interchangeable implementation — it is one deliberator with a
clause most agents do not reach. They are one class now, and no shipped behaviour moved.

**Consulting survives as a seam, and a better one.** Asking a model what next is a genuine
alternative — it is the reason the extraction happened at all — but WHICH deliberator answers
is a choice, and this project puts choices in beliefs rather than in grants: it becomes a pick
(`ag:deliberatesBy`) that an agent's review can move inside whatever room its mandate leaves,
not a capability its world derives for it once at genesis. Everything
knowledge/decisions/llm-heavy-deliberation.md fixes about it stands unchanged: a move from this
vocabulary's menu and never free text-to-action, the bid number stays deterministic, and the
keeper's patience bounds how often it is consulted.

**What stays out is everything but the whether.** The HOW is the actor's — a bid's quantity and
price are deterministic code, per knowledge/decisions/deterministic-bid.md, whoever said to bid.
The KEEPING is the ledger's: a deliberator reads what stands and never writes it, because
deciding and remembering what was decided are different things.

See knowledge/decisions/an-intention-is-an-amortised-deliberation.md.
"""

from __future__ import annotations

from pathlib import Path

from . import planner, trace
from .desire import Desire
from .menu import Affordance, menu_of
from .module import Module
from .ontology import AG, DELIBERATION_GRAPH
from .planner import Planner
from .store import bindings

# What this package asks OF others, by family — their namespaces, never their Python.
_DESIRE = "http://example.org/orexis/desire#DesireCapability"

# The moves. The intention package's individuals, referenced by IRI: a move IS what the keeper
# records when the actor carries it out, so naming anything else would put a translation table
# between deciding and remembering.
# The means are the kernel's words (the-mind-is-six-graphs): a move IS what the keeper
# records, and four packages name these, which is what makes them lingua franca.
OBSERVE = AG + "Observe"
ACTUATE = AG + "Actuate"
ACQUIRE = AG + "Acquire"

# The ladder's order IS the preference (#190): act with what is yours before buying what is
# not — each rung costlier and more social than the last. Disjoint per source by
# construction (a source with a shop is contested, so its pump yields no Actuate row; a
# source without one convenes no venue), but one agent may hold a private bottle AND bid in
# a market, and then the cheaper rung wins.
_RUNG = {ACTUATE: 0, ACQUIRE: 1}

# Which way the lot moves what it is priced in — the market vocabulary's terms, read off the
# T-Box rather than known. Issue #127: the sign used to be hardcoded here as `value < aim`,
# which was the one piece of "buy water to raise moisture" written nowhere in any graph.
#
# Joined THROUGH A VENUE I BID IN (#198), never over the T-Box at large: the direction is a
# fact about a lever, and the lever I hold is a market. Asked bare, "which way does moisture
# move" has no answer the moment a fan market lowers what a water market raises — whichever
# term the store returned first would steer the reflex, silently. Asked through my venue, the
# answer is which way MY lever moves it, which is the only question a reflex ever had.
_RAISES = "http://example.org/orexis/market#Raises"
_LOWERS = "http://example.org/orexis/market#Lowers"
_DIRECTION_Q = """
SELECT ?direction WHERE {
  <%s> market:bidsIn ?m .
  ?m market:marketFor ?src .
  ?src market:supplies ?good .
  ?term market:ofGood ?good ; market:aboutProperty <%s> ; market:direction ?direction
} LIMIT 1"""



class Deliberator(Module):
    """The decider. Speaks to no topic; its callers are its siblings, through the agent."""

    name = "deliberation"
    def pursued(self) -> list[tuple[Desire, str | None]]:
        """Every desire this agent holds, with the move I propose for it — or None.

        Here because deciding what can be done is exactly what a deliberator is, and because
        the kernel may not name a capability's family: `agent.pursuing()` merges what the modules
        want, and this is the only place that can say whether anything answers.
        """
        return [(desire, self.propose_for(desire)) for desire in self.agent.pursuing()]

    def start(self) -> None:
        """Drop whatever the last process was thinking.

        A trace describes a pass over a world, and the world moved while this agent was not
        running. Keeping one across a restart would leave the graph holding a decision about
        readings nobody has taken since — the same hazard as a trace outliving its pass, one
        lifecycle up. Cheap: the graph holds one pass per desire and most agents hold a handful.
        """
        self.agent.beliefs.clear_graph(DELIBERATION_GRAPH)

    def series(self) -> list[tuple[str, dict, dict]]:
        """The ranking, as figures — and the split that stops it misleading.

        `unactionable` is a want nothing I can propose would move: a fern above its region and
        a fern below it are both unmet at urgency 1.00, and only one of them is anybody's to
        fix, because no lever in this society lowers moisture. Counting it needs both halves —
        the wants, which are the modules', and the moves, which are mine — so it is reported
        by the one module that sees both.
        """
        pursued = self.pursued()
        #  NOTHING TO DECIDE IS NOT ZERO THINGS DECIDED. An agent with no stake — world/sensing's
        #  records and wants nothing — used to contribute no rows here because it was granted no
        #  deliberation capability at all, and `Module.reports` says outright that the ABSENCE of
        #  a module's lines is itself a reading. Dissolving the capability into the kernel would
        #  have silently turned that reading into a row of zeros on every dashboard.
        #
        #  So absence follows the FACT rather than the grant: no wants, no rows. It says the same
        #  thing the missing capability used to say, and says it about what is true of the agent
        #  now rather than about what its world provisioned for it once.
        if not pursued:
            return []
        wanting = [(g, move) for g, move in pursued if not g.is_met]
        #  `agent_goals`, like `agent_want` below, KEEPS THE RETIRED WORD. The noun gave way to
        #  `desire` when the vocabulary was ruled on (domain/desire.md), and a measurement name
        #  is the one surface where the rename costs more than it buys: it has history behind it
        #  in the series store, so renaming splits every series at the cutover and leaves a
        #  dashboard reading half of one.
        rows = [("agent_goals", {}, {
            "desires": float(len(pursued)),
            "unmet": float(len(wanting)),
            "unactionable": float(sum(1 for _, move in wanting if move is None)),
            "hottest": max((g.urgency for g, _ in pursued), default=0.0),
        })]
        #  ONE ROW PER WANT, which is what makes a single graph able to show all of them.
        #  The tag is the want ITSELF and not the property it is about, because a property
        #  cannot name every want: freshness is per instrument, a duty is per counterparty, and
        #  a panel keyed on `property` could only ever draw stakes. Urgency is unit-free by
        #  construction, so a moisture, a look overdue and a litre owed belong on one axis —
        #  that is the whole claim of a common currency, and this is where it becomes visible.
        #
        #  A DUTY is tagged by whom it is owed to and never by its claim. A jti is unique per
        #  round, so tagging by it would mint a new series every time the society traded and
        #  make the store's cardinality grow with its history — the cost of a dashboard nobody
        #  could then load. Whom I owe is a handful of agents and says the thing worth seeing.
        for desire, _ in pursued:
            about = (desire.owed_to.rsplit("#", 1)[-1] if desire.is_duty
                     else desire.uri.rsplit("#", 1)[-1])
            #  `agent_want` and its tag KEEP THE RETIRED WORD, deliberately. The noun "want"
            #  gave way to "desire" everywhere else when the vocabulary was ruled on
            #  (domain/desire.md), and a measurement name is the one place the rename costs more
            #  than it buys: it is an external surface with history behind it, so renaming
            #  splits every series at the cutover and leaves a dashboard reading half of one.
            #  The word is wrong and the continuity is worth more.
            rows.append(("agent_want", {"want": f"duty.{about}" if desire.is_duty else about},
                         {"urgency": float(desire.urgency)}))

        #  HOW IT DECIDED, not just what it wants (#256). `pursued()` above has just re-planned
        #  every desire, so the trace holds this tick's verdicts — read from there rather than
        #  counted here, so the figure a dashboard shows and the answer `orexis-ask` gives are
        #  one fact. Six fields because a planner has six answers where returning a move or
        #  None had two, and the pair worth watching is `no candidate` against `exhausted`:
        #  one says equip me, the other says my doses are too coarse.
        verdicts = trace.outcomes(self.agent.beliefs.query_union)
        rows.append(("agent_deliberation", {}, {
            outcome.replace(" ", "_"): float(verdicts.get(outcome, 0))
            for outcome in (planner.SATISFIED, planner.IMPROVED, planner.NOTHING,
                            planner.EXHAUSTED, planner.NOT_BETTER, planner.REFUSED)}))
        #  WHAT IT COST, from the same pass and not a second one. `pursued()` above re-planned
        #  every desire this agent holds, so these are that work's own figures — asking again to
        #  measure would double the cost being measured, which is the one thing an observability
        #  change must not do.
        #
        #  Three of these exist to make a RECORDED LIMIT visible rather than to confirm health.
        #  `deepest` pinned at 1 was two of them at once — a rule's CONSTRUCTs running against
        #  the store rather than the world (#254), and a cycle signature that was only the
        #  desire's own value, so a step that moved nothing else looked like somewhere already
        #  reached (#258); both are closed. `blind` above zero is a package that never stated
        #  what its lever does. A number that shows a known defect is worth more than one that
        #  says things are fine.
        rows.append(("agent_planning", {}, trace.effort(self.agent.beliefs.query_union)))
        return rows

    def propose_for(self, desire: Desire) -> str | None:
        """The move for one GOAL, whoever sourced it — the deliberator's real question.

        `propose` asks about a property and a value, which can only ever express a stake. This
        takes the want itself, so a duty reaches deliberation as what it is: a thing wanted,
        ranked in the same currency, pursued through an affordance like anything else. It is
        the widening the obligation record predicted — "the filter lifts when a member can
        pursue a desire that is a diff rather than a distance".

        A duty's means is not deduced here and could not be: it is the HONOURED row for that
        counterparty, which the market's own `honoured.rq` derives from the delivery chain.
        None where no lever answers — a debt to somebody my hardware cannot reach — and that
        None is the point. It used to be an exception thrown deep inside actuation; now it is
        a desire that stays hot, stays owed, and shows up in the ledger unpaid, which is this
        project's posture towards everything it cannot prevent: leave evidence.
        """
        #  NOT KNOWING is its own want, and the answer to it is always the same move. A want
        #  with no reading behind it, or one whose reading stopped being evidence about now,
        #  is repaired by looking and by nothing else — no lever moves a number you cannot see.
        #
        #  This is where `if value is None: return OBSERVE` used to live, as a first line in
        #  `propose` that ran before anything was asked. It said the same thing and could not
        #  say WHY: a value of None meant both "never read" and "the caller did not tell me",
        #  and the keeper exploited the second to ask "should I look at this?" by passing None
        #  deliberately. A desire carries its own state, so the question is now asked in the
        #  words it means.
        if desire.state in ("unmeasured", "stale"):
            return OBSERVE
        if not desire.is_duty:
            #  SIMULATE FIRST, where the levers say what they do. Asking whether a lever points
            #  the right way is not the same as asking whether taking it leaves this agent
            #  better off, and only the second question refuses to water a plant that is
            #  already too wet — the reflex's direction test says Raises, the gap says below
            #  the aim, and both are true of a drowning plant whose aim sits above it.
            #
            #  Falls back to the direction test whenever the search cannot answer: a means with
            #  no effect rule cannot be simulated, and most of them have none. So this changes
            #  behaviour for exactly the agents whose packages have said what their levers do,
            #  and changes nothing for the rest — which is how a widening should arrive.
            answered, move = self._simulated(desire)
            if answered:
                return move
            return self.propose(desire.observed_property, desire.value)
        #  Nobody has asked. The holder is waiting for its own watch to be live, and a host
        #  that doses early spends the water where nothing is looking (#132) — so a standing
        #  debt is visible, rankable, and still not actionable until it is presented.
        if not desire.pursuable:
            return None
        #  SIMULATE FIRST, exactly as a stake does (#255): the search sees the honoured row
        #  AND this agent's own levers, so a host owing water it does not hold plans the
        #  refill — Acquire raises the level Apply's premise reads, and "refill, then serve"
        #  falls out of two rules that never mention each other. A search that answered and
        #  found no move is the evidence the issue demands: the duty stays hot, stays owed,
        #  and is not pursued into a world where serving discharges nothing.
        answered, move = self._simulated(desire)
        if answered and move:
            return move
        #  The search speaks for a duty only when it FOUND a path — a vessel nobody has read
        #  binds no premise, and a premise that cannot bind proves nothing about serving. So
        #  anything short of a plan falls through to the pre-#255 road, unchanged: the
        #  honoured row for this counterparty, and the actuation boundary judges the vessel
        #  when it pours.
        for row in menu_of(self.agent.beliefs.query, self.me.uri, self.agent.desires.query_union):
            if not row.is_chosen and row.for_agent == desire.owed_to:
                return row.means
        return None

    def _simulated(self, desire: Desire) -> tuple[bool, str | None]:
        """`(answered, move)` — what the search says, and whether it said anything at all.

        A PAIR because there are three answers and only two would fit in one: take this move,
        take none, and "I cannot decide this by simulation". The third must not collapse into
        the second, or a lever whose package never stated its effect would silently become a
        lever nobody pulls — the search would decline for want of a rule and the agent would
        read it as a decision not to act.
        """
        deducer = self.agent.provider(_DESIRE)
        plan = Planner(self.agent, deducer, self.me).plan(desire)
        if plan.outcome == planner.NOTHING:
            return False, None               # nothing to simulate; let the reflex answer
        if plan.outcome == planner.SATISFIED and not plan.steps:
            return False, None               # already met; the reflex will also propose nothing
        if plan.steps:
            self.log.info("%s: %s (urgency %.2f -> %.2f)",
                          desire.observed_property.rsplit("#", 1)[-1] if desire.observed_property
                          else "a duty", plan.outcome, plan.urgency_now, plan.urgency_after)
            return True, plan.first
        #  A SEARCH OVER PART OF THE MENU CANNOT SAY "NOTHING HELPS". Some lever had no stated
        #  effect and was passed over, so the one that works may be the one nobody simulated —
        #  fern buys its water, Acquire has no rule, and a search that saw only Observe would
        #  have found that looking does not wet soil and stopped the plant buying. Defer.
        if plan.partial:
            return False, None
        #  A world reachable and not worth reaching. THIS is the decision the reflex could not
        #  make, and returning None here is the whole point rather than a failure to answer.
        self.log.info("%s: %s — no move improves on doing nothing",
                      desire.observed_property.rsplit("#", 1)[-1] if desire.observed_property
                      else "a duty", plan.outcome)
        return True, None

    def propose(self, observed_property: str, value: float | None) -> str | None:
        """Given where this property stands, the next move — or None, which is a decision.

        TWO CLAUSES, and the order is the one the two members had. The gap's sign answers
        first; the dealer's shop answers only if it did not. That sequencing is load-bearing
        and was nearly lost in merging them: `PlanningModule.propose` called `super().propose()`
        and then ran its own clause, so the reflex's three early returns — no reading, no
        desire module, no aim — meant "the gap says nothing", NOT "stop". Inlining the reflex
        body here would have turned each of them into a return that skips the shop, and a
        dealer whose aim was unset would have stopped refilling. Hence `_by_gap`.
        """
        if value is None:
            return None
        if (move := self._by_gap(observed_property, value)) is not None:
            return move
        #  THE DEALER'S CLAUSE, and it is inert for everyone else. `_my_shop_needs` answers
        #  only for a property that is this agent's own vessel's stock, so a fern reaches this
        #  line, gets None, and falls through exactly as the reflex always did. It was
        #  `deliberation:Planning` overriding `propose` to call `super()` and then run this;
        #  one class expresses the same thing without asking a world to choose between a
        #  member and the member that contains it.
        needed = self._my_shop_needs(observed_property)
        if (needed is not None and value < needed
                and self._direction_of(observed_property) == _RAISES):
            return ACQUIRE
        return None

    def _by_gap(self, observed_property: str, value: float) -> str | None:
        """The gap's sign against the aim — the whole of what `deliberation:Reflex` was.

        None here means THE GAP SAYS NOTHING, not that deliberation is over: `propose` runs the
        dealer's clause afterwards. That distinction is the one thing the merge had to keep, and
        it is why this is a helper rather than the first half of one function.

        With a reading in hand, the whole reflex is the gap's sign against the AIM — the pick,
        not the region's edge, because pursuing only past the band edge would leave the agent
        permanently short of where it decided to sit. Asked of desire at every call rather
        than cached: the aim is a belief, and a review may move it under a running agent.

        WHICH sign means pursue is read off the T-Box, not known (#127): the domain states that
        applying the lot raises or lowers the property its bids are priced in, and the reflex
        steers by that — below the aim with a lever that Raises, or above it with one that
        Lowers, is the move. `value < aim` used to be hardcoded here, which was the one piece
        of "buy water to raise moisture" written nowhere in any graph; a heater against a cold
        snap is now the same rule with no code change, which is what stating it bought.

        None three times over, and each is a decision: no aim means nothing to pursue toward
        (an agent that picked no point has decided not to steer this property); a gap on the
        side no lever moves means no move helps; and no stated direction means the reflex
        cannot know which way — refusing is honest where guessing would be the hardcoded sign
        sneaking back in as a default.
        """
        #  A value of None no longer means "look" — `propose_for` answers that, from a desire
        #  that says which of the two epistemic failures it is. Here it means only that the
        #  caller has no reading to steer by, and steering is all this member does.
        desire = self.agent.provider(_DESIRE)
        if desire is None:
            return None
        aim = desire.aim(observed_property)
        if aim is None:
            return None
        # MENU-DRIVEN since #190: every move the reflex can propose is a row, literally —
        # the rows for this property, cheapest rung first, and the first whose stated
        # direction matches the gap's sign is the move. Acquire used to be hardcoded here,
        # which was right while buying was the only lever that moved anything; the Actuate
        # rung made "which means" a question, and the menu was already the answer's home.
        # Chosen rows only, and the reason is narrower than it first looked. An obligation
        # IS a want (ag:Obligation, #218 remade) and is meant to reach deliberation —
        # but this member steers a PROPERTY toward an aim, and a duty is not a property-gap:
        # it is "this claim discharged", a graph-shaped desire. So the reflex passes over
        # honoured rows because it cannot express them, not because they are nobody's to
        # decide; the filter lifts when a member can pursue a desire that is a diff rather
        # than a distance — the widening a-plan-is-a-path-of-graph-diffs records.
        for row in sorted((r for r in menu_of(self.agent.beliefs.query, self.me.uri, self.agent.desires.query_union)
                           if r.observed_property == observed_property and r.direction
                           and r.is_chosen),
                          key=lambda r: _RUNG.get(r.means, len(_RUNG))):
            if row.direction == _RAISES and value < aim:
                return row.means
            if row.direction == _LOWERS and value > aim:
                return row.means
        return None

    def _direction_of(self, observed_property: str) -> str | None:
        """Which way the lever I could pull moves this property — through a venue I bid in.

        Per call rather than cached, like the aim: the T-Box is replaced on restart, not under
        a running agent, but a query this small is not worth a second copy of the truth.
        An agent bidding in no market gets None here and proposes nothing, which was already
        true — a direction with no venue behind it was the menu offering a move with no lever.
        """
        rows = bindings(self.agent.beliefs.query(
            _DIRECTION_Q % (self.me.uri, observed_property)))
        return rows[0]["direction"] if rows else None

    def _my_shop_needs(self, observed_property: str) -> float | None:
        """The lot my downstream venue owes — None when this property is not my shop's stock."""
        rows = bindings(self.agent.beliefs.query(_SHOP_Q % (
            self.me.uri, self.me.uri, observed_property,
            self.agent.beliefs.graph, self.me.uri)))
        return float(rows[0]["q"]) if rows else None

    def plan_for(self, observed_property: str) -> list[Affordance]:
        """The dealer's two-step, as rows: acquire upstream, then offer downstream.

        Empty when the property is not the vessel's stock — a planner asked about somebody
        else's gap has no chain to offer, and says so rather than inventing one. Runs the
        shipped `plan.rq`, the same text the sovereign can put over the ask channel.
        """
        rows = bindings(self.agent.beliefs.query(
            PLAN_QUERY.replace("$me", f"<{self.me.uri}>")))
        return [Affordance(means=r["means"], observed_property=r["property"],
                           via=r["via"], direction=r.get("direction"))
                for r in sorted(rows, key=lambda r: r["step"])
                if r["property"] == observed_property]


# The dealer's shop, asked from inside: the lot my downstream venue owes, IF the property in
# hand is my own vessel's stock. Both joins are the Planning grant's premises re-asked —
# I act for a vessel I offer, the property is one its stated ranges name — plus my own
# offerQuantityL belief, read from my private graph exactly as the bidder reads its
# conversion: a lot is a HOSTING belief, and this package may name the term's IRI but never
# import the market's Python.
_SHOP_Q = """
SELECT ?q WHERE {
  <%s> ag:actsFor ?vessel .
  ?vessel market:offeredBy <%s> .
  ?vessel <http://www.w3.org/ns/ssn/systems/hasOperatingRange> ?range .
  ?range <http://www.w3.org/ns/ssn/systems/inCondition> ?cond .
  ?cond <http://www.w3.org/ns/ssn/forProperty> <%s> .
  GRAPH <%s> { <%s> <http://example.org/orexis/market#offerQuantityL> ?q }
} LIMIT 1"""

# The dealer's plan ships as SPARQL beside the menu contributions (#206), so the sovereign
# may run the very text the planner runs — one file, two readers, no drift.
PLAN_QUERY = (Path(__file__).parent / "plan.rq").read_text()

OFFER = AG + "Offer"
