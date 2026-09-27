"""Derived documents: what onboarding completes of what the asserted documents leave out.

**Asserted wins, derived completes.** A sovereign asserts what they mean to decide — a world's
broker url, the installation's services — and leaves out what they do not care to; onboarding
derives the rest, and a derivation never overrides an assertion. What it derives is written as a
document, TTL like every other, and that document is the middle layer: a compose file, a broker's
config, an agent's environment and a board's `config.h` only FORMAT what the asserted and derived
graphs say together, so no renderer computes anything and every derived fact is one a reviewer
reads in a diff. A derived document is committed, and a test holds it equal to a fresh derivation,
as a committed compose file is held to what `orexis-compose` renders.

**How it arrived is the loader's to say.** A derived document says `<> a <kind>` as any document
does and nothing about its arrival, which a document may not state (`agent.store.checked`); the
reader here puts it in with `orexis:arrivedBy orexis:Derived`, as the boot classifies the
closure it derives and belief the revisions its rules conclude, and an asserted document with
`orexis:Asserted`. A reader then asks by kind and arrival, never by a file's name.

**Rules where a rule is easy, Python where it is not.** A derivation that is a join is a SPARQL
rule in onboarding's documents; one that searches — the lowest free port, keeping what was
allocated before — is Python writing into the same kind of graph. Either way the output is this
module's: `text` writes it, `put` reads it back. Nothing here is about ports.
"""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox

from agent.ontology import CATALOGUE_GRAPH
from agent.store import document, put_document, rows, update

OREXIS = "http://example.org/orexis#"
ASSERTED = OREXIS + "Asserted"
DERIVED = OREXIS + "Derived"

_GRAPHS_Q = """
SELECT ?g WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a <$kind> ; orexis:arrivedBy <$arrival> } }
ORDER BY ?g"""


def store() -> ox.Store:
    """An empty store holding a catalogue and nothing else, for documents to be put in."""
    s = ox.Store()
    update(s, f"INSERT DATA {{ GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph , orexis:Graph }} }}")
    return s


def put(into: ox.Store, path: Path, arrival: str) -> list[str]:
    """The document at `path` put into `into`, every graph it holds classified as arriving by
    `arrival` — `ASSERTED` for what a sovereign wrote, `DERIVED` for what onboarding did."""
    return put_document(into, document(path), arrival=arrival)


def graphs(of: ox.Store, kind: str, arrival: str) -> list[str]:
    """Every graph in `of` the catalogue types `kind` and says arrived by `arrival`, sorted."""
    return [r["g"] for r in rows(of, _GRAPHS_Q.replace("$kind", kind).replace("$arrival", arrival))]


def text(kind: str, statements, prefixes: dict[str, str], header: str) -> str:
    """A derived document: `header` as comment lines, the prefixes, `<> a <kind>`, then every
    statement — (subject IRI, predicate IRI, object term) — grouped by subject and predicate and
    sorted, so a derivation that did not change writes the same bytes."""
    def name(iri: str) -> str:
        for prefix, ns in sorted(prefixes.items()):
            if iri.startswith(ns) and iri[len(ns):].replace("_", "").isalnum():
                return f"{prefix}:{iri[len(ns):]}"
        return f"<{iri}>"

    grouped: dict[str, dict[str, set[str]]] = {}
    for subject, predicate, obj in statements:
        grouped.setdefault(subject, {}).setdefault(predicate, set()).add(str(obj))
    lines = [f"#  {line}".rstrip() for line in header.strip().splitlines()]
    lines += [""] + [f"@prefix {p}: <{ns}> ." for p, ns in sorted(prefixes.items())] + [""]
    lines += [f"<> a {name(kind)} .    # this document is one graph, and this is what it is", ""]
    for subject in sorted(grouped):
        said = [f"{name(p)} {' , '.join(sorted(objs))}" for p, objs in sorted(grouped[subject].items())]
        lines.append(f"{name(subject)} " + " ;\n    ".join(said) + " .")
    return "\n".join(lines) + "\n"
