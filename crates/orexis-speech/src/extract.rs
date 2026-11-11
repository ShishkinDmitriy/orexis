//! WHAT THE AGENT COMES TO BELIEVE OF ONE STATEMENT, as `agent/speech/extract.py` extracts it: what every extraction
//! it holds concludes of it, one belief graph derived from it. **AS SENSING REVISES A PERCEPT ALONE, SPEECH EXTRACTS
//! FROM A STATEMENT ALONE**: each `speech:Extraction`, a domain's `sh:construct`, is asked over the one statement and
//! the world's documents beside it, so it reads what was said and never what was believed before. What they construct
//! is one belief of the agent's own, derived from the statement and holding over its period. **AN EXTRACTION THAT WILL
//! NOT RUN EXTRACTS NOTHING, LOUDLY**, naming the rule, and the rest still run.

use oxigraph::model::{NamedNode, Quad};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::instant;
use orexis::hash::hash_named_graph;
use orexis::ontology::{BELIEF, DERIVED, local_of};
use orexis::store::{Store, Within, iri, value};

use crate::ontology::believed_graph;

const RULES_GRAPH: &str = "http://www.w3.org/ns/shacl#RulesGraph";

const EXTRACTIONS_Q: &str = "
SELECT ?rule ?text WHERE { ?rule a speech:Extraction ; sh:construct ?text .
                           FILTER NOT EXISTS { ?rule sh:deactivated true } } ORDER BY ?rule";

