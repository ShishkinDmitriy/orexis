/*  A REPLAY RENDERED WITH NO BROWSER, for the tests: the same pane and the same log the page draws, as a string.
 *
 *    { data, pane: { scene, agents, at } }   → the pane's SVG, the agents shown together at instant index `at`
 *    { data, log: agents }                    → the lines those agents' log holds, as JSON
 */
import { renderToString } from "preact-render-to-string";
import type { Drawing } from "./index";
import { every, gather, log, Pane, prepare } from "./pane";

export function run(drawings: Drawing[], asked: any): string {
  const replay = prepare(asked.data);
  const { scenes, layers } = gather(drawings);
  if (asked.pane) {
    const scene = scenes.find(s => s.name === asked.pane.scene);
    if (!scene) throw new Error(`no scene ${asked.pane.scene} among ${scenes.map(s => s.name).join(", ")}`);
    const frame = scene.frame(every(replay));
    return renderToString(<Pane replay={replay} scene={scene} frame={frame} layers={layers} agents={asked.pane.agents}
                                at={replay.instants[asked.pane.at]} />);
  }
  return JSON.stringify((asked.log as string[]).flatMap(a => log(drawings, replay.rows[a] ?? [])).map(l => l.text));
}
