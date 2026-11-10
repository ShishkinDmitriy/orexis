//! A WALKING WANT RECONSIDERED: where each standing intention stands, a world its untaken steps reach that a belief
//! makes impossible, a want a constraint couples to it, or a role above planning asking — and then its untaken steps
//! reopened.

use std::collections::{BTreeMap, BTreeSet};

use oxigraph::model::{GraphName, NamedNode, Quad};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::BELIEF;
use orexis::store::{Store, Within, instant, iri};

use super::{
    Flight, Flights, PREDICTS_Q, Planner, Reconsidered, Said, broken, graphs, later, quads_of, said, strs, zero,
};
use crate::admit::local_of;
use crate::memo::Memo;
use crate::ontology::{CONSTRAINT_GRAPH, GROUND_GRAPH, SATISFIED};
use crate::world_at::lexical;

const STANDS_AT_Q: &str = r#"
SELECT ?intention ?want ?plan ?step ?action ?due ?taken ?lands ?ending WHERE {
  GRAPH ?g { ?intention a execution:Intention ; execution:pursues ?want ; execution:by ?step ; execution:adopts ?plan .
             FILTER NOT EXISTS { ?intention execution:resolvedAt ?done }
             OPTIONAL { ?act execution:of ?step ; execution:taken true ; execution:takenAt ?taken }
             OPTIONAL { ?intention execution:endsAfter ?ending } }
  GRAPH ?plan { ?step planning:fills ?action .
                OPTIONAL { ?step execution:notBefore ?due } OPTIONAL { ?step execution:landsAt ?lands } } }
ORDER BY ?intention"#;

const REOPENS_Q: &str = r#"SELECT ?w WHERE { GRAPH ?g { $want planning:reopens ?w } } ORDER BY ?w"#;

const PLAN_FOR_Q: &str = r#"SELECT ?plan ?outcome WHERE { GRAPH ?plan { ?plan a planning:Plan ; planning:for $want ; planning:outcome ?outcome } } LIMIT 1"#;

