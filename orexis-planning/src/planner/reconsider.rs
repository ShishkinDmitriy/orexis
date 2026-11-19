//! A WALKING WANT RECONSIDERED: where each standing intention stands, a world its untaken steps reach that a belief
//! makes impossible, a want a constraint couples to it, or a role above planning asking — and then its untaken steps
//! reopened.

use std::collections::{BTreeMap, BTreeSet};

use oxigraph::model::{GraphName, NamedNode, Quad};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within, iri};

use super::search::Searcher;
use super::{
    Change, Planner, Said, StepInFlight, Walk, Walks, broken, chain, graphs, later, predicted, quads_of, said, strs,
    zero,
};
use crate::admit::local_of;
use crate::memo::Memo;
use crate::ontology::{CONSTRAINT_GRAPH, GROUND_GRAPH, SATISFIED};
use crate::world_at::lexical;

/// Every want `store` derived, across its want graphs.
fn derived(store: &Store) -> Result<BTreeSet<String>, Error> {
    const DERIVED_Q: &str = r#"PREFIX orexis: <http://example.org/orexis#>
    PREFIX planning: <http://example.org/orexis/planning#>
    SELECT ?w WHERE { GRAPH ?g { ?w a planning:Want }
      GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }"#;
    Ok(store.rows(DERIVED_Q, &[])?.iter().filter_map(|r| iri(r, "w")).collect())
}

impl Planner {
    /// Ask that each of `wants` an intention walks be searched again in the next pass.
    pub fn reopen(&mut self, wants: impl IntoIterator<Item = String>) {
        self.asked.extend(wants);
    }

    /// Whether this agent holds any constraint — the one thing a walking want can be reopened by.
    pub(super) fn holds_a_constraint(&self) -> Result<bool, Error> {
        const HOLDS_CONSTRAINT_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
            SELECT ?c WHERE { $holder planning:holds ?c . ?c a planning:Constraint } LIMIT 1"#;
        let held = graphs(&self.beliefs, &[CONSTRAINT_GRAPH])?;
        Ok(!self
            .beliefs
            .rows(
                &bind(HOLDS_CONSTRAINT_Q, &[("holder", Value::iri(self.uri.as_str()))])?,
                &strs(&held),
            )?
            .is_empty())
    }

