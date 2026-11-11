//! WHAT AN AGENT CONCLUDES OF ITS CONFLICTS, each from its own documents, as `agent/coordination/conclude.py` concludes
//! them. **EACH AGENT DECIDES ITSELF THAT THERE IS A CONFLICT**: an answer that is not empty, said or heard, under a
//! constraint both hold, is a conflict with that peer, named alike by both; it STANDS while the peer is believed in
//! range or is still asking. **ROUNDS**: a standing conflict's draw is its present round's; undecided for the agent's
//! patience it restarts in the next, a peer heard drawing in a later round brings this agent to it, and past the rounds
//! the agent states the peer is SILENT. **A PEER THAT NEVER ANSWERS IS SILENT TOO**, from the first, and a silent
//! peer's draw is a lot drawn alone, again each patience. **WHO WON IS ASKED, NOT TRIGGERED**: every outcome the world's
//! rules ship is asked each pass over everything believed. Written where it changed, as one belief of the agent's own.

use std::collections::{BTreeMap, BTreeSet};

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{instant, isoformat, seconds_of};
use orexis::hash::hash_named_graph;
use orexis::ontology::{BELIEF, DERIVED, RECEIVED, RECORDED, local_of};
use orexis::stance::stance;
use orexis::store::{Store, Within, iri, value};

use crate::ask::{held, in_range, patience};
use crate::holdings::{key_of, of_kind, rows_of};
use crate::ontology::{
    BOUND, CONFLICT, COORDINATION, QUESTION_GRAPH, ROUNDS, WON_BY, answer_graph, conflict_of, conflicts_graph, draw_of,
    question_graph,
};

/// EVERY ANSWER BETWEEN THE AGENT AND A PEER, said or heard, with the constraint and whether it carries a holding.
const ANSWERS_Q: &str = "
SELECT ?g ?asker ?answerer ?constraint (COUNT(?h) AS ?held) WHERE {
  GRAPH $cat { ?g a coordination:AnswerGraph ; orexis:arrivedBy ?arrival . VALUES ?arrival { $recorded $received } }
  GRAPH ?g { ?a a coordination:Answer ; coordination:answeredBy ?answerer ; coordination:over ?constraint ; coordination:answers ?q .
             OPTIONAL { ?a coordination:holding ?h } }
  GRAPH ?qg { ?q coordination:asks ?asker } }
GROUP BY ?g ?asker ?answerer ?constraint";

/// WHAT THE AGENT CONCLUDED BEFORE.
pub(crate) const PRIOR_Q: &str = "
SELECT ?c ?peer ?constraint ?round ?since ?standing ?silent ?winner WHERE { GRAPH $graph {
  ?c a coordination:Conflict ; coordination:with ?peer ; coordination:over ?constraint ; coordination:round ?round ;
     coordination:since ?since ; coordination:draw ?draw . OPTIONAL { ?c coordination:standing ?standing }
  OPTIONAL { ?c coordination:silent ?silent } OPTIONAL { ?draw coordination:wonBy ?winner } } }";

/// THE LATEST ROUND A PEER WAS HEARD DRAWING A CONFLICT IN.
const HEARD_Q: &str = "SELECT (MAX(?r) AS ?round) WHERE { $conflict coordination:drawnIn ?r }";

/// EVERY OUTCOME THE WORLD'S RULES SHIP, with its text.
const OUTCOMES_Q: &str = "
SELECT ?rule ?text WHERE { ?rule a coordination:Outcome ; sh:construct ?text .
                           FILTER NOT EXISTS { ?rule sh:deactivated true } } ORDER BY ?rule";

const RULES_GRAPH: &str = "http://www.w3.org/ns/shacl#RulesGraph";

const ASKED_Q: &str = "SELECT ?start WHERE { GRAPH $cat { $graph orexis:arrivedBy $recorded ; dcterms:temporal ?p . ?p orexis:start ?start } } LIMIT 1";
const HEARD_ANSWER_Q: &str =
    "SELECT ?g WHERE { GRAPH $cat { $graph orexis:arrivedBy $received . BIND($graph AS ?g) } } LIMIT 1";

/// EVERY DRAW THE AGENT CONCLUDED A WINNER OF, with the winner and the constraint its conflict is over.
const WINS_Q: &str =
    "SELECT ?draw ?constraint ?w WHERE { GRAPH $graph { ?c coordination:over ?constraint ; coordination:draw ?draw .
                                                          ?draw coordination:wonBy ?w } }";

