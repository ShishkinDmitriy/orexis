"""Talking to Fuseki — the one place that knows the HTTP shape of the belief base.

Everything else (world, beliefs, sensed writes, seeding, validation) goes through this, and
takes a `query` callable rather than a URL, so the readers stay pure and testable without a
triplestore.
"""

from __future__ import annotations

from typing import Callable

import requests

# A SPARQL SELECT -> the SPARQL-JSON results dict. The seam every reader is written against.
QueryFn = Callable[[str], dict]

PREFIXES = """
PREFIX ag:   <http://example.org/agora#>
PREFIX sosa: <http://www.w3.org/ns/sosa/>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
"""


def bindings(results: dict) -> list[dict]:
    """The rows of a SPARQL-JSON result, flattened to {var: value-string}."""
    rows = results.get("results", {}).get("bindings", [])
    return [{k: v.get("value") for k, v in row.items()} for row in rows]


class Store:
    """Read/write access to the Fuseki dataset."""

    def __init__(self, url: str, user: str = "admin", password: str = "admin"):
        base = url.rstrip("/")
        # secoresearch/fuseki serves queries at /ds/sparql (not /ds/query).
        self.query_url = base + "/sparql"
        self.update_url = base + "/update"
        self.data_url = base + "/data"
        self.auth = (user, password)

    def query(self, sparql: str) -> dict:
        resp = requests.get(
            self.query_url,
            params={"query": PREFIXES + sparql},
            headers={"Accept": "application/sparql-results+json"},
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
            timeout=10,
        )
        if resp.status_code == 404:
            return ""
        resp.raise_for_status()
        return resp.text


def from_env(env: Callable[[str, str], str]) -> Store:
    return Store(env("FUSEKI_URL", "http://localhost:3030/ds"), "admin",
                 env("FUSEKI_PASSWORD", "admin"))
