/*  THE REPLAY'S CORE — what every world's replay shares, and no word of any package's.
 *
 *  A replay is a world's run drawn from its agents' history. The core holds the instants, a pane per agent and the
 *  log of what each agent did; everything DRAWN is a package's own, registered by the `replay.js` beside its code:
 *
 *    replay.scene(name, { label, frame(points, things), Scene })    a domain's picture: the ground the others stand on
 *    replay.layer(name, { order, Layer, describe })                a package's own drawing of what it decided
 *    replay.describe(measurement, fn)                              a log line for a measurement, where the default will not do
 *
 *  `frame` is asked once with every agent's points and what the world states of the things they name, and answers
 *  `{ width, height, place(values) }` — `place` the one thing a layer needs of a scene: given the values a point
 *  carries, in the domain's own words, where they put it on the scene, `{ x, y, w, h }`, or nothing. A scene and its
 *  layers draw SVG inside one pane per agent, each handed the agent, the points the agent wrote up to the instant
 *  shown, the instant, the frame and the things.
 */
(function () {
  const { h, render } = preact;
  const html = htm.bind(h);
  const scenes = [], layers = [], describers = {};

  const replay = (globalThis.replay = {
    html, h, hooks: preactHooks,
    scenes, layers, describers,
    scene(name, spec) { scenes.push({ name, ...spec }); },
    layer(name, spec) {
      layers.push({ name, order: 0, ...spec });
      layers.sort((a, b) => a.order - b.order);
      for (const [m, fn] of Object.entries(spec.describe || {})) describers[m] = fn;
    },
    describe(measurement, fn) { describers[measurement] = fn; },

    /** Every point at or before `at`, the points being in time order. */
    upto(points, at) {
      let i = points.length;
      while (i > 0 && points[i - 1].t > at) i--;
      return points.slice(0, i);
    },
    /** The latest point per key, of the points given. */
    latest(points, keyOf) {
      const out = new Map();
      for (const p of points) { const k = keyOf(p); if (k !== undefined && k !== null) out.set(k, p); }
      return out;
    },
    /** A set said whole: per key, the members written at the instant of the latest `head` point for that key. */
    sets(points, head, member, keyOf) {
      const heads = replay.latest(points.filter(p => p.measurement === head), keyOf), out = new Map();
      for (const [k, hp] of heads) out.set(k, points.filter(p => p.measurement === member && p.t === hp.t && keyOf(p) === k));
      return out;
    },
    /** Each point's own line, where nothing describes its measurement: its measurement, tags and fields. */
    line(p) {
      const shown = v => (typeof v === "number" ? +v.toFixed(3) : v);
      const tags = Object.entries(p.tags).sort().map(([k, v]) => `${k}=${v}`).join(" ");
      const fields = Object.entries(p.fields).sort().map(([k, v]) => `${k}=${shown(v)}`).join(" ");
      return `${p.measurement} ${tags} ${fields}`.trim();
    },

    /** What each agent did, a line per thing at the instant it did it: every instant's points of one measurement
     *  handed together to whatever describes the measurement, which answers lines, or none to leave them out. */
    log(points, things) {
      const out = [], groups = new Map();
      for (const p of points) {
        const k = `${p.t}|${p.measurement}`;
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k).push(p);
      }
      for (const group of groups.values()) {
        const fn = describers[group[0].measurement];
        const said = fn ? fn(group, things) : group.map(replay.line);
        for (const text of [].concat(said || [])) out.push({ t: group[0].t, text });
      }
      return out;
    },

    /** The panes of `scene` for one agent at instant `at`, as a vnode: what the tests render headless. */
    pane(data, scene, frame, agent, at) {
      const points = replay.upto(data.points[agent] || [], at);
      const props = { agent, points, at, frame, things: data.things, place: frame.place };
      return html`<svg viewBox="0 0 ${frame.width} ${frame.height}" role="img" aria-label="${scene.label || scene.name} as ${agent} has it">
        <${scene.Scene} ...${props} />
        ${layers.map(l => html`<g data-layer=${l.name}><${l.Layer} ...${props} /></g>`)}
      </svg>`;
    },

    /** Turn the page's data into what the components read: each point's instant as milliseconds, in time order. */
    prepare(data) {
      data.instants = data.instants.map(Date.parse);
      for (const a of Object.keys(data.points)) {
        data.points[a] = data.points[a].map(p => ({ ...p, t: Date.parse(p.time) })).sort((x, y) => x.t - y.t);
      }
      return data;
    },

    mount(data, root) {
      replay.prepare(data);
      render(html`<${App} data=${data} />`, root);
    },
  });

  function clock(t) { return t === undefined ? "" : new Date(t).toISOString().replace("T", " ").replace(".000Z", "Z"); }

  function App({ data }) {
    const { useState, useEffect, useMemo } = preactHooks;
    const [i, setI] = useState(0);
    const [playing, setPlaying] = useState(false);
    const last = data.instants.length - 1, at = data.instants[i];
    const every = useMemo(() => Object.values(data.points).flat(), [data]);
    const frames = useMemo(() => scenes.map(s => s.frame(every, data.things)), [data]);
    const logs = useMemo(() => Object.fromEntries(data.agents.map(a => [a, replay.log(data.points[a] || [], data.things)])), [data]);
    useEffect(() => {
      if (!playing) return;
      const id = setInterval(() => setI(n => { if (n >= last) { setPlaying(false); return n; } return n + 1; }), 500);
      return () => clearInterval(id);
    }, [playing, last]);
    useEffect(() => {
      const key = e => { if (e.key === "ArrowRight") setI(n => Math.min(last, n + 1)); if (e.key === "ArrowLeft") setI(n => Math.max(0, n - 1)); };
      addEventListener("keydown", key);
      return () => removeEventListener("keydown", key);
    }, [last]);
    if (!data.instants.length) return html`<main><p class="empty">This history holds nothing to replay.</p></main>`;
    return html`
      <header>
        <h1>${data.world} replay</h1>
        <div class="bar">
          <button type="button" onClick=${() => { if (i >= last) setI(0); setPlaying(!playing); }}>${playing ? "Pause" : "Play"}</button>
          <button type="button" aria-label="previous instant" onClick=${() => setI(Math.max(0, i - 1))}>◀</button>
          <button type="button" aria-label="next instant" onClick=${() => setI(Math.min(last, i + 1))}>▶</button>
          <input type="range" min="0" max=${last} value=${i} aria-label="instant" onInput=${e => setI(+e.target.value)} />
          <span class="instant">${clock(at)} (${i + 1} of ${last + 1})</span>
        </div>
      </header>
      <main>
        ${scenes.map((s, n) => html`<section>
          <h2>${s.label || s.name}</h2>
          <div class="row">${data.agents.map(a => html`<div class="pane"><h3>${a}</h3>${replay.pane(data, s, frames[n], a, at)}</div>`)}</div>
        </section>`)}
        ${data.agents.map(a => html`<section class="pane">
          <h3>${a} — what it did</h3>
          <${Log} lines=${logs[a]} at=${at} />
        </section>`)}
      </main>`;
  }

  function Log({ lines, at }) {
    const { useRef, useEffect } = preactHooks;
    const ref = useRef(null);
    const shown = lines.filter(l => l.t <= at);
    useEffect(() => {                       // the list scrolls to the instant shown, and the page stays where it is
      const list = ref.current, now = list && list.querySelector(".now");
      if (now) list.scrollTop = now.offsetTop - list.offsetTop - 40;
    }, [at]);
    if (!lines.length) return html`<p class="empty">nothing recorded</p>`;
    return html`<ol class="log" ref=${ref}>${shown.map(l => html`<li class=${l.t === at ? "now" : ""}><time>${clock(l.t).slice(11, 19)}</time>${l.text}</li>`)}</ol>`;
  }
})();
