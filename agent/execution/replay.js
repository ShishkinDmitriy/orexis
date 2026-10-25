/*  EXECUTION, DRAWN — each step in flight: taken and not yet answered, as the history execution writes says it
 *  (`events.py`: a `Step` point when a step is taken and another when the world answers it, both tagged alike).
 *
 *  A layer, on whatever scene the world's domain draws: a step in flight is outlined where the scene places the
 *  values it takes. The log says each step as it was taken and as it was answered.
 */
(function () {
  const { html } = replay;
  const step = tags => `${tags.action}(` + Object.entries(tags).filter(([k]) => !["action", "want"].includes(k))
    .sort().map(([k, v]) => `${k}=${v}`).join(", ") + ")";

  function Layer({ points, place }) {
    const latest = replay.latest(points.filter(p => p.measurement === "Step"), p => JSON.stringify(Object.entries(p.tags).sort()));
    const flying = [...latest.values()].filter(p => p.fields.taken === true);
    return html`<g>${flying.map(p => {
      const c = place(p.tags);
      return c && html`<rect data-flight=${p.tags.action} x=${c.x + 1} y=${c.y + 1} width=${c.w - 2} height=${c.h - 2} rx="4" fill="none"
        stroke="var(--plan)" stroke-width="2"><title>in flight: ${step(p.tags)}</title></rect>`;
    })}</g>`;
  }

  replay.layer("execution", {
    order: 30,
    Layer,
    describe: {
      Step: group => group.map(p => ("landed" in p.fields
        ? `${step(p.tags)} ${p.fields.landed ? "landed" : p.fields.timed_out ? "timed out" : "failed"}`
        : `${p.fields.taken ? "took" : "could not take"} ${step(p.tags)}`) + ` for ${p.tags.want}`),
    },
  });
})();
