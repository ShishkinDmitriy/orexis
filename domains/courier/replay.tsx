/*  THE COURIER, DRAWN — the road as a grid of whole numbers, each van where its fix puts it and each contact where its
 *  offsets put it from the van carrying it (knowledge/domain/onboarding/replay.md).
 *
 *  A scene, the ground every package's layer stands on. It reads the courier's own words off the history — a fix's
 *  `Column` and `Row`, a contact's `RelativeColumn` and `RelativeRow` — and what the world states of the things they
 *  name: the van a contact is hosted by, the van it is a sample of, and the range its sensors declare, outside which a
 *  reading sees nothing. `place` puts on a cell whatever names a column and a row in the courier's words: a holding's
 *  `x` and `y`, a drive's `toX` and `toY`. Everything is drawn in the colour of the agent whose history said it.
 */
import type { Frame, Point, Scene, SceneProps, Things } from "@orexis/replay";

const CELL = 28, PAD = 1;
const FIX = { across: "Column", down: "Row" }, OFFSET = { across: "RelativeColumn", down: "RelativeRow" };
const DRAWN = new Set([FIX.across, FIX.down, OFFSET.across, OFFSET.down]);

interface At { x: number; y: number }
/** The road's frame: the grid's columns and rows, `[x0, y0, x1, y1]`, beside what every frame answers. */
interface RoadFrame extends Frame { box: [number, number, number, number] }
interface Fixed extends At { name: string; agent: string }
interface Seen extends At { name: string; sample: string; agent: string }

const column = (v: object) => Number((v as Record<string, unknown>).x ?? (v as Record<string, unknown>).toX);
const row = (v: object) => Number((v as Record<string, unknown>).y ?? (v as Record<string, unknown>).toY);
const one = (things: Things, thing: string, word: string) => things[thing]?.[word]?.[0] as string | undefined;

/** The range a sensor declares, as its capability's measurement range says it, or none. */
function range(things: Things, sensor: string): [number, number] | null {
  for (const capability of (things[sensor]?.hasSystemCapability ?? []) as Things[string][])
    for (const property of (capability.hasSystemProperty ?? []) as Things[string][])
      if ((property.type ?? []).includes("MeasurementRange")) return [property.minValue[0] as number, property.maxValue[0] as number];
  return null;
}

const inside = (things: Things, p: Point) => {
  const span = range(things, p.tags.sensor);
  return !span || (span[0] <= (p.fields.value as number) && (p.fields.value as number) <= span[1]);
};

/** Reads a stream of points in time order and keeps, per agent and feature, the latest reading on each axis of a fix
 *  and of an offset: where each thing stands now, as the points so far say. */
class Road {
  fixes = new Map<string, { across?: Point; down?: Point }>();
  offsets = new Map<string, { across?: Point; down?: Point }>();
  constructor(private things: Things) {}

  /** Read one point; where it moved a thing, where that thing now stands. */
  read(p: Point): At | null {
    const words = p.measurement === FIX.across || p.measurement === FIX.down ? [this.fixes, FIX]
                : p.measurement === OFFSET.across || p.measurement === OFFSET.down ? [this.offsets, OFFSET] : null;
    if (!words || !p.tags.feature) return null;
    const [by, w] = words as [Road["fixes"], typeof FIX];
    const key = `${p.agent}|${p.tags.feature}`, r = by.get(key) ?? {};
    r[p.measurement === w.across ? "across" : "down"] = p;
    by.set(key, r);
    return w === FIX ? this.fix(key) : this.sight(key);
  }

  private fix(key: string): Fixed | null {
    const r = this.fixes.get(key);
    return r?.across && r.down ? { agent: key.split("|")[0], name: r.across.tags.feature, x: r.across.fields.value as number, y: r.down.fields.value as number } : null;
  }

