//! REFINING A STEP: the want that keeps a step one level down, as `agent/planning/refine.py` mints it. THE GOAL IS
//! THE WORLD THE STEP LANDS IN, NOT ITS DIFF: every fact of a predicate a bridge concludes that the present holds,
//! less what the step retracts, plus what it adds — each regressed through the bridges, all to hold at once.

use std::collections::{BTreeSet, HashSet};
use std::sync::LazyLock;

use oxigraph::model::Triple;
use oxsdatatypes::DateTime;
use regex::Regex;

use orexis::Error;
use orexis::clock::isoformat;
use orexis::ontology::{BELIEF, GRAPH_PREFIX, RECORDED};
use orexis::store::{Store, Within};

use crate::admit::local_of;
use crate::bridge::{binding, expand, heads, literal, predicted, repr};
use crate::ontology::WANT;

static VARIABLE: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\?(\w+)\b").expect("a valid pattern"));

/// Mint the want that keeps `step` below in the agent `me`'s own want graph; the want. None where no rule the store
/// holds concludes any fact the step adds.
pub fn refine(store: &Store, me: &str, step: &str, now: DateTime) -> Result<Option<String>, Error> {
    let bridges = heads(store)?;
    let concluded: BTreeSet<String> = bridges.iter().filter_map(|b| expand(&b.head.1, &b.names)).collect();
    let (adds, retracts) = predicted(store, step)?;
    if !adds.iter().any(|f| concluded.contains(f.predicate.as_str())) {
        return Ok(None);
    }
    let beliefs = store.graphs_of(&[BELIEF], &Within::default())?;
    let sources: Vec<&str> = beliefs.iter().map(String::as_str).collect();
    let mut graphs = beliefs.clone();
    graphs.extend(store.revisions_of(&sources, BELIEF)?);
    let mut present: HashSet<Triple> = HashSet::new();
    for g in &graphs {
        for t in store.triples(g)? {
            if concluded.contains(t.predicate.as_str()) {
                present.insert(t);
            }
        }
    }
    for t in &retracts {
        present.remove(t);
    }
    present.extend(
        adds.iter()
            .filter(|f| concluded.contains(f.predicate.as_str()))
            .cloned(),
    );
    let mut target: Vec<Triple> = present.into_iter().collect();
    target.sort_by_cached_key(repr);
    let (mut prefixes, mut conjuncts) = (BTreeSet::new(), Vec::new());
    for fact in &target {
        let mut branches = Vec::new();
        for bridge in &bridges {
            let Some(bound) = binding(&bridge.head, fact, &bridge.names) else {
                continue;
            };
            let branch = VARIABLE.replace_all(&bridge.r#where, |caps: &regex::Captures<'_>| {
                bound.get(&caps[1]).cloned().unwrap_or_else(|| caps[0].to_string())
            });
            branches.push(branch.into_owned());
            prefixes.extend(bridge.declared.iter().cloned());
        }
        if !branches.is_empty() {
            conjuncts.push(
                branches
                    .iter()
                    .map(|b| format!("{{ {b} }}"))
                    .collect::<Vec<_>>()
                    .join(" UNION "),
            );
        }
    }
    if conjuncts.is_empty() {
        return Ok(None);
    }
    let goal = conjuncts
        .iter()
        .map(|c| format!("{{ FILTER NOT EXISTS {{ {c} }} }}"))
        .collect::<Vec<_>>()
        .join(" UNION ");
    let head = if prefixes.is_empty() {
        String::new()
    } else {
        format!("{}\n", prefixes.into_iter().collect::<Vec<_>>().join("\n"))
    };
    let select = format!("{head}SELECT $this WHERE {{ {goal} }}");
    let want = format!("{step}.below");
    let graph = format!("{GRAPH_PREFIX}want/refined/{}", local_of(step));
    let shape = format!("{want}.met");
    let name = local_of(step);
    store.update(&format!(
        "INSERT DATA {{ GRAPH <{graph}> {{
  <{me}> planning:holds <{want}> .
  <{step}> execution:keptBy <{want}> .
  <{want}> a planning:Want ; planning:metWhen <{shape}> ;
      rdfs:label \"what {name} comes to, one level down\" ;
      prov:generatedAtTime \"{}\"^^xsd:dateTime .
  <{shape}> a sh:NodeShape ; sh:targetNode <{me}> ;
      sh:sparql [ a sh:SPARQLConstraint ; sh:message \"{name} is not kept below yet\" ;
                  sh:select {} ] . }} }}",
        isoformat(now),
        literal(&select)
    ))?;
    store.classify(&graph, WANT, RECORDED, Some(me), None, None)?;
    log::info!(
        "refining {name} into {} — {} fact(s) of the world it lands in, held below",
        local_of(&want),
        conjuncts.len()
    );
    Ok(Some(want))
}

#[cfg(test)]
pub(crate) mod tests {
    //! `refine`, held to what `test_refine.py` holds the Python act to: the tower's shape at its smallest.

    use orexis::snapshots;

    use super::*;