const ROW_Q: &str = "
SELECT ?owner ?start ?end WHERE { GRAPH $cat { OPTIONAL { $g orexis:ownedBy ?owner }
  OPTIONAL { $g dcterms:temporal ?p . OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } }
LIMIT 1";

/// Write what every extraction concludes of `statement` into the belief graph derived from it, replacing what was
/// extracted of it before; the belief graph written, or none where nothing was.
pub fn extract(store: &Store, statement: &str) -> Result<Vec<String>, Error> {
    let target = believed_graph(statement);
    store.forget_graph(&target, Some(BELIEF))?;
    let Some(cat) = store.catalogue()? else {
        return Ok(Vec::new());
    };
    let mut reads = vec![statement.to_string()];
    reads.extend(store.graphs_of(&[BELIEF], &Within::common())?);
    let reads: Vec<&str> = reads.iter().map(String::as_str).collect();
    let rules = store.graphs_of(&[RULES_GRAPH], &Within::default())?;
    let rules: Vec<&str> = rules.iter().map(String::as_str).collect();
    let mut found = Vec::new();
    for r in store.rows(EXTRACTIONS_Q, &rules)? {
        let (Some(rule), Some(text)) = (iri(&r, "rule"), value(&r, "text")) else {
            continue;
        };
        match store.construct(&text, &reads) {
            Ok(triples) => found.extend(triples),
            Err(e) => log::error!(
                "{}: an extraction would not run, so it extracts nothing: {e}",
                local_of(&rule)
            ),
        }
    }
    if found.is_empty() {
        return Ok(Vec::new());
    }
    let row = store
        .rows(
            &bind(
                ROW_Q,
                &[("cat", Value::iri(cat.as_str())), ("g", Value::iri(statement))],
            )?,
            &[],
        )?
        .into_iter()
        .next()
        .unwrap_or_default();
    let into = NamedNode::new_unchecked(&target);
    store.add(
        found
            .into_iter()
            .map(|t| Quad::new(t.subject, t.predicate, t.object, into.clone())),
    )?;
    let owner = iri(&row, "owner");
    let start = value(&row, "start").map(|s| instant(&s)).transpose()?;
    let end = value(&row, "end").map(|s| instant(&s)).transpose()?;
    let entry = store.entry(&target, &[BELIEF], DERIVED, owner.as_deref(), start, end)?;
    store.update(&format!(
        "INSERT DATA {{ {entry}\n  GRAPH <{cat}> {{ <{target}> prov:wasDerivedFrom <{statement}> }} }}"
    ))?;
    hash_named_graph(store, &target, None)?;
    Ok(vec![target])
}

#[cfg(test)]
mod tests {
    //! `extract`, held as `agent/speech/tests/test_extract.py` holds it: what the agent believes of one statement is
    //! what its extractions conclude of it alone — one belief derived from it, its own, over its period.

    use orexis::ontology::{CATALOGUE_GRAPH, OREXIS};
    use orexis::snapshots::namespaces;

    use super::*;

    const T: &str = "http://example.org/test#";

    fn round() -> String {
        format!("{T}round")
    }

    fn claim() -> String {
        format!("{T}claim")
    }

    fn store() -> Store {
        let (me, round, claim) = (format!("{T}me"), round(), claim());
        let believed =
            format!("CONSTRUCT {{ ?s ?p ?o }} WHERE {{ ?s a ?c ; ?p ?o . VALUES ?c {{ <{T}Round> <{T}Claim> }} }}");
        let st = Store::new(namespaces()).unwrap();
        st.update(&format!(
            "INSERT DATA {{
  GRAPH <{CATALOGUE_GRAPH}> {{ <{CATALOGUE_GRAPH}> a orexis:CatalogueGraph .
      <{T}rules> a sh:RulesGraph . <{T}world> a orexis:BeliefGraph .
      <{round}> a speech:StatementGraph , orexis:Graph ; orexis:arrivedBy orexis:Received ; orexis:ownedBy <{me}> ;
                dcterms:temporal [ orexis:start \"2026-01-01T12:00:00+00:00\"^^xsd:dateTime ] .
      <{claim}> a speech:StatementGraph , orexis:Graph ; orexis:arrivedBy orexis:Received ; orexis:ownedBy <{me}> .
      <{T}held> a orexis:BeliefGraph ; orexis:arrivedBy orexis:Derived ; orexis:ownedBy <{me}> . }}
  GRAPH <{T}rules> {{ <{T}believed> a speech:Extraction ; sh:construct \"{believed}\" . }}
  GRAPH <{T}world> {{ <{T}water> a <{T}Venue> . }}
  GRAPH <{round}> {{ <{round}> a <{T}Round> ; <{T}lot> 40 ; <{T}onVenue> <{T}water> . }}
  GRAPH <{claim}> {{ <{claim}> a <{T}Claim> ; <{T}inRound> <{round}> . }}
  GRAPH <{T}held> {{ <{round}> a <{T}Round> ; <{T}lot> 40 . }} }}"
        ))
        .unwrap();
        st
    }

    fn said(store: &Store, graph: &str) -> std::collections::BTreeSet<String> {
        store
            .triples(graph)
            .unwrap()
            .iter()
            .map(|t| format!("{} {} {}", t.subject, t.predicate, t.object))
            .collect()
    }

    #[test]
    fn what_a_round_says_is_believed_the_agent_s_own_over_its_period() {
        let store = store();
        assert_eq!(extract(&store, &round()).unwrap(), [believed_graph(&round())]);
        assert_eq!(said(&store, &believed_graph(&round())), said(&store, &round()));
        assert!(
            store
                .graphs_of(&[BELIEF], &Within::default())
                .unwrap()
                .contains(&believed_graph(&round()))
        );
        let q = format!(
            "SELECT ?a ?o ?from ?start WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph .
  <{}> orexis:arrivedBy ?a ; orexis:ownedBy ?o ; prov:wasDerivedFrom ?from ; dcterms:temporal ?p . ?p orexis:start ?start }} }}",
            believed_graph(&round())
        );
        let row = &store.rows(&q, &[]).unwrap()[0];
        assert_eq!(iri(row, "a").unwrap(), format!("{OREXIS}Derived"));
        assert_eq!(iri(row, "from").unwrap(), round());
        assert!(value(row, "start").unwrap().starts_with("2026-01-01T12:00:00"));
    }

    #[test]
    fn a_claim_carries_nothing_of_the_round_it_names_believed_before() {
        let store = store();
        extract(&store, &claim()).unwrap();
        assert_eq!(said(&store, &believed_graph(&claim())), said(&store, &claim()));
    }

    #[test]
    fn extracting_again_replaces_and_nothing_extracted_is_no_belief() {
        let store = store();
        let round = round();
        extract(&store, &round).unwrap();
        store
            .update(&format!(
                "DELETE DATA {{ GRAPH <{round}> {{ <{round}> <{T}lot> 40 }} }} ; INSERT DATA {{ GRAPH <{round}> {{ <{round}> <{T}lot> 20 }} }}"
            ))
            .unwrap();
        extract(&store, &round).unwrap();
        let held = said(&store, &believed_graph(&round));
        assert!(
            held.iter().any(|t| t.contains("lot> \"20\"")) && !held.iter().any(|t| t.contains("lot> \"40\"")),
            "{held:?}"
        );
        store.update(&format!("DROP GRAPH <{round}>")).unwrap();
        assert!(extract(&store, &round).unwrap().is_empty());
        assert!(
            !store
                .graphs_of(&[BELIEF], &Within::default())
                .unwrap()
                .contains(&believed_graph(&round))
        );
    }

    #[test]
    fn an_extraction_that_will_not_run_extracts_nothing_and_the_rest_still_run() {
        let store = store();
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{T}rules> {{ <{T}broken> a speech:Extraction ; sh:construct \"CONSTRUCT {{\" . }} }}"
            ))
            .unwrap();
        assert_eq!(
            extract(&store, &round()).unwrap(),
            [believed_graph(&round())],
            "the rest still run"
        );
    }

    #[test]
    fn a_peer_saying_a_subject_belief_makes_no_belief_where_no_extraction_concludes_it() {
        let store = store();
        let rumour = format!("{T}rumour");
        store
            .update(&format!(
                "INSERT DATA {{
  GRAPH <{CATALOGUE_GRAPH}> {{ <{rumour}> a speech:StatementGraph , orexis:Graph ; orexis:arrivedBy orexis:Received ; orexis:ownedBy <{T}me> . }}
  GRAPH <{rumour}> {{ <{T}bed> <http://example.org/orexis/climate#soil> <http://example.org/orexis/climate#Dry> . }} }}"
            ))
            .unwrap();
        assert!(extract(&store, &rumour).unwrap().is_empty());
        assert!(store.triples(&believed_graph(&rumour)).unwrap().is_empty());
    }
}
