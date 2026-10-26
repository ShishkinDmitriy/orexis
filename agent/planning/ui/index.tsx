/*  PLANNING, DRAWN — the latest plan published for each want, as a path through the places its steps put things, from
 *  the events planning keeps in the journal (`events.py`), read by `ui/Plan.rq` beside this. A step is walked once
 *  the agent has taken it, and is left off the path: read off execution's `Step`, by the step's own name, which is the
 *  word planning hands its steps down in.
 *
 *  A layer, on whatever scene the world's domain draws: a step is put where the scene places the values it takes, in
 *  the agent's colour; a step taking nothing the scene places is left off the path and said in the log.
 */
import type { Describe, Layer, LayerProps, Row, Value } from "@orexis/ui";
import { call, latest, local, pivot } from "@orexis/ui";

interface Planned { step: Value; row: Row; values: Record<string, Value> }

/** A plan's steps in the order they are walked: from the one nothing comes before, along each step's next. */
function walked(rows: Row[]): Planned[] {
  const steps = new Map([...pivot(rows, "step")].map(([step, s]) => [step, { step, ...s }]));
  const after = new Set(rows.map(r => r.v.next).filter(n => n !== undefined));
  const out: Planned[] = [];
  let at = [...steps.keys()].find(s => !after.has(s));
  while (at !== undefined && steps.has(at) && !out.some(s => s.step === at)) {
    out.push(steps.get(at)!);
    at = steps.get(at)!.row.v.next;
  }
  return out;
}

/** The steps of the latest plan published for each want, less those the agent has taken since. */
export function untaken(rows: Row[], taken: Row[]): Planned[][] {
  return [...latest(rows, r => r.v.want).values()].map(last => walked(rows.filter(r => r.v.e === last.v.e))
    .filter(s => !taken.some(t => t.v.step === s.step && t.t >= last.t)));
}

function Path({ steps, place, tint }: { steps: Planned[]; place: LayerProps["place"]; tint: string }) {
  const at = steps.map(s => [s, place(s.values)] as const).filter(([, c]) => c);
  if (!at.length) return null;
  const centre = ([, c]: (typeof at)[number]) => `${c!.x + c!.w / 2},${c!.y + c!.h / 2}`;
  return (
    <g>
      <polyline points={at.map(centre).join(" ")} fill="none" stroke={tint} stroke-width="1.5" stroke-opacity="0.6" />
      {at.map(([s, c], n) => (
        <circle data-order={n} cx={c!.x + c!.w / 2} cy={c!.y + c!.h / 2} r="3" fill={tint}><title>{call(s.row.v.action, s.values)}</title></circle>
      ))}
    </g>
  );
}

function Planning({ of, place, tint }: LayerProps) {
  return <g>{untaken(of("Plan"), of("Step")).map(steps => <Path steps={steps} place={place} tint={tint} />)}</g>;
}

const describe: Describe = {
  Plan: group => [...latest(group, r => r.v.e).values()].map(last =>
    `published a plan for ${local(last.v.want)}: ` + walked(group.filter(r => r.v.e === last.v.e)).map(s => call(s.row.v.action, s.values)).join(" → ")),
};

export const layer: Layer = { name: "planning", order: 20, Layer: Planning, describe };
