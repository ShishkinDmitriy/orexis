"""The installation: what every world on this host shares, and the ports no world asserts.

  orexis-infra-compose        -> infra/compose.yaml, from infra/installation.ttl

**The installation is the deployment graph of what every world shares**
(knowledge/domain/onboarding/deployment.md), asserted in `infra/installation.ttl`: the series
store — its url, its organisation, its image, and the purposes it `onboarding:serves`, history and
metrics, each served by one store and kept as many days as `onboarding:retentionDays` says of it,
or for ever — the series view that draws it, and where a broker is allocated ports when its world
asserts none. It lives under `infra/`, and rule 3 holds of it
in the only way it can: nothing in it is true of one world.

**Asserted wins, derived completes** (`onboarding.derived`). A world may assert its broker's urls
in a deployment graph of its own, and an asserted url is what every tool is told. A broker no world
asserts a url for is ALLOCATED one: a port is unique across the host and only the installation sees
the host, so a world that does not say leaves the choice to the one reader that can make it safely.
`derive` allocates, and `infra/installation.derived.ttl` is what it wrote — the derived deployment
graph, committed, which `onboarding.mqtt.broker` reads beside a world's own and formats; nothing
downstream computes a port.

**The allocation is Python, not a rule.** It is a search — the lowest slot free of everything
asserted and allocated — and it keeps what was allocated before, both of which a SPARQL rule over
this engine does badly; it writes the same kind of graph a rule would.

**Stable, because it remembers.** An allocation already in the derived document is kept for as long
as its broker exists and asserts nothing, and a new one takes the lowest slot left, so a world added
later — whatever its name sorts as — never moves another's port. A board is flashed with its port.

**A collision is refused, never resolved.** Two brokers on one host and port, asserted or allocated,
or a broker on a service's: `derive` names both and writes nothing. A world asserting a port the
installation already allocated to another is refused too, rather than moving the other — the other
may be a board in a pot.

**The installation may name worlds; a world names nothing of the installation.** The derived
document names every broker it allocates, because the installation is the one reader that sees
every world anyway; `broker` asks it about the one broker a world's own society names, so no world
is told another's address.

**Never a credential.** A url carrying a user or a password is refused, asserted or not.

**`infra/compose.yaml` is written from it**, as a world's compose file is from the world: what each
service runs and where it answers comes from the document, and how it is run — the healthcheck, the
TLS settings, the user mapping, the secrets it is handed as files — is the template's.
"""

from __future__ import annotations

import argparse
import logging
from urllib.parse import urlparse

import pyoxigraph as ox

from agent.ontology import local_of as local
from agent.series import HISTORY, METRICS
from agent.store import DocumentRefused, graphs_of, rows

from . import derived, reading
from .reading import DEPLOYMENT, ONBOARDING
from .worlds import REPO_ROOT, world_dir, worlds

log = logging.getLogger("installation")

INSTALLATION = REPO_ROOT / "infra" / "installation.ttl"
DERIVATION = REPO_ROOT / "infra" / "installation.derived.ttl"
COMPOSE = REPO_ROOT / "infra" / "compose.yaml"

SERIES_STORE = ONBOARDING + "SeriesStore"
SERIES_VIEW = ONBOARDING + "SeriesView"
PUBLIC = "http://example.org/orexis#PublicGraph"
MQTT4SSN = "https://www.w3id.org/MQTT4SSN-Ontology#"
_SCHEMA_URL = "https://schema.org/url"
#  A scheme's port where a url states none — what each client library assumes, so a url stated
#  without one still collides with one stated with it.
DEFAULT_PORTS = {"mqtt": 1883, "mqtts": 8883, "http": 80, "https": 443}
_LAST_PORT = 65535

_SERVICE_Q = f"""
SELECT ?s ?url ?image ?organisation WHERE {{ ?s a <$kind> .
  OPTIONAL {{ ?s <{_SCHEMA_URL}> ?url }} OPTIONAL {{ ?s <{ONBOARDING}image> ?image }}
  OPTIONAL {{ ?s <{ONBOARDING}organisation> ?organisation }} }}"""
_POOL_Q = f"SELECT ?s ?url WHERE {{ ?s <{ONBOARDING}allocatesFrom> ?url }}"