    const ME: &str = "http://example.org/test#mover";
    const STEP: &str = "http://example.org/test#step";
    const T: &str = "http://example.org/test#";

    const CASE: &str = r#"
@prefix : <http://example.org/test#> .
@prefix orexis: <http://example.org/orexis#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .

GRAPH :catalogue {
  :catalogue a orexis:CatalogueGraph , orexis:Graph .
  :rules a sh:RulesGraph , orexis:Graph .
  :state a orexis:BeliefGraph , orexis:Graph .
}
GRAPH :rules {
  :stands a sh:SPARQLRule ; sh:construct """PREFIX : <http://example.org/test#>
    CONSTRUCT { ?disk :on ?peg } WHERE { ?disk :at ?cell . ?peg a :Peg ; :at ?cell }""" .
  :twice a sh:SPARQLRule ; sh:construct """PREFIX : <http://example.org/test#>
    CONSTRUCT { ?disk :near ?peg . ?peg :near ?disk } WHERE { ?disk :at ?cell . ?peg :at ?cell }""" .
}
GRAPH :state {
  :pegA a :Peg ; :at :c1 .  :pegB a :Peg ; :at :c2 .
  :d :at :c1 ; :on :pegA .  :e :at :c1 ; :on :pegA .
}
"#;

    pub(crate) fn store() -> Store {
        let store = Store::new(snapshots::namespaces()).expect("an empty store");
        store.put_trig(&format!("{T}state"), CASE).unwrap();
        store.close_catalogue().unwrap();
        store
    }

    /// The step as a plan's extraction writes one: its two graphs, named off it, holding what it adds and retracts.
    pub(crate) fn predicting(store: &Store, adds: &str, retracts: &str) -> String {
        store
            .update(&format!(
                "PREFIX : <{T}>
INSERT DATA {{
  GRAPH <{T}plan> {{ <{STEP}> a execution:Step ; execution:adds <{STEP}.adds> ; execution:retracts <{STEP}.retracts> }}
  GRAPH <{STEP}.adds> {{ {adds} }}
  GRAPH <{STEP}.retracts> {{ {retracts} }} }}"
            ))
            .unwrap();
        STEP.to_string()
    }

    fn now() -> DateTime {
        snapshots::now()
    }

    fn wants(store: &Store) -> Vec<String> {
        store.graphs_of(&[WANT], &Within::default()).unwrap()
    }

    /// The minted met-test, run as the search runs it: a violation row is the want unmet.
    fn met(store: &Store, state: &str) -> bool {
        let graphs = wants(store);
        let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
        let found = store.rows("SELECT ?q WHERE { ?s sh:select ?q }", &graphs).unwrap();
        let text = orexis::store::value(&found[0], "q")
            .unwrap()
            .replace("SELECT $this", "SELECT *");
        store.rows(&text, &[state]).unwrap().is_empty()
    }

    #[test]
    fn a_step_whose_fact_a_rule_concludes_is_a_want_below() {
        let store = store();
        let step = predicting(&store, ":d :on :pegB", ":d :on :pegA");
        let want = refine(&store, ME, &step, now()).unwrap();
        assert_eq!(want, Some(format!("{STEP}.below")));
        let graphs = wants(&store);
        let graphs: Vec<&str> = graphs.iter().map(String::as_str).collect();
        let found = store
            .rows("SELECT ?step WHERE { ?step execution:keptBy ?w }", &graphs)
            .unwrap();
        assert_eq!(orexis::store::iri(&found[0], "step").as_deref(), Some(STEP));
        assert!(!met(&store, &format!("{T}state")), "the disk still stands on A's cell");
    }

    #[test]
    fn the_want_below_is_the_world_the_step_lands_in_not_its_diff() {
        let store = store();
        let step = predicting(&store, ":d :on :pegB", ":d :on :pegA");
        refine(&store, ME, &step, now()).unwrap();
        let put = |name: &str, body: &str| {
            store
                .put_trig(
                    &format!("{T}{name}"),
                    &format!("@prefix : <http://example.org/test#> . {body}"),
                )
                .unwrap();
        };
        put(
            "moved",
            ":pegA a :Peg ; :at :c1 . :pegB a :Peg ; :at :c2 . :d :at :c2 . :e :at :c1 .",
        );
        assert!(met(&store, &format!("{T}moved")));
        put(
            "both",
            ":pegA a :Peg ; :at :c1 . :pegB a :Peg ; :at :c2 . :d :at :c2 . :e :at :c2 .",
        );
        assert!(!met(&store, &format!("{T}both")), "carrying e away breaks the frame");
    }

    #[test]
    fn a_step_no_rule_concludes_is_taken_as_it_would_be() {
        let store = store();
        let step = predicting(&store, ":d :painted :red", "");
        assert_eq!(refine(&store, ME, &step, now()).unwrap(), None);
        assert!(wants(&store).is_empty(), "nothing minted");
    }

    #[test]
    fn a_rule_of_two_head_triples_is_not_run_backwards() {
        let store = store();
        let step = predicting(&store, ":d :near :pegB", "");
        assert_eq!(refine(&store, ME, &step, now()).unwrap(), None);
    }
}
