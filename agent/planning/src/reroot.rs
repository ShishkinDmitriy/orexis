//! RE-ROOTING THE IMAGINARIUM, as `agent/planning/reroot.py` re-roots it: the world the last pass imagined that the
//! present just laid landed in is found by hash — of the worlds holding the ground's facts, the one with the largest
//! cone, then the earliest minted, a ground before any world (#925) — its cone handed to the ground, re-stamped by
//! the stretch from the match's start to the ground's, and everything else the last pass made dropped.

use std::collections::BTreeSet;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::store::{Store, iri, value};

const HASH_Q: &str = r#"SELECT ?h WHERE { GRAPH $cat { $ground orexis:hash ?h } }"#;

const MATCHES_Q: &str = r#"
SELECT ?w ?minted WHERE {
  GRAPH $cat {
    ?w orexis:hash $hash . FILTER(?w != $ground)
    { ?w a planning:PossibleGraph } UNION { ?w a planning:GroundGraph }
    FILTER NOT EXISTS { ?w prov:wasDerivedFrom+ $ground }
    FILTER NOT EXISTS { ?w (planning:by/planning:from)+ $ground }
    OPTIONAL { ?w planning:minted ?m } }
  BIND(COALESCE(?m, 0) AS ?minted) }"#;

const CONE_SIZE_Q: &str = r#"
SELECT (COUNT(DISTINCT ?w) AS ?n) WHERE { GRAPH $cat { ?w (planning:by/planning:from)+ $match } }"#;

const LAID_Q: &str = r#"
SELECT ?g WHERE { GRAPH $cat { ?g prov:wasDerivedFrom* $ground . ?g a planning:GroundGraph } }"#;

const CONE_Q: &str = r#"
SELECT DISTINCT ?w WHERE { GRAPH $cat { ?w (planning:by/planning:from)+ $match } }"#;

const MADE_Q: &str = r#"
SELECT ?w WHERE { GRAPH $cat { ?w a ?kind . VALUES ?kind { planning:PossibleGraph planning:GroundGraph }
                              FILTER(isIRI(?w)) } }"#;

const RESTAMP_U: &str = r#"
DELETE { GRAPH $cat { ?period orexis:start ?a ; orexis:end ?b . ?w planning:spent ?s } }
INSERT { GRAPH $cat { ?period orexis:start ?a2 ; orexis:end ?b2 . ?w planning:spent ?s2 } }
WHERE  { GRAPH $cat {
  $ground dcterms:temporal/orexis:start ?g0 .
  $match dcterms:temporal/orexis:start ?m .
  OPTIONAL { $match planning:spent ?ms }
  ?w (planning:by/planning:from)+ $match ; planning:spent ?s ; dcterms:temporal ?period .
  ?period orexis:start ?a ; orexis:end ?b }
  BIND(?a - (?m - ?g0) AS ?a2) BIND(?b - (?m - ?g0) AS ?b2) BIND(?s - COALESCE(?ms, 0.0) AS ?s2) }"#;

const REPARENT_U: &str = r#"
DELETE { GRAPH $cat { ?c planning:from $match } }
INSERT { GRAPH $cat { ?c planning:from $ground } }
WHERE  { GRAPH $cat { ?c planning:from $match } }"#;

const CHANGES_Q: &str = r#"
SELECT ?g WHERE { GRAPH $cat { VALUES ?w { $worlds } ?g prov:wasDerivedFrom ?w ; a ?kind .
                               VALUES ?kind { execution:AddsGraph execution:RetractsGraph } } }"#;

const DROP_GRAPHS_U: &str = r#"
DELETE { GRAPH $cat { ?g ?p ?o . ?period ?pp ?po } }
WHERE  { GRAPH $cat { VALUES ?g { $graphs } ?g ?p ?o .
                      OPTIONAL { ?g dcterms:temporal ?period . ?period ?pp ?po } } }"#;

