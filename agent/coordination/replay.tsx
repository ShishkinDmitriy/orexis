/*  COORDINATION, DRAWN — what the agent asked with, what it laid of its peers as they said it and as it foresaw them,
 *  and its conflicts, from the history coordination writes (`events.py`): each set said whole, so what stands at an
 *  instant is the latest set said of each origin, peer and constraint.
 *
 *  A layer, on whatever scene the world's domain draws: a holding is put where the scene places the values it holds
 *  on the constraint's key, in the agent's colour — solid where it asked, dashed where a peer said, dotted where it
 *  foresaw — bright while its period holds and faint before it. Its conflicts are a status, a line under the scene.
 */
import type { Describe, Layer, LayerProps, Place, Point, StatusProps } from "@orexis/replay";
import { at as when, latest, sets } from "@orexis/replay";

const KEPT = new Set(["from", "until", "taken"]);
const DASH: Record<string, string | undefined> = { asked: undefined, said: "4 2", foreseen: "1.5 2" };
const key = (p: Point) => `${p.tags.origin}|${p.tags.peer}|${p.tags.constraint}`;
const values = (h: Point) => Object.fromEntries(Object.entries(h.fields).filter(([k]) => !KEPT.has(k)));
const shown = (v: unknown) => (typeof v === "number" ? +v.toFixed(3) : v);

function Holding({ h, at, box: p, tint }: { h: Point; at: number; box: Place; tint: string }) {
  const from = h.fields.from ? Date.parse(h.fields.from as string) : -Infinity;
  const until = h.fields.until ? Date.parse(h.fields.until as string) : Infinity;
  const now = from <= at && at < until, origin = h.tags.origin;
  return (
    <rect data-origin={origin} data-thing={h.tags.thing} data-now={String(now)} x={p.x + 3} y={p.y + 3} width={p.w - 6} height={p.h - 6} rx="3"
          fill={tint} fill-opacity={now ? (origin === "asked" ? 0.22 : 0.32) : 0.08} stroke={tint} stroke-width="1.5"
          stroke-dasharray={DASH[origin]}>
      <title>{origin}{origin === "asked" ? "" : ` of ${h.tags.peer}`}: {h.tags.thing}</title>
    </rect>
  );
}

/** The conflicts standing as the agent last concluded them, in a line under the scene: a conflict is no place. */
function Conflicts({ agent, of }: StatusProps) {
  const concluded = latest(of("Conflicts"), () => "all").get("all");
  const standing = concluded ? when(of("Conflict"), concluded.t).filter(p => p.fields.standing) : [];
  if (!standing.length) return <span class="empty">{agent}: no conflict standing</span>;
  return (
    <span>{agent}: {standing.map(c => (
      <span data-conflict={c.tags.peer}>conflict with {c.tags.peer} over {c.tags.constraint}{c.fields.silent ? ", silent" : ""}, round {c.fields.round}
        {c.fields.won_by ? `, won by ${c.fields.won_by}` : ", undecided"}; </span>))}
    </span>
  );
}

function Coordination({ of, at, place, tint }: LayerProps) {
  const held = [...sets(of("Holdings"), of("Holding"), key).values()].flat();
  return <g>{held.map(h => { const p = place(values(h)); return p && <Holding h={h} at={at} box={p} tint={tint} />; })}</g>;
}

const describe: Describe = {
  Holdings: group => group.filter(h => h.fields.count === 0).map(h => `${h.tags.origin} nothing of ${h.tags.peer}`),
  Holding: group => {
    const by = new Map<string, Point[]>();
    for (const h of group) by.set(key(h), [...(by.get(key(h)) ?? []), h]);
    return [...by.values()].map(hs => `${hs[0].tags.origin}${hs[0].tags.origin === "asked" ? "" : ` of ${hs[0].tags.peer}`}: `
      + hs.map(h => `${h.tags.thing} ` + Object.entries(values(h)).sort().map(([k, v]) => `${k}=${shown(v)}`).join(" ")).join(", "));
  },
  Conflicts: group => (group.some(c => c.fields.count === 0) ? "no conflict" : null),
  Conflict: group => group.map(c => `conflict with ${c.tags.peer} over ${c.tags.constraint}: ${c.fields.standing ? "standing" : "not standing"}`
    + `${c.fields.silent ? ", silent" : ""}, round ${c.fields.round}${c.fields.won_by ? `, won by ${c.fields.won_by}` : ""}`),
};

export const layer: Layer = { name: "coordination", order: 10, Layer: Coordination, Status: Conflicts, describe };
