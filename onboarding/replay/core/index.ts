/*  THE REPLAY'S CONTRACT — what a domain's scene and a package's layer are handed and export, and the few readings of
 *  the history every drawing shares. A drawing imports this as `@orexis/replay`; it names no package's word.
 *
 *  A drawing is a `replay.tsx` beside the code or the documents it draws, exporting one of:
 *    export const scene: Scene = { name, label, frame, Scene, describe }   a domain's picture: the ground the rest stands on
 *    export const layer: Layer = { name, order, Layer, describe }          a package's own drawing of what it decided
 *  `orexis-replay` gathers every drawing the world uses and bundles them into one page (knowledge/domain/onboarding/replay.md).
 */
import type { ComponentType } from "preact";

/** One point an agent's history part wrote, as the series store keeps it, and whose it is. */
export interface Point {
  agent: string;
  measurement: string;
  tags: Record<string, string>;
  fields: Record<string, number | string | boolean>;
  /** The point's instant, in milliseconds. */
  t: number;
}

/** An agent's points of one measurement, in time order, up to the instant shown: what a drawing reads. */
export type Of = (measurement: string) => Point[];

/** What the world's common beliefs state of every thing the history names by a tag: its predicates by local name,
 *  each a list of values — an IRI's local name, a number, a text, or a blank node followed as one more of these. */
export type Things = Record<string, Described>;
export interface Described { [predicate: string]: (string | number | Described)[] }

/** Where values put something on a scene: a box in the scene's own units. */
export interface Place { x: number; y: number; w: number; h: number }

/** A scene's measure of a whole replay, asked once with every agent's points in time order: how big it is, and where
 *  the values a point carries put it. */
export interface Frame {
  width: number;
  height: number;
  place(values: object): Place | null;
}

/** What a scene draws: the points the agents shown wrote up to the instant, each agent's after the one before's, and
 *  which agents those are. */
export interface SceneProps {
  of: Of;
  agents: string[];
  at: number;
  frame: Frame;
  things: Things;
  colour(agent: string): string;
}

/** What a layer draws: one agent's points up to the instant, on whatever scene there is. */
export interface LayerProps {
  agent: string;
  of: Of;
  at: number;
  frame: Frame;
  place: Frame["place"];
  things: Things;
  /** The agent's colour: everything a layer draws of it is drawn in it. */
  tint: string;
}

/** A measurement's lines in the log, from every point of it written at one instant; nothing to leave them out. */
export type Describe = Record<string, (group: Point[], things: Things) => string | string[] | null>;

export interface Scene {
  name: string;
  label: string;
  frame(points: Point[], things: Things): Frame;
  Scene: ComponentType<SceneProps>;
  describe?: Describe;
}

/** What a layer says of an agent's state that is no place on a scene — a conflict standing — in a line under it. */
export type StatusProps = Pick<LayerProps, "agent" | "of" | "at" | "things">;

export interface Layer {
  name: string;
  /** Drawn in order, lowest first. */
  order: number;
  Layer: ComponentType<LayerProps>;
  Status?: ComponentType<StatusProps>;
  describe?: Describe;
}

/** A drawing module, as the page imports it: one that exports a scene, a layer, or both. */
export interface Drawing { scene?: Scene; layer?: Layer }

// ---------------------------------------------------------------- readings every drawing shares

/** How many of the points, in time order, were written at or before `at`. */
export function count(points: Point[], at: number): number {
  let lo = 0, hi = points.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (points[mid].t <= at) lo = mid + 1; else hi = mid; }
  return lo;
}

/** Every point at or before `at`, of points in time order. */
export function upto(points: Point[], at: number): Point[] {
  return points.slice(0, count(points, at));
}

/** The latest point per key, of the points given in time order. */
export function latest<K>(points: Point[], keyOf: (p: Point) => K | null | undefined): Map<K, Point> {
  const out = new Map<K, Point>();
  for (const p of points) { const k = keyOf(p); if (k !== null && k !== undefined) out.set(k, p); }
  return out;
}

/** A set said whole: per key, the `members` written at the instant of the latest of the `heads` for that key. */
export function sets<K>(heads: Point[], members: Point[], keyOf: (p: Point) => K): Map<K, Point[]> {
  const out = new Map<K, Point[]>();
  for (const [k, h] of latest(heads, keyOf)) out.set(k, at(members, h.t).filter(p => keyOf(p) === k));
  return out;
}

/** The points written at exactly `t`, of points in time order. */
export function at(points: Point[], t: number): Point[] {
  const end = count(points, t);
  let start = end;
  while (start > 0 && points[start - 1].t === t) start--;
  return points.slice(start, end);
}

/** Each point's own line, where nothing describes its measurement: its measurement, tags and fields. */
export function line(p: Point): string {
  const shown = (v: unknown) => (typeof v === "number" ? +v.toFixed(3) : String(v));
  const tags = Object.entries(p.tags).sort().map(([k, v]) => `${k}=${v}`).join(" ");
  const fields = Object.entries(p.fields).sort().map(([k, v]) => `${k}=${shown(v)}`).join(" ");
  return `${p.measurement} ${tags} ${fields}`.trim();
}

/** A step's filling as a point's tags say it, for a log line: the action and what it takes, leaving out `skip`. */
export function call(tags: Record<string, string>, skip: string[] = []): string {
  const said = Object.entries(tags).filter(([k]) => k !== "action" && !skip.includes(k)).sort();
  return `${tags.action ?? "?"}(${said.map(([k, v]) => `${k}=${v}`).join(", ")})`;
}
