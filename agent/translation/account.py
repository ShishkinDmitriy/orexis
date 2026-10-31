"""`account`: what the agent says of itself for a person, read off its store by the selects each package ships.

**AN ACCOUNT IS SELECTS, NOT CODE.** Every package that has something to say of itself ships an `account.rq` beside
its ontology — sensing the latest reading of each sensor, execution the intentions standing — a SELECT whose first
comment line is the section's title and whose `# reads:` line names the kinds of graph it reads, which are handed to
it as the default graph, as every reader is handed its graphs (a-reader-states-the-kinds-it-reads). The account is
each loaded package's rows, a line per row, under its title, asked when a person asks and stored nowhere: telemetry,
never a belief (an-agent-gives-an-account-of-itself-and-the-model-only-reads-it).
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from agent.ontology import local_of
from agent.store import NAMESPACES, graphs_of, rows

AGENT = Path(__file__).resolve().parent.parent
QUERY = "account.rq"
_READS = re.compile(r"^#\s*reads:\s*(.+)$", re.M)
_TITLE = re.compile(r"^#\s*(?!reads:)(.+)$", re.M)
_INSTANT = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d)(:\d\d(\.\d+)?)?(Z|[+-]\d\d:\d\d)?$")


def _queries(packages) -> list[tuple[str, str, list[str], str]]:
    """Every account select the `packages` ship, in their order: the package, the title, the kinds it reads, the text."""
    out = []
    for package in packages:
        path = AGENT / package / QUERY
        if path.exists():
            text = path.read_text()
            title = _TITLE.search(text)
            reads = _READS.search(text)
            kinds = [_expand(k.strip()) for k in reads.group(1).split(",")] if reads else []
            out.append((package, title.group(1).strip() if title else package, kinds, text))
    return out


def _expand(curie: str) -> str:
    prefix, _, name = curie.partition(":")
    return NAMESPACES[prefix] + name if prefix in NAMESPACES else curie


def _said(value: str) -> str:
    """A value as a person reads it: an IRI by its local name, an instant to the minute."""
    if value.startswith("http://") or value.startswith("https://") or value.startswith("urn:"):
        return local_of(value)
    found = _INSTANT.match(value)
    return found.group(1).replace("T", " ") + (" UTC" if found.group(4) in ("Z", "+00:00") else "") if found else value


def account(stores, packages, me: str, now: datetime) -> str:
    """The agent's account as it stands at `now`: who and when, then each package's section, a line per row over every
    store the agent holds, or that there is nothing to say yet."""
    sections = []
    for _, title, kinds, text in _queries(packages):
        lines, seen = [], set()
        for store in {id(s): s for s in stores if s is not None}.values():
            graphs = graphs_of(store, *kinds) if kinds else []
            if kinds and not graphs:
                continue
            for row in rows(store, text, graphs):
                line = ", ".join(f"{name}: {_said(value)}" for name, value in row.items() if value is not None)
                if line and line not in seen:
                    seen.add(line)
                    lines.append(line)
        if lines:
            sections.append(f"{title}:\n" + "\n".join(f" - {line}" for line in lines))
    head = f"{local_of(me)} at {now.strftime('%Y-%m-%d %H:%M')} UTC"
    return head + "\n" + ("\n".join(sections) if sections else "nothing to say yet")
