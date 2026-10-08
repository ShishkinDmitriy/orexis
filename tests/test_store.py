"""Every query must stand on its own prefixes.

This exists because of a bug that passed every test and failed in production: a query used
`rdfs:subClassOf*`, which the store's prefixes did not declare. rdflib pre-binds rdfs and the
store the agent ran on did not, so the tests were green while every bidder failed on every offer.

The lesson is not "remember to add the prefix" — it is that the test harness was more forgiving
than the store, so a whole class of query bug could not be caught by testing behaviour. This
checks the text instead: a SPARQL text in the agent, the operator's tools, the simulator, a
domain or a world uses only names `agent.store` declares, or declares them itself with `PREFIX`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from agent.store import DECLARED

REPO_ROOT = Path(__file__).resolve().parents[1]

# `?s orexis:foo ?o` — a prefixed name in a query. Deliberately loose; a false positive here is
# a prefix somebody should have declared anyway.
_PREFIXED = re.compile(r"(?<![\w:<#/-])([a-zA-Z][\w.-]*):[a-zA-Z_]")
_DECLARED_HERE = re.compile(r"PREFIX\s+([A-Za-z][\w.-]*)?\s*:", re.I)

# A text is only interesting if it is SPARQL at all: a query keyword opening a line, as every
# query here is written, and never a docstring that merely mentions one.
_SPARQL = re.compile(r"^\s*(PREFIX|SELECT|INSERT|DELETE|CONSTRUCT|ASK|WITH)\b", re.M)


def _shipped(tree: str, *suffixes: str) -> list[Path]:
    return sorted(p for suffix in suffixes for p in (REPO_ROOT / tree).rglob(f"*{suffix}")
                  if "__pycache__" not in p.parts and "tests" not in p.parts and "secrets" not in p.parts)


# Every tree that may carry a SPARQL text, as a NAMED group. Twice, moving files silently emptied
# one of these globs and took cases off this guard without failing anything; a guard that quietly
# stops guarding is worse than none, so each group is asserted non-empty below.
_GROUPS = {
    "agent": _shipped("agent", ".py", ".ttl"),
    "onboarding": _shipped("onboarding", ".py"),
    "simulation": _shipped("simulation", ".py"),
    "domains": _shipped("domains", ".ttl"),
    "worlds": _shipped("world", ".ttl", ".trig"),
}
_SOURCES = sorted({p for group in _GROUPS.values() for p in group})


@pytest.mark.parametrize("group", sorted(_GROUPS))
def test_every_source_group_is_still_found(group):
    """The guard on the guard: a tree that moved runs fewer cases below, and passes."""
    assert _GROUPS[group], f"no source found for the {group!r} group — its path has moved"


def _queries(text: str) -> list[str]:
    """Triple-quoted blocks that look like SPARQL."""
    return [block for block in re.findall(r'"""(.*?)"""', text, re.S) if _SPARQL.search(block)]


#  THE TOKEN THE SELF RETIRED. Every text about the agent was handed `$me`, threaded by hand from the
#  one identifier a process is told into every query that mentioned it, because nothing in the store
#  said who the agent was. The boot says it now — `<agent> a orexis:Self`, once, in a graph of the
#  agent's own (knowledge/domain/kernel/self.md) — so a text asks `?me a orexis:Self` and is bound
#  nothing. A `$me` left anywhere would be a text somebody must bind, and `store.bind` refuses a
#  token nobody binds only when the text is RUN; this refuses it when it is WRITTEN.
_ME_TOKEN = re.compile(r"\$me\b")


@pytest.mark.parametrize("path", _SOURCES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_text_is_handed_who_the_agent_is(path):
    found = [n for n, line in enumerate(path.read_text().splitlines(), 1) if _ME_TOKEN.search(line)]
    assert not found, (
        f"{path.relative_to(REPO_ROOT)} carries a `$me` token at line(s) {found}: a text asks the self, "
        f"`?me a orexis:Self`, and nothing hands it the agent.")


@pytest.mark.parametrize("path", _SOURCES, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_queries_use_only_declared_prefixes(path):
    for query in _queries(path.read_text()):
        used = {m.group(1) for m in _PREFIXED.finditer(query)}
        own = set(_DECLARED_HERE.findall(query))
        undeclared = used - DECLARED - own - {"http", "https", "urn", "file", "mailto"}
        assert not undeclared, (
            f"{path.relative_to(REPO_ROOT)} sends a query using {sorted(undeclared)}, which neither "
            f"the store declares nor the text does. A harness that pre-binds it would let this pass.")
