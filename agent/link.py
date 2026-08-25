"""The link: how an agent reaches its society — a contract, implemented by a transport package.

**The kernel knows that an agent meets its society somewhere and speaks to it in channels; it
does not know that the somewhere is a broker.** Until this file the runtime held a paho
client, asked the world for `mqtt:MessageBus`, read `MQTT_USERNAME` off the environment and
watched paho's private thread — the last package word the kernel spoke, and the one the
ratchet held as debt with "the transport answering *where is the bus* itself" as what would
remove it. This is that: a `Link` says what the kernel needs of any transport, and the transport
package provides one that finds its own bus in the world, in its own words
(the-link-is-the-transports).

A link is not a driver. `agent.driver.Driver` is how sensing reaches ONE DEVICE over a
binding; a link is how the AGENT reaches everyone. The same package may ship both — MQTT does —
and the two are found the same way, through `PROVIDES`.
"""

from __future__ import annotations

import logging

from . import loader

log = logging.getLogger("link")


class Link:
    """What the kernel needs of any transport. Every method is the contract; none is provided."""

    @classmethod
    def where(cls, query):
        """This transport's link to the society the world describes, or None where the world
        states no such place — found by looking, in the transport's own vocabulary."""
        return None

    def connect(self, on_up, on_down, on_message) -> None:
        """Open the link. `on_up()` when it is; `on_down(reason)` when it is not; and
        `on_message(channel, payload: bytes)` for everything that arrives."""
        raise NotImplementedError

    def subscribe(self, channel: str) -> None:
        raise NotImplementedError

    def publish(self, channel: str, payload: bytes, retain: bool = False) -> None:
        raise NotImplementedError

    def alive(self) -> bool | None:
        """Whether the link's own machinery is still running — None where it cannot say. The
        watchdog believes a corpse over a stale flag, so a transport that can see its own
        thread should say so."""
        return None

    def stop(self) -> None:
        raise NotImplementedError


def link_for(query) -> Link:
    """The one link to the society this world describes, asked of every transport loaded.

    Refused rather than guessed where none answers or two do: a world that states no bus is
    a world nobody can join, and two are a routing question nothing here decides.
    """
    found = [link for cls in loader.links() if (link := cls.where(query)) is not None]
    if not found:
        raise RuntimeError("no transport loaded finds where this world's society meets — "
                           "has the world been seeded, and is the transport package present?")
    if len(found) > 1:
        raise RuntimeError(f"{len(found)} transports find a society to join — routing between "
                           "them is not implemented; state one")
    return found[0]
