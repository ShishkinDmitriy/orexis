//! A HEAD ABOUT TO BE TAKEN, checked: the executor says `taking`, and planning asks the present whether the step's
//! precondition holds and whether the world it lands in is one the agent believes possible.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::Arc;

use oxigraph::model::{GraphName, NamedNode, Quad};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{ACTION, BELIEF};
use orexis::store::{Store, Within, iri, value};

use super::{Planner, graphs, quads_of, strs, zero};
use crate::admit::local_of;
use crate::memo::Memo;
use crate::ontology::CONSTRAINT_GRAPH;
use crate::world_at::{Asking, lexical, world_at};

const HEAD_Q: &str = r#"
SELECT ?action WHERE { GRAPH ?p { $step planning:fills ?action }
  FILTER NOT EXISTS { GRAPH ?k { $step execution:keptBelow true } } } LIMIT 1"#;

const PRECONDITION_Q: &str =
    r#"SELECT ?text ?takes WHERE { $action planning:precondition ?text . OPTIONAL { $action orexis:takes ?takes } }"#;

const FILLING_Q: &str = r#"SELECT ?p ?v WHERE { GRAPH ?plan { $step ?p ?v } }"#;

const CHANGE_Q: &str = r#"SELECT ?retracts ?adds WHERE { GRAPH ?p { $step a execution:Step .
  OPTIONAL { $step execution:retracts ?retracts } OPTIONAL { $step execution:adds ?adds } }
  FILTER(BOUND(?retracts) || BOUND(?adds)) } LIMIT 1"#;

const BAND_Q: &str =
    r#"SELECT ?due ?after WHERE { GRAPH ?p { $step execution:notBefore ?due ; execution:notAfter ?after } } LIMIT 1"#;

const AHEAD_Q: &str = r#"
SELECT ?g ?start ?end WHERE { GRAPH $cat { ?g a orexis:ForecastGraph . FILTER NOT EXISTS { ?g a execution:CommittedStepGraph }
  OPTIONAL { ?g dcterms:temporal ?p . OPTIONAL { ?p orexis:start ?start } OPTIONAL { ?p orexis:end ?end } } } }"#;

const CONSTRAINT_TEXTS_Q: &str = r#"
SELECT ?c ?text WHERE { $holder planning:holds ?c . ?c a planning:Constraint .
  { ?c planning:unmetWhen ?s . ?s sh:select ?text } UNION { ?c planning:metWhen ?shape . ?shape sh:sparql/sh:select ?text } }"#;

const SCRATCH: &str = "urn:orexis:world";

/// The rows a constraint's select yields over a world — none where its text will not run.
fn violations(world: &Store, text: &str) -> BTreeSet<String> {
    match world.rows(text, &[SCRATCH]) {
        Ok(rows) => rows
            .iter()
            .map(|r| r.iter().map(|(k, v)| format!("{k}={v}")).collect::<Vec<_>>().join(" "))
            .collect(),
        Err(_) => BTreeSet::new(),
    }
}

impl Planner {
    /// Check `step`, a head about to be handed to its taker at `at`, against the present: BLOCKED, and true, where its
    /// action's precondition admits it no more, where the world it lands in violates a constraint the world before
    /// does not, or where a world of its plan was foreseen impossible after it. A step kept below is not checked.
    pub fn check(&mut self, step: &str, at: DateTime) -> Result<bool, Error> {
        if self.doomed.values().any(|s| s == step) {
            log::info!(
                "{}: {} is not taken — a world of its plan was foreseen impossible after it",
                self.id,
                local_of(step)
            );
            self.blocked.push(step.to_string());
            return Ok(true);
        }
        let beliefs = &self.beliefs;
        let head = beliefs.rows(&bind(HEAD_Q, &[("step", Value::iri(step))])?, &[])?;
        let Some(action) = head.first().and_then(|r| iri(r, "action")) else {
            return Ok(false);
        };
        let actions = graphs(beliefs, &[ACTION])?;
        let found = beliefs.rows(
            &bind(PRECONDITION_Q, &[("action", Value::iri(action.as_str()))])?,
            &strs(&actions),
        )?;
        let Some(text) = found.first().and_then(|r| value(r, "text")) else {
            return Ok(false);
        };
        let takes: BTreeSet<String> = found.iter().filter_map(|r| iri(r, "takes")).collect();
        let filling: BTreeMap<String, String> = beliefs
            .rows(&bind(FILLING_Q, &[("step", Value::iri(step))])?, &[])?
            .iter()
            .filter_map(|r| Some((iri(r, "p")?, value(r, "v")?)))
            .filter(|(p, _)| takes.contains(p))
            .map(|(p, v)| (local_of(&p), v))
            .collect();
        let mut memo = Memo::default();
        let present = world_at(
            beliefs,
            None,
            &Asking {
                now: Some(at),
                ..Asking::default()
            },
            &mut memo,
        )?;
        let answers = beliefs.rows(&bind(&text, &[])?, &strs(&present))?;
        if !answers.iter().any(|row| {
            filling
                .iter()
                .all(|(k, v)| value(row, k).as_deref() == Some(v.as_str()))
        }) {
            log::info!(
                "{}: {} is not taken — the present admits it no more",
                self.id,
                local_of(step)
            );
        } else if let Some(broken) = self.lands_impossible(step, &present, at)? {
            log::info!(
                "{}: {} is not taken — the world it lands in violates {broken}",
                self.id,
                local_of(step)
            );
        } else {
            return Ok(false);
        }
        self.blocked.push(step.to_string());
        Ok(true)
    }

