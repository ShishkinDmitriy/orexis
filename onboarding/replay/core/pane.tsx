/*  ONE PANE OF ONE SCENE: the scene drawn from the rows of the agents shown, and on it each layer once per agent,
 *  in the agent's colour, with each layer's status under it. Shared by the page and by the tests' headless render, so
 *  what a test holds is what a person sees. And the log, every drawing's lines for one agent, in time order. */
import type { Drawing, Frame, Layer, Of, Row, Scene, Value } from "./index";
import { line, upto } from "./index";

/** What a page is handed, prepared: each agent's rows in time order, whole and by query. */
export interface Replay {
  world: string;
  agents: string[];
  instants: number[];
  rows: Record<string, Row[]>;
  by: Record<string, Record<string, Row[]>>;
  live: boolean;
}

/** What `orexis-replay` writes into a page: every query's name and the variables it projects, said once, and each row
 *  as its query, its milliseconds after `start` — or null where it binds no `?at` — and its values in that order, null
 *  where one is unbound. */
export interface Raw {
  world: string;
  agents: string[];
  start: string;
  instants: number[];
  queries: [string, string[]][];
  rows: Record<string, [number, number | null, (Value | null)[]][]>;
  live?: boolean;
}

export function prepare(raw: Raw): Replay {
  const start = Date.parse(raw.start), rows: Replay["rows"] = {}, by: Replay["by"] = {};
  for (const [agent, rs] of Object.entries(raw.rows)) {
    rows[agent] = rs.map(([q, ms, values]) => {
      const [query, vars] = raw.queries[q], v: Record<string, Value> = {};
      vars.forEach((name, n) => { if (values[n] !== null && values[n] !== undefined) v[name] = values[n]!; });
      return { agent, query, t: ms === null ? -Infinity : start + ms, v };
    }).sort((a, b) => a.t - b.t);
    by[agent] = {};
    for (const r of rows[agent]) (by[agent][r.query] ??= []).push(r);
  }
  return { world: raw.world, agents: raw.agents, instants: raw.instants.map(ms => start + ms), rows, by, live: !!raw.live };
}

/** Every agent's rows of every query over the whole run, in time order: what a scene's frame measures. */
export function every(replay: Replay): Row[] {
  return Object.values(replay.rows).flat().sort((a, b) => a.t - b.t);
}

/** The scenes and the layers the drawings export, the layers in their order. */
export function gather(drawings: Drawing[]): { scenes: Scene[]; layers: Layer[] } {
  return {
    scenes: drawings.flatMap(d => (d.scene ? [d.scene] : [])),
    layers: drawings.flatMap(d => (d.layer ? [d.layer] : [])).sort((a, b) => a.order - b.order),
  };
}

const PALETTE = ["#8e44ad", "#1f9e89", "#e8590c", "#3a86ff", "#c2255c", "#5c940d", "#b08900", "#0b7285", "#d6336c", "#5f3dc4", "#2b8a3e", "#495057"];

/** Each agent's colour, the same wherever it is drawn: its place among the world's agents, round a palette. */
export function colours(agents: string[]): (agent: string) => string {
  return agent => PALETTE[Math.max(0, agents.indexOf(agent)) % PALETTE.length];
}

/** An agent's rows of a query up to `at`; or, for several agents, each one's after the one before's. */
function reader(replay: Replay, agents: string[], at: number): Of {
  return q => agents.flatMap(a => upto(replay.by[a]?.[q] ?? [], at));
}

export function Pane({ replay, scene, frame, layers, agents, at }:
    { replay: Replay; scene: Scene; frame: Frame; layers: Layer[]; agents: string[]; at: number }) {
  const colour = colours(replay.agents);
  const of = agents.map(a => reader(replay, [a], at));
  return (
    <div class="scene">
      <svg viewBox={`0 0 ${frame.width} ${frame.height}`} role="img" aria-label={`${scene.label} as ${agents.join(", ")} have it`}>
        <scene.Scene of={reader(replay, agents, at)} agents={agents} at={at} frame={frame} colour={colour} />
        {layers.map(l => (
          <g data-layer={l.name} key={l.name}>
            {agents.map((a, n) => (
              <g data-agent={a} key={a}>
                <l.Layer agent={a} of={of[n]} at={at} frame={frame} place={frame.place} tint={colour(a)} />
              </g>
            ))}
          </g>
        ))}
      </svg>
      <ul class="status">
        {agents.map((a, n) => layers.map(l => l.Status && (
          <li data-layer={l.name} data-agent={a} key={`${l.name}|${a}`}>
            <i style={{ background: colour(a) }} title={a} /><l.Status agent={a} of={of[n]} at={at} />
          </li>)))}
      </ul>
    </div>
  );
}

export interface Line { t: number; agent: string; text: string }

/** What one agent did, a line per thing at the instant it did it: every instant's rows of one query handed together
 *  to whatever drawing describes the query, which answers lines, or none to leave them out. A row holding throughout,
 *  binding no `?at`, is no line. */
export function log(drawings: Drawing[], rows: Row[]): Line[] {
  const describers: Record<string, NonNullable<Scene["describe"]>[string]> = {};
  for (const d of drawings) Object.assign(describers, d.scene?.describe, d.layer?.describe);
  const out: Line[] = [], groups = new Map<string, Row[]>();
  for (const r of rows) {
    if (r.t === -Infinity) continue;
    const k = `${r.t}|${r.query}`;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k)!.push(r);
  }
  for (const group of groups.values()) {
    const fn = describers[group[0].query];
    const said = fn ? fn(group) : group.map(line);
    for (const text of ([] as string[]).concat(said ?? [])) out.push({ t: group[0].t, agent: group[0].agent, text });
  }
  return out;
}