  /** A contact as its agent saw it: from where the van hosting it is fixed, inside its sensors' range. */
  private sight(key: string): Seen | null {
    const r = this.offsets.get(key);
    if (!r?.across || !r.down || !inside(this.things, r.across) || !inside(this.things, r.down)) return null;
    const agent = key.split("|")[0], sample = r.across.tags.feature, hosting = one(this.things, sample, "isHostedBy");
    const host = [...this.fixes.keys()].map(k => this.fix(k)).find(v => v?.name === hosting);
    return host ? { agent, sample, name: one(this.things, sample, "isSampleOf") ?? sample,
                    x: host.x + (r.across.fields.value as number), y: host.y + (r.down.fields.value as number) } : null;
  }

  fixed(): Fixed[] { return [...this.fixes.keys()].map(k => this.fix(k)).filter((v): v is Fixed => v !== null); }
  seen(): Seen[] { return [...this.offsets.keys()].map(k => this.sight(k)).filter((v): v is Seen => v !== null); }
}

function frame(points: Point[], things: Things): RoadFrame {
  const road = new Road(things), cells: At[] = [];
  for (const p of points) {
    const moved = road.read(p);
    if (moved) cells.push(moved);
    const v = p.measurement === "Holding" ? p.fields : p.tags;
    if (!Number.isNaN(column(v)) && !Number.isNaN(row(v))) cells.push({ x: column(v), y: row(v) });
  }
  const xs = cells.map(c => c.x), ys = cells.map(c => c.y);
  const [x0, y0, x1, y1] = cells.length ? [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] : [0, 0, 0, 0];
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
  const [x0, y0, x1, y1] = frame.box, cells = [], labels = [];
  for (let x = x0; x <= x1; x++) {
    labels.push(<text x={frame.place({ x, y: y0 })!.x + CELL / 2} y={CELL * 0.7} text-anchor="middle" fill="var(--muted)">{x}</text>);
    for (let y = y0; y <= y1; y++) {
      const c = frame.place({ x, y })!;
      cells.push(<rect x={c.x + 1} y={c.y + 1} width={CELL - 2} height={CELL - 2} rx="3" fill="var(--cell)" />);
    }
  }
  for (let y = y0; y <= y1; y++) labels.push(<text x={CELL / 2} y={frame.place({ x: x0, y })!.y + CELL * 0.62} text-anchor="middle">{y}</text>);
  return <g>{cells}{labels}</g>;
}

function Van({ van, frame, colour }: { van: Fixed; frame: Frame; colour: string }) {
  const p = frame.place(van)!;
  return (
    <g data-fixed={van.name} data-x={van.x} data-y={van.y} data-by={van.agent}>
      <circle cx={p.x + CELL / 2} cy={p.y + CELL / 2} r={CELL / 3} fill={colour}><title>{van.name}, fixed by {van.agent}</title></circle>
      <text x={p.x + CELL / 2} y={p.y + CELL - 1} text-anchor="middle" style="font-size:7px">{van.name}</text>
    </g>
  );
}

function Contact({ seen, frame, colour }: { seen: Seen; frame: Frame; colour: string }) {
  const p = frame.place(seen);
  if (!p) return null;
  return (
    <rect data-seen={seen.name} data-x={seen.x} data-y={seen.y} data-by={seen.agent} x={p.x + 6} y={p.y + 6}
          width={CELL - 12} height={CELL - 12} rx="2" fill="none" stroke={colour} stroke-width="2">
      <title>{seen.name === seen.sample ? seen.name : `${seen.name} (${seen.sample})`}, seen by {seen.agent}</title>
    </rect>
  );
}

function Road_({ of, frame, things, colour }: SceneProps) {
  const road = new Road(things);
  for (const m of DRAWN) for (const p of of(m)) road.read(p);
  return (
    <g>
      <Grid frame={frame as RoadFrame} />
      {road.seen().map(s => <Contact seen={s} frame={frame} colour={colour(s.agent)} />)}
      {road.fixed().map(v => <Van van={v} frame={frame} colour={colour(v.agent)} />)}
    </g>
  );
}

export const scene: Scene = {
  name: "road",
  label: "the road",
  frame,
  Scene: Road_,
  //  A FIX AND AN OFFSET ARE DRAWN, not said: the scene shows them, so the log leaves them out.
  describe: Object.fromEntries([...DRAWN].map(m => [m, () => null])),
};
