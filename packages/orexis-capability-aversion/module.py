"""Steering clear of ratified avoided states — `aversion:Heeding` (#468).

The SHALL NOT of the #467 sitting, soft by construction: an entered avoided state is a hot
want the search answers through the ordinary achiever road — a candidate world where the
pattern binds nothing is MET, and among worlds that exit the state the cheapest wins. What
this module holds is only the judging: is the pattern entered, in whichever world is asked
about. It proposes nothing, times nothing, and owns no lever.

One text, one engine, everywhere. The ratified select is run with `$this` and `$state`
substituted — against the live belief base for the want's own row, against the planner's
imaginarium for a candidate world — so the entered-or-held verdict can never be answered
two ways by two engines. That is why the want carries no `orexis:metWhen`: met IS this
measure reading zero (the call road, #359), and a met-shape would have been a second text.
"""

from __future__ import annotations

from datetime import datetime

from orexis_agent_deliberation.desire import Desire
from orexis_agent_progression.ontology import DESIRES, DESIRE_URGENCY, STATE_GRAPH
from orexis_agent_progression.store import bindings

from agent.module import Module
from assembly.contribute import contributes

from .terms import AVERSION, HEEDING

#  My wants, asked of the desire modality — the derivation minted them, the store holds them,
#  and this module recognises its own by the KIND, never by a flag (the-stake-is-sensings-want's
#  discipline, one package over). The select rides on the copied statement node.
_WANTS_Q = f"""
SELECT ?want ?state ?select ?label WHERE {{
  <%s> orexis:holds ?want .
  ?want a <{AVERSION}> ; orexis:about ?state .
  ?state sh:select ?select .
  OPTIONAL {{ ?want rdfs:label ?label }}
}}"""


class AversionModule(Module):
    """The judging half of steering clear; the steering itself is the search's."""

    CAPABILITY = HEEDING
    name = "aversion"

    # --- the pattern, run about a world ------------------------------------------------------

    def _mine(self) -> list[dict]:
        return bindings(self.agent.desires.query_union(_WANTS_Q % self.me.uri))

    def _entered(self, query, state: str, select: str) -> bool:
        """Whether the avoided pattern binds, in the world `query` answers about.

        The ratified text, substituted exactly as a measure's parameters are: `$this` is this
        agent, `$state` names the graph the readings live in — the live sensed graph, or a
        candidate node's own inside the imaginarium — and rows mean ENTERED.
        """
        text = (select.replace("$this", f"<{self.me.uri}>")
                      .replace("$state", f"<{state}>"))
        try:
            return bool(bindings(query(text)))
        except Exception as exc:
            #  A pattern that will not run must read as ENTERED, not as held: the loud
            #  direction. A select the gates admitted and the engine refuses is a defect
            #  someone must see, and a want stuck hot is how this architecture says so.
            self.log.error("avoided-state pattern failed to run: %s", exc)
            return True

    # --- the choir ---------------------------------------------------------------------------

    @contributes(DESIRES)
    def desires(self, now: datetime | None = None) -> list[Desire]:
        """My contribution to what this agent pursues: its aversions, entered first.

        Binary on purpose — the four-measures table's third row: between entered and held
        there is nothing to be nearer to, so `met` at 0.0 and `entered` at 1.0 is the whole
        gradient, and the search crosses any multi-step exit on the frontier, which never
        needed a slope.
        """
        out = []
        for row in self._mine():
            entered = self._entered(self.agent.beliefs.query, STATE_GRAPH, row["select"])
            out.append(Desire(uri=row["want"],
                              urgency=1.0 if entered else 0.0,
                              state="entered" if entered else "met"))
        return out

    @contributes(DESIRE_URGENCY)
    def desire_urgency(self, desire, query, state: str,
                       value: float | None = None) -> float | None:
        """The measure, for MY kind of want, about whichever world is being judged.

        This is what keeps a held aversion from being planned into noise: the planner's root
        urgency reads 0.0 and the pass ends SATISFIED with no steps, where the flat
        not-knowing fallback would have sent the search shopping for a want that wants
        nothing. And it is what makes an entered one plannable: a candidate world where the
        pattern no longer binds scores 0.0, is MET by the same reading, and joins the
        achievers, where cost decides.
        """
        for row in self._mine():
            if row["want"] == desire.uri:
                return 1.0 if self._entered(query, state, row["select"]) else 0.0
        return None
