/*  PLANNING, DRAWN — the latest plan published for each want, as a path through the places its steps put things, from
 *  the history planning writes (`events.py`: a `Plan` point per step). A step answered since the plan was published
 *  is walked and left off the path, read off execution's `Step`, the word planning hands its steps down in.
 *
 *  A layer, on whatever scene the world's domain draws: a step is put where the scene places the values it takes, in
 *  the agent's colour; a step taking nothing the scene places is left off the path and said in the log.
 */
import type { Describe, Layer, LayerProps, Of, Point } from "@orexis/replay";
import { at, call, latest } from "@orexis/replay";

const OWN = ["want", "plan", "order"];
const filling = (tags: Record<string, string>) => JSON.stringify(Object.entries(tags).filter(([k]) => k !== "plan" && k !== "order").sort());

/** The steps of the latest plan published for each want, less those answered since it was. */
export function untaken(of: Of): Point[][] {
  const plans = latest(of("Plan"), p => p.tags.want);
  const walked = of("Step").filter(p => "landed" in p.fields);
  return [...plans.values()].map(last => at(of("Plan"), last.t)
    .filter(p => p.tags.want === last.tags.want)
    .sort((a, b) => +a.tags.order - +b.tags.order)
    .filter(p => !walked.some(w => w.t >= p.t && filling(w.tags) === filling(p.tags))));
}

function Path({ steps, place, tint }: { steps: Point[]; place: LayerProps["place"]; tint: string }) {
  const at = steps.map(p => [p, place(p.tags)] as const).filter(([, c]) => c);
  if (!at.length) return null;
  const centre = ([, c]: (typeof at)[number]) => `${c!.x + c!.w / 2},${c!.y + c!.h / 2}`;
  return (
    <g data-plan={steps[0].tags.want}>
      <polyline points={at.map(centre).join(" ")} fill="none" stroke={tint} stroke-width="1.5" stroke-opacity="0.6" />
      {at.map(([p, c]) => (
        <circle data-order={p.tags.order} cx={c!.x + c!.w / 2} cy={c!.y + c!.h / 2} r="3" fill={tint}><title>{call(p.tags, OWN)}</title></circle>
      ))}
    </g>
  );
}

function Planning({ of, place, tint }: LayerProps) {
  return <g>{untaken(of).map(steps => <Path steps={steps} place={place} tint={tint} />)}</g>;
}

const describe: Describe = {
  Plan: group => {
    const by = new Map<string, Point[]>();
    for (const p of group) by.set(p.tags.plan, [...(by.get(p.tags.plan) ?? []), p]);
    return [...by.values()].map(ps => `published a plan for ${ps[0].tags.want}: `
      + ps.sort((a, b) => +a.tags.order - +b.tags.order).map(p => call(p.tags, OWN)).join(" → "));
  },
};

export const layer: Layer = { name: "planning", order: 20, Layer: Planning, describe };