    /// Where every standing intention stands, by the want it pursues.
    pub(super) fn walks(&self, at: DateTime) -> Result<Walks, Error> {
        const STANDS_AT_Q: &str = r#"PREFIX execution: <http://example.org/orexis/execution#>
        PREFIX planning: <http://example.org/orexis/planning#>
        SELECT ?intention ?want ?plan ?step ?action ?due ?taken ?lands ?ending WHERE {
          GRAPH ?g { ?intention a execution:Intention ; execution:pursues ?want ; execution:by ?step ; execution:adopts ?plan .
                     FILTER NOT EXISTS { ?intention execution:resolvedAt ?done }
                     OPTIONAL { ?act execution:of ?step ; execution:taken true ; execution:takenAt ?taken }
                     OPTIONAL { ?intention execution:endsAfter ?ending } }
          GRAPH ?plan { ?step planning:fills ?action .
                        OPTIONAL { ?step execution:notBefore ?due } OPTIONAL { ?step execution:landsAt ?lands } } }
        ORDER BY ?intention"#;
        let mut held: BTreeMap<String, Vec<Walk>> = BTreeMap::new();
        for r in self.beliefs.rows(STANDS_AT_Q, &[])? {
            let (Some(want), Some(plan), Some(head), Some(action)) =
                (iri(&r, "want"), iri(&r, "plan"), iri(&r, "step"), iri(&r, "action"))
            else {
                continue;
            };
            let taken = r.get("taken").map(lexical).transpose()?;
            let due = r.get("due").map(lexical).transpose()?;
            let lands = r.get("lands").map(lexical).transpose()?;
            let (mut landing, mut late) = (at, zero());
            match (taken, lands) {
                (Some(taken), Some(lands)) => {
                    if let Some(due) = due
                        && let Some(behind) = taken.checked_sub(due)
                        && behind > zero()
                    {
                        late = behind;
                    }
                    landing = lands.checked_add_day_time_duration(late).unwrap_or(lands);
                }
                (None, _) => {
                    if let Some(due) = due
                        && let Some(behind) = at.checked_sub(due)
                        && behind > zero()
                    {
                        late = behind;
                    }
                }
                _ => {}
            }
            let walk = Walk {
                plan,
                head,
                action,
                in_flight: taken.is_some(),
                ending: r.contains_key("ending"),
                late,
                landing: later(landing, at),
                steps_in_flight: Vec::new(),
                steps: Vec::new(),
                predicts: BTreeMap::new(),
            };
            held.entry(want).or_default().push(walk);
        }
        let mut out = Walks::new();
        //  ONE WALK PER WANT, though an intention ending after its step in flight and the one replacing it both pursue
        //  it: the standing one's plan and head, every step in flight of either, and the latest landing.
        for (want, walks) in held {
            let mut walk = walks.iter().find(|w| !w.ending).unwrap_or(&walks[0]).clone();
            walk.steps_in_flight = walks
                .iter()
                .filter(|w| w.in_flight)
                .map(|w| StepInFlight {
                    action: w.action.clone(),
                    lands: w.landing,
                    plan: w.plan.clone(),
                    step: w.head.clone(),
                })
                .collect();
            walk.landing = walks.iter().map(|w| w.landing).fold(at, later);
            //  WHAT ITS PLAN SAYS AND PREDICTS, read here, so that a scope's search reads nothing of the beliefs.
            walk.steps = chain(&self.beliefs, &walk.plan)?;
            for (step, said) in predicted(&self.beliefs, walk.plan.as_str())? {
                let change = Change {
                    lands: said.lands,
                    retracts: quads_of(&self.beliefs, said.retracts)?,
                    adds: quads_of(&self.beliefs, said.adds)?,
                };
                walk.predicts.insert(step, change);
            }
            out.insert(want, walk);
        }
        Ok(out)
    }
}

impl Searcher {
    /// The asked wants a walking plan of this scope pursues, derived here and not ending; each taken from the asked as the pass ends.
    pub(super) fn asked_here(
        &self,
        store: &Store,
        walks: &Walks,
        only: Option<&BTreeSet<String>>,
        asked: &BTreeSet<String>,
    ) -> Result<BTreeSet<String>, Error> {
        if asked.is_empty() {
            return Ok(BTreeSet::new());
        }
        let derived = derived(store)?;
        let out: BTreeSet<String> = asked
            .iter()
            .filter(|w| {
                walks
                    .get(*w)
                    .is_some_and(|f| !f.ending && only.is_none_or(|o| o.contains(&f.action)))
                    && derived.contains(*w)
            })
            .cloned()
            .collect();
        for want in &out {
            log::info!("{}: {} is reopened, as asked", self.id, local_of(want));
        }
        Ok(out)
    }

