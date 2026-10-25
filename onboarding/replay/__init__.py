"""orexis-replay — a world's run drawn from its agents' history: every agent side by side, at every instant the
history holds, each thing drawn by the package that decides it.

  orexis-replay <world> [--since 1h] [--recording FILE ...] [--out FILE]

A REPLAY IS THE HISTORY DRAWN, AND NEVER A BELIEF (reflection-is-genesis-run-again-over-the-series). It reads what
each agent wrote of what it observed, planned, asked, laid and took, as its history part wrote it — from the agents'
history buckets with the installation's admin token, as `orexis-explain` reads them, or from a recording a world's
test made of a walk (`recorder`) — and opens no volume. What it shows is what each agent believed and did, so two
agents disagreeing about where a van stands is something a replay shows, not something it settles.

THE PACKAGE THAT DECIDES A THING DRAWS IT (a-replay-is-the-history-drawn-by-the-package-that-decides-it). The core
here is what every world shares and names no package's word: the instants, the agents to show — together on one
scene, or side by side — and the log (`core/`). Everything drawn is a `replay.tsx` beside the code or the documents it
draws — a domain's SCENE, the ground its world stands on (`domains/courier/replay.tsx`, the road and its vans), and a
package's LAYER, what it decided drawn on whatever scene there is (`agent/coordination/replay.tsx`, the holdings and the
conflicts) — each Preact components in TSX, held by `npm run check` to the contract `core/index.ts` states. A page
gathers the scene of every domain the world imports, the world's own where it has one, and every package's layer, and
esbuild bundles them with Preact into the one page (`build.mjs`), which opens offline.

A LONG RUN OF MANY AGENTS is thinned where nothing is lost: a sensor's reading the same as the one before it on the same
series is left out, since what a scene draws of it is its latest; and `--since` and `--until` take a stretch.

WHAT THE WORLD STATES of the things the history names is handed to the scenes as it is (`things`): every subject of
the world's common beliefs whose local name a point carries as a tag, its predicates by local name, a blank node
followed a few steps — what a contact is hosted by, what it is a sample of and the range its sensors declare.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import functools
import subprocess
import tempfile
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
DRAWING = "replay.tsx"
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

def data(world: str, history: dict[str, list[dict]], described: dict, until: datetime | None = None) -> dict:
    """What the page is handed: the world, its agents, every instant the history holds up to `until`, each agent's
    points as the store keeps them and thinned, and what the world states of the things they name. Every distinct
    measurement and tag set is a SERIES said once, and a point is its series, its milliseconds after the first instant
    and its fields — a long run of many agents says its tags once rather than per point (`core/pane.tsx`, `Raw`)."""
    points = {a: thinned([p for p in kept(ps) if until is None or p["time"] <= until]) for a, ps in sorted(history.items())}
    instants = sorted({p["time"] for ps in points.values() for p in ps})
    start = instants[0] if instants else datetime.fromtimestamp(0).astimezone()
    series: dict[tuple, int] = {}

    def ms(t: datetime) -> int:
        return round((t - start).total_seconds() * 1000)

    def of(p: dict) -> int:
        return series.setdefault((p["measurement"], tuple(sorted(p["tags"].items()))), len(series))
    written = {a: [[of(p), ms(p["time"]), p["fields"]] for p in ps] for a, ps in points.items()}
    return {"world": world, "agents": sorted(points), "start": start.isoformat(), "instants": [ms(t) for t in instants],
            "series": [[m, dict(tags)] for m, tags in series], "points": written, "things": described}


def thinned(points: list[dict]) -> list[dict]:
    """The points less every reading a sensor gave that is the same as the one before it on its series — the same
    measurement and tags, and the same fields — since a scene draws a reading's latest, which they do not change. Any
    other point is kept: a step said twice alike is two steps, and a set's members are said with their set."""
    last: dict[tuple, dict] = {}
    out = []
    for p in points:
        if "sensor" in p["tags"]:
            series = (p["measurement"], tuple(sorted(p["tags"].items())))
            if series in last and last[series] == p["fields"]:
                continue
            last[series] = p["fields"]
        out.append(p)
    return out


def page(drawn: dict, drawings_: list[Path]) -> str:
    """The replay as one HTML document holding everything it draws: the core, every drawing and Preact, bundled."""
    return ((HERE / "page.html").read_text()
            .replace("__TITLE__", f"{drawn['world']} replay")
            .replace("__SCRIPT__", _escaped(_bundle(tuple(drawings_), "browser")))
            .replace("__DATA__", json.dumps(drawn, separators=(",", ":")).replace("</", "<\\/")))


