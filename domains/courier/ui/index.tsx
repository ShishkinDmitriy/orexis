/*  THE COURIER, DRAWN — the road as a grid of whole numbers, each van where its fix puts it and each contact where its
 *  offsets put it from the van carrying it (knowledge/domain/onboarding/history-view.md).
 *
 *  A scene, the ground every package's layer stands on. It reads two selects beside it, in the courier's own words:
 *  `ui/Fixed.rq`, a van's `Column` and `Row` as the agent observed them, and `ui/Seen.rq`, a contact's
 *  `RelativeColumn` and `RelativeRow`, with the van it is hosted by, what it is a sample of and the range its sensor
 *  declares, outside which a reading sees nothing. `place` puts on a cell whatever names a column and a row in the
 *  courier's words: a holding's `x` and `y`, a drive's `toX` and `toY`. Everything is drawn in the colour of the agent
 *  that observed it.
 */
import type { Frame, Row, Scene, SceneProps, Value } from "@orexis/ui";
import { local } from "@orexis/ui";

const CELL = 28, PAD = 1;

interface At { x: number; y: number }
/** The road's frame: the grid's columns and rows, `[x0, y0, x1, y1]`, beside what every frame answers. */
interface RoadFrame extends Frame { box: [number, number, number, number] }
interface Fixed extends At { name: string; agent: string }
interface Seen extends At { name: string; sample: string; agent: string }

const column = (v: Record<string, Value>) => Number(v.x ?? v.toX);
const row = (v: Record<string, Value>) => Number(v.y ?? v.toY);
const across = (r: Row) => /Column$/.test(String(r.v.axis));
const inside = (r: Row) => r.v.least === undefined || (+r.v.least <= +r.v.value && +r.v.value <= +r.v.most);

/** Where each thing stands, from the rows so far: per agent and van the latest number on each axis of a fix, and per
 *  agent and contact the latest on each of an offset, a contact put where the van hosting it is fixed. */
function road(fixes: Row[], sights: Row[]): { fixed: Fixed[]; seen: Seen[] } {
  const latest = (rows: Row[], by: string) => {
    const out = new Map<string, { across?: Row; down?: Row }>();
    for (const r of rows) {
      const key = `${r.agent}|${r.v[by]}`, held = out.get(key) ?? {};
      held[across(r) ? "across" : "down"] = r;
      out.set(key, held);
    }
    return out;
  };
  const fixed: Fixed[] = [];
  for (const { across: a, down: d } of latest(fixes, "van").values())
    if (a && d) fixed.push({ agent: a.agent, name: local(a.v.van), x: +a.v.value, y: +d.v.value });
  const seen: Seen[] = [];
  for (const { across: a, down: d } of latest(sights, "contact").values()) {
    if (!a || !d || !inside(a) || !inside(d)) continue;
    const host = fixed.find(v => v.agent === a.agent && v.name === local(a.v.host));
    if (host) seen.push({ agent: a.agent, sample: local(a.v.contact), name: local(a.v.stands ?? a.v.contact),
                          x: host.x + +a.v.value, y: host.y + +d.v.value });
  }
  return { fixed, seen };
}

/** Every cell any row names: a van fixed, a contact seen, and whatever any query's rows put on the road — a holding's
 *  `x` and `y`, a step's `toX` and `toY` — each said as a `?key` and its `?value` per row, beside what else the row
 *  binds, which says what the values are of. */
function cells(rows: Row[]): At[] {
  const fixes = rows.filter(r => r.query === "Fixed"), sights = rows.filter(r => r.query === "Seen"), out: At[] = [];
  //  EVERY CELL A THING STOOD ON, not only the last: the road as it stood at each instant a fix or a sight came.
  for (const t of new Set([...fixes, ...sights].map(r => r.t))) {
    const { fixed, seen } = road(fixes.filter(r => r.t <= t), sights.filter(r => r.t <= t));
    out.push(...fixed, ...seen);
  }
  const by = new Map<string, Record<string, Value>>();
  for (const r of rows) {
    if (r.v.key === undefined) continue;
    const { key, value, ...rest } = r.v, k = `${r.agent}|${r.query}|${JSON.stringify(Object.entries(rest).sort())}`;
    by.set(k, { ...(by.get(k) ?? {}), [local(key)]: value });
  }
  for (const v of by.values()) if (!Number.isNaN(column(v)) && !Number.isNaN(row(v))) out.push({ x: column(v), y: row(v) });
  return out;
}

