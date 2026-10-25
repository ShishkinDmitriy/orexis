"""orexis-replay — a world's run drawn from its agents' history: every agent side by side, at every instant the
history holds, as the views its domains state draw it.

  orexis-replay <world> [--since 1h] [--recording FILE ...] [--out FILE]

A REPLAY IS THE HISTORY DRAWN, AND NEVER A BELIEF (reflection-is-genesis-run-again-over-the-series). It reads what
each agent wrote of what it observed, planned, asked, laid and took, as its history part wrote it — from the agents'
history buckets with the installation's admin token, as `orexis-explain` reads them, or from a recording a world's
test made of a walk (`recorder`) — and opens no volume. What it shows is what each agent believed and did, so two
agents disagreeing about where a van stands is something a replay shows, not something it settles.

A GENERIC CORE AND A DOMAIN'S VIEWS (knowledge/domain/onboarding/view.md). The core is the same for every world: a
scrubber over every instant, a pane per agent, and beside it what the agent did at that instant, said in the
history's own tags. A domain brings how its history is DRAWN, as documents and no code: a graph of
`onboarding:ViewGraph` beside its ontology states views of a kind this tool renders, each saying in the domain's own
words which of the history's points place what on it. A world whose domains state none is drawn by the core alone.

ONE KIND TODAY, THE GRID (`onboarding:Grid`): two axes of whole numbers, each saying what places a thing on it in
each kind of point — the key predicate a holding is said under, the property a fix and an offset observe, and the
parameter a step moves a thing by. At each instant, for each agent:
- FIXED, each thing its own fixes place, at its latest;
- SEEN, each sample its offsets place from the thing hosting it, as that thing was fixed — drawn as the thing it is
  a sample of where it is one, and not at all where its latest offset lies outside the range its sensor declares;
- PLANNED, the steps of the latest plan published for each want, and IN FLIGHT, a step taken and not yet answered;
- ASKED, SAID and FORESEEN, the latest set of each coordination said, a holding drawn whole where its period holds;
- and its CONFLICTS, the latest it concluded.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import time
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pyoxigraph as ox

from agent.ontology import BELIEF, local_of
from agent.series import HISTORY, Sink
from agent.store import graphs_of, rows

from . import installation, reading
from .compose import roster
from .influx import _admin_token, bucket_name
from .explain import read
from .worlds import world_dir, worlds

log = logging.getLogger("replay")

VIEW = "http://example.org/orexis/onboarding#ViewGraph"
GRID = "http://example.org/orexis/onboarding#Grid"

#  EVERY GRID A VIEW GRAPH STATES, with what places a thing on each of its two axes in each kind of point.
_GRIDS_Q = """
SELECT ?grid ?label ?side ?holds ?fixes ?offsets ?moves WHERE {
  ?grid a onboarding:Grid ; ?side ?axis . VALUES ?side { onboarding:across onboarding:down }
  OPTIONAL { ?grid rdfs:label ?label } OPTIONAL { ?axis onboarding:holds ?holds } OPTIONAL { ?axis onboarding:fixes ?fixes }
  OPTIONAL { ?axis onboarding:offsets ?offsets } OPTIONAL { ?axis onboarding:moves ?moves } } ORDER BY ?grid"""
#  EVERY SAMPLE AND THE THING HOSTING IT, and the thing it is a sample of where it is one; and every sensor's range.
_SAMPLES_Q = """SELECT ?s ?host ?of WHERE { ?s a sosa:Sample ; sosa:isHostedBy ?host . OPTIONAL { ?s sosa:isSampleOf ?of } }"""
_RANGES_Q = """SELECT ?sensor ?least ?most WHERE { ?sensor ssn-system:hasSystemCapability ?c . ?c ssn-system:hasSystemProperty ?r .
  ?r a ssn-system:MeasurementRange ; schema:minValue ?least ; schema:maxValue ?most }"""


# ---------------------------------------------------------------- what the world states

@dataclass(frozen=True)
class Axis:
    """What places a thing on one axis, in each kind of point, by local name: the key predicate a holding is said
    under, the property a fix and an offset observe, and the parameter a step moves a thing by."""
    holds: str | None = None
    fixes: str | None = None
    offsets: str | None = None
    moves: str | None = None


@dataclass(frozen=True)
class Grid:
    name: str
    label: str
    across: Axis
    down: Axis


@dataclass(frozen=True)
class Things:
    """What the world states of the things a history names, by local name: the thing hosting each sample, the thing
    each is a sample of, and the range each sensor declares."""
    hosts: dict = field(default_factory=dict)
    of: dict = field(default_factory=dict)
    ranges: dict = field(default_factory=dict)


def views(store: ox.Store) -> list[Grid]:
    """Every grid the view graphs in `store` state."""
    sides: dict[str, dict] = defaultdict(dict)
    labels = {}
    for r in rows(store, _GRIDS_Q, graphs_of(store, VIEW)):
        labels[r["grid"]] = r.get("label") or local_of(r["grid"])
        sides[r["grid"]][local_of(r["side"])] = Axis(*(local_of(r[k]) if r.get(k) else None for k in ("holds", "fixes", "offsets", "moves")))
    return [Grid(local_of(g), labels[g], s["across"], s["down"]) for g, s in sides.items() if {"across", "down"} <= set(s)]


def things(store: ox.Store) -> Things:
    """What the world in `store` states of samples and sensors, as its common beliefs say it."""
    common = graphs_of(store, BELIEF, common=True)
    out = Things()
    for r in rows(store, _SAMPLES_Q, common):
        out.hosts[local_of(r["s"])] = local_of(r["host"])
        if r.get("of"):
            out.of[local_of(r["s"])] = local_of(r["of"])
    for r in rows(store, _RANGES_Q, common):
        out.ranges[local_of(r["sensor"])] = (float(r["least"]), float(r["most"]))
    return out


# ---------------------------------------------------------------- what a walk records

def recorder(path: Path, agent: str) -> Sink:
    """A sink recording `agent`'s history to `path`, a JSON line a point, for `agent.series.install(HISTORY, ..., agent)`
    — what a world's test hands each agent it walks, so the walk can be replayed."""
    path = Path(path)

    def write(bucket, record):
        with path.open("a") as out:
            for p in record:
                out.write(json.dumps({"agent": agent, **p, "time": p["time"].isoformat() if p.get("time") else None}) + "\n")
    return Sink(HISTORY, agent, write)


