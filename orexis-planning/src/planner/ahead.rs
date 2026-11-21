//! THE STEPS KEPT BELOW, AHEAD OF THEIR TURN: a step a bridge keeps below is given its want as soon as the plan below
//! the step before it is published, so the plan below it is found while the steps before are still walked. Such a
//! want begins where that plan ends: its graph holds from that instant, and a ground is laid there holding what the
//! plans below still change, which is the state its search starts from, as any want's is the ground at its instant.
//! Where each plan ends is computed off the plans and the intentions at every planning, never stored: a walk running
//! late moves every plan after it.

use std::collections::{BTreeMap, BTreeSet};

use oxigraph::model::Triple;
use oxsdatatypes::{DateTime, DayTimeDuration};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::isoformat;
use orexis::metadata::stated;
use orexis::ontology::BELIEF;
use orexis::store::{Store, iri};

use super::{Planner, Refined, chain, later, refined, zero};
use crate::admit::local_of;
use crate::lay_ground::Landed;
use crate::refine::refine;
use crate::withdraw::withdraw;
use crate::world_at::lexical;

/// A plan still to be walked: published and not adopted yet, or adopted by an intention that stands. Its steps in
/// the order walked, the one its intention stands at, and when that one was taken, where it is in flight.
pub(super) struct Live {
    plan: String,
    want: String,
    steps: Vec<String>,
    head: usize,
    adopted: bool,
    taken: Option<DateTime>,
}

/// What one step of a plan says of itself: the action it fills, when it is due and lands, whether a bridge keeps it
/// below, and its change.
struct Step {
    action: String,
    due: Option<DateTime>,
    lands: Option<DateTime>,
    kept: bool,
    adds: Vec<Triple>,
    retracts: Vec<Triple>,
}

/// What steps change, in the order walked: each one's action, what it adds and what it retracts.
type Changes = Vec<(String, Vec<Triple>, Vec<Triple>)>;

/// WHAT THE PLANS BELOW STILL CHANGE BEFORE A WANT BEGINS, and the instant it begins at: each step's action and
/// change, in the order walked, for the scope that lays it to take its own.
#[derive(Clone)]
pub(super) struct Ahead {
    at: DateTime,
    steps: Changes,
}

impl Ahead {
    /// What the steps `admits` come to together, as one change landing where the want begins; none where they
    /// change nothing.
    pub(super) fn landed(&self, admits: impl Fn(&str) -> bool) -> Option<Landed> {
        let (mut adds, mut retracts): (Vec<Triple>, Vec<Triple>) = (Vec::new(), Vec::new());
        for (action, added, retracted) in &self.steps {
            if !admits(action) {
                continue;
            }
            //  EACH STEP'S CHANGE APPLIED OVER THE ONES BEFORE: what it retracts of what they added is added no
            //  longer, and what it adds of what they retracted is put back.
            adds.retain(|t| !retracted.contains(t));
            for t in retracted {
                if !retracts.contains(t) {
                    retracts.push(t.clone());
                }
            }
            retracts.retain(|t| !added.contains(t));
            for t in added {
                if !adds.contains(t) {
                    adds.push(t.clone());
                }
            }
        }
        (!adds.is_empty() || !retracts.is_empty()).then_some(Landed {
            at: self.at,
            retracts,
            adds,
        })
    }
}

/// Every step of `plan`, by its name.
fn steps_of(beliefs: &Store, plan: &str) -> Result<BTreeMap<String, Step>, Error> {
    const STEPS_Q: &str = r#"PREFIX execution: <http://example.org/orexis/execution#>
    PREFIX planning: <http://example.org/orexis/planning#>
    SELECT ?step ?action ?due ?lands ?kept ?adds ?retracts WHERE { GRAPH $plan {
      ?step a execution:Step ; planning:fills ?action .
      OPTIONAL { ?step execution:notBefore ?due } OPTIONAL { ?step execution:landsAt ?lands }
      OPTIONAL { ?step execution:keptBelow ?kept }
      OPTIONAL { ?step execution:adds ?adds } OPTIONAL { ?step execution:retracts ?retracts } } }"#;
    let mut out = BTreeMap::new();
    for r in beliefs.rows(&bind(STEPS_Q, &[("plan", Value::iri(plan))])?, &[])? {
        let (Some(step), Some(action)) = (iri(&r, "step"), iri(&r, "action")) else {
            continue;
        };
        let triples = |graph: Option<String>| -> Result<Vec<Triple>, Error> {
            match graph {
                Some(g) => Ok(stated(beliefs.triples(&g)?)),
                None => Ok(Vec::new()),
            }
        };
        out.insert(
            step,
            Step {
                action,
                due: r.get("due").map(lexical).transpose()?,
                lands: r.get("lands").map(lexical).transpose()?,
                kept: r.contains_key("kept"),
                adds: triples(iri(&r, "adds"))?,
                retracts: triples(iri(&r, "retracts"))?,
            },
        );
    }
    Ok(out)
}

