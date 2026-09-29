"""The HTTP driver: the agent's side of the web, answering the transport family's `Transport`
contract from the WoT Thing Description's words.

**WHAT THE WORLD SAYS AND WHAT FOLLOWS.** A sensor is this member's when it is the agent's and a
`td:Thing` with a `td:hasForm`; it is read at the form's `hctl:hasTarget`, a URI template (RFC 6570,
simple variables) whose `{name}`s are filled from the literals said of the `schema:geo` of what the
sensor is hosted by, by local name. A template with a variable nothing fills is not fetched, and
says so: a world whose location is kept in its `secrets/` and was not given it still boots.

**A RESPONSE BECOMES OBSERVATIONS THROUGH SENSING, AND THE MEMBER KNOWS NO CODEC.** `handle` takes the
sensor as its channel and the body as bytes, and calls sensing's `received`, which reads the codec,
the pointers and the scaling off the sensor's own binding — a forecast service's series among them.

**IT POLLS.** `start` asks the runtime to fetch each of its sensors at once and then every
`ssn-system:Frequency` the sensor states (sensing's `cadence_of`, the one read of SSN's word), once
where it states none: the runtime does the waiting and the member says what it waits for
(a-package-starts-itself). A fetch runs on a thread of its own, one at a time per sensor, and the
body is submitted to the runtime as a job that `handle`s it.
"""

from __future__ import annotations

import logging
import re
import threading
import urllib.parse
import urllib.request

from agent import clock
from agent.ontology import PUBLIC, local_of
from agent.sensing.cadence import cadence_of
from agent.store import answer, graphs_of, rows
from agent.transport.transport import Transport

log = logging.getLogger("http")

#  HOW LONG ONE FETCH MAY TAKE, in real seconds.
TIMEOUT_S = 30.0

#  EVERY SENSOR OF THE AGENT'S THAT IS A THING WITH A FORM.
_MINE_Q = """
SELECT DISTINCT ?sensor WHERE {
  $me orexis:actsFor ?subject . ?subject schema:containedInPlace* ?host .
  ?sensor sosa:isHostedBy/(sosa:isSampleOf)? ?host ; td:hasForm ?form }
ORDER BY ?sensor"""

#  WHERE A SENSOR IS READ: its form's target.
_TARGET_Q = "SELECT ?target WHERE { $sensor td:hasForm ?form . ?form hctl:hasTarget ?target } ORDER BY ?target"

_REACHES_Q = "ASK { $device td:hasForm ?form }"

#  WHAT A TEMPLATE'S VARIABLES ARE FILLED FROM: every literal said of the geo of what the sensor is hosted by.
_WHERE_Q = """
SELECT ?property ?value WHERE {
  $sensor sosa:isHostedBy ?host . ?host schema:geo ?geo . ?geo ?property ?value . FILTER(isLiteral(?value)) }"""

_VARIABLE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def fill(template: str, values: dict[str, str]) -> str | None:
    """The URI a template names with its simple `{name}` variables filled from `values`, each
    percent-encoded; None where one names a value that is not there."""
    if any(name not in values for name in _VARIABLE.findall(template)):
        return None
    return _VARIABLE.sub(lambda m: urllib.parse.quote(str(values[m.group(1)]), safe=""), template)


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "orexis-agent"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:        # noqa: S310 — a world's own target
        return response.read()


class Http(Transport):
    """One agent's side of the web: what the container needs of this transport, answered from the
    world in the Thing Description's words, over a `client` that fetches a URI's body."""

    def __init__(self, me: str, deliver=None, client=None, spawn=None):
        self.me = me
        self.deliver = deliver or (lambda *message: None)
        self.client = client or _get
        self.spawn = spawn or (lambda work: threading.Thread(target=work, daemon=True).start())
        self._lock = threading.Lock()
        self._fetching: set[str] = set()

    @classmethod
    def connect(cls, me: str, deliver=None, *, environ=None, client=None) -> "Http":
        """The agent's side of the web, up: nothing to connect to until a sensor is due, and no
        credential, since what it reads is public."""
        log.info("%s reads the web", local_of(me))
        return cls(me, deliver, client)

    def start(self, runtime) -> None:
        """Begin as every member does, and poll each of its sensors: at once, then every frequency
        the sensor states."""
        super().start(runtime)
        for sensor in self.open(runtime.beliefs):
            every = cadence_of(runtime.beliefs, sensor)
            poll = lambda sensor=sensor: self.sense_now(runtime.beliefs, sensor) or []
            if every is None:
                runtime.submit(poll)
            else:
                runtime.every(every, poll)

    def open(self, store) -> list[str]:
        """The sensors of the agent's this member reads."""
        sensors = [r["sensor"] for r in rows(store, _MINE_Q, graphs_of(store, PUBLIC), me=self.me)]
        log.info("%s reads %s over HTTP", local_of(self.me), [local_of(s) for s in sensors] or "nothing")
        return sensors

    def reaches(self, store, device: str) -> bool:
        return bool(answer(store, _REACHES_Q, graphs_of(store, PUBLIC), device=device)["boolean"])

    def sense_now(self, store, sensor: str) -> None:
        """Fetch what `sensor` reads, on a thread of its own, unless it is being fetched already."""
        with self._lock:
            if sensor in self._fetching:
                return
        public = graphs_of(store, PUBLIC)
        targets = [r["target"] for r in rows(store, _TARGET_Q, public, sensor=sensor)]
        values = {local_of(r["property"]): r["value"] for r in rows(store, _WHERE_Q, public, sensor=sensor)}
        url = fill(targets[0], values) if targets else None
        if url is None:
            log.warning("%s: %s names what nothing here says — is the place's location in the world's secrets/?",
                        local_of(sensor), targets[0] if targets else "no target")
            return
        with self._lock:
            self._fetching.add(sensor)

        def fetch():
            try:
                body = self.client(url)
                self.deliver(sensor, body, clock.now())
            except Exception as exc:                                    # noqa: BLE001 — the web fails
                log.warning("%s: %s would not answer: %s", local_of(sensor), url.split("?", 1)[0], exc)
            finally:
                with self._lock:
                    self._fetching.discard(sensor)

        self.spawn(fetch)

    def handle(self, store, channel: str, payload: bytes, at, *, memo=None) -> list[tuple[str | None, str]]:
        """What `channel`, a sensor of this member's, read: handed to sensing's `received`, each graph
        written answered with the sensor."""
        from agent.sensing.received import received
        return [(channel, graph) for graph in received(store, self.me, channel, payload, at, memo=memo)]
