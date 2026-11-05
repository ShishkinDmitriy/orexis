//! PUBLISHING A PLAN: every plan a pass left in the imaginarium handed DOWN into the beliefs, as
//! `agent/planning/publish_plan.py` hands them: an `orexis:PlanGraph` the agent recorded, pursuing its want, with
//! the two graphs each step predicts in, under names of their own. A plan whose want is gone is nobody's and goes;
//! a plan for a want an intention walks does not cross, nor does a step a standing intention already walks.

use std::collections::{BTreeMap, BTreeSet};

use oxigraph::model::{GraphName, NamedNode, NamedOrBlankNode, Quad, Term};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{BELIEF, GRAPH_PREFIX, RECORDED};
use orexis::store::{Store, Within, iri};

use crate::admit::local_of;
use crate::ontology::{ADDS_GRAPH, PLAN, PLAN_GRAPH, RETRACTS_GRAPH, WANT};

const STANDS_Q: &str = "SELECT ?w WHERE { $want a planning:Want . BIND($want AS ?w) } LIMIT 1";
const FOR_Q: &str = "SELECT ?want WHERE { GRAPH $plan { $plan planning:for ?want } }";
const STEPS_Q: &str = "SELECT ?step WHERE { GRAPH $plan { ?step a execution:Step } }";
const DERIVED_Q: &str = "SELECT ?d WHERE { GRAPH ?g { $want prov:wasDerivedFrom ?d } }";
const STEP_GRAPHS_Q: &str = "SELECT ?step ?g ?side WHERE { GRAPH $plan { ?step ?side ?g . VALUES ?side { execution:adds execution:retracts } } }";

/// Eight hex characters of fresh randomness, as Python's `uuid.uuid4().hex[:8]`: a name is for eyes.
fn tag() -> String {
    let mut bytes = [0u8; 4];
    getrandom::fill(&mut bytes).expect("the system's randomness");
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

/// Hand every plan in `imaginarium` down into `beliefs`, the agent `me`'s, for a want not in `walking`, less the
/// steps `kept` says a standing intention walks. The plan graphs written.
pub fn publish_plan(
    imaginarium: &Store,
    beliefs: &Store,
    me: &str,
    walking: &BTreeSet<String>,
    kept: &BTreeMap<String, Vec<String>>,
) -> Result<Vec<String>, Error> {
    let wants = imaginarium.graphs_of(&[WANT], &Within::default())?;
    let wants: Vec<&str> = wants.iter().map(String::as_str).collect();
    let mut handed = Vec::new();
    for graph in imaginarium.graphs_of(&[PLAN_GRAPH], &Within::default())? {
        let plan = Value::iri(graph.as_str());
        let Some(want) = imaginarium
            .rows(&bind(FOR_Q, &[("plan", plan.clone())])?, &[])?
            .first()
            .and_then(|r| iri(r, "want"))
        else {
            log::error!("a plan graph names no want, so it cannot be published: {graph}");
            continue;
        };
        let step_graphs = imaginarium.rows(&bind(STEP_GRAPHS_Q, &[("plan", plan.clone())])?, &[])?;
        if imaginarium
            .rows(&bind(STANDS_Q, &[("want", Value::iri(want.as_str()))])?, &wants)?
            .is_empty()
        {
            //  A PLAN WHOSE WANT IS GONE is nobody's, and goes with what its steps predict.
            for g in step_graphs.iter().filter_map(|r| iri(r, "g")) {
                imaginarium.forget_graph(&g, Some(BELIEF))?;
            }
            imaginarium.forget_graph(&graph, Some(BELIEF))?;
            continue;
        }
        let skipped: BTreeSet<&String> = kept.get(&want).into_iter().flatten().collect();
        let steps: Vec<String> = imaginarium
            .rows(&bind(STEPS_Q, &[("plan", plan.clone())])?, &[])?
            .iter()
            .filter_map(|r| iri(r, "step"))
            .filter(|s| !skipped.contains(s))
            .collect();
        if walking.contains(&want) || steps.is_empty() {
            continue;
        }
        let published = format!("{GRAPH_PREFIX}plan/{}/{}.{}", local_of(me), local_of(&want), tag());
        let moved = |term: Term| -> Term {
            match &term {
                Term::NamedNode(n) if n.as_str().starts_with(graph.as_str()) => {
                    NamedNode::new_unchecked(format!("{published}{}", &n.as_str()[graph.len()..])).into()
                }
                _ => term,
            }
        };
        let name = GraphName::NamedNode(NamedNode::new_unchecked(published.clone()));
        let mut quads = Vec::new();
        for q in imaginarium.quads(&graph)? {
            let subject: Term = q.subject.clone().into();
            if let Term::NamedNode(s) = &subject
                && skipped.contains(&s.as_str().to_string())
            {
                continue;
            }
            let Ok(subject) = NamedOrBlankNode::try_from(moved(subject)) else {
                continue;
            };
            quads.push(Quad::new(subject, q.predicate, moved(q.object), name.clone()));
        }
        beliefs.add(quads)?;
        let mut entries = Vec::new();
        for r in &step_graphs {
            let (Some(step), Some(g), Some(side)) = (iri(r, "step"), iri(r, "g"), iri(r, "side")) else {
                continue;
            };
            if skipped.contains(&step) {
                continue;
            }
            let Term::NamedNode(into) = moved(NamedNode::new_unchecked(g.clone()).into()) else {
                continue;
            };
            let target = GraphName::NamedNode(into.clone());
            beliefs.add(
                imaginarium
                    .quads(&g)?
                    .into_iter()
                    .map(|q| Quad::new(q.subject, q.predicate, q.object, target.clone())),
            )?;
            let kind = if side.ends_with("adds") {
                ADDS_GRAPH
            } else {
                RETRACTS_GRAPH
            };
            entries.push(beliefs.entry(into.as_str(), &[kind], RECORDED, Some(me), None, None)?);
        }
        let derived: Vec<String> = imaginarium
            .rows(&bind(DERIVED_Q, &[("want", Value::iri(want.as_str()))])?, &[])?
            .iter()
            .filter_map(|r| iri(r, "d"))
            .map(|d| format!("<{want}> prov:wasDerivedFrom <{d}> ."))
            .collect();
        beliefs.update(&format!(
            "INSERT DATA {{
  GRAPH <{published}> {{ <{published}> execution:pursues <{want}> . {} }}
  {} {} }}",
            derived.join(" "),
            beliefs.entry(&published, &[PLAN], RECORDED, Some(me), None, None)?,
            entries.join(" ")
        ))?;
        handed.push(published);
    }
    Ok(handed)
}
