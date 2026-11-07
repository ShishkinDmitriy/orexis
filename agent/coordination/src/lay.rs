//! WHAT AN AGENT LAYS OF A PEER'S HOLDINGS AS FORECASTS, as `agent/coordination/lay.py` lays them — a belief about the
//! peer's thing over each period, which the grounds take in where each begins.
//!
//! **WHILE A DRAW STANDS, BOTH LAY; ONCE DECIDED, THE LOSER LAYS ALL AND THE WINNER THE STEP IN FLIGHT.** **OF A SILENT
//! PEER THAT SAID NOTHING, WHERE ITS THINGS MAY BE**: each `coordination:Reach` a world's rules ship, asked as many
//! times as the agent's lookahead says, gives every place the thing may stand by then, each a node of its own, laid
//! from now for as many of the longest step a reach says; a place laid stands while a step of its window is left, and
//! none is laid where the agent's own step in flight lands. **ONLY WHAT THE AGENT'S OWN CONSTRAINTS ADMIT**. **AT EACH
//! INSTANT, EVERYTHING THE PEER MAY HOLD, BEGUN OR NOT** (`timeline`). Written where it changed — a forecast of the
//! agent's own, received, per holding laid — and forgotten when nothing lays it any more.

use std::collections::{BTreeMap, BTreeSet};

use oxigraph::model::{NamedNode, NamedOrBlankNode, Quad, Term};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, seconds, seconds_of};
use orexis::hash::hash_named_graph;
use orexis::ontology::{BELIEF, FORECAST, RECEIVED};
use orexis::stance::stance;
use orexis::store::{Store, iri, value};

use crate::holdings::{
    Holding, TEXTS_Q, asked, common, constraints_and_self, heard, holdings, key_of, of_kind, present, rows_of, scratch,
    sorted,
};
use crate::ontology::{
    CONSTRAINT_GRAPH, LOOKAHEAD, LOOKING, answer_graph, conflicts_graph, laid_graph, laid_root, question_graph,
};

const STANDING_Q: &str = "
SELECT ?c ?peer ?constraint ?draw ?silent WHERE { GRAPH $graph {
  ?c a coordination:Conflict ; coordination:with ?peer ; coordination:over ?constraint ; coordination:draw ?draw ;
     coordination:standing true . OPTIONAL { ?c coordination:silent ?silent } } }";

const WON_Q: &str = "SELECT ?w WHERE { $draw coordination:wonBy ?w } LIMIT 1";

/// EVERY GRAPH THE AGENT LAID BEFORE: its own forecasts, named under its laid root.
const LAID_Q: &str = "SELECT ?g WHERE { GRAPH $cat { ?g a orexis:ForecastGraph . FILTER(STRSTARTS(STR(?g), $root)) } }";

const ACTS_FOR_Q: &str = "SELECT ?t WHERE { $peer orexis:actsFor ?t } ORDER BY ?t";

const REACH_Q: &str = "SELECT ?text ?step WHERE { ?rule a coordination:Reach ; sh:construct ?text .
                                         OPTIONAL { ?rule coordination:stepS ?step }
                                         FILTER NOT EXISTS { ?rule sh:deactivated true } } ORDER BY ?rule";

const RULES_GRAPH: &str = "http://www.w3.org/ns/shacl#RulesGraph";

