/*  PLANNING, DRAWN — the latest plan published for each want, as a path through the places its steps put things,
 *  from the history planning writes (`events.py`: a `Plan` point per step). A step answered since the plan was
 *  published is walked and left off the path, read off execution's `Step`, the word planning hands its steps down in.
 *
 *  A layer, on whatever scene the world's domain draws: a step is put where the scene places the values it takes,
 *  and a step taking none the scene places is left off the path and said in the log.
 */
(function () {
  const { html } = replay;
  const filling = tags => JSON.stringify(Object.entries(tags).filter(([k]) => k !== "plan" && k !== "order").sort());
  const step = tags => `${tags.action}(` + Object.entries(tags).filter(([k]) => !["action", "want", "plan", "order"].includes(k))
    .sort().map(([k, v]) => `${k}=${v}`).join(", ") + ")";

  function Layer({ points, place }) {
    const plans = replay.latest(points.filter(p => p.measurement === "Plan"), p => p.tags.want);
    const walked = points.filter(p => p.measurement === "Step" && "landed" in p.fields);
    const paths = [];
    for (const latest of plans.values()) {
      const steps = points.filter(p => p.measurement === "Plan" && p.t === latest.t && p.tags.want === latest.tags.want)
        .sort((a, b) => a.tags.order - b.tags.order)
        .filter(p => !walked.some(w => w.t >= p.t && filling(w.tags) === filling(p.tags)));
      const at = steps.map(p => [p, place(p.tags)]).filter(([, c]) => c);
      if (!at.length) continue;
      paths.push(html`<g data-plan=${latest.tags.want}>
        <polyline points=${at.map(([, c]) => `${c.x + c.w / 2},${c.y + c.h / 2}`).join(" ")} fill="none" stroke="var(--plan)" stroke-width="1.5" stroke-opacity="0.6" />
        ${at.map(([p, c]) => html`<circle data-order=${p.tags.order} cx=${c.x + c.w / 2} cy=${c.y + c.h / 2} r="3" fill="var(--plan)"><title>${step(p.tags)}</title></circle>`)}
      </g>`);
    }
    return html`<g>${paths}</g>`;
  }

  replay.layer("planning", {
    order: 20,
    Layer,
    describe: {
      Plan: group => {
        const by = group.reduce((m, p) => ((m[p.tags.plan] = m[p.tags.plan] || []).push(p), m), {});
        return Object.values(by).map(ps => `published a plan for ${ps[0].tags.want}: `
          + ps.sort((a, b) => a.tags.order - b.tags.order).map(p => step(p.tags)).join(" → "));
      },
    },
  });
})();