    /// The constraint the world `step` lands in violates where the world before it does not, as the agent believes
    /// them now: the present beside every forecast holding in the step's band, and its change applied by key.
    fn lands_impossible(&self, step: &str, present: &[String], at: DateTime) -> Result<Option<String>, Error> {
        if !self.holds_a_constraint()? {
            return Ok(None);
        }
        let beliefs = &self.beliefs;
        let change = beliefs.rows(&bind(CHANGE_Q, &[("step", Value::iri(step))])?, &[])?;
        let change = change.first();
        let retracts = quads_of(beliefs, change.and_then(|r| iri(r, "retracts")))?;
        let adds = quads_of(beliefs, change.and_then(|r| iri(r, "adds")))?;
        if retracts.is_empty() && adds.is_empty() {
            return Ok(None);
        }
        let band = beliefs.rows(&bind(BAND_Q, &[("step", Value::iri(step))])?, &[])?;
        let latest = match band.first() {
            Some(b) if b.contains_key("after") && b.contains_key("due") => {
                let stretch = lexical(&b["after"])?
                    .checked_sub(lexical(&b["due"])?)
                    .unwrap_or_else(zero);
                at.checked_add_day_time_duration(stretch).unwrap_or(at)
            }
            _ => at,
        };
        let catalogue = beliefs.catalogue()?.unwrap_or_default();
        let mut ahead = Vec::new();
        for r in beliefs.rows(&bind(AHEAD_Q, &[("cat", Value::Raw(format!("<{catalogue}>")))])?, &[])? {
            let Some(g) = iri(&r, "g") else { continue };
            let starts_by = r.get("start").map(lexical).transpose()?.is_none_or(|s| s <= latest);
            let ends_after = r.get("end").map(lexical).transpose()?.is_none_or(|e| e > at);
            if !present.contains(&g) && starts_by && ends_after {
                ahead.push(g);
            }
        }
        let world = Store::new(Arc::new(beliefs.namespaces().clone()))?;
        let scratch = GraphName::NamedNode(NamedNode::new_unchecked(SCRATCH));
        for g in present.iter().chain(&ahead) {
            world.add(
                beliefs
                    .quads(g)?
                    .into_iter()
                    .map(|q| Quad::new(q.subject, q.predicate, q.object, scratch.clone())),
            )?;
        }
        let mut held = graphs(beliefs, &[CONSTRAINT_GRAPH])?;
        held.extend(beliefs.graphs_of(&[BELIEF], &Within::common())?);
        let texts: Vec<(String, String)> = beliefs
            .rows(
                &bind(CONSTRAINT_TEXTS_Q, &[("holder", Value::iri(self.uri.as_str()))])?,
                &strs(&held),
            )?
            .iter()
            .filter_map(|r| Some((iri(r, "c")?, value(r, "text")?)))
            .collect();
        let before: Vec<BTreeSet<String>> = texts.iter().map(|(_, t)| violations(&world, t)).collect();
        let at_scratch = |q: &Quad| {
            Quad::new(
                q.subject.clone(),
                q.predicate.clone(),
                q.object.clone(),
                scratch.clone(),
            )
        };
        world.remove_all(&retracts.iter().map(at_scratch).collect::<Vec<_>>())?;
        let keys: BTreeSet<(String, String)> = adds
            .iter()
            .map(|q| (q.subject.to_string(), q.predicate.to_string()))
            .collect();
        let superseded: Vec<Quad> = world
            .quads(SCRATCH)?
            .into_iter()
            .filter(|q| keys.contains(&(q.subject.to_string(), q.predicate.to_string())))
            .collect();
        world.remove_all(&superseded)?;
        world.add(adds.iter().map(at_scratch))?;
        for ((c, text), before) in texts.iter().zip(before) {
            if !violations(&world, text).is_subset(&before) {
                return Ok(Some(local_of(c)));
            }
        }
        Ok(None)
    }
}