def headless(drawn: dict, drawings_: list[Path], *, pane: tuple[str, list[str], int] | None = None, log_of: list[str] | None = None):
    """One pane's SVG — `(scene, agents shown, instant)` — or the lines the agents' log holds, rendered by the page's own
    components with no browser (`core/headless.tsx`, under Node): what the tests hold the drawings to."""
    asked = {"data": drawn, **({"pane": {"scene": pane[0], "agents": pane[1], "at": pane[2]}} if pane else {"log": log_of})}
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as script:
        script.write(_bundle(tuple(drawings_), "node"))
    try:
        out = subprocess.run(["node", script.name], input=json.dumps(asked), capture_output=True, text=True)
    finally:
        Path(script.name).unlink()
    if out.returncode:
        raise RuntimeError(f"the headless replay failed: {out.stderr}")
    return out.stdout if pane else json.loads(out.stdout)


@functools.lru_cache(maxsize=8)
def _bundle(drawings_: tuple[Path, ...], platform: str) -> str:
    """The core and `drawings_` bundled by esbuild for `platform`, `browser` or `node`: an entry naming each drawing,
    written beside nothing, built by `build.mjs` from the toolchain `npm ci` installs."""
    imports = "\n".join(f'import * as d{n} from {json.dumps(str(p.resolve()))};' for n, p in enumerate(drawings_))
    every = "[" + ", ".join(f"d{n}" for n in range(len(drawings_))) + "]"
    if platform == "browser":
        entry = (f'import {{ mount }} from "@orexis/replay/app";\n{imports}\n'
                 f'mount({every}, JSON.parse(document.getElementById("data")!.textContent!), document.getElementById("replay")!);\n')
    else:
        entry = (f'import {{ run }} from "@orexis/replay/headless";\nimport {{ readFileSync }} from "node:fs";\n{imports}\n'
                 f'process.stdout.write(run({every}, JSON.parse(readFileSync(0, "utf8"))));\n')
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "entry.tsx").write_text(entry)
        out = Path(tmp) / "out.js"
        built = subprocess.run(["node", str(HERE / "build.mjs"), str(Path(tmp) / "entry.tsx"), str(out), platform],
                               capture_output=True, text=True)
        if built.returncode:
            raise RuntimeError(f"the replay would not build — is the toolchain installed (`npm ci`)?\n{built.stderr}")
        return out.read_text()


def _escaped(script: str) -> str:
    """A script as it may stand inside a `<script>` element: no `</script` in it ends the element early."""
    return script.replace("</script", "<\\/script")


def _shown(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PACKAGES.parent))
    except ValueError:
        return path.name


# ---------------------------------------------------------------- the command

def replay(world: str, since: str | None = None, recordings: list[Path] | None = None,
           until: datetime | None = None) -> tuple[dict, list[Path]]:
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
    return data(world, history, things(reading.world(here), history), until), drawings(here)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-replay",
        description="A world's run drawn from its agents' history — every agent side by side at every instant, each thing "
                    "drawn by the package that decides it — read from the history buckets or a walk's recording, never a belief.")
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--since", help="how far back: a Flux duration (1h, 30m) or an RFC 3339 instant; everything held where not given")
    p.add_argument("--until", help="an RFC 3339 instant: nothing after it is drawn")
    p.add_argument("--recording", action="append", type=Path, help="a recording a world's test made of a walk, read instead of the buckets")
    p.add_argument("--out", type=Path, help="where the page goes; <world>.replay.html where not given")
    args = p.parse_args()
    if args.since and not re.fullmatch(r"\d+(ms|s|m|h|d|w|mo|y)", args.since):
        try:
            datetime.fromisoformat(args.since.replace("Z", "+00:00"))
        except ValueError:
            raise SystemExit(f"orexis-replay: --since {args.since!r} is neither a Flux duration (1h) nor an RFC 3339 instant")
    out = args.out or Path(f"{args.world}.replay.html")
    until = datetime.fromisoformat(args.until.replace("Z", "+00:00")) if args.until else None
    drawn, scripts = replay(args.world, args.since, args.recording, until)
    out.write_text(page(drawn, scripts))
    log.info("%s: %d instant(s) of %s, drawn by %s — %s", args.world, len(drawn["instants"]),
             ", ".join(drawn["agents"]) or "no agent", ", ".join(_shown(s) for s in scripts) or "the core alone", out)


if __name__ == "__main__":
    main()
