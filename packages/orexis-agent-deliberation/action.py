"""One action: a way of acting, as the vocabulary declares it.

The MODEL, and a LONG-LIVED OBJECT — a node a package ships in its `actions.ttl`, carrying the
precondition that says when it is possible. It is declared once, it outlives every situation, and
that is exactly why it can be stored at all: a schema cannot outlive anything
(a-situated-instance-is-kept-only-when-it-is-testimony).

What it comes to in one world is an `Affordance`, which is situational data about it and is kept
nowhere. The mapping is neither one-to-one nor onto: measured on `world/simulation`, eleven
actions afforded four rows for the fern, nine of them afforded nothing at all, and `Serving`
alone afforded three — one per valve. See knowledge/domain/action.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Action:
    """An action and the precondition it carries.

    STORED FACTS ONLY, and only the three a menu needs. What it makes true is its EFFECT, read by
    `effects.py` from the same node; what it costs, who takes it and what steps it comes to are
    read by whoever needs them. A model carrying every column of its node would make every reader
    of one column depend on all of them.
    """

    uri: str
    #  The SELECT whose rows are this action's affordances, with `$me`, `$wants` and `$picks`
    #  still in it — a template, bound by whoever asks and against whichever world.
    available: str = ""
    #  WHAT IT TAKES: the parameters it is filled with, by IRI, each declared by the package
    #  that declared the action (`orexis:takes`). The precondition projects one variable per
    #  parameter, named for the IRI's local part, and a rule reads the same name as a `$token`.
    #  The kernel holds a row to this list and interprets no member of it — a disk, a peg, a
    #  valve and a venue are all just parameters here.
    takes: tuple[str, ...] = ()
