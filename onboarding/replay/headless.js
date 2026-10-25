/*  A REPLAY RENDERED WITH NO BROWSER, for the tests: the page's scripts run in a context of their own, and one pane
 *  or one agent's log is answered on stdout.
 *
 *    node headless.js < {"scripts": [paths], "data": {...}, "pane": [scene, agent, instant]}   → the pane's SVG
 *    node headless.js < {"scripts": [paths], "data": {...}, "log": agent}                      → the log, as JSON
 */
const fs = require("fs"), vm = require("vm"), path = require("path");

const asked = JSON.parse(fs.readFileSync(0, "utf8"));
const context = vm.createContext({ console });
context.globalThis = context;
context.self = context;
const vendor = path.join(__dirname, "vendor");
for (const file of [path.join(vendor, "preact.umd.js"), path.join(vendor, "hooks.umd.js"), path.join(vendor, "htm.umd.js"),
                    path.join(vendor, "render-to-string.umd.js"), path.join(__dirname, "core.js"), ...asked.scripts])
  vm.runInContext(fs.readFileSync(file, "utf8"), context, { filename: file });

const replay = context.replay, data = replay.prepare(asked.data);
if (asked.pane) {
  const [name, agent, n] = asked.pane;
  const scene = replay.scenes.find(s => s.name === name);
  const frame = scene.frame(Object.values(data.points).flat(), data.things);
  process.stdout.write(context.preactRenderToString.render(replay.pane(data, scene, frame, agent, data.instants[n])));
} else {
  process.stdout.write(JSON.stringify(replay.log(data.points[asked.log] || [], data.things).map(l => l.text)));
}
