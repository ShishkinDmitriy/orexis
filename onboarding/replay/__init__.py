"""orexis-replay — a world's run drawn from its agents' journals and observations: every agent side by side, at every
instant they hold, each thing drawn by the package that decides it.

  orexis-replay <world> [--since 1h] [--until T] [--journal AGENT=DIR ...] [--recording FILE ...] [--out FILE]
  orexis-replay <world> --live [--window 10m] [--port 8765]

A REPLAY IS WHAT THE AGENTS KEPT, DRAWN, AND NEVER A BELIEF (the-journal-is-the-agents-flight-recorder). It reads each
agent's journal — what it planned, asked, laid, concluded and took, as events in its packages' words — at the endpoint
the installation allocated it, or, for an agent that has stopped, its journal's store opened read-only (`--journal`);
and what it observed, from its history bucket with the installation's admin token as `orexis-explain` reads it, or
from a recording a world's test made of a walk (`recorder`). It opens no belief volume. What it shows is what each
agent believed and did, so two agents disagreeing about where a van stands is something a replay shows, not something
it settles.

EVERYTHING DRAWN IS A QUERY'S ROWS. The journals, the observations — each point made a `sosa:Observation` again, its
sensor, its feature and its property found by local name in the world's documents — and the world's documents
themselves are loaded into one store in memory, and every drawing's selects (`replay.<Query>.rq`, beside its
`replay.tsx`) are run once per agent: that agent's observations and the world's documents as the default graph, and
its journal's entries as the named graphs, so a select reads an event within its own graph (`GRAPH ?e`) and what the
world states around it. The rows go into the page.

THE PACKAGE THAT DECIDES A THING DRAWS IT (a-replay-is-the-history-drawn-by-the-package-that-decides-it). The core here
is what every world shares and names no package's word: the instants, the agents to show — together on one scene, or
side by side — and the log (`core/`). Everything drawn is a `replay.tsx` beside the code or the documents it draws, its
queries beside it — a domain's SCENE, the ground its world stands on (`domains/courier/replay.tsx`, the road and its
vans), and a package's LAYER, what it decided drawn on whatever scene there is (`agent/coordination/replay.tsx`, the
holdings and the conflicts) — each Preact components in TSX, held by `npm run check` to the contract `core/index.ts`
states. esbuild bundles them with Preact into the one page (`build.mjs`), which opens offline.

LIVE, the page is served on the host's loopback and asks again every few seconds for the last `--window` of the run, as
the agents' endpoints answer it, and follows the latest instant.
"""

from __future__ import annotations

import argparse
import functools
import json
import logging
import re
import subprocess
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pyoxigraph as ox

from agent import runtime
from agent.journal import ask
from agent.ontology import local_of
from agent.runtime import documents, read_with_imports
from agent.series import HISTORY, Sink

from .. import installation, reading
from ..compose import roster
from ..explain import _since, journal_of, read
from ..influx import _admin_token, bucket_name
from ..worlds import world_dir, worlds

log = logging.getLogger("replay")

HERE = Path(__file__).parent
PACKAGES = Path(runtime.__file__).parent
DRAWING = "replay.tsx"
_XSD = "http://www.w3.org/2001/XMLSchema#"
_NUMBERS = {_XSD + t for t in ("integer", "decimal", "double", "float", "int", "long")}
_SOSA = "http://www.w3.org/ns/sosa/"
_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
_RAW = ox.NamedNode("http://example.org/orexis/sensing#rawResult")


# ---------------------------------------------------------------- what draws a world

def drawings(here: Path) -> list[Path]:
    """Every drawing a replay of the world in `here` gathers: the scene of each domain it imports, the world's own, and
    each package's layer — in that order, so a layer stands on the scenes."""
    here = Path(here).resolve()
    read_ = {p.parent for p, _ in read_with_imports(documents(here))}
    out = sorted(d / DRAWING for d in read_ - {here} if (d / DRAWING).exists() and not d.is_relative_to(PACKAGES))
    if (here / DRAWING).exists():
        out.append(here / DRAWING)
    return out + sorted(PACKAGES.glob(f"*/{DRAWING}"))


def queries(drawings_: list[Path]) -> dict[str, str]:
    """Every select the drawings read, by name: `replay.<Query>.rq` beside each `replay.tsx`. Two drawings naming one
    query is refused, since `of(name)` would read both."""
    out: dict[str, str] = {}
    for drawing in drawings_:
        for path in sorted(drawing.parent.glob("replay.*.rq")):
            name = path.name[len("replay."):-len(".rq")]
            if name in out:
                raise SystemExit(f"two drawings read a query named {name!r}; {_shown(path)} is the second")
            out[name] = path.read_text()
    return out