/// One conflict as concluded.
#[derive(Clone, Debug, PartialEq)]
pub(crate) struct Concluded {
    pub peer: String,
    pub constraint: String,
    pub round: i64,
    pub since: DateTime,
    pub standing: bool,
    pub silent: bool,
    pub winner: Option<String>,
}

impl Concluded {
    fn fresh(peer: &str, constraint: &str, at: DateTime) -> Self {
        Concluded {
            peer: peer.to_string(),
            constraint: constraint.to_string(),
            round: 0,
            since: at,
            standing: false,
            silent: false,
            winner: None,
        }
    }
}

fn since(at: DateTime, before: DateTime) -> f64 {
    at.checked_sub(before).map_or(0.0, seconds_of)
}

/// What the agent concluded before, by conflict.
pub(crate) fn prior(store: &Store, me: &str) -> Result<BTreeMap<String, Concluded>, Error> {
    let mut out = BTreeMap::new();
    for r in store.rows(&bind(PRIOR_Q, &[("graph", Value::iri(conflicts_graph(me)))])?, &[])? {
        let (Some(c), Some(peer), Some(constraint)) = (iri(&r, "c"), iri(&r, "peer"), iri(&r, "constraint")) else {
            continue;
        };
        out.insert(
            c,
            Concluded {
                peer,
                constraint,
                round: value(&r, "round").and_then(|n| n.parse().ok()).unwrap_or(0),
                since: instant(&value(&r, "since").unwrap_or_default())?,
                standing: value(&r, "standing").as_deref() == Some("true"),
                silent: value(&r, "silent").as_deref() == Some("true"),
                winner: iri(&r, "winner"),
            },
        );
    }
    Ok(out)
}

/// Conclude the conflicts of the self `me` of `store` at `at`, and write them where they changed; the graph written,
/// or none.
pub fn conclude(store: &Store, me: &str, at: DateTime) -> Result<Vec<String>, Error> {
    let Some(cat) = store.catalogue()? else {
        return Ok(Vec::new());
    };
    let patience = patience(store)?;
    let bound = stance(store, ROUNDS)?.unwrap_or(BOUND);
    let graph = conflicts_graph(me);
    let prior = prior(store, me)?;
    let won = won(store)?;
    let mut met: BTreeMap<(String, String), bool> = BTreeMap::new();
    let answers = bind(
        ANSWERS_Q,
        &[
            ("cat", Value::iri(cat.as_str())),
            ("recorded", Value::iri(RECORDED)),
            ("received", Value::iri(RECEIVED)),
        ],
    )?;
    for r in store.rows(&answers, &[])? {
        let (Some(asker), Some(answerer), Some(constraint)) =
            (iri(&r, "asker"), iri(&r, "answerer"), iri(&r, "constraint"))
        else {
            continue;
        };
        if me != asker && me != answerer {
            continue;
        }
        let peer = if asker == me { answerer } else { asker };
        let held = value(&r, "held").and_then(|n| n.parse::<i64>().ok()).unwrap_or(0) > 0;
        let entry = met.entry((peer, constraint)).or_insert(false);
        *entry = *entry || held;
    }
    let beliefs = of_kind(store, &[BELIEF])?;
    let asking: BTreeSet<String> = store
        .graphs_of(&[QUESTION_GRAPH], &Within::at(at))?
        .into_iter()
        .collect();
    let mut concluded = prior.clone();
    for ((peer, constraint), meets) in &met {
        let c = conflict_of(me, peer, constraint);
        let row = concluded
            .entry(c.clone())
            .or_insert_with(|| Concluded::fresh(peer, constraint, at));
        //  A PEER THAT SAID ITS HOLDINGS AND FELL SILENT IN THE DRAW draws no lot.
        if row.winner.is_none() && !row.silent {
            row.winner = won.get(&draw_of(&c, row.round)).cloned();
        }
        let mut decided = row.winner.is_some();
        let in_range = in_range(store, me, &key_of(store, constraint)?, at)?.contains(peer)
            || asking.contains(&question_graph(peer, me, constraint));
        if !in_range || !(*meets || row.standing) {
            row.standing = false;
            continue;
        }
        if !row.standing {
            if prior.contains_key(&c) && decided {
                row.round += 1;
            }
            row.standing = true;
            row.since = at;
            row.silent = false;
            row.winner = won.get(&draw_of(&c, row.round)).cloned();
            decided = row.winner.is_some();
        }
        let heard = rows_of(store, HEARD_Q, &[("conflict", Value::iri(c.as_str()))], &beliefs)?;
        let later = heard
            .first()
            .and_then(|r| value(r, "round"))
            .and_then(|n| n.parse::<i64>().ok());
        if let Some(later) = later.filter(|n| *n > row.round) {
            row.round = later;
            row.since = at;
            row.winner = won.get(&draw_of(&c, later)).cloned();
        } else if !decided && !row.silent && since(at, row.since) >= patience {
            row.round += 1;
            row.since = at;
            row.winner = None;
        }
        if !decided && (row.round as f64) >= bound {
            row.silent = true;
        }
    }
    for (c, row) in unanswered(store, me, &cat, at, patience, &met, &concluded, &asking)? {
        concluded.insert(c, row);
    }
    for (c, row) in concluded.iter_mut() {
        if row.standing && row.silent && !met.contains_key(&(row.peer.clone(), row.constraint.clone())) {
            if row.winner.is_none() {
                row.winner = won.get(&draw_of(c, row.round)).cloned();
            }
            if since(at, row.since) >= patience {
                row.round += 1;
                row.since = at;
                row.winner = won.get(&draw_of(c, row.round)).cloned();
            }
        }
    }
    written(store, me, &graph, &concluded, &prior)
}

