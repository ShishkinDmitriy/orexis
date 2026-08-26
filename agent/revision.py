"""The belief-revision seam: what a change to the belief base is worth waking the mind for.

**The one row of the agent stack that had no home.** Below it is bytes and translation, above it
the mind; the seam decides which of a change's consequences is worth a deliberation pass at all
(the-agent-stack-is-a-second-axis, layered-by-timescale-and-interruptibility). Until this file
the decision was spread across whoever happened to call `execution.pursue_for` — sensing's
actuator on a fresh reading, the bidder on an offer, the host on a claim — so there was no place
to state the rule and no place to change it.

**What it is today: one door, and it is honest about being thin.** The rule the agents actually
run is *something moved, and a want about it is worth a pass*, with the redundant impulse
absorbed by `adopt`'s patience one layer down. This file does not invent policy on top of that;
what it buys is that every reactive path goes through one function, so the three things the
records ask for next are each a change to this file alone:

- **#392** — deliberation must not run on the transport's callback thread. `wake` becomes a
  MARKER the deliberator drains on its own clock, rather than a call, and no caller changes.
- **bands, not raw values** — a self-telemetry belief that churns must be filtered here, where
  the churn is visible, rather than by each writer.
- **the projections** — *sensor unreachable*, *bus degraded* would be minted here, at the seam,
  which is where an infrastructure fact is allowed to become a belief at all
  (model-it-only-if-a-plan-would-branch-on-it).
"""

from __future__ import annotations

import logging

from . import execution

log = logging.getLogger("revision")


def wake(agent, want: str) -> str | None:
    """Something moved that this want is about — reconsider it. The intention that now stands
    for it, or None where the search proposed nothing.

    THE ONLY DOOR from a change to a deliberation pass. It is a direct call today, which means
    the pass runs on whatever thread noticed the change — the defect #392 records — and the
    fix lands here rather than in any caller.
    """
    return execution.pursue_for(agent, want)


def wake_for(agent, desire) -> str | None:
    """The same door, for a caller holding the want itself rather than its node — a host with a
    call to convene for, a keeper's tick walking everything the agent pursues."""
    return execution.pursue(agent, desire)
