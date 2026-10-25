/*  COORDINATION, DRAWN — what the agent asked with, what it laid of its peers as they said it and as it foresaw them,
 *  and its conflicts, from the history coordination writes (`events.py`): each set said whole, so what stands at an
 *  instant is the latest set said of each origin, peer and constraint.
 *
 *  A layer, on whatever scene the world's domain draws: a holding is put where the scene places the values it holds
 *  on the constraint's key, and a holding is bright while its period holds, faint before it. Coordination's own
 *  colours: blue asked, orange said, red foreseen.
 */
(function () {
  const { html } = replay;
  const COLOUR = { asked: "var(--asked)", said: "var(--said)", foreseen: "var(--foreseen)" };
  const KEPT = new Set(["from", "until", "taken"]);
  const key = p => `${p.tags.origin}|${p.tags.peer}|${p.tags.constraint}`;
  const values = h => Object.fromEntries(Object.entries(h.fields).filter(([k]) => !KEPT.has(k)));
  const shown = v => (typeof v === "number" ? +v.toFixed(3) : v);

  function Layer({ points, at, place, frame }) {
    const held = [];
    for (const members of replay.sets(points, "Holdings", "Holding", key).values())
      for (const h of members) {
        const p = place(values(h));
        if (!p) continue;
        const from = h.fields.from ? Date.parse(h.fields.from) : -Infinity, until = h.fields.until ? Date.parse(h.fields.until) : Infinity;
        const now = from <= at && at < until, origin = h.tags.origin;
        const fill = origin === "said" ? (now ? 0.4 : 0.14) : origin === "foreseen" ? (now ? 0.28 : 0.1) : (now ? 0.25 : 0.08);
        held.push(html`<rect data-origin=${origin} data-thing=${h.tags.thing} data-now=${now} x=${p.x + 3} y=${p.y + 3} width=${p.w - 6} height=${p.h - 6} rx="3"
          fill=${COLOUR[origin]} fill-opacity=${fill} stroke=${COLOUR[origin]} stroke-width="1.5"
          stroke-dasharray=${origin === "foreseen" ? "3 2" : origin === "said" && !h.fields.taken ? "4 2" : undefined}><title>${origin}: ${h.tags.thing}</title></rect>`);
      }
    const concluded = [...replay.latest(points.filter(p => p.measurement === "Conflicts"), () => "all").values()][0];
    const standing = concluded ? points.filter(p => p.measurement === "Conflict" && p.t === concluded.t && p.fields.standing) : [];
    return html`<g>${held}
      ${standing.map((c, n) => html`<text data-conflict=${c.tags.peer} x="4" y=${frame.height - 3 - 9 * n} fill="var(--conflict)" style="font-size:7px">
        conflict with ${c.tags.peer}${c.fields.silent ? ", silent" : ""}, round ${c.fields.round}${c.fields.won_by ? ", won by " + c.fields.won_by : ""}</text>`)}</g>`;
  }

  replay.layer("coordination", {
    order: 10,
    Layer,
    describe: {
      Holdings: group => group.filter(h => h.fields.count === 0).map(h => `${h.tags.origin} nothing of ${h.tags.peer}`),
      Holding: group => {
        const by = group.reduce((m, h) => ((m[key(h)] = m[key(h)] || []).push(h), m), {});
        return Object.values(by).map(hs => `${hs[0].tags.origin}${hs[0].tags.origin === "asked" ? "" : " of " + hs[0].tags.peer}: `
          + hs.map(h => `${h.tags.thing} ` + Object.entries(values(h)).sort().map(([k, v]) => `${k}=${shown(v)}`).join(" ")).join(", "));
      },
      Conflicts: group => (group.some(c => c.fields.count === 0) ? "no conflict" : null),
      Conflict: group => group.map(c => `conflict with ${c.tags.peer} over ${c.tags.constraint}: ${c.fields.standing ? "standing" : "not standing"}`
        + `${c.fields.silent ? ", silent" : ""}, round ${c.fields.round}${c.fields.won_by ? ", won by " + c.fields.won_by : ""}`),
    },
  });
})();