# ---------------------------------------------------------------- what the agents kept

#  A JOURNAL'S ENTRIES, as quads, since an instant: every graph whose entry is at or after it.
_ENTRIES_Q = """
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?g ?s ?p ?o WHERE { GRAPH ?g { ?g prov:atTime ?t } %s GRAPH ?g { ?s ?p ?o } }"""


def entries(journal, since: datetime | None = None) -> list[ox.Quad]:
    """Every entry of `journal` — a store, or the url its endpoint answers at — since `since`, as quads."""
    text = _ENTRIES_Q % (f'FILTER(?t >= "{since.isoformat()}"^^<{_XSD}dateTime>)' if since else "")
    found = journal.query(text) if isinstance(journal, ox.Store) else ask(journal.rstrip("/") + "/sparql", text)
    return [ox.Quad(r["s"], r["p"], r["o"], r["g"]) for r in found]


class Run:
    """One store in memory holding everything a replay reads: the world's documents, and each agent's observations and
    journal entries, kept apart by graph — the dataset each agent's queries are asked over."""

    def __init__(self, world: ox.Store):
        self.store = ox.Store()
        self.store.extend(world.quads_for_pattern(None, None, None, None))
        self.world = [g for g in self.store.named_graphs()]
        self._named = _named(world)
        self.observed: dict[str, ox.NamedNode] = {}
        self.kept: dict[str, set] = defaultdict(set)

    def keep(self, agent: str, quads) -> None:
        """An agent's journal entries."""
        quads = list(quads)
        self.store.extend(quads)
        self.kept[agent] |= {q.graph_name for q in quads}

    def observe(self, agent: str, points: list[dict]) -> None:
        """An agent's observations, each point made a `sosa:Observation` again, in a graph of the agent's."""
        graph = self.observed.setdefault(agent, ox.NamedNode(f"urn:orexis:replay:observed:{agent}"))
        triples = [t for p in points for t in _observation(p, self._named)]
        self.store.extend([ox.Quad(t.subject, t.predicate, t.object, graph) for t in triples])

    def agents(self) -> list[str]:
        return sorted(set(self.observed) | set(self.kept))

    def rows(self, agent: str, text: str):
        """What `text` answers over `agent`'s dataset: the world and its observations as the default graph, its
        journal's entries named."""
        default = [*self.world, *([self.observed[agent]] if agent in self.observed else [])]
        return self.store.query(text, default_graph=default, named_graphs=sorted(self.kept.get(agent, ()), key=str) or [])


def _named(world: ox.Store) -> dict:
    """How a point's local names are made IRIs again: each sensor the world states by its local name, with every
    property it observes by its local name; and every subject by its local name."""
    sensors: dict[str, tuple[ox.NamedNode, dict[str, ox.NamedNode]]] = {}
    for q in world.quads_for_pattern(None, ox.NamedNode(_SOSA + "observes"), None, None):
        if isinstance(q.subject, ox.NamedNode) and isinstance(q.object, ox.NamedNode):
            sensors.setdefault(local_of(q.subject.value), (q.subject, {}))[1][local_of(q.object.value)] = q.object
    subjects = {local_of(q.subject.value): q.subject for q in world.quads_for_pattern(None, None, None, None)
                if isinstance(q.subject, ox.NamedNode)}
    return {"sensors": sensors, "subjects": subjects}


def _observation(p: dict, named: dict) -> list[ox.Triple]:
    """A point an observation was written as, made the observation again — or nothing, where its sensor or what it
    observes is stated nowhere in the world."""
    sensor = named["sensors"].get(p.get("tags", {}).get("sensor", ""))
    observed = sensor[1].get(p["measurement"]) if sensor else None
    feature = named["subjects"].get(p.get("tags", {}).get("feature", ""))
    if observed is None or feature is None or "value" not in p.get("fields", {}) or p.get("time") is None:
        return []
    o, at = ox.BlankNode(), p["time"] if p["time"].tzinfo else p["time"].replace(tzinfo=timezone.utc)
    out = [ox.Triple(o, _TYPE, ox.NamedNode(_SOSA + "Observation")), ox.Triple(o, ox.NamedNode(_SOSA + "madeBySensor"), sensor[0]),
           ox.Triple(o, ox.NamedNode(_SOSA + "observedProperty"), observed),
           ox.Triple(o, ox.NamedNode(_SOSA + "hasFeatureOfInterest"), feature),
           ox.Triple(o, ox.NamedNode(_SOSA + "hasSimpleResult"), ox.Literal(repr(float(p["fields"]["value"])), datatype=ox.NamedNode(_XSD + "double"))),
           ox.Triple(o, ox.NamedNode(_SOSA + "resultTime"), ox.Literal(at.isoformat(), datatype=ox.NamedNode(_XSD + "dateTime")))]
    if p["fields"].get("raw") is not None:
        out.append(ox.Triple(o, _RAW, ox.Literal(repr(float(p["fields"]["raw"])), datatype=ox.NamedNode(_XSD + "double"))))
    return out