#  WHICH STORE SERVES A PURPOSE, and how long the installation keeps the purpose's points. A purpose
#  is a concept the code names (`agent.series`), so the word for each is onboarding's vocabulary's,
#  and this is the one table from the agent's spelling of a purpose to it.
PURPOSE_OF = {HISTORY: ONBOARDING + "History", METRICS: ONBOARDING + "Metrics"}
_SERVES_Q = f"SELECT ?s WHERE {{ ?s a <{ONBOARDING}SeriesStore> ; <{ONBOARDING}serves> <$purpose> }}"
_RETENTION_Q = f"SELECT ?days WHERE {{ <$purpose> <{ONBOARDING}retentionDays> ?days }}"
_URLS_Q = f"SELECT ?s ?url WHERE {{ ?s <{_SCHEMA_URL}> ?url }}"

#  A WORLD'S BROKER, as its society names it, and the urls its own documents assert on it — over
#  its public graphs and its deployment graphs, since an assertion anywhere is an assertion.
_BROKERS_Q = f"SELECT ?b WHERE {{ ?b a <{MQTT4SSN}Broker> }}"
_ASSERTED_Q = f"SELECT ?b ?url WHERE {{ ?b a <{MQTT4SSN}Broker> ; <{_SCHEMA_URL}> ?url }}"


def _where(path) -> str:
    return str(path.relative_to(REPO_ROOT)) if path.is_relative_to(REPO_ROOT) else str(path)


def _store(with_derivation: bool = True) -> ox.Store:
    """The installation as onboarding reads it: the asserted document, and the derived one where it
    is on disk and asked for, each classified by how it arrived."""
    if not INSTALLATION.exists():
        raise SystemExit(f"no installation at {_where(INSTALLATION)} — the shared services are stated there")
    s = derived.store()
    try:
        derived.put(s, INSTALLATION, derived.ASSERTED)
        if with_derivation and DERIVATION.exists():
            derived.put(s, DERIVATION, derived.DERIVED)
    except DocumentRefused as refused:
        raise SystemExit(f"the installation does not load — {refused}")
    if not derived.graphs(s, DEPLOYMENT, derived.ASSERTED):
        raise SystemExit(f"the installation at {_where(INSTALLATION)} holds no onboarding:DeploymentGraph")
    return s


def _asserted(s: ox.Store, text: str) -> list[dict]:
    return rows(s, text, derived.graphs(s, DEPLOYMENT, derived.ASSERTED))


def _port(url) -> int | None:
    return url.port or DEFAULT_PORTS.get(url.scheme)


def _parsed(owner: str, text: str):
    url = urlparse(text)
    if url.username or url.password:
        raise SystemExit(f"a credential is stated in the url of {owner} — a deployment graph says where, "
                         "never what may be done there")
    return url


# ---------------------------------------------------------------- the services


def _service(kind: str, label: str, iri: str | None = None) -> dict:
    """The installation's one service of `kind` — or the one named `iri` — its url, and its image
    and organisation where stated. One, because each is handed to its readers as one address."""
    s = _store(with_derivation=False)
    found = [r for r in _asserted(s, _SERVICE_Q.replace("$kind", kind)) if iri is None or r["s"] == iri]
    named = sorted({r["s"] for r in found})
    if len(named) != 1:
        raise SystemExit(f"the installation states {len(named)} {label}s"
                         + (f" ({', '.join(named)})" if named else "") + " — it is told as one")
    values = {key: sorted({r[key] for r in found if r.get(key)}) for key in ("url", "image", "organisation")}
    for key, stated in values.items():
        if len(stated) > 1:
            raise SystemExit(f"the installation states two {key}s for its {label} {named[0]}: {', '.join(stated)}")
    if not values["url"]:
        raise SystemExit(f"the installation states no url for its {label} {named[0]}")
    _parsed(named[0], values["url"][0])
    return {"iri": named[0], **{key: (stated[0] if stated else None) for key, stated in values.items()}}


def series(purpose: str) -> tuple[str, str]:
    """(url, organisation) of the series store that `onboarding:serves` `purpose` — what
    `orexis-influx` mints the purpose's buckets in and what `orexis-compose` tells every agent under
    the purpose's keys. One, since an agent is told one store per purpose, and none is refused: a
    purpose the installation serves nowhere would be a sink every agent is told of and none has."""
    s = _store(with_derivation=False)
    found = _asserted(s, _SERVES_Q.replace("$purpose", PURPOSE_OF[purpose]))
    named = sorted({r["s"] for r in found})
    if len(named) != 1:
        raise SystemExit(f"the installation states {len(named)} onboarding:SeriesStores serving "
                         f"{local(PURPOSE_OF[purpose])}" + (f" ({', '.join(named)})" if named else "")
                         + " — an agent is told one store per purpose")
    store = _service(SERIES_STORE, "onboarding:SeriesStore", named[0])
    if not store["organisation"]:
        raise SystemExit(f"the installation states no onboarding:organisation for {store['iri']}")
    return store["url"], store["organisation"]