function frame(rows: Row[]): RoadFrame {
  const all = cells(rows), xs = all.map(c => c.x), ys = all.map(c => c.y);
  const [x0, y0, x1, y1] = all.length ? [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] : [0, 0, 0, 0];
  return {
    width: (x1 - x0 + 1 + 2 * PAD) * CELL, height: (y1 - y0 + 1 + 2 * PAD) * CELL,
    place(values) {
      const x = column(values), y = row(values);
      if (Number.isNaN(x) || Number.isNaN(y) || x < x0 || x > x1 || y < y0 || y > y1) return null;
      return { x: (x - x0 + PAD) * CELL, y: (y - y0 + PAD) * CELL, w: CELL, h: CELL };
    },
    box: [x0, y0, x1, y1],
  };
}

function Grid({ frame }: { frame: RoadFrame }) {
  const [x0, y0, x1, y1] = frame.box, grid = [], labels = [];
  for (let x = x0; x <= x1; x++) {
    labels.push(<text x={frame.place({ x, y: y0 })!.x + CELL / 2} y={CELL * 0.7} text-anchor="middle" fill="var(--muted)">{x}</text>);
    for (let y = y0; y <= y1; y++) {
      const c = frame.place({ x, y })!;
      grid.push(<rect x={c.x + 1} y={c.y + 1} width={CELL - 2} height={CELL - 2} rx="3" fill="var(--cell)" />);
    }
  }
  for (let y = y0; y <= y1; y++) labels.push(<text x={CELL / 2} y={frame.place({ x: x0, y })!.y + CELL * 0.62} text-anchor="middle">{y}</text>);
  return <g>{grid}{labels}</g>;
}

function Van({ van, frame, colour }: { van: Fixed; frame: Frame; colour: string }) {
  const p = frame.place({ ...van })!;
  return (
    <g data-fixed={van.name} data-x={van.x} data-y={van.y} data-by={van.agent}>
      <circle cx={p.x + CELL / 2} cy={p.y + CELL / 2} r={CELL / 3} fill={colour}><title>{van.name}, fixed by {van.agent}</title></circle>
      <text x={p.x + CELL / 2} y={p.y + CELL - 1} text-anchor="middle" style="font-size:7px">{van.name}</text>
    </g>
  );
}

function Contact({ seen, frame, colour }: { seen: Seen; frame: Frame; colour: string }) {
  const p = frame.place({ ...seen });
  if (!p) return null;
  return (
    <rect data-seen={seen.name} data-x={seen.x} data-y={seen.y} data-by={seen.agent} x={p.x + 6} y={p.y + 6}
          width={CELL - 12} height={CELL - 12} rx="2" fill="none" stroke={colour} stroke-width="2">
      <title>{seen.name === seen.sample ? seen.name : `${seen.name} (${seen.sample})`}, seen by {seen.agent}</title>
    </rect>
  );
}

function Road({ of, frame, colour }: SceneProps) {
  const { fixed, seen } = road(of("Fixed"), of("Seen"));
  return (
    <g>
      <Grid frame={frame as RoadFrame} />
      {seen.map(s => <Contact seen={s} frame={frame} colour={colour(s.agent)} />)}
      {fixed.map(v => <Van van={v} frame={frame} colour={colour(v.agent)} />)}
    </g>
  );
}

export const scene: Scene = {
  name: "road",
  label: "the road",
  frame,
  Scene: Road,
  //  A FIX AND AN OFFSET ARE DRAWN, not said: the scene shows them, so the log leaves them out.
  describe: { Fixed: () => null, Seen: () => null },
};