# ---------------------------------------------------------------- what a walk records

def recorder(path: Path, agent_id: str) -> Sink:
    """A sink recording `agent_id`'s observations to `path`, a JSON line a point, for
    `agent.series.install(HISTORY, ..., agent_id)` — what a world's test hands each agent it walks, beside a journal of
    its own, so the walk can be replayed."""
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


def thinned(points: list[dict]) -> list[dict]:
    """The points less every reading a sensor gave that is the same as the one before it on its series — the same
    measurement and tags, and the same fields — since a scene draws a reading's latest, which they do not change."""
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


# ---------------------------------------------------------------- the page

def run_of(world: ox.Store, journals: dict[str, object], points: dict[str, list[dict]],
           since: datetime | None = None) -> Run:
    """The run of every agent: its journal — a store, a url or quads — and its observation points, kept and thinned,
    each since `since`."""
    run = Run(world)
    for agent, journal in journals.items():
        run.keep(agent, journal if isinstance(journal, list) else entries(journal, since))
    for agent, ps in points.items():
        run.observe(agent, thinned(kept(ps)))
    return run


def _value(term):
    if isinstance(term, ox.Literal):
        if term.datatype.value in _NUMBERS:
            number = float(term.value)
            return int(number) if number.is_integer() and term.datatype.value != _XSD + "double" else number
        if term.datatype.value == _XSD + "boolean":
            return term.value == "true"
        return term.value
    return term.value if isinstance(term, ox.NamedNode) else f"_:{term.value}"


def data(world: str, run: Run, asked: dict[str, str], until: datetime | None = None, live: bool = False) -> dict:
    """What the page is handed: the world, its agents, every instant a row holds up to `until`, and each agent's rows of
    every query — each query's name and variables said once, and a row its query, its milliseconds after the first
    instant, or none where it binds no `?at`, and its values (`core/pane.tsx`, `Raw`)."""
    names = sorted(asked)
    answered: dict[str, list[tuple[int, datetime | None, list]]] = {}
    variables: dict[str, list[str]] = {}
    for agent in run.agents():
        out = []
        for n, name in enumerate(names):
            found = run.rows(agent, asked[name])
            variables[name] = [v.value for v in found.variables]
            for r in found:
                at = r["at"] if "at" in variables[name] else None
                t = datetime.fromisoformat(at.value) if at is not None else None
                if t is not None and until is not None and t > until:
                    continue
                out.append((n, t, [_value(r[v]) if r[v] is not None else None for v in variables[name]]))
        answered[agent] = out
    instants = sorted({t for rs in answered.values() for _, t, _ in rs if t is not None})
    start = instants[0] if instants else datetime.fromtimestamp(0, timezone.utc)

    def ms(t: datetime | None) -> int | None:
        return None if t is None else round((t - start).total_seconds() * 1000)
    return {"world": world, "agents": run.agents(), "start": start.isoformat(), "instants": [ms(t) for t in instants],
            "queries": [[name, variables.get(name, [])] for name in names],
            "rows": {a: [[n, ms(t), vs] for n, t, vs in rs] for a, rs in answered.items()}, "live": live}


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

def _points(world: str, since: str | None) -> dict[str, list[dict]]:
    token = _admin_token()
    url, org = installation.series(HISTORY)
    return {a: read(url, org, token, bucket_name(world, a, HISTORY), since) for a in roster(world)}


def _journals(world: str, stopped: dict[str, Path]) -> dict[str, object]:
    """Each agent's journal: the store a stopped one left, opened read-only, or the endpoint allocated it."""
    out: dict[str, object] = {}
    for agent in roster(world):
        if agent in stopped:
            out[agent] = ox.Store.read_only(str(stopped[agent]))
        elif (url := journal_of(world, agent)) is not None:
            out[agent] = url
        else:
            log.warning("%s is allocated no journal — run `orexis-onboard %s`", agent, world)
    return out


def _reachable(journals: dict[str, object], since: datetime | None) -> dict[str, list[ox.Quad]]:
    """Each journal's entries, an agent whose endpoint answers nothing said in the log and left out."""
    out = {}
    for agent, journal in journals.items():
        try:
            out[agent] = entries(journal, since)
        except OSError as exc:
            log.warning("%s's journal at %s answers nothing (%s): is it running? A stopped one is read with --journal",
                        agent, journal, exc)
    return out


