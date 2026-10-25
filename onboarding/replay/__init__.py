"""orexis-replay — a world's run drawn from its agents' history: every agent side by side, at every instant the
history holds, each thing drawn by the package that decides it.

  orexis-replay <world> [--since 1h] [--recording FILE ...] [--out FILE]

A REPLAY IS THE HISTORY DRAWN, AND NEVER A BELIEF (reflection-is-genesis-run-again-over-the-series). It reads what
each agent wrote of what it observed, planned, asked, laid and took, as its history part wrote it — from the agents'
history buckets with the installation's admin token, as `orexis-explain` reads them, or from a recording a world's
test made of a walk (`recorder`) — and opens no volume. What it shows is what each agent believed and did, so two
agents disagreeing about where a van stands is something a replay shows, not something it settles.

THE PACKAGE THAT DECIDES A THING DRAWS IT (a-replay-is-the-history-drawn-by-the-package-that-decides-it). The core
here is what every world shares and names no package's word: the instants, a pane per agent and the log
(`core.js`). Everything drawn is a `replay.js` beside the code or the documents it draws — a domain's SCENE, the
ground its world stands on (`domains/courier/replay.js`, the road and its vans), and a package's LAYER, what it
decided drawn on whatever scene there is (`agent/coordination/replay.js`, the holdings and the conflicts). A page
gathers the scene of every domain the world imports, the world's own where it has one, and every package's layer,
as Preact components written with `htm`, vendored and inlined so the page needs no build and opens offline.

WHAT THE WORLD STATES of the things the history names is handed to the scenes as it is (`things`): every subject of
the world's common beliefs whose local name a point carries as a tag, its predicates by local name, a blank node
followed a few steps — what a contact is hosted by, what it is a sample of and the range its sensors declare.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pyoxigraph as ox

from agent import runtime
from agent.ontology import BELIEF, local_of
from agent.runtime import documents, read_with_imports
from agent.series import HISTORY, Sink
from agent.store import graphs_of

from .. import installation, reading
from ..compose import roster
from ..explain import read
from ..influx import _admin_token, bucket_name
from ..worlds import world_dir, worlds

log = logging.getLogger("replay")

HERE = Path(__file__).parent
PACKAGES = Path(runtime.__file__).parent
VENDOR = [HERE / "vendor" / name for name in ("preact.umd.js", "hooks.umd.js", "htm.umd.js")]
DRAWING = "replay.js"
_NUMBERS = {"http://www.w3.org/2001/XMLSchema#" + t for t in ("integer", "decimal", "double", "float", "int", "long")}
_DEPTH = 3


# ---------------------------------------------------------------- what draws a world

def drawings(here: Path) -> list[Path]:
    """Every drawing a replay of the world in `here` gathers: the scene of each domain it imports, the world's own, and
    each package's layer — in that order, so a layer stands on the scenes."""
    here = Path(here).resolve()
    read = {p.parent for p, _ in read_with_imports(documents(here))}
    out = sorted(d / DRAWING for d in read - {here} if (d / DRAWING).exists() and not d.is_relative_to(PACKAGES))
    if (here / DRAWING).exists():
        out.append(here / DRAWING)
    return out + sorted(PACKAGES.glob(f"*/{DRAWING}"))


def things(store: ox.Store, history: dict[str, list[dict]]) -> dict[str, dict]:
    """What the world in `store` states of every thing `history` names by a tag: each subject of the common beliefs
    whose local name a point carries, its predicates by local name, each a list of values — an IRI's local name, a
    number, a text, or a blank node followed as one more of these."""
    named = {v for ps in history.values() for p in ps for v in p.get("tags", {}).values()}
    about: dict[ox.Term, set] = defaultdict(set)
    for g in graphs_of(store, BELIEF, common=True):
        for q in store.quads_for_pattern(None, None, None, ox.NamedNode(g)):
            about[q.subject].add((q.predicate.value, q.object))

    def described(subject, depth: int) -> dict:
        out: dict[str, list] = defaultdict(list)
        for predicate, term in sorted(about.get(subject, ()), key=lambda pv: (pv[0], str(pv[1]))):
            out[local_of(predicate)].append(value(term, depth))
        return dict(out)

    def value(term, depth: int):
        if isinstance(term, ox.BlankNode):
            return described(term, depth + 1) if depth < _DEPTH else None
        if isinstance(term, ox.NamedNode):
            return local_of(term.value)
        return float(term.value) if term.datatype.value in _NUMBERS else term.value

    return {local_of(s.value): described(s, 0) for s in about if isinstance(s, ox.NamedNode) and local_of(s.value) in named}


# ---------------------------------------------------------------- what a walk records

def recorder(path: Path, agent_id: str) -> Sink:
    """A sink recording `agent_id`'s history to `path`, a JSON line a point, for
    `agent.series.install(HISTORY, ..., agent_id)` — what a world's test hands each agent it walks, so the walk can be
    replayed."""
    path = Path(path)

    def write(bucket, record):
        with path.open("a") as out:
            for p in record:
                out.write(json.dumps({"agent": agent_id, **p, "time": p["time"].isoformat() if p.get("time") else None}) + "\n")
    return Sink(HISTORY, agent_id, write)