def recording(*paths: Path) -> dict[str, list[dict]]:
    """Every agent's points in the recordings at `paths`, as their history part wrote them."""
    out: dict[str, list[dict]] = defaultdict(list)
    for path in paths:
        for line in Path(path).read_text().splitlines():
            if line.strip():
                p = json.loads(line)
                out[p.pop("agent")].append({**p, "time": datetime.fromisoformat(p["time"]) if p.get("time") else None})
    return dict(out)


# ---------------------------------------------------------------- the frames

class _Series:
    """One agent's points of one kind in time order, asked what the latest is at or before an instant."""

    def __init__(self, points):
        self.points = sorted(points, key=lambda p: p["time"])
        self.times = [p["time"] for p in self.points]

    def latest(self, at):
        i = bisect_right(self.times, at)
        return self.points[i - 1] if i else None

    def at_latest(self, at) -> list[dict]:
        """Every point at the latest instant at or before `at`: one set, said whole."""
        last = self.latest(at)
        if last is None:
            return []
        i = bisect_right(self.times, last["time"])
        j = i
        while j > 0 and self.times[j - 1] == last["time"]:
            j -= 1
        return self.points[j:i]


def _number(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def frames(history: dict[str, list[dict]], grids: list[Grid], world: Things) -> dict:
    """The replay of `history`, every agent's points by its id: every instant the history holds, what each agent did at
    each — said in the history's own tags — and for each grid what it showed of each agent at each instant."""
    points = {a: _kept(ps) for a, ps in history.items()}
    instants = sorted({p["time"] for ps in points.values() for p in ps})
    agents = sorted(points)
    drawn = {m for g in grids for axis in (g.across, g.down) for m in (axis.fixes, axis.offsets) if m}
    out = {"instants": [t.isoformat() for t in instants], "agents": agents,
           "log": {a: _log(points[a], instants, drawn) for a in agents}, "grids": []}
    for g in grids:
        frames_of = {a: [_grid_frame(points[a], g, world, t) for t in instants] for a in agents}
        cells = [c for fs in frames_of.values() for f in fs for layer in f.values() if isinstance(layer, list)
                 for c in layer if isinstance(c, dict) and "x" in c]
        box = ([min(c["x"] for c in cells), min(c["y"] for c in cells), max(c["x"] for c in cells), max(c["y"] for c in cells)]
               if cells else [0, 0, 0, 0])
        out["grids"].append({"name": g.name, "label": g.label, "box": box, "frames": frames_of})
    return out


def _kept(points: list[dict]) -> list[dict]:
    """The points as the series store keeps them, in time order: one per measurement, tag set and instant, the last
    written — so a recording, which keeps every write, replays as the buckets would."""
    kept = {}
    for p in points:
        if p.get("time") is not None:
            kept[(p["measurement"], tuple(sorted(p["tags"].items())), p["time"])] = p
    return sorted(kept.values(), key=lambda p: p["time"])


def _grid_frame(points: list[dict], g: Grid, world: Things, at: datetime) -> dict:
    """What `g` shows of one agent's `points` at `at`."""
    by: dict[str, list[dict]] = defaultdict(list)
    for p in points:
        if p["time"] <= at:
            by[p["measurement"]].append(p)
    fixed = _fixed(by, g, at)
    frame = {"fixed": [{"x": x, "y": y, "name": f} for f, (x, y) in sorted(fixed.items())],
             "seen": _seen(by, g, world, fixed, at), "planned": [], "flight": [], "conflicts": []}
    #  THE LATEST PLAN PUBLISHED FOR EACH WANT, and the steps taken and not yet answered.
    plans: dict[str, list[dict]] = defaultdict(list)
    for p in by.get("Plan", ()):
        plans[p["tags"].get("want", "")].append(p)
    walked = defaultdict(list)                      # when each step was answered, by what it fills and takes
    for p in by.get("Step", ()):
        if "landed" in p["fields"]:
            walked[_filling(p["tags"])].append(p["time"])
    for want, ps in sorted(plans.items()):
        for p in _Series(ps).at_latest(at):
            x, y = _number(p["tags"].get(g.across.moves)), _number(p["tags"].get(g.down.moves))
            if any(t >= p["time"] for t in walked.get(_filling(p["tags"]), ())):
                continue                            # walked since the plan was published
            if x is not None and y is not None:
                frame["planned"].append({"x": x, "y": y, "order": int(p["tags"].get("order", 0)), "want": want})
    steps: dict[tuple, dict] = {}
    for p in by.get("Step", ()):                      # a step is in flight where its latest point is its taking
        key = tuple(sorted(p["tags"].items()))
        if key not in steps or steps[key]["time"] <= p["time"]:
            steps[key] = p
    for p in steps.values():
        if p["fields"].get("taken") is True:
            x, y = _number(p["tags"].get(g.across.moves)), _number(p["tags"].get(g.down.moves))
            if x is not None and y is not None:
                frame["flight"].append({"x": x, "y": y, "action": p["tags"].get("action", "")})
    #  WHAT COORDINATION SAID LAST OF EACH SET: the header says when, the members at that instant are the set.
    heads: dict[tuple, list[dict]] = defaultdict(list)
    for p in by.get("Holdings", ()):
        heads[(p["tags"].get("origin"), p["tags"].get("peer"), p["tags"].get("constraint"))].append(p)
    members: dict[tuple, list[dict]] = defaultdict(list)
    for p in by.get("Holding", ()):
        members[(p["tags"].get("origin"), p["tags"].get("peer"), p["tags"].get("constraint"), p["time"])].append(p)
    for key, hs in sorted(heads.items(), key=lambda kv: tuple(str(k) for k in kv[0])):
        head = _Series(hs).latest(at)
        for p in members.get((*key, head["time"]), ()):
            x, y = _number(p["fields"].get(g.across.holds)), _number(p["fields"].get(g.down.holds))
            if x is None or y is None:
                continue
            start, end = p["fields"].get("from") or None, p["fields"].get("until") or None
            frame.setdefault(key[0], []).append({
                "x": x, "y": y, "name": p["tags"].get("thing", ""), "peer": key[1],
                "now": (start is None or datetime.fromisoformat(start) <= at) and (end is None or at < datetime.fromisoformat(end)),
                "taken": bool(p["fields"].get("taken"))})
    concluded = _Series(by.get("Conflicts", ())).latest(at)
    if concluded is not None:
        for p in by.get("Conflict", ()):
            if p["time"] == concluded["time"]:
                frame["conflicts"].append({**{k: p["tags"].get(k, "") for k in ("peer", "constraint")},
                                           **{k: p["fields"].get(k) for k in ("standing", "silent", "round", "won_by")}})
    return frame


def _filling(tags: dict) -> tuple:
    """A step's filling as its point's tags say it — the action, the want and the values it takes — whether the point
    is of the plan or of the step taken."""
    return tuple(sorted((k, v) for k, v in tags.items() if k not in ("plan", "order")))


def _fixed(by: dict, g: Grid, at: datetime) -> dict[str, tuple[float, float]]:
    """Each feature its fixes place, at its latest reading on each axis."""
    out = {}
    across, down = _latest_by_feature(by.get(g.across.fixes, ())), _latest_by_feature(by.get(g.down.fixes, ()))
    for f in sorted(set(across) & set(down)):
        out[f] = (across[f]["fields"]["value"], down[f]["fields"]["value"])
    return out


def _seen(by: dict, g: Grid, world: Things, fixed: dict, at: datetime) -> list[dict]:
    """Each sample its latest offsets place from the thing hosting it as it is fixed, where both lie inside the range
    each one's sensor declares."""
    out = []
    across, down = _latest_by_feature(by.get(g.across.offsets, ())), _latest_by_feature(by.get(g.down.offsets, ()))
    for f in sorted(set(across) & set(down)):
        host = world.hosts.get(f)
        if host not in fixed:
            continue
        a, d = across[f], down[f]
        if not all(_inside(world, p) for p in (a, d)):
            continue
        out.append({"x": fixed[host][0] + a["fields"]["value"], "y": fixed[host][1] + d["fields"]["value"],
                    "name": world.of.get(f, f), "sample": f})
    return out


def _inside(world: Things, p: dict) -> bool:
    least, most = world.ranges.get(p["tags"].get("sensor", ""), (float("-inf"), float("inf")))
    return least <= p["fields"]["value"] <= most


def _latest_by_feature(points) -> dict[str, dict]:
    out = {}
    for p in points:
        f = p["tags"].get("feature")
        if f and (f not in out or out[f]["time"] <= p["time"]):
            out[f] = p
    return out


# ---------------------------------------------------------------- the core's log

def _log(points: list[dict], instants: list[datetime], drawn: set[str]) -> list[list]:
    """What the agent did, a line per thing at the instant it did it, in the history's own tags: every point but the
    observations a view draws, a set said as one line."""
    index = {t: i for i, t in enumerate(instants)}
    out: list[list] = []
    sets: dict[tuple, list[dict]] = defaultdict(list)
    for p in points:
        m = p["measurement"]
        if m in drawn:
            continue
        if m in ("Holdings", "Conflicts"):
            continue                                # a set's header: said below where the set is empty
        if m in ("Holding", "Conflict", "Plan"):
            sets[(m, p["time"], p["tags"].get("origin"), p["tags"].get("peer"), p["tags"].get("plan"))].append(p)
            continue
        out.append([index[p["time"]], _line(p)])
    heads = {(p["measurement"], p["time"], p["tags"].get("origin"), p["tags"].get("peer")): p
             for p in points if p["measurement"] in ("Holdings", "Conflicts")}
    for (m, t, origin, peer, plan), ps in sets.items():
        if m == "Plan":
            steps = sorted(ps, key=lambda p: int(p["tags"].get("order", 0)))
            out.append([index[t], f"published a plan for {steps[0]['tags'].get('want', '?')}: "
                                  + " → ".join(_step(p["tags"]) for p in steps)])
        elif m == "Holding":
            out.append([index[t], f"{origin}: " + ", ".join(_held(p) for p in ps)])
        else:
            out.append([index[t], "; ".join(_conflict(p) for p in ps)])
    for (m, t, origin, peer), head in heads.items():
        if head["fields"].get("count") == 0:
            out.append([index[t], f"{origin} nothing" + (f" of {peer}" if peer else "") if m == "Holdings" else "no conflict"])
    return sorted(out, key=lambda e: e[0])


def _step(tags: dict) -> str:
    said = {k: v for k, v in tags.items() if k not in ("action", "want", "plan", "order")}
    return f"{tags.get('action', '?')}(" + ", ".join(f"{k}={v}" for k, v in sorted(said.items())) + ")"


def _held(p: dict) -> str:
    values = {k: v for k, v in p["fields"].items() if k not in ("from", "until", "taken")}
    return f"{p['tags'].get('thing', '?')} " + " ".join(f"{k}={_shown(v)}" for k, v in sorted(values.items()))


def _conflict(p: dict) -> str:
    f = p["fields"]
    return (f"conflict with {p['tags'].get('peer')} over {p['tags'].get('constraint')}: "
            + ("standing" if f.get("standing") else "not standing") + (", silent" if f.get("silent") else "")
            + f", round {f.get('round')}" + (f", won by {f['won_by']}" if f.get("won_by") else ""))


def _line(p: dict) -> str:
    tags = " ".join(f"{k}={v}" for k, v in sorted(p["tags"].items()))
    fields = " ".join(f"{k}={_shown(v)}" for k, v in sorted(p["fields"].items()))
    return f"{p['measurement']} {tags} {fields}".strip()


def _shown(v) -> str:
    return f"{v:g}" if isinstance(v, float) else str(v)


# ---------------------------------------------------------------- the page

def page(world: str, replay: dict) -> str:
    """The replay as one HTML document, holding everything it draws: no script or style from elsewhere."""
    return (_PAGE.replace("__TITLE__", f"{world} replay")
            .replace("__DATA__", json.dumps(replay, separators=(",", ":")).replace("</", "<\\/")))


_PAGE = (Path(__file__).parent / "replay.html").read_text()


# ---------------------------------------------------------------- the command

def replay(world: str, since: str | None = None, recordings: list[Path] | None = None) -> dict:
    """The replay of `world`: from `recordings` where any are given, otherwise from every agent's history bucket."""
    here = world_dir(world)
    store = reading.world(here)
    if recordings:
        history = recording(*recordings)
    else:
        token = _admin_token()
        url, org = installation.series(HISTORY)
        started = time.perf_counter()
        history = {a: read(url, org, token, bucket_name(world, a, HISTORY), since) for a in roster(world)}
        log.info("read %d point(s) in %.2f s", sum(map(len, history.values())), time.perf_counter() - started)
    return frames(history, views(store), things(store))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(
        prog="orexis-replay",
        description="A world's run drawn from its agents' history — every agent side by side at every instant, as the "
                    "views its domains state draw it — read from the history buckets or a walk's recording, never a belief.")
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
    drawn = replay(args.world, args.since, args.recording)
    out.write_text(page(args.world, drawn))
    log.info("%s: %d instant(s) of %s, %d view(s) — %s", args.world, len(drawn["instants"]),
             ", ".join(drawn["agents"]) or "no agent", len(drawn["grids"]), out)


if __name__ == "__main__":
    main()