const DERIVED_Q: &str = r#"
SELECT ?w WHERE { GRAPH ?g { ?w a planning:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }"#;

const FORESEEN_U: &str = r#"
INSERT { GRAPH ?cat { $world dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start $start ] } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"#;

const UNWEIGH_U: &str = r#"
DELETE { GRAPH ?cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      ?x planning:weighs $world ; ?p ?o .
                      OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"#;

const HOLDS_CONSTRAINT_Q: &str = r#"SELECT ?c WHERE { $holder planning:holds ?c . ?c a planning:Constraint } LIMIT 1"#;

impl<'a> Planner<'a> {
    /// Ask that each of `wants` an intention walks be searched again in the next pass.
    pub fn reopen(&mut self, wants: impl IntoIterator<Item = String>) {
        self.asked.extend(wants);
    }

    /// The asked wants a walking plan of this scope pursues, derived here and not ending; each taken from the asked.
    pub(super) fn asked_here(
        &mut self,
        store: &Store,
        flights: &Flights,
        only: Option<&BTreeSet<String>>,
    ) -> Result<BTreeSet<String>, Error> {
        if self.asked.is_empty() {
            return Ok(BTreeSet::new());
        }
        let derived: BTreeSet<String> = store.rows(DERIVED_Q, &[])?.iter().filter_map(|r| iri(r, "w")).collect();
        let out: BTreeSet<String> = self
            .asked
            .iter()
            .filter(|w| {
                flights
                    .get(*w)
                    .is_some_and(|f| !f.ending && only.is_none_or(|o| o.contains(&f.action)))
                    && derived.contains(*w)
            })
            .cloned()
            .collect();
        for want in &out {
            log::info!("{}: {} is reopened, as asked", self.id, local_of(want));
            self.asked.remove(want);
        }
        Ok(out)
    }

    /// Whether this agent holds any constraint — the one thing a walking want can be reopened by.
    pub(super) fn holds_a_constraint(&self) -> Result<bool, Error> {
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
    pub(super) fn flights(&self, at: DateTime) -> Result<Flights, Error> {
        let mut held: BTreeMap<String, Vec<(Flight, String)>> = BTreeMap::new();
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
            let flight = Flight {
                plan,
                head,
                action,
                in_flight: taken.is_some(),
                ending: r.contains_key("ending"),
                late,
                landing: later(landing, at),
                landings: Vec::new(),
                in_flight_steps: Vec::new(),
            };
            held.entry(want)
                .or_default()
                .push((flight, iri(&r, "intention").unwrap_or_default()));
        }
        let mut out = Flights::new();
        for (want, flights) in held {
            let mut flight = flights.iter().find(|(f, _)| !f.ending).unwrap_or(&flights[0]).0.clone();
            flight.landings = flights
                .iter()
                .filter(|(f, _)| f.in_flight)
                .map(|(f, _)| (f.action.clone(), f.landing))
                .collect();
            flight.in_flight_steps = flights
                .iter()
                .filter(|(f, _)| f.in_flight)
                .map(|(f, _)| (f.action.clone(), f.landing, f.plan.clone(), f.head.clone()))
                .collect();
            flight.landing = flights.iter().map(|(f, _)| f.landing).fold(at, later);
            out.insert(want, flight);
        }
        Ok(out)
    }

    /// The walking wants of this scope a world of whose plan is IMPOSSIBLE in the grounds as now laid (#921): the
    /// plan's untaken steps replayed on the new grounds, each world weighed for the constraints.
    pub(super) fn impossible_ahead(
        &mut self,
        store: &Store,
        flights: &Flights,
        constraints: &[String],
        only: Option<&BTreeSet<String>>,
        memo: &mut Memo,
    ) -> Result<BTreeSet<String>, Error> {
        let derived: BTreeSet<String> = store.rows(DERIVED_Q, &[])?.iter().filter_map(|r| iri(r, "w")).collect();
        let mut out = BTreeSet::new();
        for (want, flight) in flights {
            if flight.ending || !derived.contains(want) || only.is_some_and(|o| !o.contains(&flight.action)) {
                continue;
            }
            let chain: Vec<String> = self
                .chain(&self.beliefs, &flight.plan)?
                .into_iter()
                .map(|(s, _)| s)
                .collect();
            let from = chain.iter().position(|s| *s == flight.head).unwrap_or(chain.len());
            let untaken = &chain[from..];
            if untaken.is_empty() || (untaken.len() == 1 && flight.in_flight) {
                continue;
            }
            let predicts: BTreeMap<String, orexis::store::Row> = self
                .beliefs
                .rows(&bind(PREDICTS_Q, &[("plan", Value::iri(flight.plan.as_str()))])?, &[])?
                .into_iter()
                .filter_map(|r| Some((iri(&r, "step")?, r)))
                .collect();
            let mut foreseen: Vec<String> = Vec::new();
            let found = (|| -> Result<Option<bool>, Error> {
                let mut changes: Vec<(Vec<Quad>, Vec<Quad>)> = Vec::new();
                let (mut before, mut world): (Option<String>, Option<String>) = (None, None);
                for step in untaken {
                    let row = predicts.get(step);
                    let lands = match row.and_then(|r| r.get("lands")) {
                        Some(l) => lexical(l)?
                            .checked_add_day_time_duration(flight.late)
                            .unwrap_or(flight.landing),
                        None => flight.landing,
                    };
                    let lands = later(lands, flight.landing);
                    let Some(ground) = store.graphs_of(&[GROUND_GRAPH], &Within::at(lands))?.into_iter().next() else {
                        return Ok(None);
                    };
                    let change = (
                        quads_of(&self.beliefs, row.and_then(|r| iri(r, "retracts")))?,
                        quads_of(&self.beliefs, row.and_then(|r| iri(r, "adds")))?,
                    );
                    changes.push(change.clone());
                    let (base, applying) = match (&before, &world) {
                        (Some(b), Some(w)) if *b == ground => (w.clone(), vec![change]),
                        _ => (ground.clone(), changes.clone()),
                    };
                    let next = format!("{step}.foreseen");
                    foreseen.push(next.clone());
                    store.copy_graph(&base, &next)?;
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
                        &[("world", Value::iri(next.as_str())), ("start", instant(lands))],
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
                            self.doomed.insert(want.clone(), step.clone());
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
                    self.doomed.remove(want);
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
        &mut self,
        store: &Store,
        want: &str,
        flights: &Flights,
        kept: &mut BTreeMap<String, Vec<String>>,
    ) -> Result<(), Error> {
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
                self.chain(store, &iri(r, "plan").unwrap_or_default())?
            }
            _ => Vec::new(),
        };
        if joint.is_empty() {
            return Ok(());
        }
        let mut queues: BTreeMap<String, Vec<Said>> = BTreeMap::new();
        for walked in &reopened {
            let Some(flight) = flights.get(walked) else { continue };
            let steps = self.chain(&self.beliefs, &flight.plan)?;
            let at = steps.iter().position(|(s, _)| *s == flight.head).unwrap_or(steps.len());
            let from = (at + usize::from(flight.in_flight)).min(steps.len());
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
            let flight = &flights[walked];
            log::info!(
                "{}: {} replaces the untaken steps of {} — it ends after {}",
                self.id,
                local_of(want),
                local_of(walked),
                local_of(&flight.head)
            );
            self.superseded.push(Reconsidered {
                head: flight.head.clone(),
                walked: walked.clone(),
                by: want.to_string(),
            });
            if self.watch.connected() {
                self.watch.emit(&crate::events::PlanSuperseded {
                    head: flight.head.clone(),
                    by: want.to_string(),
                    at: self.watch.at(),
                });
            }
        }
        Ok(())
    }
}