def recording(*paths: Path) -> dict[str, list[dict]]:
    """Every agent's points in the recordings at `paths`, as their history part wrote them."""
    out: dict[str, list[dict]] = defaultdict(list)
    for path in paths:
        for line in Path(path).read_text().splitlines():
            if line.strip():
                p = json.loads(line)
                out[p.pop("agent")].append({**p, "time": datetime.fromisoformat(p["time"]) if p.get("time") else None})
    return dict(out)


def kept(points: list[dict]) -> list[dict]:
    """The points as the series store keeps them, in time order: one per measurement, tag set and instant, the last
    written — so a recording, which keeps every write, replays as the buckets would."""
    out = {}
    for p in points:
        if p.get("time") is not None:
            out[(p["measurement"], tuple(sorted(p["tags"].items())), p["time"])] = p
    return sorted(out.values(), key=lambda p: p["time"])


# ---------------------------------------------------------------- the page

def data(world: str, history: dict[str, list[dict]], described: dict) -> dict:
    """What the page is handed: the world, its agents, every instant the history holds, each agent's points as the
    store keeps them, and what the world states of the things they name."""
    points = {a: kept(ps) for a, ps in sorted(history.items())}
    instants = sorted({p["time"] for ps in points.values() for p in ps})
    return {"world": world, "agents": sorted(points), "instants": [t.isoformat() for t in instants],
            "points": {a: [{**p, "time": p["time"].isoformat()} for p in ps] for a, ps in points.items()},
            "things": described}


def page(drawn: dict, scripts: list[Path]) -> str:
    """The replay as one HTML document, holding everything it draws: the vendored Preact and htm, the core and every
    drawing, inlined, and nothing from elsewhere."""
    inlined = "\n".join(f"<script>/* {_shown(p)} */\n{_escaped(p.read_text())}\n</script>" for p in [*VENDOR, HERE / "core.js", *scripts])
    return ((HERE / "page.html").read_text()
            .replace("__TITLE__", f"{drawn['world']} replay")
            .replace("__SCRIPTS__", inlined)
            .replace("__DATA__", json.dumps(drawn, separators=(",", ":")).replace("</", "<\\/")))


def headless(drawn: dict, scripts: list[Path], *, pane: tuple[str, str, int] | None = None, log_of: str | None = None):
    """One pane's SVG — `(scene, agent, instant)` — or one agent's log lines, rendered by the page's own scripts with no
    browser (`headless.js`, under Node): what the tests hold the drawings to."""
    asked = {"scripts": [str(p) for p in scripts], "data": drawn, **({"pane": list(pane)} if pane else {"log": log_of})}
    out = subprocess.run(["node", str(HERE / "headless.js")], input=json.dumps(asked), capture_output=True, text=True, check=True)
    return out.stdout if pane else json.loads(out.stdout)


def _escaped(script: str) -> str:
    """A script as it may stand inside a `<script>` element: no `</script` in it ends the element early."""
    return script.replace("</script", "<\\/script")


def _shown(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PACKAGES.parent))
    except ValueError:
        return path.name


# ---------------------------------------------------------------- the command

def replay(world: str, since: str | None = None, recordings: list[Path] | None = None) -> tuple[dict, list[Path]]:
    """The replay of `world` and the drawings it gathers: from `recordings` where any are given, otherwise from every
    agent's history bucket."""
    here = world_dir(world)
    if recordings:
        history = recording(*recordings)
    else:
        token = _admin_token()
        url, org = installation.series(HISTORY)
        started = time.perf_counter()
        history = {a: read(url, org, token, bucket_name(world, a, HISTORY), since) for a in roster(world)}
        log.info("read %d point(s) in %.2f s", sum(map(len, history.values())), time.perf_counter() - started)
    return data(world, history, things(reading.world(here), history)), drawings(here)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-replay",
        description="A world's run drawn from its agents' history — every agent side by side at every instant, each thing "
                    "drawn by the package that decides it — read from the history buckets or a walk's recording, never a belief.")
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--since", help="how far back: a Flux duration (1h, 30m) or an RFC 3339 instant; everything held where not given")
    p.add_argument("--recording", action="append", type=Path, help="a recording a world's test made of a walk, read instead of the buckets")
    p.add_argument("--out", type=Path, help="where the page goes; <world>.replay.html where not given")
    args = p.parse_args()
    if args.since and not re.fullmatch(r"\d+(ms|s|m|h|d|w|mo|y)", args.since):
        try:
            datetime.fromisoformat(args.since.replace("Z", "+00:00"))
        except ValueError:
            raise SystemExit(f"orexis-replay: --since {args.since!r} is neither a Flux duration (1h) nor an RFC 3339 instant")
    out = args.out or Path(f"{args.world}.replay.html")
    drawn, scripts = replay(args.world, args.since, args.recording)
    out.write_text(page(drawn, scripts))
    log.info("%s: %d instant(s) of %s, drawn by %s — %s", args.world, len(drawn["instants"]),
             ", ".join(drawn["agents"]) or "no agent", ", ".join(_shown(s) for s in scripts) or "the core alone", out)


if __name__ == "__main__":
    main()