impl Planner {
    /// Every plan still to be walked, as the beliefs hold them.
    pub(super) fn live(&self) -> Result<Vec<Live>, Error> {
        const LIVE_Q: &str = r#"PREFIX execution: <http://example.org/orexis/execution#>
        PREFIX orexis: <http://example.org/orexis#>
        SELECT ?plan ?want ?head ?taken WHERE {
          GRAPH $cat { ?plan a orexis:PlanGraph } GRAPH ?plan { ?root execution:pursues ?want }
          OPTIONAL { GRAPH ?g { ?i a execution:Intention ; execution:adopts ?plan ; execution:by ?head .
                                FILTER NOT EXISTS { ?i execution:resolvedAt ?done }
                                OPTIONAL { ?act execution:of ?head ; execution:taken true ; execution:takenAt ?taken } } }
          FILTER(BOUND(?head) || NOT EXISTS { GRAPH ?h { ?x execution:adopts ?plan } }) }
        ORDER BY ?plan"#;
        let Some(catalogue) = self.beliefs.catalogue()? else {
            return Ok(Vec::new());
        };
        let mut out: Vec<Live> = Vec::new();
        for r in self
            .beliefs
            .rows(&bind(LIVE_Q, &[("cat", Value::Raw(format!("<{catalogue}>")))])?, &[])?
        {
            let (Some(plan), Some(want)) = (iri(&r, "plan"), iri(&r, "want")) else {
                continue;
            };
            if out.iter().any(|l| l.plan == plan) {
                continue;
            }
            let steps: Vec<String> = chain(&self.beliefs, &plan)?.into_iter().map(|(s, _)| s).collect();
            let head = iri(&r, "head");
            out.push(Live {
                head: head
                    .as_ref()
                    .and_then(|h| steps.iter().position(|s| s == h))
                    .unwrap_or(0),
                adopted: head.is_some(),
                taken: r.get("taken").map(lexical).transpose()?,
                plan,
                want,
                steps,
            });
        }
        Ok(out)
    }

    /// A want kept below for a step no plan still to be walked comes to any more is nothing's: withdrawn, here and
    /// everywhere.
    pub(super) fn withdraw_orphaned_refinements(&self, live: &[Live], walking: &BTreeSet<String>) -> Result<(), Error> {
        let ahead: BTreeSet<&String> = live.iter().flat_map(|l| l.steps.iter().skip(l.head)).collect();
        for Refined { want, graph: g, step } in refined(&self.beliefs)? {
            if ahead.contains(&step) || walking.contains(&want) {
                continue;
            }
            self.beliefs.forget_graph(&g, Some(BELIEF))?;
            let reached = BTreeSet::from([want.clone()]);
            for store in self.imaginaria.values() {
                withdraw(store, None, &reached, &BTreeSet::new())?;
            }
            log::info!(
                "{}: withdrew {}, since no plan comes to the step it kept",
                self.id,
                local_of(&want)
            );
        }
        Ok(())
    }