/// The conflicts with every peer that never answered: silent and standing where the agent has asked it under a
/// constraint it holds, a patience has passed since the asking began and no answer of its under it was heard, while
/// it is in range or asking; one that no longer is stands no more.
#[allow(clippy::too_many_arguments)]
fn unanswered(
    store: &Store,
    me: &str,
    cat: &str,
    at: DateTime,
    patience: f64,
    met: &BTreeMap<(String, String), bool>,
    concluded: &BTreeMap<String, Concluded>,
    asking: &BTreeSet<String>,
) -> Result<BTreeMap<String, Concluded>, Error> {
    let mut out = BTreeMap::new();
    for constraint in held(store)? {
        for peer in in_range(store, me, &key_of(store, &constraint)?, at)? {
            if met.contains_key(&(peer.clone(), constraint.clone())) {
                continue;
            }
            let asked = store.rows(
                &bind(
                    ASKED_Q,
                    &[
                        ("cat", Value::iri(cat)),
                        ("graph", Value::iri(question_graph(me, &peer, &constraint))),
                        ("recorded", Value::iri(RECORDED)),
                    ],
                )?,
                &[],
            )?;
            let heard = store.rows(
                &bind(
                    HEARD_ANSWER_Q,
                    &[
                        ("cat", Value::iri(cat)),
                        ("graph", Value::iri(answer_graph(&peer, me, &constraint))),
                        ("received", Value::iri(RECEIVED)),
                    ],
                )?,
                &[],
            )?;
            let Some(start) = asked.first().and_then(|r| value(r, "start")) else {
                continue;
            };
            if !heard.is_empty() || since(at, instant(&start)?) < patience {
                continue;
            }
            let c = conflict_of(me, &peer, &constraint);
            let mut row = concluded
                .get(&c)
                .cloned()
                .unwrap_or_else(|| Concluded::fresh(&peer, &constraint, at));
            if !row.standing {
                row.standing = true;
                row.since = at;
                row.winner = None;
                if concluded.contains_key(&c) {
                    row.round += 1;
                }
            }
            row.silent = true;
            out.insert(c, row);
        }
    }
    for (c, row) in concluded {
        if out.contains_key(c) || !row.standing || met.contains_key(&(row.peer.clone(), row.constraint.clone())) {
            continue;
        }
        let key = key_of(store, &row.constraint)?;
        if !in_range(store, me, &key, at)?.contains(&row.peer)
            && !asking.contains(&question_graph(&row.peer, me, &row.constraint))
        {
            out.insert(
                c.clone(),
                Concluded {
                    standing: false,
                    ..row.clone()
                },
            );
        }
    }
    Ok(out)
}

/// Every draw the self `me` of `store` concluded it won, with the constraint its conflict is over.
pub fn wins(store: &Store, me: &str) -> Result<BTreeMap<String, String>, Error> {
    let mut out = BTreeMap::new();
    for r in store.rows(&bind(WINS_Q, &[("graph", Value::iri(conflicts_graph(me)))])?, &[])? {
        if iri(&r, "w").as_deref() == Some(me)
            && let (Some(draw), Some(constraint)) = (iri(&r, "draw"), iri(&r, "constraint"))
        {
            out.insert(draw, constraint);
        }
    }
    Ok(out)
}

