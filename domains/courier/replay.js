/*  THE COURIER, DRAWN — the road as a grid of whole numbers, each van where its fix puts it and each contact where
 *  its offsets put it from the van carrying it (knowledge/domain/onboarding/replay.md).
 *
 *  A scene: the ground every package's layer stands on. It reads the courier's own words off the history — a fix's
 *  `Column` and `Row`, a contact's `RelativeColumn` and `RelativeRow` — and what the world states of the things they
 *  name: the van a contact is hosted by, the van it is a sample of, and the range its sensors declare, outside which
 *  a reading sees nothing. `place` puts on a cell whatever names a column and a row in the courier's words: a
 *  holding's `x` and `y`, a drive's `toX` and `toY`.
 */
(function () {
  const { html } = replay;
  const CELL = 28, PAD = 1;
  const FIX = { across: "Column", down: "Row" }, OFFSET = { across: "RelativeColumn", down: "RelativeRow" };
  const PALETTE = ["#8e44ad", "#1f9e89", "#e8590c", "#3a86ff", "#c2255c", "#5c940d", "#b08900", "#495057"];

  const one = (things, thing, word) => ((things[thing] || {})[word] || [])[0];
  const column = v => Number(v.x ?? v.toX), row = v => Number(v.y ?? v.toY);

  /** The range a sensor declares, as its capability's measurement range says it, or none. */
  function range(things, sensor) {
    for (const capability of (things[sensor] || {}).hasSystemCapability || [])
      for (const property of capability.hasSystemProperty || [])
        if ((property.type || []).includes("MeasurementRange")) return [property.minValue[0], property.maxValue[0]];
    return null;
  }

  /** Per feature, its latest reading on both axes of `words`, of the points given. */
  function latestOn(points, words) {
    const by = {};
    for (const p of points) {
      const axis = p.measurement === words.across ? "across" : p.measurement === words.down ? "down" : null;
      if (axis && p.tags.feature) (by[p.tags.feature] = by[p.tags.feature] || {})[axis] = p;
    }
    return by;
  }

  /** Every van as fixed, and every contact as seen from the van hosting it, at the latest of the points given. */
  function positions(points, things) {
    const fixed = [], seen = [];
    for (const [f, r] of Object.entries(latestOn(points, FIX)))
      if (r.across && r.down) fixed.push({ name: f, x: r.across.fields.value, y: r.down.fields.value });
    for (const [f, r] of Object.entries(latestOn(points, OFFSET))) {
      if (!r.across || !r.down) continue;
      const host = fixed.find(v => v.name === one(things, f, "isHostedBy"));
      const inside = p => { const span = range(things, p.tags.sensor); return !span || (span[0] <= p.fields.value && p.fields.value <= span[1]); };
      if (host && inside(r.across) && inside(r.down))
        seen.push({ name: one(things, f, "isSampleOf") || f, sample: f, x: host.x + r.across.fields.value, y: host.y + r.down.fields.value });
    }
    return { fixed, seen };
  }

  replay.scene("road", {
    label: "the road",
    frame(points, things) {
      const cells = [];
      const at = [...new Set(points.map(p => p.t))];
      const by = points.reduce((m, p) => ((m[p.t] = m[p.t] || []).push(p), m), {});
      let upto = [];
      for (const t of at.sort((a, b) => a - b)) {
        upto = upto.concat(by[t]);
        const { fixed, seen } = positions(upto, things);
        cells.push(...fixed, ...seen);
      }
      for (const p of points) {
        const v = p.measurement === "Holding" ? p.fields : p.tags;
        if (!Number.isNaN(column(v)) && !Number.isNaN(row(v))) cells.push({ x: column(v), y: row(v) });
      }
      const xs = cells.map(c => c.x), ys = cells.map(c => c.y);
      const box = cells.length ? [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)] : [0, 0, 0, 0];
      const names = [...new Set(cells.filter(c => c.name && c.name !== c.sample).map(c => c.name))].sort();
      return {
        box, width: (box[2] - box[0] + 1 + 2 * PAD) * CELL, height: (box[3] - box[1] + 1 + 2 * PAD) * CELL + 12,
        colour: name => (names.includes(name) ? PALETTE[names.indexOf(name) % PALETTE.length] : "var(--seen)"),
        place(values) {
          const x = column(values), y = row(values);
          if (Number.isNaN(x) || Number.isNaN(y)) return null;
          return { x: (x - box[0] + PAD) * CELL, y: (y - box[1] + PAD) * CELL, w: CELL, h: CELL };
        },
      };
    },
    Scene({ points, things, frame }) {
      const [x0, y0, x1, y1] = frame.box, cells = [];
      for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) {
        const c = frame.place({ x, y });
        cells.push(html`<rect x=${c.x + 1} y=${c.y + 1} width=${CELL - 2} height=${CELL - 2} rx="3" fill="var(--cell)" />`);
      }
      const labels = [];
      for (let x = x0; x <= x1; x++) labels.push(html`<text x=${frame.place({ x, y: y0 }).x + CELL / 2} y=${CELL * 0.7} text-anchor="middle" fill="var(--muted)">${x}</text>`);
      for (let y = y0; y <= y1; y++) labels.push(html`<text x=${CELL / 2} y=${frame.place({ x: x0, y }).y + CELL * 0.62} text-anchor="middle">${y}</text>`);
      const { fixed, seen } = positions(points, things);
      return html`<g>${cells}${labels}
        ${seen.map(c => { const p = frame.place(c); return html`<rect data-seen=${c.name} data-x=${c.x} data-y=${c.y} x=${p.x + 6} y=${p.y + 6}
            width=${CELL - 12} height=${CELL - 12} rx="2" fill="none" stroke=${frame.colour(c.name)} stroke-width="2"><title>seen: ${c.name}</title></rect>`; })}
        ${fixed.map(c => { const p = frame.place(c); return html`<g data-fixed=${c.name} data-x=${c.x} data-y=${c.y}>
            <circle cx=${p.x + CELL / 2} cy=${p.y + CELL / 2} r=${CELL / 3} fill=${frame.colour(c.name)}><title>fixed: ${c.name}</title></circle>
            <text x=${p.x + CELL / 2} y=${p.y + CELL - 1} text-anchor="middle" style="font-size:7px">${c.name}</text></g>`; })}
      </g>`;
    },
  });

  //  A FIX AND AN OFFSET ARE DRAWN, not said: the scene shows them, so the log leaves them out.
  for (const m of [FIX.across, FIX.down, OFFSET.across, OFFSET.down]) replay.describe(m, () => null);
})();