    /// Give each step kept below the want that keeps it, as far ahead as the plans below reach: the step an
    /// intention stands at once it is due, and each one after it once the plan below the one before is published.
    /// The want graphs minted, and where each want still to be planned begins.
    pub(super) fn keep_below(&self, live: &[Live], at: DateTime) -> Result<(Vec<String>, Vec<Ahead>), Error> {
        let beliefs = &self.beliefs;
        let below: BTreeMap<&str, &Live> = live.iter().map(|l| (l.want.as_str(), l)).collect();
        let (mut minted, mut ahead) = (Vec::new(), Vec::new());
        for upper in live {
            if !upper.adopted && !self.walked {
                continue;
            }
            let said = steps_of(beliefs, &upper.plan)?;
            if !upper.steps.iter().any(|s| said.get(s).is_some_and(|s| s.kept)) {
                continue;
            }
            let kept: BTreeMap<String, (String, String)> = refined(beliefs)?
                .into_iter()
                .map(|r| (r.step, (r.want, r.graph)))
                .collect();
            //  THE STEPS NOT YET ANSWERED BEFORE THE ONE LOOKED AT, where the plan below the last of them ends, and
            //  what the plans below still change on the way there.
            let mut before: Vec<String> = Vec::new();
            let mut begins: Option<DateTime> = None;
            let mut changes: Changes = Vec::new();
            for (i, step) in upper.steps.iter().enumerate().skip(upper.head) {
                let Some(this) = said.get(step) else { break };
                if !this.kept {
                    break;
                }
                let (want, graph) = match kept.get(step) {
                    Some(held) => held.clone(),
                    None => {
                        if i == upper.head && this.due.is_some_and(|due| due > at) {
                            break;
                        }
                        let Some(want) = refine(beliefs, &self.uri, step, &before, begins, at)? else {
                            break;
                        };
                        let Some(graph) = refined(beliefs)?.into_iter().find(|r| r.want == want).map(|r| r.graph)
                        else {
                            break;
                        };
                        minted.push(graph.clone());
                        (want, graph)
                    }
                };
                let Some(plan) = below.get(want.as_str()) else {
                    //  NOT PLANNED YET: it begins where the plans before it now end, and that is laid for its search.
                    self.begin(&graph, begins)?;
                    log::debug!(
                        "{}: {} begins {} after {} step(s) below",
                        self.id,
                        local_of(&want),
                        begins.map_or("in the present".to_string(), |b| format!("at {}", isoformat(b))),
                        changes.len()
                    );
                    if let Some(at) = begins
                        && !changes.is_empty()
                    {
                        ahead.push(Ahead { at, steps: changes });
                    }
                    break;
                };
                let (ends, changed) = self.span(plan, begins, at)?;
                changes.extend(changed);
                begins = Some(ends);
                before.push(step.clone());
            }
        }
        Ok((minted, ahead))
    }

    /// When the plan `below` ends, begun where the plan before it ends, and what its steps still to be answered
    /// change, in the order walked. A walk under way ends as late as it runs; one not begun, as long after it begins
    /// as it was planned to take; and neither sooner than a second from now, a plan unfinished being unfinished.
    fn span(&self, below: &Live, begins: Option<DateTime>, at: DateTime) -> Result<(DateTime, Changes), Error> {
        let mut said = steps_of(&self.beliefs, &below.plan)?;
        let first = below.steps.first().and_then(|s| said.get(s)).and_then(|s| s.due);
        let last = below.steps.last().and_then(|s| said.get(s)).and_then(|s| s.lands);
        let head = below
            .steps
            .get(below.head)
            .and_then(|s| said.get(s))
            .and_then(|s| s.due);
        let behind = |from: DateTime, due: Option<DateTime>| {
            due.and_then(|due| from.checked_sub(due))
                .filter(|late| *late > zero())
                .unwrap_or_else(zero)
        };
        let plus = |when: DateTime, by: DayTimeDuration| when.checked_add_day_time_duration(by).unwrap_or(when);
        let ends = if below.head > 0 || below.taken.is_some() {
            last.map(|last| plus(last, behind(below.taken.unwrap_or(at), head)))
        } else {
            let begun = later(begins.or(first).unwrap_or(at), at);
            match (first, last) {
                (Some(first), Some(last)) => Some(plus(begun, last.checked_sub(first).unwrap_or_else(zero))),
                _ => Some(begun),
            }
        };
        let ends = later(ends.unwrap_or(at), plus(at, DayTimeDuration::new(1)));
        let mut changed = Vec::new();
        for step in below.steps.iter().skip(below.head) {
            if let Some(Step {
                action, adds, retracts, ..
            }) = said.remove(step)
            {
                changed.push((action, adds, retracts));
            }
        }
        Ok((ends, changed))
    }

