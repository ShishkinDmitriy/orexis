/*  ONE PANE OF ONE SCENE: the scene drawn from the points of the agents shown, and on it each layer once per agent,
 *  in the agent's colour, with each layer's status under it. Shared by the page and by the tests' headless render, so
 *  what a test holds is what a person sees. And the log, every drawing's lines for one agent, in time order. */
import type { Drawing, Frame, Layer, Of, Point, Scene, Things } from "./index";
import { line, upto } from "./index";

/** What a page is handed, prepared: each agent's points in time order, whole and by measurement. */
export interface Replay {
  world: string;
  agents: string[];
  instants: number[];
  points: Record<string, Point[]>;
  by: Record<string, Record<string, Point[]>>;
  things: Things;
}

/** What `orexis-replay` writes into a page: every distinct measurement and tag set once, as a SERIES, and each point
 *  as its series, its milliseconds after `start` and its fields — a long run's tags said once rather than per point. */
export interface Raw {
  world: string;
  agents: string[];
  start: string;
  instants: number[];
  series: [string, Record<string, string>][];
  points: Record<string, [number, number, Point["fields"]][]>;
  things: Things;
}

export function prepare(raw: Raw): Replay {
  const start = Date.parse(raw.start), points: Replay["points"] = {}, by: Replay["by"] = {};
  for (const [agent, ps] of Object.entries(raw.points)) {
    points[agent] = ps.map(([s, ms, fields]) => ({ agent, measurement: raw.series[s][0], tags: raw.series[s][1], fields, t: start + ms }))
                      .sort((a, b) => a.t - b.t);
    by[agent] = {};
    for (const p of points[agent]) (by[agent][p.measurement] ??= []).push(p);
  }
  return { world: raw.world, agents: raw.agents, instants: raw.instants.map(ms => start + ms), points, by, things: raw.things };
}

/** Every agent's points in time order, for a scene's frame. */
export function every(replay: Replay): Point[] {
  return Object.values(replay.points).flat().sort((a, b) => a.t - b.t);
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

/** An agent's points of a measurement up to `at`; or, for several agents, each one's after the one before's. */
function reader(replay: Replay, agents: string[], at: number): Of {
  return m => agents.flatMap(a => upto(replay.by[a]?.[m] ?? [], at));
}

export function Pane({ replay, scene, frame, layers, agents, at }:
    { replay: Replay; scene: Scene; frame: Frame; layers: Layer[]; agents: string[]; at: number }) {
  const colour = colours(replay.agents);
  const of = agents.map(a => reader(replay, [a], at));
  return (
    <div class="scene">
      <svg viewBox={`0 0 ${frame.width} ${frame.height}`} role="img" aria-label={`${scene.label} as ${agents.join(", ")} have it`}>
        <scene.Scene of={reader(replay, agents, at)} agents={agents} at={at} frame={frame} things={replay.things} colour={colour} />
        {layers.map(l => (
          <g data-layer={l.name} key={l.name}>
            {agents.map((a, n) => (
              <g data-agent={a} key={a}>
                <l.Layer agent={a} of={of[n]} at={at} frame={frame} place={frame.place} things={replay.things} tint={colour(a)} />
              </g>
            ))}
          </g>
        ))}
      </svg>
      <ul class="status">
        {agents.map((a, n) => layers.map(l => l.Status && (
          <li data-layer={l.name} data-agent={a} key={`${l.name}|${a}`}>
            <i style={{ background: colour(a) }} title={a} /><l.Status agent={a} of={of[n]} at={at} things={replay.things} />
          </li>)))}
      </ul>
    </div>
  );
}

export interface Line { t: number; agent: string; text: string }

/** What one agent did, a line per thing at the instant it did it: every instant's points of one measurement handed
 *  together to whatever drawing describes the measurement, which answers lines, or none to leave them out. */
export function log(drawings: Drawing[], points: Point[], things: Things): Line[] {
  const describers: Record<string, NonNullable<Scene["describe"]>[string]> = {};
  for (const d of drawings) Object.assign(describers, d.scene?.describe, d.layer?.describe);
  const out: Line[] = [], groups = new Map<string, Point[]>();
  for (const p of points) {
    const k = `${p.t}|${p.measurement}`;
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k)!.push(p);
  }
  for (const group of groups.values()) {
    const fn = describers[group[0].measurement];
    const said = fn ? fn(group, things) : group.map(line);
    for (const text of ([] as string[]).concat(said ?? [])) out.push({ t: group[0].t, agent: group[0].agent, text });
  }
  return out;
}
