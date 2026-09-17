"""The AFFORDER: the service that puts a world's rows together out of two collections.

**IT HOLDS LOGIC AND NOT ONE QUERY**, which is the whole of why it is a service and the two
things it uses are repositories (a-repository-is-not-a-service). It decides WHAT to ask — which
actions are worth asking about at all, whose wants to ask them against, how to order what comes
back — and each collection knows HOW to fetch its own: `Actions` reads the vocabulary,
`Affordances` runs one action's precondition against one world, `Desires` says what this agent
holds. No string in this file is a query, and a test in this package holds it to that.

**THE CLASS IS BACK AND IT MEANS SOMETHING NOW.** There was a file of this name that held a
model, a collection and a question belonging to the desire modality, and no class at all — which
is what "there is no such class inside" meant. Affording really is a service; it just was not one
while it also held its own query texts.

**THE TWO SIDES ARE ASKED AT DIFFERENT RATES**, and the split is what lets them be. What a
package declares is public and timeless; what a world affords is neither. They were read together
once per node of a search: a three-disk hanoi solve re-read the same eleven templates eighteen
times, and a pass over a larger frontier scales with it. The templates are read once here.
"""

from __future__ import annotations

from .affordance import Affordance


class Afforder:
    """What an agent could do, in the world it is asked about — assembled, never stored."""

    def __init__(self, actions, desires, agent_uri: str):
        #  The two collections that answer about the AGENT, which does not change between
        #  worlds: what its packages declare, and what it holds.
        self._actions = actions
        self._desires = desires
        self._me = agent_uri
        #  BOTH SIDES ASKED ONCE, and how often to ask is precisely this service's decision —
        #  neither collection could know that its answer is stable for a pass. What a package
        #  declares cannot change while one runs, and what the agent holds is re-projected by a
        #  write rather than by a search. The world is the only thing that moves per node, and
        #  the world is not here.
        self._about_of: dict | None = None
        self._templates: list | None = None

    def offered(self, affordances, only=None) -> list[Affordance]:
        """Every row this agent has in the world `affordances` opens, name-ordered.

        THE WORLD IS A PARAMETER OF THE ASK and not of this service, which is what lets the two
        sides be asked at their own rates: one afforder per pass holds the templates and what the
        agent holds, and a search hands it a fresh `Affordances` per node. Before the split both
        were re-read per node.

        `only` is the set of actions worth asking at all — the search's RELEVANT set (#504), or
        None for every action. A precondition is a query per action per world, and a lever that
        touches nothing the want reads was already never simulated; asked through here it is
        never asked either, so a menu that grows by unrelated domains costs a pass nothing. It
        is decided HERE because what is worth asking is a judgement about the search, not
        something either collection could know.
        """
        #  Asked ONCE, of the collection that owns the question — it was `wants_of`, reading the
        #  desire modality from inside the menu, which is why "why does the afforder ask for
        #  wants?" was a fair question. The service needs to know what the agent holds; being
        #  told is not the same as fetching it.
        if self._about_of is None:
            self._about_of = self._desires.abouts(self._me)
        if self._templates is None:
            self._templates = self._actions.find_all()
        rows: list[Affordance] = []
        for action in self._templates:
            if only is not None and action.uri not in only:
                continue
            rows += affordances.find_all_by_action(action, self._about_of)
        #  Sorted because per-action order is no order.
        return sorted(rows, key=lambda a: (a.want or "", a.action, a.for_agent or ""))
