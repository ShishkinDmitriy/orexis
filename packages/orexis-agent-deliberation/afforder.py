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

    def __init__(self, actions, affordances, desires, agent_uri: str, picks: str):
        #  The collections. `affordances` is the DEFAULT one — over the belief base, which is
        #  the world the agent is actually in; a caller asking about an imagined world passes
        #  the collection over the store those worlds live in, because which store a collection
        #  is over is the question's, not this service's.
        self._actions = actions
        self._affordances = affordances
        self._desires = desires
        #  AND THE IDENTITY, which a SERVICE may hold where a collection may not. This one is
        #  the agent's afforder; a collection is nobody's, which is why the agent's URI and its
        #  own graph reach the collections below as criteria rather than as state.
        self._me = agent_uri
        self._picks = picks

    def offered(self, affordances=None, *, graphs=None, only=None) -> list[Affordance]:
        """Every row this agent has in one world, name-ordered.

        THE WORLD IS A PARAMETER OF THE ASK and of nothing else — not of this service, and not
        of the collections it uses. A search names a world per node and builds nothing per node:
        one afforder, one collection per STORE, and as many worlds as the pass reaches.

        `affordances` says which store the worlds are in, defaulting to the agent's own. A
        search passes its imaginarium's, because an imagined world is not in the belief base —
        which is the one thing about this that a caller genuinely knows and the service cannot.

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
        #  STATELESS, and the sovereign's question is why. Holding a memo here made this a
        #  thing callers had to keep, so there were three of them — one per pass, one per
        #  deliberator call, one per remembered candidate. An agent has ONE afforder now; each
        #  collection remembers its own answer for exactly as long as it is allowed to.
        about_of = self._desires.abouts(self._me)
        rows: list[Affordance] = []
        for action in self._actions.find_all():
            if only is not None and action.uri not in only:
                continue
            rows += (affordances or self._affordances).find_all_by_action(
                action, about_of, self._me, self._picks, graphs=graphs)
        #  Sorted because per-action order is no order.
        return sorted(rows, key=lambda a: (a.want or "", a.action, a.for_agent or ""))