def retention(purpose: str) -> int | None:
    """How many days the installation keeps `purpose`'s points, `onboarding:retentionDays` on the
    purpose — or None where it states none, and the purpose's buckets keep everything."""
    days = {int(r["days"]) for r in _asserted(_store(with_derivation=False), _RETENTION_Q.replace("$purpose", PURPOSE_OF[purpose]))}
    if len(days) > 1:
        raise SystemExit(f"the installation states {len(days)} retentions for {local(PURPOSE_OF[purpose])}")
    return next(iter(days), None)


def view() -> dict:
    """The series view: its url and its image."""
    return _service(SERIES_VIEW, "onboarding:SeriesView")


# ---------------------------------------------------------------- a world's broker


def brokers_of(world_store: ox.Store) -> list[str]:
    """Every broker a world's society names, sorted."""
    return sorted({r["b"] for r in rows(world_store, _BROKERS_Q, graphs_of(world_store, PUBLIC))})


def asserted_on(world_store: ox.Store, broker: str) -> list[str]:
    """The urls a world's own documents assert on `broker`, sorted — none where it leaves them to
    the installation."""
    graphs = graphs_of(world_store, PUBLIC, DEPLOYMENT)
    return sorted(r["url"] for r in rows(world_store, _ASSERTED_Q, graphs) if r["b"] == broker)


def allocated(broker: str) -> list[str]:
    """The urls the derived deployment graph allocates `broker`, sorted — asked for by the IRI a
    world's society names it by, and nothing about anything else."""
    s = _store()
    return sorted(r["url"] for r in rows(s, _URLS_Q, derived.graphs(s, DEPLOYMENT, derived.DERIVED)) if r["s"] == broker)


# ---------------------------------------------------------------- the derivation


class _Taken:
    """Every host and port something holds, and what holds it; a second holder is refused."""

    def __init__(self):
        self.held: dict[tuple[str, int], tuple[str, str]] = {}

    def free(self, url) -> bool:
        return (url.hostname, _port(url)) not in self.held

    def take(self, owner: str, how: str, text: str) -> None:
        url = _parsed(owner, text)
        if not url.hostname or not _port(url):
            return
        key = (url.hostname, _port(url))
        if key in self.held and self.held[key][0] != owner:
            other, was = self.held[key]
            raise SystemExit(f"{key[0]}:{key[1]} is held by {other} ({was}) and by {owner} ({how}) — a "
                             "port is unique on its host; nothing was allocated")
        self.held[key] = (owner, how)


def _shifted(url, by: int) -> str:
    return url._replace(netloc=f"{url.hostname}:{url.port + by}").geturl()


def _pool(s: ox.Store, wanting: str | None = None) -> list:
    """The urls the installation allocates from, parsed — one pool, each url with a host and a port."""
    pool = [(r["s"], r["url"]) for r in _asserted(s, _POOL_Q)]
    if not pool:
        raise SystemExit(f"{wanting or 'a broker'} asserts no url and the installation states nothing to "
                         "allocate from (onboarding:allocatesFrom)")
    if len({owner for owner, _ in pool}) > 1:
        raise SystemExit(f"the installation states {len({o for o, _ in pool})} pools to allocate from")
    firsts = [_parsed(owner, url) for owner, url in pool]
    if not all(u.hostname and u.port for u in firsts):
        raise SystemExit("every url the installation allocates from states a host and a port")
    return firsts


