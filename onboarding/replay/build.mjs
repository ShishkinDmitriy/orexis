/*  The one build a replay has: esbuild bundling an entry `orexis-replay` writes — the core and every drawing the
 *  world uses — into one script, for the page (`browser`, an IIFE) or for the tests' headless render (`node`).
 *
 *    node build.mjs <entry.tsx> <out.js> <browser|node>
 */
import * as esbuild from "esbuild";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "..", "..");
const [entry, outfile, platform] = process.argv.slice(2);
await esbuild.build({
  entryPoints: [entry],
  outfile,
  bundle: true,
  platform,
  format: platform === "node" ? "cjs" : "iife",
  jsx: "automatic",
  jsxImportSource: "preact",
  alias: { "@orexis/replay": path.join(here, "core") },
  nodePaths: [path.join(root, "node_modules")],
  minify: platform !== "node",
  legalComments: "none",
  logLevel: "error",
});
