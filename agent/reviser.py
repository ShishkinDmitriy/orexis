"""The REVISER: the belief-revision seam — what a change to the belief base is worth waking the
mind for.

Named apart from `review:Revision`, which is a different thing entirely: a record of a belief
re-picked, kept by the review capability. This is the seam a change passes through.

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
import threading

from . import execution

log = logging.getLogger("reviser")


class Reviser:
    """The seam, with a queue behind it: a change is NOTED here and a pass runs elsewhere.

    **Deliberation may not run on the thread that noticed the change** (#392). A reading
    arriving is reactive — milliseconds, atomic, no search — and the search it used to trigger
    ran inside the transport's callback, so one pass blocked every other message and a slow
    deliberator would have stalled the bus outright. The want is now marked and the pass runs
    on a thread of the mind's own, which is the whole of the fix and is why every reactive
    caller was routed through this file first.

    **Deduplicated by want, and that is the beginning of the filter.** Ten readings between two
    passes leave one mark, not ten; the record's *bands, not raw values* belongs here next, and
    the projections after it (layered-by-timescale-and-interruptibility).

    The words — a MARK, DRAINED on the agent's own clock — are the dictionary's:
    knowledge/domain/reviser.md, and knowledge/domain/row.md for the rows they keep apart.
    """

    def __init__(self, agent):
        self.agent = agent
        self._pending: dict[str, object] = {}   # want -> the desire, where the caller had one
        self._lock = threading.Condition()
        self._drain_lock = threading.Lock()     # one pass at a time, whoever asked for it
        self._worker: threading.Thread | None = None
        self._stopped = False

    # --- the door -----------------------------------------------------------------------

    def note(self, want: str, desire=None) -> None:
        """Something moved that this want is about. Returns at once, whatever it costs to
        reconsider it."""
        with self._lock:
            self._pending.setdefault(want, desire)
            if desire is not None:
                self._pending[want] = desire
            self._lock.notify_all()

    # --- the drain ----------------------------------------------------------------------

    def start(self) -> None:
        self._worker = threading.Thread(target=self._serve, name=f"{self.agent.id}-mind",
                                        daemon=True)
        self._worker.start()

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            self._lock.notify_all()

    def settle(self, timeout: float = 30.0) -> None:
        """Drain what is pending and return when it is done — the door a TEST knocks on.

        With a worker running this waits for it; without one it drains on a thread of its own
        and joins, which is deterministic for a caller that wants the consequences before it
        asserts, and is still never the delivering thread.
        """
        if self._worker is not None and self._worker.is_alive():
            with self._lock:
                self._lock.wait_for(lambda: not self._pending, timeout=timeout)
            with self._drain_lock:      # and until the pass in flight finishes
                pass
            return
        drain = threading.Thread(target=self._drain, name=f"{self.agent.id}-mind", daemon=True)
        drain.start()
        drain.join(timeout)

    def _serve(self) -> None:
        while True:
            with self._lock:
                self._lock.wait_for(lambda: self._pending or self._stopped)
                if self._stopped:
                    return
            self._drain()

    def _drain(self) -> None:
        """Every marked want, reconsidered. Never raises: the mind must not die of one want."""
        with self._drain_lock:
            while True:
                with self._lock:
                    if not self._pending:
                        self._lock.notify_all()
                        return
                    want, desire = next(iter(self._pending.items()))
                    del self._pending[want]
                try:
                    if desire is not None:
                        execution.pursue(self.agent, desire)
                    else:
                        execution.pursue_for(self.agent, want)
                except Exception as exc:
                    log.error("%s: could not reconsider %s: %s", self.agent.id,
                              want.rsplit("#", 1)[-1], exc)





def wake(agent, want: str) -> None:
    """Something moved that this want is about — mark it, and return.

    THE ONLY DOOR from a change to a deliberation pass, and it answers nothing: what the search
    decides is not knowable to the caller, because the caller is a handler and the search is
    not its to wait for. A caller that needs the consequence reads it where it lands — the
    ledger, the act it takes — not from here.
    """
    agent.reviser.note(want)


def wake_for(agent, desire) -> None:
    """The same door, for a caller holding the want itself rather than its node — a host with a
    call to convene for. The desire travels with the mark, because the caller derived it and
    the drain would have no way to find it again."""
    agent.reviser.note(desire.uri, desire)
