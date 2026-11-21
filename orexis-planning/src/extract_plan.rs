//! READING A PLAN OUT OF THE WORLDS THAT WERE WALKED TO FIND IT, as `agent/planning/extract_plan.py` reads it: the
//! cheapest world the want is met in, on time before late, and its ancestry walked back by `planning:by/planning:from`
//! to the ground, one `execution:Step` minted per candidate on the way — or, where nothing met it, the empty plan
//! saying which silence it is. ONE UPDATE: the root, the steps, the chain off the ancestry, the plan's row, and what
//! each step predicts as two graphs it names, the diff a pattern the engine computes where the worlds are.
//!
//! WHAT A STEP PREDICTS IS A DIFF OF CONTENT: what a world says of itself - that it is a possible world, when it
//! holds, what it hashes to - is its metadata, which differs between any two worlds and is no change a step
//! makes; so each text that reads a whole world asks, in its own words, for what is about no graph and no period.
//!
//! THE PLAN IS NOT ITS GRAPH: the root, the node that is the `planning:Plan`, has a name of its own (`plan_root`),
//! where it bore its graph's, one IRI for two things — a plan, which is for a want and ended some way, and the graph
//! it is written in, which arrived some way and is somebody's.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::GRAPH_PREFIX;
use orexis::store::{Store, iri, value};

use crate::admit::local_of;
use crate::ontology::{EXHAUSTED, NO_CANDIDATE, SATISFIED};

