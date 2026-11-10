//! THE PLANS A PASS KEPT: the steps a published plan says, the plans marked kept, the refinements nobody's plan
//! needs any more withdrawn, and whether a want's search has exhausted what it can reach.

use std::collections::{BTreeMap, BTreeSet};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{ACTION, BELIEF};
use orexis::store::{Store, Within, iri, value};

use super::{Planner, REFINED_Q, Said, graphs, strs};
use crate::admit::local_of;
use crate::bridge::keeps;
use crate::ontology::{EXHAUSTED, PLAN_GRAPH};
use crate::withdraw::withdraw;

const CHAIN_Q: &str = r#"
SELECT ?step ?next ?action ?p ?v WHERE { GRAPH $plan { ?step a execution:Step ; planning:fills ?action ; ?p ?v .
  OPTIONAL { ?step execution:then ?next } } }"#;

const TAKES_Q: &str = r#"SELECT ?takes WHERE { $action orexis:takes ?takes }"#;

const STANDING_AT_Q: &str = r#"
SELECT DISTINCT ?step WHERE { GRAPH ?g { ?i a execution:Intention ; execution:by ?step .
                                         FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }"#;

const FICTIVE_STEPS_Q: &str = r#"
SELECT ?step WHERE {
  GRAPH $plan { ?step a execution:Step ; planning:fills ?action }
  ?action execution:implementation/execution:operation ?op . ?op a execution:Fictive }
ORDER BY ?step"#;

const OUTCOMES_Q: &str = r#"SELECT ?o WHERE { GRAPH $plan { ?p a planning:Plan ; planning:outcome ?o } }"#;

impl<'a> Planner<'a> {
    /// The steps of `plan` in `store`, in the order walked, each with the action it fills and its filling.
    pub(super) fn chain(&self, store: &Store, plan: &str) -> Result<Vec<(String, Said)>, Error> {
        let actions = graphs(&self.beliefs, &[ACTION])?;
        let mut said: BTreeMap<String, (String, BTreeMap<String, String>)> = BTreeMap::new();
        let mut after: BTreeMap<String, String> = BTreeMap::new();
        for r in store.rows(&bind(CHAIN_Q, &[("plan", Value::iri(plan))])?, &[])? {
            let (Some(step), Some(action)) = (iri(&r, "step"), iri(&r, "action")) else {
                continue;
            };
            let held = said.entry(step.clone()).or_insert_with(|| (action, BTreeMap::new()));
            if let (Some(p), Some(v)) = (iri(&r, "p"), value(&r, "v")) {
                held.1.insert(p, v);
            }
            if let Some(next) = iri(&r, "next") {
                after.insert(step, next);
            }
        }
        let mut takes: BTreeMap<String, BTreeSet<String>> = BTreeMap::new();
        for (action, _) in said.values() {
            if !takes.contains_key(action) {
                let found: BTreeSet<String> = self
                    .beliefs
                    .rows(
                        &bind(TAKES_Q, &[("action", Value::iri(action.as_str()))])?,
                        &strs(&actions),
                    )?
                    .iter()
                    .filter_map(|t| iri(t, "takes"))
                    .collect();
                takes.insert(action.clone(), found);
            }
        }
        let followers: BTreeSet<&String> = after.values().collect();
        let mut head = said.keys().find(|s| !followers.contains(s)).cloned();
        let mut out = Vec::new();
        let mut seen = BTreeSet::new();
        while let Some(step) = head {
            let Some((action, values)) = said.get(&step) else { break };
            if !seen.insert(step.clone()) {
                break;
            }
            let filling = values
                .iter()
                .filter(|(p, _)| takes[action].contains(*p))
                .map(|(p, v)| (p.clone(), v.clone()))
                .collect();
            out.push((step.clone(), (action.clone(), filling)));
            head = after.get(&step).cloned();
        }
        Ok(out)
    }

    /// Say of every step of a plan published that a bridge keeps below that it is `execution:keptBelow`.
    pub(super) fn mark_kept(&self, handed: &[String]) -> Result<(), Error> {
        let actions = graphs(&self.beliefs, &[ACTION])?;
        for plan in handed {
            for r in self.beliefs.rows(
                &bind(FICTIVE_STEPS_Q, &[("plan", Value::iri(plan.as_str()))])?,
                &strs(&actions),
            )? {
                let Some(step) = iri(&r, "step") else { continue };
                if keeps(&self.beliefs, &step)? {
                    self.beliefs.update(&format!(
                        "INSERT DATA {{ GRAPH <{plan}> {{ <{step}> execution:keptBelow true }} }}"
                    ))?;
                }
            }
        }
        Ok(())
    }

    /// A want kept below for a step no intention stands at any more is nothing's: withdrawn, here and everywhere.
    pub(super) fn withdraw_orphaned_refinements(&self, walking: &BTreeSet<String>) -> Result<(), Error> {
        let standing_at: BTreeSet<String> = self
            .beliefs
            .rows(STANDING_AT_Q, &[])?
            .iter()
            .filter_map(|r| iri(r, "step"))
            .collect();
        for r in self.beliefs.rows(REFINED_Q, &[])? {
            let (Some(step), Some(want), Some(g)) = (iri(&r, "step"), iri(&r, "want"), iri(&r, "g")) else {
                continue;
            };
            if standing_at.contains(&step) || walking.contains(&want) {
                continue;
            }
            self.beliefs.forget_graph(&g, Some(BELIEF))?;
            let reached = BTreeSet::from([want.clone()]);
            for store in self.imaginaria.values() {
                withdraw(store, None, &reached, &BTreeSet::new())?;
            }
            log::info!(
                "{}: withdrew {}, since nothing stands at the step it kept",
                self.id,
                local_of(&want)
            );
        }
        Ok(())
    }

    /// Whether any search of the last pass stopped on its budget rather than on an answer.
    pub fn exhausted(&self) -> Result<bool, Error> {
        for store in self.imaginaria.values() {
            for plan in store.graphs_of(&[PLAN_GRAPH], &Within::default())? {
                let found = store.rows(&bind(OUTCOMES_Q, &[("plan", Value::iri(plan.as_str()))])?, &[])?;
                if found.iter().any(|r| iri(r, "o").as_deref() == Some(EXHAUSTED)) {
                    return Ok(true);
                }
            }
        }
        Ok(false)
    }
}
