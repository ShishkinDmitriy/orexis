"""The instant the next ground a world can be told from begins — where a wait lands (#920).

A GROUND IS A PERIOD IN WHICH NOTHING PREDICTED CHANGES (`lay_ground`): the present, and the present
with each prediction applied at its instant, a boundary that changes nothing being no period at
all. So the next ground is the next instant something predicted changes, and nothing between the two
can be waited for. A world stands in the ground holding at its start, the earliest its path reaches
it, as `take` forks it.

**AND THE NEXT GROUND IS THE NEXT ONE THE SEARCH CAN TELL FROM IT.** `lay_ground` tells a period from
the one before it by EVERYTHING it holds, so a prediction that moves only what no text reads — a
reading's number inside its band, the stretch a reading holds for — is a ground of its own; but the
search tells two worlds apart within what is read (`hash_named_graph`), and a wait landing in such a
ground reaches its parent again and is passed over as a repeat. Measured on the shipped worlds before
this read the hashes: the greenhouse's soil forked one such wait per pass and an allotment grower
three a search, every one a repeat. So the ground a wait lands in is the first later than the world's
whose hash on its row — taken within what is read — is not the hash of the ground the world stands
in; one wait then spans every stretch in which nothing read changes, and none is offered where
nothing read is predicted to change at all.

A READ: it writes nothing, and the two acts that ask it — `admit`, whether a world admits a wait at
all, and `take`, where the wait it admitted lands — ask the one question, so the instant cannot be
one thing to the admission and another to the fork.
"""

from __future__ import annotations

from datetime import datetime

from agent.store import Raw, catalogue_of, remember, rows

#  EVERY GROUND, ITS START AND WHAT IT HOLDS BY HASH, earliest first — once a pass, since the grounds
#  are laid before the search and the search lays none.
_GROUNDS_Q = """
SELECT ?at ?hash WHERE { GRAPH $cat { ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?at ; orexis:hash ?hash } }
ORDER BY ?at"""

#  A WORLD'S START, off its row — a ground's or a possible world's, both under `dcterms:temporal`.
_START_Q = """SELECT ?at WHERE { GRAPH $cat { $world dcterms:temporal/orexis:start ?at } } LIMIT 1"""


def next_ground(store, world: str, *, memo=None) -> datetime | None:
    """The instant the first ground after the one `world` stands in that holds something else, as
    the search reads it, begins — or None where nothing laid after it does. Remembered per world for
    the pass: the grounds are laid before the search and a world's start is written when it is forked."""
    def ask():
        cat = Raw(f"<{remember(memo, ('catalogue',), lambda: catalogue_of(store))}>")
        grounds = remember(memo, ("grounds_by_hash",), lambda: [
            (datetime.fromisoformat(r["at"]), r["hash"]) for r in rows(store, _GROUNDS_Q, (), cat=cat)])
        if len({h for _, h in grounds}) < 2:
            return None                 # every ground the same place: no world has anything to wait for
        found = rows(store, _START_Q, (), world=world, cat=cat)
        if not found:
            return None
        start = datetime.fromisoformat(found[0]["at"])
        standing = [h for at, h in grounds if at <= start]
        here = standing[-1] if standing else None
        return next((at for at, h in grounds if at > start and h != here), None)
    return remember(memo, ("next_ground", world), ask)