/// Mint `want`'s plan from what its search left, into its own graph, replaced whole with its steps' graphs. The
/// graph's name. Refused where nothing was weighed for the want.
pub fn extract_plan(store: &Store, want: &str) -> Result<String, Error> {
    const PLAN_U: &str = r#"PREFIX dcterms: <http://purl.org/dc/terms/>
    PREFIX execution: <http://example.org/orexis/execution#>
    PREFIX orexis: <http://example.org/orexis#>
    PREFIX planning: <http://example.org/orexis/planning#>
    PREFIX prov: <http://www.w3.org/ns/prov#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
    INSERT { GRAPH $plan { $root a planning:Plan ; planning:for $want ; planning:outcome $outcome $costs } }
    WHERE  {} ;
    INSERT { GRAPH $plan { ?step a execution:Step ; execution:partOf $root ;
                           planning:fills ?action ; planning:of ?by ;
                           execution:notBefore ?since ; execution:landsAt ?lands ; execution:notAfter ?after ;
                           execution:adds ?adds ; execution:retracts ?retracts . ?step ?p ?v } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                          $world (planning:by/planning:from)* ?w . ?w planning:by ?by .
                          ?by planning:fills ?action ; planning:from ?in .
                          ?in dcterms:temporal/orexis:start ?since .
                          ?w dcterms:temporal ?period . ?period orexis:start ?lands . OPTIONAL { ?period orexis:end ?after }
                          OPTIONAL { ?by ?p ?v . FILTER(?p NOT IN (planning:fills, planning:from, planning:minted, rdf:type)) } }
             BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?w), "^.*/", ""))) AS ?step)
             BIND(IRI(CONCAT(STR(?step), ".adds")) AS ?adds)
             BIND(IRI(CONCAT(STR(?step), ".retracts")) AS ?retracts) } ;
    INSERT { GRAPH $plan { ?prev execution:then ?step } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                          $world (planning:by/planning:from)* ?w . ?w planning:by ?by .
                          ?w planning:by/planning:from ?parent . ?parent planning:by ?was }
             BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?w), "^.*/", ""))) AS ?step)
             BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?parent), "^.*/", ""))) AS ?prev) } ;
    INSERT { GRAPH ?cat { $plan a planning:PlanGraph ; orexis:arrivedBy orexis:Derived }
             GRAPH $plan { $plan a planning:PlanGraph , orexis:Graph ; orexis:arrivedBy orexis:Derived } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } } ;
    INSERT { GRAPH ?cat { $plan a ?kind } GRAPH $plan { $plan a ?kind } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph }
             GRAPH ?vocabulary { ?vocabulary a orexis:OntologyGraph . planning:PlanGraph rdfs:subClassOf ?kind } } ;
    INSERT { GRAPH ?adds { ?s ?p ?o } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                          $world (planning:by/planning:from)* ?w . ?w planning:by ?by . ?by planning:from ?in
                          FILTER NOT EXISTS { ?own prov:wasDerivedFrom ?w ; a execution:AddsGraph } }
             GRAPH ?w { ?s ?p ?o FILTER NOT EXISTS { ?s a orexis:Graph } FILTER NOT EXISTS { ?s a dcterms:PeriodOfTime } }
             FILTER NOT EXISTS { GRAPH ?in { ?s ?p ?o } }
             BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?w), "^.*/", ""), ".adds")) AS ?adds) } ;
    INSERT { GRAPH ?adds { ?s ?p ?o } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                          $world (planning:by/planning:from)* ?w . ?w planning:by ?by .
                          ?own prov:wasDerivedFrom ?w ; a execution:AddsGraph }
             GRAPH ?own { ?s ?p ?o FILTER NOT EXISTS { ?s a orexis:Graph } FILTER NOT EXISTS { ?s a dcterms:PeriodOfTime } }
             BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?w), "^.*/", ""), ".adds")) AS ?adds) } ;
    INSERT { GRAPH ?retracts { ?s ?p ?o } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                          $world (planning:by/planning:from)* ?w . ?w planning:by ?by . ?by planning:from ?in
                          FILTER NOT EXISTS { ?own prov:wasDerivedFrom ?w ; a execution:RetractsGraph } }
             GRAPH ?in { ?s ?p ?o FILTER NOT EXISTS { ?s a orexis:Graph } FILTER NOT EXISTS { ?s a dcterms:PeriodOfTime } }
             FILTER NOT EXISTS { GRAPH ?w { ?s ?p ?o } }
             BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?w), "^.*/", ""), ".retracts")) AS ?retracts) } ;
    INSERT { GRAPH ?retracts { ?s ?p ?o } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                          $world (planning:by/planning:from)* ?w . ?w planning:by ?by .
                          ?own prov:wasDerivedFrom ?w ; a execution:RetractsGraph }
             GRAPH ?own { ?s ?p ?o FILTER NOT EXISTS { ?s a orexis:Graph } FILTER NOT EXISTS { ?s a dcterms:PeriodOfTime } }
             BIND(IRI(CONCAT(STR($plan), ".", REPLACE(STR(?w), "^.*/", ""), ".retracts")) AS ?retracts) } ;
    INSERT { GRAPH ?cat { ?adds a execution:AddsGraph ; orexis:arrivedBy orexis:Derived .
                          ?retracts a execution:RetractsGraph ; orexis:arrivedBy orexis:Derived }
             GRAPH ?adds { ?adds a execution:AddsGraph , orexis:Graph ; orexis:arrivedBy orexis:Derived }
             GRAPH ?retracts { ?retracts a execution:RetractsGraph , orexis:Graph ; orexis:arrivedBy orexis:Derived } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph }
             GRAPH $plan { ?step execution:adds ?adds ; execution:retracts ?retracts } } ;
    INSERT { GRAPH ?cat { ?g a ?kind } GRAPH ?g { ?g a ?kind } }
    WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph }
             GRAPH $plan { ?step execution:adds|execution:retracts ?g }
             GRAPH ?g { ?g a ?class }
             GRAPH ?vocabulary { ?vocabulary a orexis:OntologyGraph . ?class rdfs:subClassOf ?kind } }"#;
    /// THE BEST WORLD WHERE THE WANT IS MET: on time and cheapest, or the soonest and then the cheapest.
    const BEST_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
    PREFIX planning: <http://example.org/orexis/planning#>
    SELECT ?w ?spent WHERE {
      GRAPH ?cat { ?cat a orexis:CatalogueGraph .
        ?x a planning:Weighing ; planning:for $want ; planning:met true ; planning:weighs ?w .
        OPTIONAL { ?w planning:spent ?s } OPTIONAL { ?w planning:minted ?m }
        OPTIONAL { ?x planning:late ?lands } }
      BIND(COALESCE(?s, 0.0) AS ?spent) BIND(COALESCE(?m, 0) AS ?minted) BIND(IF(BOUND(?lands), 1, 0) AS ?late) }
    ORDER BY ?late ?lands ?spent ?minted LIMIT 1";
    /// THE GROUND THE SEARCH STOOD IN, and what the search spent, which tells the two silences apart.
    const ROOT_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
    PREFIX planning: <http://example.org/orexis/planning#>
    SELECT ?g (COUNT(?y) AS ?spent) WHERE {
      GRAPH ?cat { ?cat a orexis:CatalogueGraph .
        ?x a planning:Weighing ; planning:for $want ; planning:weighs ?g . ?g a planning:GroundGraph .
        OPTIONAL { ?y a planning:Weighing ; planning:for $want ; planning:weighs ?w .
                   FILTER NOT EXISTS { ?w a planning:GroundGraph } } } }
    GROUP BY ?g";
    /// THE GRAPHS A PLAN'S STEPS NAME — what goes when the plan is replaced.
    const STEP_GRAPHS_Q: &str = "PREFIX execution: <http://example.org/orexis/execution#>
        SELECT ?g WHERE { GRAPH $plan { ?step execution:adds|execution:retracts ?g } }";
    let found = store.rows(&bind(BEST_Q, &[("want", Value::iri(want))])?, &[])?;
    let (world, outcome, cost) = match found.first().and_then(|b| Some((iri(b, "w")?, value(b, "spent")?))) {
        Some((world, spent)) => (world, SATISFIED, Some(spent)),
        None => {
            let roots = store.rows(&bind(ROOT_Q, &[("want", Value::iri(want))])?, &[])?;
            let Some(root) = roots.first() else {
                return Err(Error::Evaluation(format!(
                    "nothing was weighed for {want} — has its search begun?"
                )));
            };
            let spent: u64 = value(root, "spent").and_then(|s| s.parse().ok()).unwrap_or(0);
            let world = iri(root, "g").ok_or_else(|| Error::Evaluation("a root that names no ground".into()))?;
            (world, if spent > 0 { EXHAUSTED } else { NO_CANDIDATE }, None)
        }
    };
    let graph = plan_graph(want);
    let plan = Value::iri(graph.as_str());
    for r in store.rows(&bind(STEP_GRAPHS_Q, &[("plan", plan.clone())])?, &[])? {
        if let Some(g) = iri(&r, "g") {
            store.forget_graph(&g, Some(orexis::ontology::BELIEF))?;
        }
    }
    store.clear_graph(&graph)?;
    let costs = match cost {
        Some(spent) => format!(" ; planning:spent \"{}\"^^xsd:decimal", py_float(&spent)),
        None => String::new(),
    };
    store.update(&bind(
        PLAN_U,
        &[
            ("plan", plan),
            ("root", Value::iri(plan_root(&graph))),
            ("want", Value::iri(want)),
            ("outcome", Value::iri(outcome)),
            ("world", Value::iri(world.as_str())),
            ("costs", Value::Raw(costs)),
        ],
    )?)?;
    Ok(graph)
}

/// The root of the plan written in `graph`: the node that is the plan, named off its graph and never as it.
pub fn plan_root(graph: &str) -> String {
    format!("{graph}.plan")
}

/// A decimal's lexical form as Python's `str(float(...))` spells it.
fn py_float(lexical: &str) -> String {
    lexical
        .parse::<f64>()
        .map_or_else(|_| lexical.to_string(), orexis::rdf::repr)
}

/// The graph one want's plan is written into — one per want, replaced whole.
pub fn plan_graph(want: &str) -> String {
    format!("{GRAPH_PREFIX}plan/{}", quoted(&local_of(want)))
}

/// A name as Python's `urllib.parse.quote(…, safe="")` escapes it.
fn quoted(text: &str) -> String {
    let mut out = String::new();
    for b in text.bytes() {
        if b.is_ascii_alphanumeric() || b"_.-~".contains(&b) {
            out.push(b as char);
        } else {
            out.push_str(&format!("%{b:02X}"));
        }
    }
    out
}