    /// Say that the want graph `graph` holds from `begins`, or from the first where it begins in the present: its
    /// period, on its row and in the graph itself, written again where it says another instant.
    fn begin(&self, graph: &str, begins: Option<DateTime>) -> Result<(), Error> {
        const BEGINS_Q: &str = r#"PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX orexis: <http://example.org/orexis#>
        SELECT ?start WHERE { GRAPH $cat { $graph dcterms:temporal/orexis:start ?start } }"#;
        /// THE PERIOD TAKEN BACK where `$in` says it: on the graph's row, and in the graph itself.
        const UNBEGIN_U: &str = r#"PREFIX dcterms: <http://purl.org/dc/terms/>
        DELETE { GRAPH $in { $graph dcterms:temporal ?period . ?period ?p ?o } }
        WHERE  { GRAPH $in { $graph dcterms:temporal ?period . ?period ?p ?o } }"#;
        let Some(catalogue) = self.beliefs.catalogue()? else {
            return Ok(());
        };
        let marks = [
            ("cat", Value::Raw(format!("<{catalogue}>"))),
            ("graph", Value::iri(graph)),
        ];
        let said = self
            .beliefs
            .rows(&bind(BEGINS_Q, &marks)?, &[])?
            .first()
            .and_then(|r| r.get("start"))
            .map(lexical)
            .transpose()?;
        if said == begins {
            return Ok(());
        }
        for said_in in [catalogue.as_str(), graph] {
            self.beliefs.update(&bind(
                UNBEGIN_U,
                &[("in", Value::iri(said_in)), ("graph", Value::iri(graph))],
            )?)?;
        }
        if let Some(begins) = begins {
            let begins = isoformat(begins);
            self.beliefs.update(&format!(
                "PREFIX dcterms: <http://purl.org/dc/terms/>
                 PREFIX orexis: <http://example.org/orexis#>
                 PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                 INSERT DATA {{ GRAPH <{catalogue}> {{ <{graph}> dcterms:temporal [ a dcterms:PeriodOfTime ; \
                 orexis:start \"{begins}\"^^xsd:dateTime ] }}
                 GRAPH <{graph}> {{ <{graph}> a orexis:Graph ; dcterms:temporal [ a dcterms:PeriodOfTime ; \
                 orexis:start \"{begins}\"^^xsd:dateTime ] }} }}"
            ))?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use oxigraph::model::{Literal, NamedNode};

    use super::*;

    fn fact(subject: &str, predicate: &str, value: &str) -> Triple {
        let node = |local: &str| NamedNode::new(format!("http://example.org/test#{local}")).unwrap();
        Triple::new(node(subject), node(predicate), Literal::new_simple_literal(value))
    }

    /// A van driven from cell 0 to 1 and on to 2, and a parcel picked at 0 and dropped at 2.
    fn walked() -> Ahead {
        Ahead {
            at: orexis::snapshots::now(),
            steps: vec![
                (
                    "pick".into(),
                    vec![fact("parcel", "carried", "yes")],
                    vec![fact("parcel", "x", "0")],
                ),
                ("drive".into(), vec![fact("van", "x", "1")], vec![fact("van", "x", "0")]),
                ("drive".into(), vec![fact("van", "x", "2")], vec![fact("van", "x", "1")]),
                (
                    "drop".into(),
                    vec![fact("parcel", "x", "2")],
                    vec![fact("parcel", "carried", "yes")],
                ),
            ],
        }
    }

    #[test]
    fn the_steps_before_a_want_begins_come_to_one_change_where_it_begins() {
        let landed = walked().landed(|_| true).expect("the steps change something");
        assert_eq!(landed.adds, [fact("van", "x", "2"), fact("parcel", "x", "2")]);
        assert!(
            !landed.adds.contains(&fact("van", "x", "1")) && !landed.adds.contains(&fact("parcel", "carried", "yes")),
            "what a later step retracts of an earlier one's is added no longer"
        );
        for gone in [fact("parcel", "x", "0"), fact("van", "x", "0")] {
            assert!(landed.retracts.contains(&gone), "{gone}");
        }
    }

    #[test]
    fn a_scope_lays_the_steps_of_its_own_actions_alone() {
        let landed = walked()
            .landed(|action| action == "drive")
            .expect("the drives change something");
        assert_eq!(landed.adds, [fact("van", "x", "2")]);
        assert!(
            walked().landed(|_| false).is_none(),
            "and a scope none of them is of lays no ground"
        );
    }
}
