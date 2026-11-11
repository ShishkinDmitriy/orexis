//! AN ACTION'S IMPLEMENTATION, as `agent/execution/implementation.py` reads it: the operations taking a step does,
//! each of a kind execution knows — a command to a device, a saying to a peer, a fictive write of the step's own
//! effect — grouped by `sh:order`, an absent order being 0 as SHACL says.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::ACTION;
use orexis::store::{Store, Within, iri, value};

const OPERATIONS_Q: &str = "
SELECT ?kind ?order ?text WHERE {
  $action execution:implementation/execution:operation ?op .
  ?op a ?kind . VALUES ?kind { execution:Command execution:Saying execution:Fictive }
  OPTIONAL { ?op sh:order ?o } OPTIONAL { ?op sh:select ?select } OPTIONAL { ?op sh:construct ?construct }
  BIND(COALESCE(?o, 0) AS ?order) BIND(COALESCE(?select, ?construct) AS ?text) }
ORDER BY ?order ?kind ?text";

/// One operation: its kind, its order, and its text where it has one.
#[derive(Clone, Debug, PartialEq)]
pub struct Operation {
    pub kind: String,
    pub order: f64,
    pub text: Option<String>,
}

/// Every operation `action`'s implementation holds, in order — none for an action stating no implementation.
pub fn operations(store: &Store, action: &str) -> Result<Vec<Operation>, Error> {
    let actions = store.graphs_of(&[ACTION], &Within::default())?;
    let actions: Vec<&str> = actions.iter().map(String::as_str).collect();
    let rows = store.rows(&bind(OPERATIONS_Q, &[("action", Value::iri(action))])?, &actions)?;
    Ok(rows
        .iter()
        .filter_map(|r| {
            Some(Operation {
                kind: iri(r, "kind")?,
                order: value(r, "order")?.parse().ok()?,
                text: value(r, "text"),
            })
        })
        .collect())
}
