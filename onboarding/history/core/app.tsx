/*  THE PAGE: the instants on a scrubber, the agents to show picked from however many the world has, each scene once
 *  with every agent shown on it — or side by side, a pane per agent, to compare what two believed — and the log of
 *  what the agents shown did, near the instant shown. */
import { render } from "preact";
import { useEffect, useMemo, useState } from "preact/hooks";
import type { Drawing } from "./index";
import { colours, every, gather, log, Pane, prepare, type Line, type Raw, type History } from "./pane";

/** How many agents are shown at first: every one of a small world, and the first few of a large one. */
const AT_FIRST = 4;
/** How many of the log's lines up to the instant shown are kept on the page. */
const LINES = 300;

function clock(t: number | undefined) {
  return t === undefined ? "" : new Date(t).toISOString().replace("T", " ").replace(".000Z", "Z");
}

function App({ history, drawings }: { history: History; drawings: Drawing[] }) {
  const { scenes, layers } = useMemo(() => gather(drawings), [drawings]);
  const frames = useMemo(() => { const all = every(history); return scenes.map(s => s.frame(all)); }, [history, scenes]);
  const lines = useMemo(() => Object.values(history.rows).flatMap(rs => log(drawings, rs)).sort((a, b) => a.t - b.t),
                        [history, drawings]);
  const colour = colours(history.agents);
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [shown, setShown] = useState<string[]>(history.agents.slice(0, AT_FIRST));
  const [apart, setApart] = useState(false);
  const [who, setWho] = useState("");
  const [grep, setGrep] = useState("");
  const last = history.instants.length - 1, at = history.instants[Math.min(i, last)];
  //  LIVE, THE LAST INSTANT IS FOLLOWED: a page standing at the end moves on as the run does.
  const [following, setFollowing] = useState(history.live);
  useEffect(() => { if (following) setI(Math.max(0, last)); }, [following, last]);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => setI(n => { if (n >= last) { setPlaying(false); return n; } return n + 1; }), 500);
    return () => clearInterval(id);
  }, [playing, last]);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === "INPUT" && (e.target as HTMLInputElement).type === "text") return;
      if (e.key === "ArrowRight") setI(n => Math.min(last, n + 1));
      if (e.key === "ArrowLeft") setI(n => Math.max(0, n - 1));
    };
    addEventListener("keydown", key);
    return () => removeEventListener("keydown", key);
  }, [last]);

  if (!history.instants.length) return <main><p class="empty">{history.live ? "Nothing yet — waiting for the agents." : "This history holds nothing yet."}</p></main>;
  const toggle = (a: string) => setShown(s => (s.includes(a) ? s.filter(x => x !== a) : history.agents.filter(x => x === a || s.includes(x))));
  const listed = history.agents.filter(a => a.includes(who));
  return (
    <>
      <header>
        <h1>{history.world} history</h1>
        <div class="bar">
          <button type="button" onClick={() => { if (i >= last) setI(0); setPlaying(!playing); }}>{playing ? "Pause" : "Play"}</button>
          <button type="button" aria-label="previous instant" onClick={() => setI(Math.max(0, i - 1))}>◀</button>
          <button type="button" aria-label="next instant" onClick={() => setI(Math.min(last, i + 1))}>▶</button>
          <input type="range" min="0" max={last} value={i} aria-label="instant"
                 onInput={e => { const n = +(e.target as HTMLInputElement).value; setI(n); setFollowing(history.live && n >= last); }} />
          <span class="instant">{clock(at)} ({Math.min(i, last) + 1} of {last + 1})</span>
          {history.live && <label><input type="checkbox" checked={following} onChange={() => setFollowing(!following)} /> live</label>}
        </div>
        <div class="bar agents">
          <input type="text" placeholder={`${history.agents.length} agents — filter`} value={who} onInput={e => setWho((e.target as HTMLInputElement).value)} />
          <button type="button" onClick={() => setShown(listed)}>all</button>
          <button type="button" onClick={() => setShown([])}>none</button>
          <label><input type="checkbox" checked={apart} onChange={() => setApart(!apart)} /> side by side</label>
          <div class="chips">
            {listed.map(a => (
              <label class={shown.includes(a) ? "chip on" : "chip"} key={a}>
                <input type="checkbox" checked={shown.includes(a)} onChange={() => toggle(a)} />
                <i style={{ background: colour(a) }} />{a}
              </label>
            ))}
          </div>
        </div>
      </header>
      <main>
        {!shown.length && <p class="empty">No agent shown — pick one above.</p>}
        {shown.length > 0 && scenes.map((s, n) => (
          <section key={s.name}>
            <h2>{s.label}</h2>
            {apart
              ? <div class="row">{shown.map(a => (
                  <div class="pane" key={a}><h3><i style={{ background: colour(a) }} />{a}</h3>
                    <Pane history={history} scene={s} frame={frames[n]} layers={layers} agents={[a]} at={at} /></div>))}</div>
              : <div class="pane wide"><Pane history={history} scene={s} frame={frames[n]} layers={layers} agents={shown} at={at} /></div>}
          </section>
        ))}
        <section class="pane">
          <h3>What {shown.length === 1 ? shown[0] : "the agents shown"} did
            <input type="text" placeholder="filter lines" value={grep} onInput={e => setGrep((e.target as HTMLInputElement).value)} /></h3>
          <Log lines={lines} shown={shown} at={at} grep={grep} colour={colour} />
        </section>
      </main>
    </>
  );
}

function Log({ lines, shown, at, grep, colour }: { lines: Line[]; shown: string[]; at: number; grep: string; colour(a: string): string }) {
  const kept = lines.filter(l => l.t <= at && shown.includes(l.agent) && (!grep || l.text.includes(grep))).slice(-LINES);
  if (!kept.length) return <p class="empty">nothing yet</p>;
  return (
    <ol class="log" ref={el => { if (el) el.scrollTop = el.scrollHeight; }}>
      {kept.map((l, n) => (
        <li class={l.t === at ? "now" : ""} key={n}>
          <time>{clock(l.t).slice(11, 19)}</time><i style={{ background: colour(l.agent) }} title={l.agent} />{l.text}
        </li>
      ))}
    </ol>
  );
}

/** Every few seconds, a live page asks its server for the run as it now stands. */
const POLL_MS = 3000;

function Live({ first, drawings }: { first: Raw; drawings: Drawing[] }) {
  const [raw, setRaw] = useState(first);
  useEffect(() => {
    const id = setInterval(() => fetch("data.json").then(r => r.json()).then(setRaw).catch(() => {}), POLL_MS);
    return () => clearInterval(id);
  }, []);
  const history = useMemo(() => prepare(raw), [raw]);
  return <App history={history} drawings={drawings} />;
}

export function mount(drawings: Drawing[], raw: Raw, root: HTMLElement) {
  render(raw.live ? <Live first={raw} drawings={drawings} /> : <App history={prepare(raw)} drawings={drawings} />, root);
}