def derive(remember: bool = True) -> dict[str, list[str]]:
    """{broker: urls} for every broker a world's society names and no world asserts a url for.

    Everything held first — the services, every asserted url, and, `remember`ing, every allocation
    the derived document already makes that still stands — and then each broker left, in the order
    its IRI sorts, at the lowest slot where every pool url raised by the slot is free. Refused where
    two things hold one port, and where the pool is needed and not stated."""
    s = _store(with_derivation=remember)
    taken = _Taken()
    for kind in (SERIES_STORE, SERIES_VIEW):
        for r in _asserted(s, _SERVICE_Q.replace("$kind", kind)):
            if r.get("url"):
                taken.take(r["s"], "the installation's service", r["url"])

    asserted: dict[str, list[str]] = {}
    for w in worlds():
        try:
            world_store = reading.world(world_dir(w))
        except DocumentRefused as refused:
            raise SystemExit(f"world {w!r} does not load, so no port can be allocated safely beside it — {refused}")
        for broker in brokers_of(world_store):
            asserted[broker] = asserted_on(world_store, broker)
    for broker, urls in sorted(asserted.items()):
        for url in urls:
            taken.take(broker, "asserted", url)

    out: dict[str, list[str]] = {}
    if remember:
        before: dict[str, list[str]] = {}
        for r in rows(s, _URLS_Q, derived.graphs(s, DEPLOYMENT, derived.DERIVED)):
            before.setdefault(r["s"], []).append(r["url"])
        for broker, urls in sorted(before.items()):
            if broker in asserted and not asserted[broker]:
                #  REMEMBERED, SO CHECKED: an allocation kept is one slot of the pool, or the
                #  document was edited by hand — which a derivation that keeps its own output
                #  would otherwise take as given, and the test holding it to a fresh one pass.
                firsts = _pool(s)
                if not any(sorted(urls) == sorted(_shifted(u, n) for u in firsts)
                           for n in range(_LAST_PORT - max(u.port for u in firsts) + 1)):
                    raise SystemExit(f"{_where(DERIVATION)} allocates {broker} {', '.join(sorted(urls))}, which is no "
                                     "slot of the installation's pool — it was edited, or the pool moved; "
                                     "assert the port in the world to pin it, or remove the allocation to re-derive it")
                for url in urls:
                    taken.take(broker, "allocated", url)
                out[broker] = sorted(urls)

    for broker in sorted(b for b, urls in asserted.items() if not urls and b not in out):
        firsts = _pool(s, broker)
        for n in range(_LAST_PORT - max(u.port for u in firsts) + 1):
            candidates = [urlparse(_shifted(u, n)) for u in firsts]
            if all(taken.free(u) for u in candidates):
                out[broker] = sorted(u.geturl() for u in candidates)
                for u in candidates:
                    taken.take(broker, "allocated", u.geturl())
                break
        else:
            raise SystemExit(f"no port is left to allocate {broker}")
    return {b: out[b] for b in sorted(out)}


_HEADER = """GENERATED by `orexis-onboard` from infra/installation.ttl and every world's own documents —
do not edit. What the installation allocated: a url on each broker whose world asserts none, at
the lowest slot of `onboarding:allocatesFrom` free of everything asserted and allocated before.
Kept across runs, so a world added later moves no other's port. An asserted url always wins: to
pin a broker's port, assert it in the world's own deployment graph (knowledge/domain/onboarding/deployment.md)."""


def derivation_text(allocation: dict[str, list[str]] | None = None) -> str:
    """The derived deployment graph's document for `allocation`, or as `derive` would write it now."""
    allocation = derive() if allocation is None else allocation
    statements = [(b, _SCHEMA_URL, ox.Literal(url)) for b, urls in allocation.items() for url in urls]
    return derived.text(DEPLOYMENT, statements, {"onboarding": ONBOARDING, "schema": "https://schema.org/"}, _HEADER)


def write_derivation() -> None:
    """Allocate, and write what was allocated beside the installation."""
    allocation = derive()
    DERIVATION.write_text(derivation_text(allocation))
    for broker, urls in allocation.items():
        log.info("  allocated %s  %s", broker, " ".join(urls))
    log.info("wrote %s", _where(DERIVATION))


# ---------------------------------------------------------------- infra/compose.yaml


def _published(url: str, label: str, schemes: tuple[str, ...]) -> int:
    parsed = urlparse(url)
    if parsed.scheme not in schemes:
        raise SystemExit(f"the installation's {label} is at {url}, and this template serves it over "
                         f"{' or '.join(schemes)}")
    return _port(parsed)