    /// The walking wants of this scope a world of whose plan is IMPOSSIBLE in the grounds as now laid (#921): the
    /// plan's untaken steps replayed on the new grounds, each world weighed for the constraints.
    pub(super) fn impossible_ahead(
        &self,
        store: &Store,
        walks: &Walks,
        constraints: &[String],
        only: Option<&BTreeSet<String>>,
        doomed: &mut Vec<(String, Option<String>)>,
        memo: &mut Memo,
    ) -> Result<BTreeSet<String>, Error> {
        const FORESEEN_U: &str = r#"PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX orexis: <http://example.org/orexis#>
        INSERT { GRAPH ?cat { $world dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start $start ] } }
        WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"#;
        const UNWEIGH_U: &str = r#"PREFIX orexis: <http://example.org/orexis#>
        PREFIX planning: <http://example.org/orexis/planning#>
        DELETE { GRAPH ?cat { ?x ?p ?o . ?v ?vp ?vo } }
        WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                              ?x planning:weighs $world ; ?p ?o .
                              OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"#;
        let derived = derived(store)?;
        let mut out = BTreeSet::new();
        for (want, walk) in walks {
            if walk.ending || !derived.contains(want) || only.is_some_and(|o| !o.contains(&walk.action)) {
                continue;
            }
            let chain: Vec<String> = walk.steps.iter().map(|(s, _)| s.clone()).collect();
            let from = chain.iter().position(|s| *s == walk.head).unwrap_or(chain.len());
            let untaken = &chain[from..];
            if untaken.is_empty() || (untaken.len() == 1 && walk.in_flight) {
                continue;
            }
            let mut foreseen: Vec<String> = Vec::new();
            let found = (|| -> Result<Option<bool>, Error> {
                let mut changes: Vec<(Vec<Quad>, Vec<Quad>)> = Vec::new();
                let (mut before, mut world): (Option<String>, Option<String>) = (None, None);
                for step in untaken {
                    let row = walk.predicts.get(step);
                    let lands = match row.and_then(|p| p.lands.as_ref()) {
                        Some(l) => lexical(l)?
                            .checked_add_day_time_duration(walk.late)
                            .unwrap_or(walk.landing),
                        None => walk.landing,
                    };
                    let lands = later(lands, walk.landing);
                    let Some(ground) = store.graphs_of(&[GROUND_GRAPH], &Within::at(lands))?.into_iter().next() else {
                        return Ok(None);
                    };
                    let change = (
                        row.map(|p| p.retracts.clone()).unwrap_or_default(),
                        row.map(|p| p.adds.clone()).unwrap_or_default(),
                    );
                    changes.push(change.clone());
                    let (base, applying) = match (&before, &world) {
                        (Some(b), Some(w)) if *b == ground => (w.clone(), vec![change]),
                        _ => (ground.clone(), changes.clone()),
                    };
                    let next = format!("{step}.foreseen");
                    foreseen.push(next.clone());
                    crate::fork::fork(store, &base, &next, &[], &[])?;
                    let target = GraphName::NamedNode(NamedNode::new_unchecked(next.clone()));
                    for (retracts, adds) in &applying {
                        let at_target = |q: &Quad| {
                            Quad::new(q.subject.clone(), q.predicate.clone(), q.object.clone(), target.clone())
                        };
                        store.remove_all(&retracts.iter().map(at_target).collect::<Vec<_>>())?;
                        let keys: BTreeSet<(String, String)> = adds
                            .iter()
                            .map(|q| (q.subject.to_string(), q.predicate.to_string()))
                            .collect();
                        let superseded: Vec<Quad> = store
                            .quads(&next)?
                            .into_iter()
                            .filter(|q| keys.contains(&(q.subject.to_string(), q.predicate.to_string())))
                            .collect();
                        store.remove_all(&superseded)?;
                        store.add(adds.iter().map(at_target))?;
                    }
                    store.update(&bind(
                        FORESEEN_U,
                        &[("world", Value::iri(next.as_str())), ("start", Value::instant(lands))],
                    )?)?;
                    before = Some(ground);
                    world = Some(next.clone());
                    for c in constraints {
                        let rows = broken(store, c, &next, memo)?;
                        if !rows.is_empty() {
                            log::info!(
                                "{}: {} would be impossible after {} — it violates {}: {}, so it is reopened",
                                self.id,
                                local_of(want),
                                local_of(step),
                                local_of(c),
                                said(&rows)
                            );
                            doomed.push((want.clone(), Some(step.clone())));
                            return Ok(Some(true));
                        }
                    }
                }
                Ok(Some(false))
            })();
            for world in &foreseen {
                store.update(&bind(UNWEIGH_U, &[("world", Value::iri(world.as_str()))])?)?;
                store.forget_graph(world, Some(BELIEF))?;
            }
            match found? {
                Some(true) => {
                    out.insert(want.clone());
                }
                Some(false) => {
                    doomed.push((want.clone(), None));
                    log::debug!(
                        "{}: {} world(s) of {}'s untaken steps foreseen, none impossible",
                        self.id,
                        foreseen.len(),
                        local_of(want)
                    );
                }
                None => {}
            }
        }
        Ok(out)
    }

    /// Hold the plan `want`'s search just wrote against the walking intentions it reopens: where it begins with their
    /// untaken steps they stand and those steps are kept out of what is published; anything else replaces them.
    pub(super) fn reconsider(
        &self,
        store: &Store,
        want: &str,
        walks: &Walks,
        kept: &mut BTreeMap<String, Vec<String>>,
    ) -> Result<(), Error> {
        const REOPENS_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
            SELECT ?w WHERE { GRAPH ?g { $want planning:reopens ?w } } ORDER BY ?w"#;
        const PLAN_FOR_Q: &str = r#"PREFIX planning: <http://example.org/orexis/planning#>
            SELECT ?plan ?outcome WHERE { GRAPH ?plan { ?plan a planning:Plan ; planning:for $want ; planning:outcome ?outcome } } LIMIT 1"#;
        let reopened: Vec<String> = store
            .rows(&bind(REOPENS_Q, &[("want", Value::iri(want))])?, &[])?
            .iter()
            .filter_map(|r| iri(r, "w"))
            .collect();
        if reopened.is_empty() {
            return Ok(());
        }
        let found = store.rows(&bind(PLAN_FOR_Q, &[("want", Value::iri(want))])?, &[])?;
        let joint = match found.first() {
            Some(r) if iri(r, "outcome").as_deref() == Some(SATISFIED) => {
                chain(store, &iri(r, "plan").unwrap_or_default())?
            }
            _ => Vec::new(),
        };
        if joint.is_empty() {
            return Ok(());
        }
        let mut queues: BTreeMap<String, Vec<Said>> = BTreeMap::new();
        for walked in &reopened {
            let Some(walk) = walks.get(walked) else { continue };
            let steps = &walk.steps;
            let at = steps.iter().position(|(s, _)| *s == walk.head).unwrap_or(steps.len());
            let from = (at + usize::from(walk.in_flight)).min(steps.len());
            queues.insert(walked.clone(), steps[from..].iter().map(|(_, s)| s.clone()).collect());
        }
        let total: usize = queues.values().map(Vec::len).sum();
        let prefix = &joint[..total.min(joint.len())];
        let mut pending = queues.clone();
        let mut agrees = prefix.len() == total;
        for (_, said) in prefix {
            let owner = pending
                .iter()
                .find(|(_, q)| q.first() == Some(said))
                .map(|(w, _)| w.clone());
            match owner {
                Some(owner) => {
                    pending.get_mut(&owner).expect("an owner").remove(0);
                }
                None => {
                    agrees = false;
                    break;
                }
            }
        }
        if agrees && queues.contains_key(want) && joint.len() > prefix.len() {
            agrees = false;
        }
        if agrees {
            kept.insert(want.to_string(), prefix.iter().map(|(s, _)| s.clone()).collect());
            log::info!(
                "{}: {} agrees with what {} already walks — the intention stands, and {} new step(s) are adopted beside it",
                self.id,
                local_of(want),
                queues.keys().map(|w| local_of(w)).collect::<Vec<_>>().join(", "),
                joint.len() - prefix.len()
            );
            return Ok(());
        }
        for walked in queues.keys() {
            let walk = &walks[walked];
            log::info!(
                "{}: {} replaces the untaken steps of {} — it ends after {}",
                self.id,
                local_of(want),
                local_of(walked),
                local_of(&walk.head)
            );
            if self.watch.connected() {
                self.say(&crate::events::PlanSuperseded {
                    head: walk.head.clone(),
                    by: want.to_string(),
                    at: self.watch.at(),
                });
            }
        }
        Ok(())
    }
}
