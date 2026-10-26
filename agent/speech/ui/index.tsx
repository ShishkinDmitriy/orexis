/*  SPEECH, IN THE HISTORY — the exchange between agents: each statement the agent said, to whom, and each it heard, as
 *  the events speech keeps in the journal say it (`events.py`), read by `Statements.rq` beside this.
 *
 *  A statement is no place on a scene, so speech draws nothing on one: it says each statement in the log, by the kind
 *  the statement says it is — a question, an answer, a commitment, in the words of whoever spoke it — and the latest
 *  exchange as a status under the scene.
 */
import type { Describe, Layer, Row, StatusProps } from "@orexis/ui";
import { latest, local } from "@orexis/ui";

/** Each statement once, said or heard: the kinds it says it is and whom it was told to. */
function statements(rows: Row[]): { row: Row; kinds: string[]; to: string[] }[] {
  const by = new Map<string, { row: Row; kinds: Set<string>; to: Set<string> }>();
  for (const r of rows) {
    const s = by.get(String(r.v.e)) ?? { row: r, kinds: new Set(), to: new Set() };
    if (r.v.type !== undefined) s.kinds.add(local(r.v.type));
    if (r.v.to !== undefined) s.to.add(local(r.v.to));
    by.set(String(r.v.e), s);
  }
  return [...by.values()].map(s => ({ row: s.row, kinds: [...s.kinds].sort(), to: [...s.to].sort() }));
}

function said({ row, kinds, to }: ReturnType<typeof statements>[number]): string {
  const what = kinds.join(", ") || local(row.v.statement);
  return local(row.v.kind) === "Said" ? `said ${what}${to.length ? ` to ${to.join(", ")}` : ""}` : `heard ${what}`;
}

/** The latest statement said and the latest heard, in a line under the scene. */
function Exchange({ agent, of }: StatusProps) {
  const last = latest(statements(of("Statements")).map(s => s.row), r => local(r.v.kind));
  const shown = statements(of("Statements")).filter(s => [...last.values()].some(r => r.v.e === s.row.v.e));
  return shown.length ? <span data-exchange={agent}>{agent}: {shown.map(said).join("; ")}</span>
                      : <span class="empty">{agent}: nothing said or heard</span>;
}

const describe: Describe = { Statements: group => statements(group).map(said) };

export const layer: Layer = { name: "speech", order: 40, Status: Exchange, describe };