def render() -> str:
    store, shown = _service(SERIES_STORE, "onboarding:SeriesStore"), view()
    for service in (store, shown):
        if not service["image"]:
            raise SystemExit(f"the installation states no onboarding:image for {service['iri']}")
    if not (organisation := store["organisation"]):
        raise SystemExit(f"the installation states no onboarding:organisation for {store['iri']}")
    store_port = _published(store["url"], "series store", ("http",))
    view_port = _published(shown["url"], "series view", ("https",))
    return f"""# GENERATED by `orexis-infra-compose` from infra/installation.ttl beside it — do not edit.
#
# The shared services: the series store, and Grafana for eyeballing it. What each runs and where
# it answers — the image, the port, the organisation — is the installation document's; how each
# is run is this template's. Change the document and regenerate.
#
#   cd infra && podman compose up -d
#
# `compose.yaml` is the Compose Specification's own filename, so no -f is needed — the same
# invocation as a world (`cd world/<name> && podman compose up -d`).
#
# There is no triplestore. Each agent holds its own belief base inside its own container —
# see knowledge/decisions/where-the-belief-base-lives.md — so the only shared infrastructure
# left is the history and the view of it. All images have arm64 builds, so this runs on
# the Raspberry Pi as-is.
#
# The broker is NOT here. There is one per world, in world/<name>/compose.yaml, on the ports its
# world asserts or the installation allocates it — so a world's ACL derives from its own wiring
# alone and a new world disturbs nothing. See knowledge/domain/onboarding/onboarding.md.
#
# (What follows is kept because it explains why the image is built rather than pulled.)
# The broker image is built from infra/mosquitto/Containerfile. It is a custom image for
# one reason, recorded there: the official Alpine image cannot read a config file on this host
# by ANY means — bind mount, baked layer, or a file it writes itself — while a Debian build of
# the same package works first try. Without a config mosquitto binds localhost only, so the
# boards would never reach it.

name: orexis

# podman-compose puts every service in one pod by default, and a pod cannot combine with the
# per-service user-namespace mapping grafana needs ("--userns and --pod cannot be set together").
# That mapping is what lets grafana read its own 0600 TLS key, so the pod is what gives way.
# Ignored by docker compose, which does not create pods at all — the same escape the generated
# world compose files use.
x-podman:
  in_pod: false

services:
  influxdb:
    # PINNED in the installation, and load-bearing: see the comment on its image there.
    image: {store["image"]}
    ports: ["{store_port}:8086"]
    environment:
      DOCKER_INFLUXDB_INIT_MODE: setup
      DOCKER_INFLUXDB_INIT_ORG: {organisation}
      # The org must be born holding something, and this is NOT where readings go: every agent
      # writes to a bucket of its own, minted by `orexis-influx`. This one exists so setup mode
      # has an answer, and stays empty.
      DOCKER_INFLUXDB_INIT_BUCKET: genesis
    # The admin username, password and token — the only credential that opens every bucket.
    # Delivered as a file because a credential is in no document and in no agent's environment.
    env_file: [./secrets/admin.env]
    volumes:
      - influxdb-data:/var/lib/influxdb2
    healthcheck:
      test: ["CMD", "influx", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  grafana:
    image: {shown["image"]}
    ports: ["{view_port}:3000"]
    environment:
      # Anonymous viewing is OFF. Grafana legitimately spans every agent's bucket — it is the
      # operator's view, not a member's view of its neighbours — and that is exactly why it
      # must not be readable by anyone who can reach the port.
      GF_AUTH_ANONYMOUS_ENABLED: "false"
      GF_SERVER_PROTOCOL: https
      GF_SERVER_CERT_FILE: /etc/grafana/certs/grafana.crt
      GF_SERVER_CERT_KEY: /etc/grafana/certs/grafana.key
      # The organisation its datasource reads, interpolated by grafana/provisioning.
      INFLUX_ORG: {organisation}
    # Its admin password, and its own READ-ONLY Influx token. The admin token is deliberately
    # not here any more: a dashboard on the network should not be able to mint credentials.
    env_file: [./secrets/admin.env, ./secrets/grafana.env]
    # Grafana runs as uid 472 and opens its key after startup, so map your uid onto that one —
    # otherwise the 0600 key is unreadable and it falls back to plain HTTP. Same trap as the
    # broker's keyfile, different service.
    userns_mode: "keep-id:uid=472,gid=472"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
      - ./grafana/dashboards:/etc/grafana/dashboards:ro
      - ./grafana/certs:/etc/grafana/certs:ro
    depends_on: [influxdb]

volumes:
  influxdb-data:
  grafana-data:
"""


def generate() -> None:
    COMPOSE.write_text(render())
    log.info("wrote %s", _where(COMPOSE))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    argparse.ArgumentParser(
        prog="orexis-infra-compose",
        description="Write infra/compose.yaml from the installation document beside it. INFRA, "
                    "not onboarding: it takes no world.").parse_args()
    generate()


if __name__ == "__main__":
    main()