def replay(world: str, since: str | None = None, recordings: list[Path] | None = None, until: datetime | None = None,
           stopped: dict[str, Path] | None = None, live: bool = False) -> tuple[dict, list[Path]]:
    """The replay of `world` and the drawings it gathers: every agent's journal and its observations — from
    `recordings` where any are given, otherwise from its history bucket."""
    here = world_dir(world)
    drawn = drawings(here)
    started = time.perf_counter()
    points = recording(*recordings) if recordings else _points(world, since)
    journals = _reachable(_journals(world, stopped or {}), _since(since))
    run = run_of(reading.world(here), journals, points)
    log.info("read %d observation(s) and %d entr(ies) in %.2f s", sum(map(len, points.values())),
             sum(len(r) for r in run.kept.values()), time.perf_counter() - started)
    return data(world, run, queries(drawn), until, live), drawn


def server(world: str, window: str, port: int) -> ThreadingHTTPServer:
    """The page, live, to be served on the host's loopback at `port`: answering `data.json` with the last `window` of
    the run as the agents' endpoints and the series store answer it now, asked at most every two seconds."""
    drawn = drawings(world_dir(world))
    script = _bundle(tuple(drawn), "browser")
    cache: dict[str, tuple[float, bytes]] = {}

    def now() -> bytes:
        if "data" not in cache or time.monotonic() - cache["data"][0] > 2:
            cache["data"] = (time.monotonic(), json.dumps(replay(world, window, live=True)[0], separators=(",", ":")).encode())
        return cache["data"][1]

    class Asked(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split("?")[0] == "/data.json":
                body, kind = now(), "application/json"
            else:
                body = ((HERE / "page.html").read_text().replace("__TITLE__", f"{world} live")
                        .replace("__SCRIPT__", _escaped(script)).replace("__DATA__", now().decode().replace("</", "<\\/"))).encode()
                kind = "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):                              # noqa: A002 — the base class's name
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Asked)


def serve(world: str, window: str, port: int) -> None:
    """The page, live, until the process is stopped."""
    live = server(world, window, port)
    log.info("%s, live over the last %s: http://127.0.0.1:%d/", world, window, live.server_address[1])
    live.serve_forever()


def _duration(text: str) -> str:
    if not re.fullmatch(r"\d+(ms|s|m|h|d|w|mo|y)", text):
        try:
            datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            raise SystemExit(f"orexis-replay: {text!r} is neither a Flux duration (1h) nor an RFC 3339 instant")
    return text


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-replay",
        description="A world's run drawn from its agents' journals and observations — every agent side by side at every "
                    "instant, each thing drawn by the package that decides it — never a belief.")
    p.add_argument("world", help="which world. Available: " + ", ".join(worlds()))
    p.add_argument("--since", type=_duration, help="how far back: a Flux duration (1h, 30m) or an RFC 3339 instant; everything held where not given")
    p.add_argument("--until", help="an RFC 3339 instant: nothing after it is drawn")
    p.add_argument("--journal", action="append", default=[], metavar="AGENT=DIR",
                   help="a stopped agent's journal store, opened read-only, instead of its endpoint")
    p.add_argument("--recording", action="append", type=Path, help="a recording a world's test made of a walk, read instead of the buckets")
    p.add_argument("--out", type=Path, help="where the page goes; <world>.replay.html where not given")
    p.add_argument("--live", action="store_true", help="serve the page on the host's loopback, following the run as it goes")
    p.add_argument("--window", type=_duration, default="10m", help="live, how much of the run the page holds: a Flux duration")
    p.add_argument("--port", type=int, default=8765, help="live, the port the page is served at")
    args = p.parse_args()
    if args.live:
        serve(args.world, args.window, args.port)
        return
    stopped = dict(j.split("=", 1) for j in args.journal)
    out = args.out or Path(f"{args.world}.replay.html")
    until = datetime.fromisoformat(args.until.replace("Z", "+00:00")) if args.until else None
    drawn, scripts = replay(args.world, args.since, args.recording, until, {a: Path(d) for a, d in stopped.items()})
    out.write_text(page(drawn, scripts))
    log.info("%s: %d instant(s) of %s, drawn by %s — %s", args.world, len(drawn["instants"]),
             ", ".join(drawn["agents"]) or "no agent", ", ".join(_shown(s) for s in scripts) or "the core alone", out)


if __name__ == "__main__":
    main()
