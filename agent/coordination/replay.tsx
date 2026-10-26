/*  COORDINATION, DRAWN — what the agent asked with, what it laid of its peers as they said it and as it foresaw them,
 *  and its conflicts, from the events coordination keeps in the journal (`events.py`), read by the two selects beside
 *  this: `replay.Held.rq` and `replay.Concluded.rq`. Each set is said whole, so what stands at an instant is the latest
 *  set said of each origin, peer and constraint.
 *
 *  A layer, on whatever scene the world's domain draws: a holding is put where the scene places the values it holds
 *  on the constraint's key, in the agent's colour — solid where it asked, dashed where a peer said, dotted where it
 *  foresaw — bright while its period holds and faint before it. Its conflicts are a status, a line under the scene.
 */
import type { Describe, Layer, LayerProps, Place, Row, StatusProps, Value } from "@orexis/replay";
import { latest, local, pivot, sets, shown } from "@orexis/replay";

const DASH: Record<string, string | undefined> = { Asked: undefined, Said: "4 2", Foreseen: "1.5 2" };
const key = (r: Row) => `${r.v.origin}|${r.v.peer}|${r.v.constraint}`;
const origin = (r: Row) => local(r.v.origin);

interface Held { row: Row; values: Record<string, Value> }

/** The holdings standing at the instant: the latest set of each origin, peer and constraint, a holding each. */
function standing(rows: Row[]): Held[] {
  return [...sets(rows, key).values()].flatMap(set => [...pivot(set, "h").values()]);
}

function Holding({ held, at, box: p, tint }: { held: Held; at: number; box: Place; tint: string }) {
  const { v } = held.row, from = v.from ? Date.parse(String(v.from)) : -Infinity, until = v.until ? Date.parse(String(v.until)) : Infinity;
  const now = from <= at && at < until, o = origin(held.row);
  return (
    <rect data-origin={o.toLowerCase()} data-thing={local(v.thing)} data-now={String(now)} x={p.x + 3} y={p.y + 3} width={p.w - 6} height={p.h - 6} rx="3"
          fill={tint} fill-opacity={now ? (o === "Asked" ? 0.22 : 0.32) : 0.08} stroke={tint} stroke-width="1.5" stroke-dasharray={DASH[o]}>
      <title>{o.toLowerCase()}{o === "Asked" ? "" : ` of ${local(v.peer)}`}: {local(v.thing)}</title>
    </rect>
  );
}

/** The conflicts standing as the agent last concluded them, in a line under the scene: a conflict is no place. */
function Conflicts({ agent, of }: StatusProps) {
  const last = latest(of("Concluded"), () => "all").get("all");
  const now = last ? of("Concluded").filter(r => r.v.e === last.v.e && r.v.c !== undefined && r.v.standing === true) : [];
  if (!now.length) return <span class="empty">{agent}: no conflict standing</span>;
  return (
    <span>{agent}: {now.map(c => (
      <span data-conflict={local(c.v.peer)}>conflict with {local(c.v.peer)} over {local(c.v.constraint)}{c.v.silent === true ? ", silent" : ""}, round {c.v.round}
        {c.v.wonBy ? `, won by ${local(c.v.wonBy)}` : ", undecided"}; </span>))}
    </span>
  );
}

function Coordination({ of, at, place, tint }: LayerProps) {
  return <g>{standing(of("Held")).map(h => { const p = place(h.values); return p && <Holding held={h} at={at} box={p} tint={tint} />; })}</g>;
}

const describe: Describe = {
  Held: group => [...sets(group, key).values()].map(set => {
    const first = set[0], o = origin(first).toLowerCase(), whose = o === "asked" ? "" : ` of ${local(first.v.peer)}`;
    const held = [...pivot(set, "h").values()].sort((a, b) => local(a.row.v.thing).localeCompare(local(b.row.v.thing)));
    return held.length ? `${o}${whose}: ` + held.map(h => `${local(h.row.v.thing)} `
      + Object.entries(h.values).sort().map(([k, v]) => `${k}=${shown(v)}`).join(" ")).join(", ")
      : `${o} nothing of ${local(first.v.peer)}`;
  }),
  Concluded: group => {
    const conflicts = group.filter(r => r.v.c !== undefined);
    return conflicts.length ? conflicts.map(c => `conflict with ${local(c.v.peer)} over ${local(c.v.constraint)}: `
      + `${c.v.standing === true ? "standing" : "not standing"}${c.v.silent === true ? ", silent" : ""}, round ${c.v.round}`
      + `${c.v.wonBy ? `, won by ${local(c.v.wonBy)}` : ""}`) : "no conflict";
  },
};

export const layer: Layer = { name: "coordination", order: 10, Layer: Coordination, Status: Conflicts, describe };
