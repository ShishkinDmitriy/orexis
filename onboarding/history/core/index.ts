/*  THE HISTORY VIEW'S CONTRACT — what a domain's scene and a package's layer are handed and export, and the few readings of
 *  the rows every drawing shares. A drawing imports this as `@orexis/ui`; it names no package's word.
 *
 *  A drawing is a `ui/index.tsx` beside the code or the documents it draws, with the SPARQL selects it reads beside it,
 *  each `ui/<Query>.rq`, exporting one of:
 *    export const scene: Scene = { name, label, frame, Scene, describe }   a domain's picture: the ground the rest stands on
 *    export const layer: Layer = { name, order, Layer, describe }          a package's own drawing of what it decided
 *  `orexis-history` runs every query over each agent's journal, its observations and what the world states, and bundles
 *  the drawings with the rows into one page (knowledge/domain/onboarding/history-view.md).
 */
import type { ComponentType } from "preact";

/** A value a query bound: an IRI as its text, a number, a boolean, or any other literal's text. */
export type Value = string | number | boolean;

/** One row a query answered over one agent's journal and observations, and whose it is. */
export interface Row {
  agent: string;
  /** The query's name: `ui/<Query>.rq`. */
  query: string;
  /** The row's instant, `?at`, in milliseconds; minus infinity for a row that binds no `?at`, which holds throughout. */
  t: number;
  /** Every variable the row binds, by name. */
  v: Record<string, Value>;
}

/** An agent's rows of one query, in time order, up to the instant shown: what a drawing reads. */
export type Of = (query: string) => Row[];

/** Where values put something on a scene: a box in the scene's own units. */
export interface Place { x: number; y: number; w: number; h: number }

/** A scene's measure of a whole history, asked once with every agent's rows of every query: how big it is, and where
 *  values in the world's own words — by local name — put a thing. */
export interface Frame {
  width: number;
  height: number;
  place(values: Record<string, Value>): Place | null;
}

/** What a scene draws: the rows the agents shown answered up to the instant, each agent's after the one before's, and
 *  which agents those are. */
export interface SceneProps {
  of: Of;
  agents: string[];
  at: number;
  frame: Frame;
  colour(agent: string): string;
}

/** What a layer draws: one agent's rows up to the instant, on whatever scene there is. */
export interface LayerProps {
  agent: string;
  of: Of;
  at: number;
  frame: Frame;
  place: Frame["place"];
  /** The agent's colour: everything a layer draws of it is drawn in it. */
  tint: string;
}

/** A query's lines in the log, from every row of it at one instant; nothing to leave them out. */
export type Describe = Record<string, (group: Row[]) => string | string[] | null>;

export interface Scene {
  name: string;
  label: string;
  /** The frame, from every agent's rows of every query over the whole run, in time order. */
  frame(rows: Row[]): Frame;
  Scene: ComponentType<SceneProps>;
  describe?: Describe;
}

/** What a layer says of an agent's state that is no place on a scene — a conflict standing — in a line under it. */
export type StatusProps = Pick<LayerProps, "agent" | "of" | "at">;

export interface Layer {
  name: string;
  /** Drawn in order, lowest first. */
  order: number;
  /** What it draws on the scene; none for a layer that is no place, which says itself in its status and the log. */
  Layer?: ComponentType<LayerProps>;
  Status?: ComponentType<StatusProps>;
  describe?: Describe;
}

/** A drawing module, as the page imports it: one that exports a scene, a layer, or both. */
export interface Drawing { scene?: Scene; layer?: Layer }

// ---------------------------------------------------------------- readings every drawing shares

/** An IRI's local name: what follows its last `#` or `/`. */
export function local(iri: Value | undefined): string {
  return String(iri ?? "").replace(/^.*[#/]/, "");
}

/** How many of the rows, in time order, are at or before `at`. */
export function count(rows: Row[], at: number): number {
  let lo = 0, hi = rows.length;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (rows[mid].t <= at) lo = mid + 1; else hi = mid; }
  return lo;
}

/** Every row at or before `at`, of rows in time order. */
export function upto(rows: Row[], at: number): Row[] {
  return rows.slice(0, count(rows, at));
}

/** The latest row per key, of the rows given in time order. */
export function latest<K>(rows: Row[], keyOf: (r: Row) => K | null | undefined): Map<K, Row> {
  const out = new Map<K, Row>();
  for (const r of rows) { const k = keyOf(r); if (k !== null && k !== undefined) out.set(k, r); }
  return out;
}

/** A set said whole, as one event: per key, every row of the latest event, `?e`, for that key — so an event saying an
 *  empty set replaces the one before with its one row binding no member. */
export function sets<K>(rows: Row[], keyOf: (r: Row) => K): Map<K, Row[]> {
  const out = new Map<K, Row[]>();
  for (const [k, last] of latest(rows, keyOf)) out.set(k, rows.filter(r => r.v.e === last.v.e));
  return out;
}

/** The values of each thing a query says one per row — a `?key` and its `?value` beside the thing named by `by` — as
 *  one record per thing, by each key's local name, beside the first row about it. */
export function pivot(rows: Row[], by: string): Map<Value, { row: Row; values: Record<string, Value> }> {
  const out = new Map<Value, { row: Row; values: Record<string, Value> }>();
  for (const r of rows) {
    const thing = r.v[by];
    if (thing === undefined) continue;
    if (!out.has(thing)) out.set(thing, { row: r, values: {} });
    if (r.v.key !== undefined && r.v.value !== undefined) out.get(thing)!.values[local(r.v.key)] = r.v.value;
  }
  return out;
}

/** The rows at exactly `t`, of rows in time order. */
export function at(rows: Row[], t: number): Row[] {
  const end = count(rows, t);
  let start = end;
  while (start > 0 && rows[start - 1].t === t) start--;
  return rows.slice(start, end);
}

/** A value as a line says it: an IRI by its local name, a number to three places. */
export function shown(v: Value | undefined): string {
  return typeof v === "number" ? String(+v.toFixed(3)) : typeof v === "string" && /^[a-z]+:/.test(v) ? local(v) : String(v ?? "");
}

/** Each row's own line, where nothing describes its query: its query and what it binds. */
export function line(r: Row): string {
  return `${r.query} ${Object.entries(r.v).filter(([k]) => k !== "at" && k !== "e").sort().map(([k, v]) => `${k}=${shown(v)}`).join(" ")}`.trim();
}

/** A step's filling for a log line: the action and the values it takes, by each parameter's local name. */
export function call(action: Value | undefined, values: Record<string, Value>): string {
  return `${local(action) || "?"}(${Object.entries(values).sort().map(([k, v]) => `${k}=${shown(v)}`).join(", ")})`;
}
