"""Talking to Fuseki — the one place that knows the HTTP shape of the belief base.

Everything else (world, beliefs, sensed writes, seeding, validation) goes through this, and
takes a `query` callable rather than a URL, so the readers stay pure and testable without a
triplestore.

There are **two doors**, because Jena's per-graph access control is read-only:

- the **secured** door, where an agent authenticates as itself and can read the shared graphs
  plus its own beliefs. Another agent's beliefs return nothing — the store refuses, rather
  than the code politely not asking.
- the **plain** door, for writes: every agent may update (each writes its own readings), and
  only admin may read or replace whole graphs, which is what seeding and validation need.

See knowledge/decisions/belief-base-isolation.md for what this does and does not buy.
"""

from __future__ import annotations

from typing import Callable

import requests

# A SPARQL SELECT -> the SPARQL-JSON results dict. The seam every reader is written against.
QueryFn = Callable[[str], dict]

# Sent with every query. This is the ONLY set a query may use — rdflib silently pre-binds
# common prefixes and Fuseki does not, so anything relying on that works in a test and 400s
# against the real store. `test_store.py` holds the codebase to this list.
PREFIXES = """
PREFIX ag:   <http://example.org/agora#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""

DECLARED = frozenset(
    line.split()[1].rstrip(":") for line in PREFIXES.splitlines() if line.startswith("PREFIX")
)


def bindings(results: dict) -> list[dict]:
    """The rows of a SPARQL-JSON result, flattened to {var: value-string}."""
    rows = results.get("results", {}).get("bindings", [])
    return [{k: v.get("value") for k, v in row.items()} for row in rows]


class Store:
    """Read/write access to the belief base, as one identity.

    `url` is the secured service (reads); `write_url` is the plain one (updates, and — for
    admin — whole-graph reads and replacement). They are the same underlying store.
    """

    def __init__(self, url: str, user: str = "admin", password: str = "admin",
                 write_url: str | None = None):
        base = url.rstrip("/")
        write = (write_url or base).rstrip("/")
        self.query_url = base + "/sparql"
        self.update_url = write + "/update"
        self.data_url = write + "/data"
        self.admin_query_url = write + "/sparql"  # unfiltered; admin only
        self.auth = (user, password)

    def query(self, sparql: str) -> dict:
        """Read as myself. What comes back is what I am allowed to see."""
        return self._query(self.query_url, sparql)

    def query_all(self, sparql: str) -> dict:
        """Read unfiltered, through the plain door. Admin only — seeding and validation."""
        return self._query(self.admin_query_url, sparql)

    def _query(self, url: str, sparql: str) -> dict:
        resp = requests.get(
            url,
            params={"query": PREFIXES + sparql},
            headers={"Accept": "application/sparql-results+json"},
            auth=self.auth,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def update(self, sparql: str) -> None:
        resp = requests.post(
            self.update_url, data={"update": PREFIXES + sparql}, auth=self.auth, timeout=10
        )
        resp.raise_for_status()

    def put_graph(self, graph_iri: str, ttl: str) -> None:
        """Replace a named graph with the given Turtle (Graph Store Protocol PUT)."""
        resp = requests.put(
            self.data_url,
            params={"graph": graph_iri},
            data=ttl.encode("utf-8"),
            headers={"Content-Type": "text/turtle"},
            auth=self.auth,
            timeout=15,
        )
        resp.raise_for_status()

    def get_graph(self, graph_iri: str) -> str:
        """A graph's contents, or empty if it does not exist yet.

        A graph nobody has written to is not an error: on a fresh install `:sensed` is absent
        until the first reading, and validation should say so rather than crash.
        """
        resp = requests.get(
            self.data_url,
            params={"graph": graph_iri},
            headers={"Accept": "text/turtle"},
            auth=self.auth,
            timeout=10,
        )
        if resp.status_code == 404:
            return ""
        resp.raise_for_status()
        return resp.text


def _secret_for(agent_id: str) -> str | None:
    """An agent's own store credential, kept beside the signing keys and never committed."""
    from .config import PROJECT_ROOT

    path = PROJECT_ROOT.parent / "keys" / "fuseki" / f"{agent_id}.pw"
    return path.read_text().strip() if path.exists() else None


def world_url(env: Callable[[str, str], str], world: str) -> str:
    """Where ONE world's belief base lives.

    A world is a belief base — each has its own isolated dataset, so seeding one cannot
    overwrite another and readings stay with the world they were observed in. This is the only
    thing that has to know the naming convention; agents are handed the finished URL, because
    an agent knows its own id and nothing else about where it lives.
    """
    base = env("FUSEKI_BASE", "http://localhost:3030").rstrip("/")
    return f"{base}/ds-{world}"


def from_env(env: Callable[[str, str], str], agent_id: str | None = None,
             world: str | None = None) -> Store:
    """The store as seen by one identity.

    With an agent id, it connects as that agent and sees only what the world entitles it to.
    Without one — seeding, validation — it connects as admin. With a world, it targets that
    world's dataset; without one it takes FUSEKI_URL, which is what an agent is given.
    """
    read_url = world_url(env, world) if world else env("FUSEKI_URL", "http://localhost:3030/ds")
    write_url = env("FUSEKI_WRITE_URL", read_url.rstrip("/") + "-rw")

    if agent_id:
        secret = _secret_for(agent_id)
        if secret:
            return Store(read_url, agent_id, secret, write_url=write_url)
        # No credential yet: fall back to admin so an un-provisioned deployment still runs,
        # and say so, because this is the difference between enforced and assumed privacy.
        import logging

        logging.getLogger("store").warning(
            "%s has no store credential (run agora-acl) — connecting as admin, so its "
            "isolation from other agents' beliefs is NOT enforced", agent_id)

    # Admin has no entry in the secured registry — by design, since that door exists to
    # constrain agents. So admin reads through the plain door, where it sees everything.
    return Store(write_url, "admin", env("FUSEKI_PASSWORD", "admin"), write_url=write_url)