const DROP_ROWS_U: &str = r#"
DELETE { GRAPH $cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH $cat {
  { ?x a planning:Weighing ; planning:weighs ?w . OPTIONAL { ?w planning:from ?f } }
  UNION { ?x a planning:Candidate ; planning:from ?f }
  BIND(COALESCE(?f, ?w) AS ?home) FILTER NOT EXISTS { ?home a ?kind }
  ?x ?p ?o . OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"#;

const POSSIBLE_Q: &str = r#"SELECT ?m WHERE { GRAPH $cat { $match a planning:PossibleGraph } BIND($match AS ?m) }"#;

/// What a re-root found: the world matched, or None; which of the four the present was — `first`, `ground`,
/// `child` or `surprise` — and the worlds kept and dropped.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Rerooting {
    pub matched: Option<String>,
    pub present: &'static str,
    pub kept: BTreeSet<String>,
    pub dropped: Vec<String>,
}

fn graphs(names: &[String]) -> Value {
    Value::Raw(names.iter().map(|g| format!("<{g}>")).collect::<Vec<_>>().join(" "))
}

/// The world the present is: of the worlds holding the ground's facts, the largest cone, then the earliest minted.
fn matched(store: &Store, ground: &str, hash: &str, cat: &Value) -> Result<Option<String>, Error> {
    let tied = store.rows(
        &bind(
            MATCHES_Q,
            &[
                ("ground", Value::iri(ground)),
                ("cat", cat.clone()),
                ("hash", Value::Raw(format!("\"{hash}\""))),
            ],
        )?,
        &[],
    )?;
    if tied.len() < 2 {
        return Ok(tied.first().and_then(|r| iri(r, "w")));
    }
    let mut ranked = Vec::new();
    for r in &tied {
        let Some(w) = iri(r, "w") else { continue };
        let cone: i64 = store
            .rows(
                &bind(CONE_SIZE_Q, &[("match", Value::iri(w.as_str())), ("cat", cat.clone())])?,
                &[],
            )?
            .first()
            .and_then(|c| value(c, "n"))
            .and_then(|n| n.parse().ok())
            .unwrap_or(0);
        let minted: i64 = value(r, "minted").and_then(|m| m.parse().ok()).unwrap_or(0);
        ranked.push((-cone, minted, w));
    }
    ranked.sort();
    Ok(ranked.into_iter().next().map(|(_, _, w)| w))
}

/// Find the world the last pass imagined that `ground` landed in, hand its cone to the ground, and drop everything
/// else the last pass made. Refused where the ground has no hash.
pub fn reroot(store: &Store, ground: &str) -> Result<Rerooting, Error> {
    let catalogue = store
        .catalogue()?
        .ok_or_else(|| Error::Evaluation("a store with no catalogue".into()))?;
    let cat = Value::Raw(format!("<{catalogue}>"));
    let at = |m: &str| -> Value { Value::iri(m) };
    let hash = store
        .rows(&bind(HASH_Q, &[("ground", at(ground)), ("cat", cat.clone())])?, &[])?
        .first()
        .and_then(|r| value(r, "h"))
        .ok_or_else(|| Error::Evaluation(format!("{ground} has no hash — is it a ground lay_ground laid?")))?;
    let found = matched(store, ground, &hash, &cat)?;
    let mut kept: BTreeSet<String> = store
        .rows(&bind(LAID_Q, &[("ground", at(ground)), ("cat", cat.clone())])?, &[])?
        .iter()
        .filter_map(|r| iri(r, "g"))
        .collect();
    let landed = match &found {
        Some(m) => !store
            .rows(&bind(POSSIBLE_Q, &[("match", at(m)), ("cat", cat.clone())])?, &[])?
            .is_empty(),
        None => false,
    };
    if let Some(m) = &found {
        kept.extend(
            store
                .rows(&bind(CONE_Q, &[("match", at(m)), ("cat", cat.clone())])?, &[])?
                .iter()
                .filter_map(|r| iri(r, "w")),
        );
        let marks = [("ground", at(ground)), ("match", at(m)), ("cat", cat.clone())];
        store.update(&bind(RESTAMP_U, &marks)?)?;
        store.update(&bind(REPARENT_U, &marks)?)?;
    }
    let mut gone: Vec<String> = store
        .rows(&bind(MADE_Q, &[("cat", cat.clone())])?, &[])?
        .iter()
        .filter_map(|r| iri(r, "w"))
        .filter(|w| !kept.contains(w))
        .collect();
    gone.sort();
    let mut changes: Vec<String> = if gone.is_empty() {
        Vec::new()
    } else {
        store
            .rows(
                &bind(CHANGES_Q, &[("cat", cat.clone()), ("worlds", graphs(&gone))])?,
                &[],
            )?
            .iter()
            .filter_map(|r| iri(r, "g"))
            .collect()
    };
    changes.sort();
    for graph in gone.iter().chain(&changes) {
        store.clear_graph(graph)?;
    }
    if !gone.is_empty() {
        let all: Vec<String> = gone.iter().chain(&changes).cloned().collect();
        store.update(&bind(DROP_GRAPHS_U, &[("cat", cat.clone()), ("graphs", graphs(&all))])?)?;
        store.update(&bind(DROP_ROWS_U, &[("cat", cat.clone())])?)?;
    }
    let present = match (&found, gone.is_empty()) {
        (None, true) => "first",
        (None, false) => "surprise",
        (Some(_), _) if landed => "child",
        _ => "ground",
    };
    if found.is_none() && gone.is_empty() {
        log::debug!("nothing imagined yet: the present is the ground");
    } else {
        log::info!(
            "the present is {present}; {} world(s) kept, {} dropped",
            kept.len(),
            gone.len()
        );
    }
    Ok(Rerooting {
        matched: found,
        present,
        kept,
        dropped: gone,
    })
}

#[cfg(test)]
mod tests;