const PERIOD_Q: &str = "
SELECT ?start ?end WHERE { GRAPH $cat { $graph dcterms:temporal ?p . OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } LIMIT 1";

const HELD_Q: &str = "SELECT ?c WHERE { ?me a orexis:Self ; planning:holds ?c . ?c a planning:Constraint }";

fn named(iri: &str) -> NamedNode {
    NamedNode::new_unchecked(iri)
}

fn between(from: DateTime, to: DateTime) -> f64 {
    to.checked_sub(from).map_or(0.0, seconds_of)
}

/// Lay, as forecasts, the peers' holdings the self `me` of `store` yields to at `at`, and take back what it laid and
/// yields to no more; every graph written or forgotten.
pub fn lay(store: &Store, me: &str, at: DateTime) -> Result<Vec<String>, Error> {
    let Some(cat) = store.catalogue()? else {
        return Ok(Vec::new());
    };
    let beliefs = of_kind(store, &[BELIEF])?;
    let mut wanted: BTreeMap<String, Holding> = BTreeMap::new();
    let mut foreseen: BTreeMap<String, f64> = BTreeMap::new();
    for r in store.rows(&bind(STANDING_Q, &[("graph", Value::iri(conflicts_graph(me)))])?, &[])? {
        let (Some(peer), Some(constraint), Some(draw)) = (iri(&r, "peer"), iri(&r, "constraint"), iri(&r, "draw"))
        else {
            continue;
        };
        let winner = rows_of(store, WON_Q, &[("draw", Value::iri(draw.as_str()))], &beliefs)?
            .first()
            .and_then(|w| iri(w, "w"));
        let mut theirs = heard(store, &question_graph(&peer, me, &constraint))?;
        if theirs.is_empty() {
            theirs = heard(store, &answer_graph(&peer, me, &constraint))?;
        }
        let said = !theirs.is_empty();
        if winner.as_deref() == Some(me) {
            theirs.retain(|h| h.start.is_none() || h.taken);
        }
        if value(&r, "silent").as_deref() == Some("true") && !said {
            let looking = stance(store, LOOKAHEAD)?.unwrap_or(LOOKING) as i64;
            let ahead = looking + i64::from(winner.as_ref().is_some_and(|w| w != me));
            let landing: Vec<Holding> = holdings(store, &constraint, at)?
                .into_iter()
                .filter(|h| h.taken)
                .collect();
            let mut reached = Vec::new();
            for h in reach(store, &peer, &constraint, ahead, at)? {
                if !refused(store, &h, at, &landing)? {
                    reached.push(h);
                }
            }
            for h in &reached {
                if let Some(end) = h.end {
                    foreseen.insert(h.thing.clone(), between(at, end) / (ahead.max(1) as f64));
                }
            }
            theirs.extend(reached);
        }
        let mut kept = Vec::new();
        for h in theirs {
            if h.start.is_none() || !refused(store, &h, at, &[])? {
                kept.push(h);
            }
        }
        for (n, h) in timeline(&kept).into_iter().enumerate() {
            if h.end.is_none_or(|end| end > at) {
                wanted.insert(laid_graph(me, &peer, &constraint, n), h);
            }
        }
    }
    let text = bind(
        LAID_Q,
        &[
            ("cat", Value::iri(cat.as_str())),
            ("root", Value::raw(format!("\"{}\"", laid_root(me)))),
        ],
    )?;
    let laid: BTreeSet<String> = store.rows(&text, &[])?.iter().filter_map(|r| iri(r, "g")).collect();
    let mut written = Vec::new();
    for graph in laid.iter().filter(|g| !wanted.contains_key(*g)) {
        store.forget_graph(graph, Some(BELIEF))?;
        written.push(graph.clone());
    }
    for (graph, h) in &wanted {
        let held = if laid.contains(graph) {
            holding_in(store, graph)?
        } else {
            None
        };
        if let Some(held) = &held {
            let standing = foreseen.get(&h.thing).is_some_and(|step| {
                held.thing == h.thing && held.values == h.values && held.end.is_some_and(|end| between(at, end) > *step)
            });
            if held == h || standing {
                continue;
            }
        }
        store.forget_graph(graph, Some(BELIEF))?;
        let facts: String = h
            .values
            .iter()
            .map(|(p, v)| format!("<{}> <{p}> {v} . ", h.thing))
            .collect();
        let entry = store.entry(graph, &[FORECAST], RECEIVED, Some(me), h.start, h.end)?;
        store.update(&format!("INSERT DATA {{ GRAPH <{graph}> {{ {facts}}} {entry} }}"))?;
        hash_named_graph(store, graph, None)?;
        written.push(graph.clone());
    }
    Ok(written)
}

/// Every place a thing `peer` acts for may stand `ahead` of its steps on, as the world's reaches say: a holding per
/// place, of a node standing for the thing there, from `at` for `ahead` of the longest step a reach says.
fn reach(store: &Store, peer: &str, constraint: &str, ahead: i64, at: DateTime) -> Result<Vec<Holding>, Error> {
    let key = key_of(store, constraint)?;
    let reaches = rows_of(store, REACH_Q, &[], &of_kind(store, &[RULES_GRAPH])?)?;
    let texts: Vec<String> = reaches.iter().filter_map(|r| value(r, "text")).collect();
    if key.is_empty() || texts.is_empty() {
        return Ok(Vec::new());
    }
    let steps: Vec<f64> = reaches
        .iter()
        .filter_map(|r| value(r, "step"))
        .filter_map(|s| s.parse().ok())
        .collect();
    let until = if steps.len() == reaches.len() {
        let longest = steps.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
        at.checked_add_day_time_duration(seconds(ahead as f64 * longest))
    } else {
        None
    };
    let present = present(store, at)?;
    let common = common(store)?;
    let mut graphs: Vec<String> = Vec::new();
    for g in common.iter().chain(&present) {
        if !graphs.contains(g) {
            graphs.push(g.clone());
        }
    }
    let mut out = Vec::new();
    for r in rows_of(store, ACTS_FOR_Q, &[("peer", Value::iri(peer))], &common)? {
        let Some(thing) = iri(&r, "t") else { continue };
        let node: NamedOrBlankNode = named(&thing).into();
        let mut rest = Vec::new();
        let mut now = Vec::new();
        for graph in &graphs {
            for q in store.quads(graph)? {
                if q.subject == node && key.contains(q.predicate.as_str()) {
                    now.push((q.predicate.as_str().to_string(), q.object));
                } else {
                    rest.push((q.subject, q.predicate, q.object));
                }
            }
        }
        let now = sorted(now);
        let room = scratch(store, rest)?;
        let mut seen: BTreeSet<Vec<(String, String)>> = BTreeSet::from([spelled(&now)]);
        let mut frontier = vec![now];
        let mut places: BTreeMap<String, Vec<(String, Term)>> = BTreeMap::new();
        for _ in 0..ahead {
            let mut next = Vec::new();
            for values in &frontier {
                let held: Vec<Quad> = values
                    .iter()
                    .map(|(p, v)| {
                        Quad::new(
                            named(&thing),
                            named(p),
                            v.clone(),
                            named("urn:orexis:coordination:scratch"),
                        )
                    })
                    .collect();
                room.add(held.clone())?;
                for text in &texts {
                    let mut found: Vec<(String, Vec<(String, Term)>)> = Vec::new();
                    for t in room.construct(
                        &bind(text, &[("this", Value::iri(thing.as_str()))])?,
                        &["urn:orexis:coordination:scratch"],
                    )? {
                        let subject = match &t.subject {
                            NamedOrBlankNode::NamedNode(n) => n.as_str().to_string(),
                            other => other.to_string(),
                        };
                        let pair = (t.predicate.as_str().to_string(), t.object.clone());
                        match found.iter_mut().find(|(s, _)| *s == subject) {
                            Some((_, pvs)) => pvs.push(pair),
                            None => found.push((subject, vec![pair])),
                        }
                    }
                    for (node, pvs) in found {
                        let place = sorted(pvs.iter().filter(|(p, _)| key.contains(p)).cloned().collect());
                        if place.is_empty() || seen.contains(&spelled(&place)) {
                            continue;
                        }
                        seen.insert(spelled(&place));
                        next.push(place);
                        places.insert(node, sorted(pvs));
                    }
                }
                room.remove_all(&held)?;
            }
            frontier = next;
        }
        for (node, values) in places {
            out.push(Holding {
                thing: node,
                values,
                start: Some(at),
                end: until,
                taken: false,
            });
        }
    }
    Ok(out)
}

fn spelled(values: &[(String, Term)]) -> Vec<(String, String)> {
    values.iter().map(|(p, v)| (p.clone(), v.to_string())).collect()
}

/// What a peer's thing may hold at each instant its holdings say anything changes: every value of every holding whose
/// period holds then, from each start or end to the next. Nothing is laid before the first change, which is sensing's.
pub(crate) fn timeline(held: &[Holding]) -> Vec<Holding> {
    let mut out: Vec<Holding> = Vec::new();
    let things: BTreeSet<&String> = held.iter().map(|h| &h.thing).collect();
    for thing in things {
        let mine: Vec<&Holding> = held.iter().filter(|h| &h.thing == thing).collect();
        let mut cuts: Vec<DateTime> = mine.iter().flat_map(|h| [h.start, h.end]).flatten().collect();
        cuts.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        cuts.dedup();
        for (n, t) in cuts.iter().enumerate() {
            let values = sorted(
                mine.iter()
                    .filter(|h| h.start.is_none_or(|s| s <= *t) && h.end.is_none_or(|e| e > *t))
                    .flat_map(|h| h.values.iter().cloned())
                    .collect(),
            );
            let end = cuts.get(n + 1).copied();
            if values.is_empty() {
                continue;
            }
            if let Some(last) = out.last_mut()
                && &last.thing == thing
                && last.values == values
                && last.end == Some(*t)
            {
                last.end = end;
            } else {
                out.push(Holding {
                    thing: thing.clone(),
                    values,
                    start: Some(*t),
                    end,
                    taken: false,
                });
            }
        }
    }
    out
}

/// What a laid forecast holds, as the holding it was laid of.
fn holding_in(store: &Store, graph: &str) -> Result<Option<Holding>, Error> {
    let quads = store.quads(graph)?;
    let Some(first) = quads.first() else { return Ok(None) };
    let thing = match &first.subject {
        NamedOrBlankNode::NamedNode(n) => n.as_str().to_string(),
        other => other.to_string(),
    };
    let cat = store.catalogue()?.unwrap_or_default();
    let row = store
        .rows(
            &bind(PERIOD_Q, &[("cat", Value::iri(cat)), ("graph", Value::iri(graph))])?,
            &[],
        )?
        .into_iter()
        .next()
        .unwrap_or_default();
    Ok(Some(Holding {
        thing,
        values: sorted(
            quads
                .iter()
                .map(|q| (q.predicate.as_str().to_string(), q.object.clone()))
                .collect(),
        ),
        start: value(&row, "start").map(|s| instant(&s)).transpose()?,
        end: value(&row, "end").map(|s| instant(&s)).transpose()?,
        taken: false,
    }))
}

/// Whether a constraint the agent holds reads a violation of the peer's thing holding `held`'s values beside
/// everything else the agent believes now — and again beside each of `landing`, a holding of the agent's own its step
/// in flight lands in, that overlaps `held` in time.
fn refused(store: &Store, held: &Holding, at: DateTime, landing: &[Holding]) -> Result<bool, Error> {
    let present = present(store, at)?;
    let common = common(store)?;
    let mut graphs: Vec<String> = Vec::new();
    for g in common.iter().chain(&present) {
        if !graphs.contains(g) {
            graphs.push(g.clone());
        }
    }
    let mut base = Vec::new();
    for graph in &graphs {
        base.extend(store.quads(graph)?);
    }
    let thing = named(&held.thing);
    let mut texts = Vec::new();
    let mut constraint_graphs = of_kind(store, &[CONSTRAINT_GRAPH])?;
    constraint_graphs.extend(common.clone());
    for c in rows_of(store, HELD_Q, &[], &constraints_and_self(store)?)? {
        let Some(c) = iri(&c, "c") else { continue };
        for r in rows_of(
            store,
            TEXTS_Q,
            &[("constraint", Value::iri(c.as_str()))],
            &constraint_graphs,
        )? {
            if let Some(text) = value(&r, "text") {
                texts.push(text);
            }
        }
    }
    let mut beside = vec![held];
    beside.extend(landing.iter().filter(|m| {
        held.end.is_none_or(|end| m.start.is_none_or(|s| s < end))
            && m.end.is_none_or(|end| held.start.is_none_or(|s| s < end))
    }));
    for h in beside {
        let pair: Vec<&Holding> = if h == held { vec![held] } else { vec![held, h] };
        let replaced: BTreeSet<(String, String)> = pair
            .iter()
            .flat_map(|x| x.values.iter().map(|(p, _)| (x.thing.clone(), p.clone())))
            .collect();
        let mut quads: Vec<(NamedOrBlankNode, NamedNode, Term)> = base
            .iter()
            .filter(|q| {
                let subject = match &q.subject {
                    NamedOrBlankNode::NamedNode(n) => n.as_str().to_string(),
                    other => other.to_string(),
                };
                !replaced.contains(&(subject, q.predicate.as_str().to_string()))
            })
            .map(|q| (q.subject.clone(), q.predicate.clone(), q.object.clone()))
            .collect();
        for x in &pair {
            for (p, v) in &x.values {
                quads.push((named(&x.thing).into(), named(p), v.clone()));
            }
        }
        let room = scratch(store, quads)?;
        for text in &texts {
            let Ok(rows) = asked(&room, text) else { continue };
            if rows
                .iter()
                .any(|row| row.values().any(|t| *t == Term::NamedNode(thing.clone())))
            {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

/// EVERY CONFLICT THE AGENT HOLDS, by peer and constraint.
const ALL_Q: &str = "SELECT DISTINCT ?peer ?constraint WHERE { GRAPH $graph { ?c a coordination:Conflict ; coordination:with ?peer ;
                                                                   coordination:over ?constraint } } ORDER BY ?peer ?constraint";

/// A peer and a constraint, and the holdings laid of the peer under it: as said, and as foreseen.
pub(crate) type Laid = ((String, String), (Vec<Holding>, Vec<Holding>));

/// What the self `me` of `store` lays now, per peer and constraint of a conflict it holds: the holdings the peer said,
/// and those it foresaw of the peer — told apart by whether the peer acts for the thing. What a history view is told; a
/// conflict laying nothing answers two empty lists.
pub(crate) fn laid(store: &Store, me: &str) -> Result<Vec<Laid>, Error> {
    let Some(cat) = store.catalogue()? else {
        return Ok(Vec::new());
    };
    let text = bind(
        LAID_Q,
        &[
            ("cat", Value::iri(cat.as_str())),
            ("root", Value::raw(format!("\"{}\"", laid_root(me)))),
        ],
    )?;
    let present: BTreeSet<String> = store.rows(&text, &[])?.iter().filter_map(|r| iri(r, "g")).collect();
    let common = store.graphs_of(&[BELIEF], &orexis::store::Within::common())?;
    let common: Vec<&str> = common.iter().map(String::as_str).collect();
    let mut out = Vec::new();
    for r in store.rows(&bind(ALL_Q, &[("graph", Value::iri(conflicts_graph(me)))])?, &[])? {
        let (Some(peer), Some(constraint)) = (iri(&r, "peer"), iri(&r, "constraint")) else {
            continue;
        };
        let acts: BTreeSet<String> = store
            .rows(&bind(ACTS_FOR_Q, &[("peer", Value::iri(peer.as_str()))])?, &common)?
            .iter()
            .filter_map(|a| iri(a, "t"))
            .collect();
        let full = laid_graph(me, &peer, &constraint, 0);
        let under = &full[..full.len() - 1];
        let mut graphs: Vec<(usize, &String)> = present
            .iter()
            .filter_map(|g| g.strip_prefix(under).and_then(|n| n.parse().ok()).map(|n| (n, g)))
            .collect();
        graphs.sort();
        let (mut said, mut foreseen) = (Vec::new(), Vec::new());
        for (_, graph) in graphs {
            if let Some(h) = holding_in(store, graph)? {
                if acts.contains(&h.thing) {
                    said.push(h)
                } else {
                    foreseen.push(h)
                }
            }
        }
        out.push(((peer, constraint), (said, foreseen)));
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    //! `lay`, held to `agent/coordination/tests/lay/`'s cases as `test_lay_cases.py` holds the Python act: each a
    //! store before, and the diff of the forecasts `lay` leaves.

    use std::path::Path;

    use orexis::snapshots::{ME, all_read, cases_in, held_to_diff, now, stand_in};

    use super::*;

    #[test]
    fn lay_leaves_what_the_case_says() {
        let cases = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/lay");
        all_read(&cases, 7);
        for case in cases_in(&cases) {
            let store = stand_in(&case);
            lay(&store, ME, now()).unwrap();
            held_to_diff(&case, &store, "lay");
        }
    }
}