/// Who won each draw, as every outcome the world's rules ship concludes it over what the agent believes.
fn won(store: &Store) -> Result<BTreeMap<String, String>, Error> {
    let beliefs = of_kind(store, &[BELIEF])?;
    let beliefs: Vec<&str> = beliefs.iter().map(String::as_str).collect();
    let mut out = BTreeMap::new();
    for r in rows_of(store, OUTCOMES_Q, &[], &of_kind(store, &[RULES_GRAPH])?)? {
        let (Some(rule), Some(text)) = (iri(&r, "rule"), value(&r, "text")) else {
            continue;
        };
        match store.construct(&text, &beliefs) {
            Ok(found) => {
                for t in found {
                    if t.predicate.as_str() == WON_BY {
                        let object = match &t.object {
                            oxigraph::model::Term::NamedNode(n) => n.as_str().to_string(),
                            other => other.to_string(),
                        };
                        let subject = match &t.subject {
                            oxigraph::model::NamedOrBlankNode::NamedNode(n) => n.as_str().to_string(),
                            other => other.to_string(),
                        };
                        out.entry(subject).or_insert(object);
                    }
                }
            }
            Err(e) => log::error!(
                "{}: an outcome would not run, so it concludes nothing: {e}",
                local_of(&rule)
            ),
        }
    }
    Ok(out)
}

/// The conflicts graph rewritten where what it says changed; the graph, or none.
fn written(
    store: &Store,
    me: &str,
    graph: &str,
    concluded: &BTreeMap<String, Concluded>,
    prior: &BTreeMap<String, Concluded>,
) -> Result<Vec<String>, Error> {
    if concluded == prior {
        return Ok(Vec::new());
    }
    store.forget_graph(graph, Some(BELIEF))?;
    if concluded.is_empty() {
        return Ok(Vec::new());
    }
    let mut facts = Vec::new();
    for (c, row) in concluded {
        let draw = draw_of(c, row.round);
        facts.push(format!(
            "<{c}> a <{CONFLICT}> ; <{COORDINATION}with> <{}> ; <{COORDINATION}over> <{}> ; <{COORDINATION}round> {} ; \
             <{COORDINATION}since> \"{}\"^^xsd:dateTime ; <{COORDINATION}draw> <{draw}>{}{} .",
            row.peer,
            row.constraint,
            row.round,
            isoformat(row.since),
            if row.standing {
                format!(" ; <{COORDINATION}standing> true")
            } else {
                String::new()
            },
            if row.silent {
                format!(" ; <{COORDINATION}silent> true")
            } else {
                String::new()
            },
        ));
        if let Some(winner) = &row.winner {
            facts.push(format!("<{draw}> <{WON_BY}> <{winner}> ."));
        }
    }
    let entry = store.entry(graph, &[BELIEF], DERIVED, Some(me), None, None)?;
    store.update(&format!(
        "INSERT DATA {{ GRAPH <{graph}> {{ {} }} {entry} }}",
        facts.join(" ")
    ))?;
    hash_named_graph(store, graph, None)?;
    Ok(vec![graph.to_string()])
}

/// Every conflict the self `me` of `store` holds, as it last concluded them: what the history view is told.
pub(crate) fn conflicts(store: &Store, me: &str) -> Result<Vec<crate::events::Conflict>, Error> {
    let mut out: Vec<crate::events::Conflict> = store
        .rows(&bind(PRIOR_Q, &[("graph", Value::iri(conflicts_graph(me)))])?, &[])?
        .iter()
        .filter_map(|r| {
            Some(crate::events::Conflict {
                conflict: iri(r, "c")?,
                peer: iri(r, "peer")?,
                constraint: iri(r, "constraint")?,
                standing: value(r, "standing").as_deref() == Some("true"),
                silent: value(r, "silent").as_deref() == Some("true"),
                round: value(r, "round").and_then(|v| v.parse().ok()).unwrap_or(0),
                won_by: iri(r, "winner"),
            })
        })
        .collect();
    out.sort_by(|a, b| a.conflict.cmp(&b.conflict));
    Ok(out)
}

#[cfg(test)]
mod tests {
    //! `conclude`, held to `orexis-coordination/tests/conclude/`'s cases as `test_conclude_cases.py` holds the Python
    //! act: each a store before, and the diff of what `conclude` leaves.

    use std::path::Path;

    use orexis::snapshots::{ME, all_read, cases_in, held_to_diff, now, stand_in};

    use super::*;

    #[test]
    fn conclude_leaves_what_the_case_says() {
        let cases = Path::new(env!("CARGO_MANIFEST_DIR")).join("tests/conclude");
        all_read(&cases, 9);
        for case in cases_in(&cases) {
            let store = stand_in(&case);
            conclude(&store, ME, now()).unwrap();
            held_to_diff(&case, &store, "conclude");
        }
    }
}
