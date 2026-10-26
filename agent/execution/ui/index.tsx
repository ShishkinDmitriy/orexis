/*  EXECUTION, DRAWN — each step in flight: taken and not yet answered, as the events execution keeps in the journal say
 *  it (`events.py`: `execution:StepTaken` when a step is taken and `execution:StepAnswered` when the world answers it),
 *  read by `ui/Step.rq` beside this.
 *
 *  A layer, on whatever scene the world's domain draws: a step in flight is outlined, in the agent's colour, where the
 *  scene places the values it takes. The log says each step as it was taken and as it was answered.
 */
import type { Describe, Layer, LayerProps, Row, Value } from "@orexis/ui";
import { call, latest, local, pivot } from "@orexis/ui";

/** Every act whose latest event is its taking: taken, and not yet answered — with the values its step takes. */
export function inFlight(rows: Row[]): { row: Row; values: Record<string, Value> }[] {
  const last = latest(rows, r => r.v.act);
  return [...last.values()].filter(r => local(r.v.kind) === "StepTaken" && r.v.taken === true)
    .map(r => pivot(rows.filter(x => x.v.e === r.v.e), "act").get(r.v.act)!);
}

function Execution({ of, place, tint }: LayerProps) {
  return (
    <g>{inFlight(of("Step")).map(({ row, values }) => {
      const c = place(values);
      return c && (
        <rect data-flight={local(row.v.action)} x={c.x + 1} y={c.y + 1} width={c.w - 2} height={c.h - 2} rx="4" fill="none" stroke={tint} stroke-width="2">
          <title>in flight: {call(row.v.action, values)} for {local(row.v.want)}</title>
        </rect>
      );
    })}</g>
  );
}

const describe: Describe = {
  Step: group => [...pivot(group, "e").values()].map(({ row, values }) => {
    const step = call(row.v.action, values);
    if (local(row.v.kind) === "StepTaken") return row.v.taken === true ? `took ${step}` : `could not take ${step}`;
    return row.v.landed === true ? `${step} landed` : `${step} failed`;
  }),
};

export const layer: Layer = { name: "execution", order: 30, Layer: Execution, describe };
