//! RE-ROOTING THE IMAGINARIUM, as `agent/planning/reroot.py` re-roots it: the world the last pass imagined that the
//! present just laid landed in is found by hash — of the worlds holding the ground's facts, the one with the largest
//! cone, then the earliest minted, a ground before any world (#925) — its cone handed to the ground, re-stamped by
//! the stretch from the match's start to the ground's, and everything else the last pass made dropped.

use std::collections::BTreeSet;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::HASH;
use orexis::store::{Store, iri, value};

use crate::ontology::POSSIBLE_GRAPH;

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
/// A WORLD WEIGHED FOR A WANT THAT HAS NOT BEGUN IS NONE OF THEM, though it hold the present's facts: it follows a
/// state not reached yet, and a want beginning where a plan ends searched back over the present in a yard of nine
/// cells, so the present was taken for a world of its search and handed that search's worlds as its own.
fn matched(store: &Store, ground: &str, hash: &str, cat: &Value) -> Result<Option<String>, Error> {
    const MATCHES_Q: &str = r#"PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX orexis: <http://example.org/orexis#>
    PREFIX planning: <http://example.org/orexis/planning#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    SELECT ?w ?minted WHERE {
      GRAPH ?m_w {
        ?w orexis:hash $hash . FILTER(?w != $ground)
        { ?w a planning:PossibleGraph } UNION { ?w a planning:GroundGraph } }
      FILTER NOT EXISTS { GRAPH $cone { ?w prov:wasDerivedFrom+ $ground } }
      FILTER NOT EXISTS { GRAPH $cone { ?w (planning:by/planning:from)+ $ground } }
      OPTIONAL { GRAPH $cone { ?w planning:minted ?mint } }
      FILTER NOT EXISTS {
        GRAPH $cone { ?x planning:weighs ?w ; planning:for ?later }
        GRAPH ?wanted { ?later a planning:Want }
        GRAPH ?m_wanted { ?wanted a planning:WantGraph ; dcterms:temporal/orexis:start ?begins }
        GRAPH ?m_ground { $ground dcterms:temporal/orexis:start ?now } FILTER(?begins > ?now) }
      BIND(COALESCE(?mint, 0) AS ?minted) }"#;
    const CONE_SIZE_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
    SELECT (COUNT(DISTINCT ?w) AS ?n) WHERE { GRAPH $cone { ?w (planning:by/planning:from)+ $match } }"#;
    let tied = store.rows(
        &bind(
            MATCHES_Q,
            &[
                ("ground", Value::iri(ground)),
                ("cone", cat.clone()),
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
                &bind(CONE_SIZE_Q, &[("match", Value::iri(w.as_str())), ("cone", cat.clone())])?,
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
    const CONE_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
    SELECT DISTINCT ?w WHERE { GRAPH $cone { ?w (planning:by/planning:from)+ $match } }"#;
    const LAID_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    SELECT ?g WHERE { GRAPH $cone { ?g prov:wasDerivedFrom+ $ground } GRAPH ?m_g { ?g a planning:GroundGraph } }"#;
    const MADE_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
    SELECT ?w WHERE { GRAPH ?m_w { ?w a ?kind . VALUES ?kind { planning:PossibleGraph planning:GroundGraph }
                                  FILTER(isIRI(?w)) } }"#;
    /// THE CONE UNDER THE MATCH IS THE GROUND'S NOW: each world of it holds as long before as the match held after
    /// the ground, said in the world's metadata.
    const RESTAMP_U: &str = r#"PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX orexis: <http://example.org/orexis#>
    PREFIX planning: <http://example.org/orexis/planning#>
    DELETE { GRAPH ?m_w { ?period orexis:start ?a ; orexis:end ?b } }
    INSERT { GRAPH ?m_w { ?period orexis:start ?a2 ; orexis:end ?b2 } }
    WHERE  {
      GRAPH ?m_ground { $ground dcterms:temporal/orexis:start ?g0 }
      GRAPH ?m_match { $match dcterms:temporal/orexis:start ?m0 }
      GRAPH $cone { ?w (planning:by/planning:from)+ $match }
      GRAPH ?m_w { ?w dcterms:temporal ?period . ?period orexis:start ?a ; orexis:end ?b }
      BIND(?a - (?m0 - ?g0) AS ?a2) BIND(?b - (?m0 - ?g0) AS ?b2) }"#;
    /// AND WHAT THE PATH TO EACH SPENT IS COUNTED FROM THE MATCH, in the cone graph.
    const RESPEND_U: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
    DELETE { GRAPH $cone { ?w planning:spent ?s } }
    INSERT { GRAPH $cone { ?w planning:spent ?s2 } }
    WHERE  { GRAPH $cone {
      OPTIONAL { $match planning:spent ?ms }
      ?w (planning:by/planning:from)+ $match ; planning:spent ?s }
      BIND(?s - COALESCE(?ms, 0.0) AS ?s2) }"#;
    const REPARENT_U: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
    DELETE { GRAPH $cone { ?c planning:from $match } }
    INSERT { GRAPH $cone { ?c planning:from $ground } }
    WHERE  { GRAPH $cone { ?c planning:from $match } }"#;
    const CHANGES_Q: &str = r#"PREFIX execution: <http://example.org/orexis/execution#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    SELECT ?g WHERE { GRAPH ?m_g { VALUES ?w { $worlds } ?g prov:wasDerivedFrom ?w ; a ?kind .
                                   VALUES ?kind { execution:AddsGraph execution:RetractsGraph } } }"#;
    /// EVERY WEIGHING AND EVERY CANDIDATE WHOSE WORLD IS GONE, nothing saying any more what that world is.
    const DROP_ROWS_U: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
    DELETE { GRAPH $cone { ?x ?p ?o . ?v ?vp ?vo } }
    WHERE  { GRAPH $cone {
      { ?x a planning:Weighing ; planning:weighs ?w . OPTIONAL { ?w planning:from ?f } }
      UNION { ?x a planning:Candidate ; planning:from ?f }
      BIND(COALESCE(?f, ?w) AS ?home) FILTER NOT EXISTS { GRAPH ?m_home { ?home a ?kind } }
      ?x ?p ?o . OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"#;
    let cat = Value::iri(crate::world_at::cone_of(store)?);
    let at = |m: &str| -> Value { Value::iri(m) };
    let hash = store
        .said_of(ground, HASH)?
        .into_iter()
        .find_map(|h| match h {
            oxigraph::model::Term::Literal(h) => Some(h.value().to_string()),
            _ => None,
        })
        .ok_or_else(|| Error::Evaluation(format!("{ground} has no hash — is it a ground lay_ground laid?")))?;
    let found = matched(store, ground, &hash, &cat)?;
    //  THE GROUND AND EVERY GROUND LAID FROM IT: the ground is named here, since a path of no step is answered only
    //  for a node the cone graph holds, and a ground nothing was imagined from is in no row of it.
    let mut kept: BTreeSet<String> = store
        .rows(&bind(LAID_Q, &[("ground", at(ground)), ("cone", cat.clone())])?, &[])?
        .iter()
        .filter_map(|r| iri(r, "g"))
        .collect();
    kept.insert(ground.to_string());
    let landed = match &found {
        Some(m) => store.kinds_of(m)?.iter().any(|k| k == POSSIBLE_GRAPH),
        None => false,
    };
    if let Some(m) = &found {
        kept.extend(
            store
                .rows(&bind(CONE_Q, &[("match", at(m)), ("cone", cat.clone())])?, &[])?
                .iter()
                .filter_map(|r| iri(r, "w")),
        );
        let marks = [("ground", at(ground)), ("match", at(m)), ("cone", cat.clone())];
        store.update(&bind(RESTAMP_U, &marks)?)?;
        store.update(&bind(RESPEND_U, &marks)?)?;
        store.update(&bind(REPARENT_U, &marks)?)?;
    }
    //  A GROUND LAID AGAIN UNDER ITS NAME AS IT STOOD IS ITS OWN MATCH (#1158): two plannings at one instant lay one
    //  name twice, so no other world holds the present's hash, and what was imagined from the ground the first time
    //  still hangs from it - `lay_ground` took back the candidates of a ground laid again as another, and a cone
    //  begins at a candidate. Called a surprise, a search the budget cut short lost everything it had weighed.
    //  AND WHAT WAS IMAGINED FROM A GROUND AHEAD STAYS WITH IT, whatever the present is: a want that begins there is
    //  searched from it over several plannings, while the present moves towards it.
    let mut own = false;
    for laid in kept.clone() {
        if found.is_some() && laid == ground {
            continue;
        }
        let cone: Vec<String> = store
            .rows(&bind(CONE_Q, &[("match", at(&laid)), ("cone", cat.clone())])?, &[])?
            .iter()
            .filter_map(|r| iri(r, "w"))
            .collect();
        own = own || (found.is_none() && !cone.is_empty());
        kept.extend(cone);
    }
    let mut gone: Vec<String> = store
        .rows(&bind(MADE_Q, &[("cone", cat.clone())])?, &[])?
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
                &bind(CHANGES_Q, &[("cone", cat.clone()), ("worlds", graphs(&gone))])?,
                &[],
            )?
            .iter()
            .filter_map(|r| iri(r, "g"))
            .collect()
    };
    changes.sort();
    //  EACH GOES WITH WHAT IS SAID OF IT, its metadata graph and its rows in the cone.
    for graph in gone.iter().chain(&changes) {
        store.forget_graph(graph, None)?;
        crate::world_at::out_of_the_cone(store, graph)?;
    }
    if !gone.is_empty() {
        store.update(&bind(DROP_ROWS_U, &[("cone", cat.clone())])?)?;
    }
    let present = match (&found, gone.is_empty()) {
        (None, _) if own => "ground",
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
mod tests {
    //! `reroot`, held to `orexis-planning/tests/reroot/`'s cases as `test_reroot.py` holds the Python act.

    use std::path::PathBuf;

    use oxsdatatypes::{DateTime, DayTimeDuration};

    use orexis::snapshots;

    use super::*;
    use crate::world_at::lexical;
    use orexis::snapshots::SAID_TOGETHER;

    fn cases() -> PathBuf {
        snapshots::tree().join("orexis-planning/tests/reroot")
    }

    const WORLDS_Q: &str = "PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX orexis: <http://example.org/orexis#>
PREFIX planning: <http://example.org/orexis/planning#>
SELECT ?w ?at ?until ?spent WHERE {
  GRAPH ?m_w { ?w a planning:PossibleGraph .
               OPTIONAL { ?w dcterms:temporal ?p . ?p orexis:start ?at . OPTIONAL { ?p orexis:end ?until } } }
  OPTIONAL { GRAPH ?c { ?w planning:spent ?spent } } }";

    fn present(store: &Store) -> String {
        /// THE PRESENT: the newest ground laid from nothing.
        const PRESENT_Q: &str = "PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX orexis: <http://example.org/orexis#>
    PREFIX planning: <http://example.org/orexis/planning#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    SELECT ?g WHERE {
      GRAPH ?m_g { ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?start }
      FILTER NOT EXISTS { GRAPH ?c { ?g prov:wasDerivedFrom ?parent } } }
    ORDER BY DESC(?start) LIMIT 1";
        iri(&store.rows(PRESENT_Q, &[]).unwrap()[0], "g").unwrap()
    }

    #[test]
    fn reroot_leaves_the_store_the_diff_says() {
        for case in snapshots::cases_in(&cases()) {
            let store = snapshots::stand_in(&case);
            reroot(&store, &present(&store)).unwrap();
            snapshots::held_to_diff(&case, &store, "reroot");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        snapshots::all_read(&cases(), 3);
    }

    #[test]
    fn a_world_weighed_for_a_want_that_has_not_begun_is_not_the_present() {
        let case = cases().join("a_step_taken_as_predicted_keeps_its_cone.trig");
        let store = snapshots::stand_in(&case);
        let matched = reroot(&store, &present(&store))
            .unwrap()
            .matched
            .expect("the case's present is a world imagined");
        //  THE SAME STORE, the world weighed for a want whose graph holds from an hour on.
        let store = snapshots::stand_in(&case);
        let (said, cone) = (SAID_TOGETHER, crate::world_at::cone_of(&store).unwrap());
        let begins = snapshots::now()
            .checked_add_day_time_duration(DayTimeDuration::new(3600))
            .unwrap();
        store
            .update(&format!(
                "PREFIX dcterms: <http://purl.org/dc/terms/>
                 PREFIX orexis: <http://example.org/orexis#>
                 PREFIX planning: <http://example.org/orexis/planning#>
                 PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                 INSERT DATA {{
                   GRAPH <{cone}> {{
                     <urn:test:weighing> a planning:Weighing ; planning:weighs <{matched}> ; planning:for <urn:test:later> }}
                   GRAPH <{said}> {{
                     <urn:test:wanted> a planning:WantGraph ;
                       dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start \"{}\"^^xsd:dateTime ] }}
                   GRAPH <urn:test:wanted> {{ <urn:test:later> a planning:Want }} }}",
                orexis::clock::isoformat(begins)
            ))
            .unwrap();
        assert_ne!(
            reroot(&store, &present(&store)).unwrap().matched,
            Some(matched),
            "it follows a state not reached yet, whatever facts it holds"
        );
    }

    #[test]
    fn every_kept_world_is_re_stamped_and_none_loses_its_instant() {
        let store = snapshots::stand_in(&cases().join("a_step_taken_as_predicted_keeps_its_cone.trig"));
        assert!(reroot(&store, &present(&store)).unwrap().matched.is_some());
        let kept = store.rows(WORLDS_Q, &[]).unwrap();
        assert!(!kept.is_empty(), "the cone beneath the match is kept");
        let later: DateTime = snapshots::now()
            .checked_add_day_time_duration(DayTimeDuration::new(60))
            .unwrap();
        for r in &kept {
            let (at, until) = (lexical(&r["at"]).unwrap(), lexical(&r["until"]).unwrap());
            assert!(until >= at && at >= later, "{r:?}");
            assert!(r.contains_key("spent"));
        }
        let least = kept
            .iter()
            .filter_map(|r| value(r, "spent")?.parse::<f64>().ok())
            .fold(f64::MAX, f64::min);
        assert_eq!(least, 1.0, "the match's spent was taken off: its children cost one");
    }

    #[test]
    fn a_surprise_keeps_nothing() {
        let store = snapshots::stand_in(&cases().join("a_surprise_drops_everything.trig"));
        assert!(reroot(&store, &present(&store)).unwrap().matched.is_none());
        assert!(store.rows(WORLDS_Q, &[]).unwrap().is_empty());
    }

    const GROUND: &str = "http://example.org/orexis/graph/ground/";

    #[test]
    fn two_grounds_holding_the_presents_facts_are_told_by_their_cones_and_never_by_name() {
        for holder_is_old in [true, false] {
            let store = snapshots::stand_in(&cases().join("nothing_happened_and_the_cone_is_kept_whole.trig"));
            let (cat, cone) = (SAID_TOGETHER, crate::world_at::cone_of(&store).unwrap());
            let (old, landing) = (
                format!("{GROUND}2026-01-01T120000p0000"),
                format!("{GROUND}2026-01-01T120030p0000"),
            );
            store
                .update(&format!(
                    "PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX orexis: <http://example.org/orexis#>
    PREFIX planning: <http://example.org/orexis/planning#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT {{ GRAPH <{cat}> {{ <{landing}> a planning:GroundGraph ; orexis:arrivedBy orexis:Derived ; orexis:hash ?h ;
    dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start \"2026-01-01T12:00:30+00:00\"^^xsd:dateTime ] }}
    GRAPH <{cone}> {{ <{landing}> prov:wasDerivedFrom <{old}> }} }}
WHERE {{ GRAPH ?m {{ <{old}> orexis:hash ?h }} }}"
                ))
                .unwrap();
            orexis::metadata::moved(&store, SAID_TOGETHER, &landing).unwrap();
            let (held, bare) = if holder_is_old {
                (&old, &landing)
            } else {
                (&landing, &old)
            };
            if !holder_is_old {
                store
                    .update(&format!(
                        "PREFIX planning: <http://example.org/orexis/planning#>
DELETE {{ GRAPH <{cone}> {{ ?c planning:from <{old}> }} }} INSERT {{ GRAPH <{cone}> {{ ?c planning:from <{landing}> }} }}
WHERE {{ GRAPH <{cone}> {{ ?c planning:from <{old}> }} }}"
                    ))
                    .unwrap();
            }
            let whole = store.rows(WORLDS_Q, &[]).unwrap().len();
            let found = reroot(&store, &present(&store)).unwrap();
            assert_eq!(found.matched.as_ref(), Some(held), "{bare} holds no search");
            assert!(found.kept.len() >= whole && store.rows(WORLDS_Q, &[]).unwrap().len() == whole);
            assert!(
                found.dropped.contains(bare),
                "the bare ground goes with the rest the pass made"
            );
        }
    }
}
