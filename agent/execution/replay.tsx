/*  EXECUTION, DRAWN — each step in flight: taken and not yet answered, as the history execution writes says it
 *  (`events.py`: a `Step` point when a step is taken and another when the world answers it, both tagged alike).
 *
 *  A layer, on whatever scene the world's domain draws: a step in flight is outlined, in the agent's colour, where the
 *  scene places the values it takes. The log says each step as it was taken and as it was answered.
 */
import type { Describe, Layer, LayerProps, Of, Point } from "@orexis/replay";
import { call, latest } from "@orexis/replay";

/** Every step whose latest point is its taking: taken, and not yet answered. */
export function inFlight(of: Of): Point[] {
  const steps = latest(of("Step"), p => JSON.stringify(Object.entries(p.tags).sort()));
  return [...steps.values()].filter(p => p.fields.taken === true);
}

function Execution({ of, place, tint }: LayerProps) {
  return (
    <g>{inFlight(of).map(p => {
      const c = place(p.tags);
      return c && (
        <rect data-flight={p.tags.action} x={c.x + 1} y={c.y + 1} width={c.w - 2} height={c.h - 2} rx="4" fill="none" stroke={tint} stroke-width="2">
          <title>in flight: {call(p.tags, ["want"])}</title>
        </rect>
      );
    })}</g>
  );
}

const describe: Describe = {
  Step: group => group.map(p => ("landed" in p.fields
    ? `${call(p.tags, ["want"])} ${p.fields.landed ? "landed" : p.fields.timed_out ? "timed out" : "failed"}`
    : `${p.fields.taken ? "took" : "could not take"} ${call(p.tags, ["want"])}`) + ` for ${p.tags.want}`),
};

export const layer: Layer = { name: "execution", order: 30, Layer: Execution, describe };
