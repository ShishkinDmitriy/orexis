//! THE EXECUTOR, as `agent/execution/executor.py` keeps it: the intentions this agent is committed to, which it owns
//! and alone writes — rows of a graph of the belief base, `execution:IntentionGraph`, so a lived-in volume finds them.
//! A plan planning published is adopted BY REFERENCE, an intention that `execution:adopts` it and holds its own rows,
//! and every act here is a read of those rows and a write of a few more.
//!
//! TWO DOORS: `tick` hands the heads due to the queue and holds every head taken to what it predicted; `drain` takes
//! what is queued. The Python copy's two threads called the same two; here the runtime's pass does, by `walk`.
//!
//! A STEP TAKEN WAITS FOR THE WORLD: one predicting something stays the head until the present holds every fact its
//! `execution:adds` names and none of those its `execution:retracts` names, from its `landsAt` on, and fails a
//! patience past its `notAfter`; one predicting nothing moves at once. A FICTIVE step's taking writes its own
//! prediction into the beliefs. A COMMITTED STEP is a belief over its landing window (#849), closed when the world
//! answers it or its intention ends, and swept when its window has ended. A STEP IN FLIGHT IS NEVER CANCELLED
//! (#905): planning ends an intention by `end_for`, `end_at` and `supersede_after`, and the plan that replaced one
//! waits for it. EVERY HEAD IS CHECKED WHEN IT IS TAKEN, and not here (#916): where the executor `asks`, a head due is
//! said `execution:HeadAsked` and stays in flight until `judged` hears the answer, and a head blocked ends its intention
//! `failed` and is not taken.
//!
//! WHAT IT SAYS HAPPENED goes to whoever watches the agent (`events`), made only where somebody does: a step taken,
//! a step answered, an intention resolved, and how many stand after a walk.
//!
//! NOT PORTED: the threads. Every graph written as the world is kept in `written`, which the part hands the runtime as
//! what its job wrote, so belief hears it by kind; that an intention was resolved, off `resolved`.

use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::sync::Arc;

use oxigraph::model::vocab::{rdf, xsd};
use oxigraph::model::{GraphName, Literal, NamedNode, NamedOrBlankNode, Quad, Term, Triple};
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::{Clock, instant as parse_instant, isoformat, seconds, seconds_of};
use orexis::events::{Event, Watch};
use orexis::hash::hash_named_graph;
use orexis::ontology::{BELIEF, DERIVED, OREXIS, RECORDED, local_of};
use orexis::stance::stance;
use orexis::store::{Row, Store, Within, instant, iri, value};

use crate::events::{About, HeadAsked, IntentionAdopted, IntentionResolved, StepAnswered, StepTaken, Walked};
use crate::implementation::operations;
use crate::ontology::{
    ADDS_GRAPH, ANSWERED_WITHIN_S, COMMITTED_STEP_GRAPH, EXECUTION, FICTIVE, INTENTION, INTENTION_GRAPH,
    LANDS_WITHIN_S, PATIENCE_S, RETRACTS_GRAPH, STEP_CLASS, committed_graph, fictive_graph, intentions_graph,
};

/// The patience, in seconds, where the agent's self graph states no `execution:patienceS`.
pub const DEFAULT_PATIENCE_S: f64 = 60.0;

const ADOPTS: &str = "http://example.org/orexis/execution#adopts";
const BY: &str = "http://example.org/orexis/execution#by";
const STEP: &str = "http://example.org/orexis/execution#step";
const PURSUES: &str = "http://example.org/orexis/execution#pursues";
const ADOPTED_AT: &str = "http://example.org/orexis/execution#adoptedAt";
const ENDS_AFTER: &str = "http://example.org/orexis/execution#endsAfter";
const WAITS_FOR: &str = "http://example.org/orexis/execution#waitsFor";

const HEAD_Q: &str = "
SELECT ?step WHERE {
  GRAPH $plan {
    ?step a execution:Step ; execution:partOf $root .
    FILTER NOT EXISTS { ?other execution:then ?step } } }";

const STEPS_Q: &str = "
SELECT ?step WHERE { GRAPH $plan { ?step a execution:Step ; execution:partOf $root } }";

const WALKING_Q: &str = "
SELECT DISTINCT ?want WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:pursues ?want .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }
ORDER BY ?want";

const STANDING_Q: &str = "
SELECT ?intention ?want ?at ?adopted WHERE {
  GRAPH $intentions {
    ?intention a execution:Intention ;
               execution:pursues ?want ;
               execution:adoptedAt ?adopted .
    OPTIONAL { ?intention execution:by ?at }
    FILTER NOT EXISTS { ?intention execution:resolvedAt ?done } } }
ORDER BY ?adopted";

const HEADS_Q: &str = "
SELECT ?intention ?step ?due ?kept ?act ?taken ?lands ?after ?adds ?retracts WHERE {
  GRAPH $intentions {
    ?intention a execution:Intention ; execution:by ?step ; execution:adopts ?plan .
    FILTER NOT EXISTS { ?intention execution:resolvedAt ?done }
    OPTIONAL { ?act execution:of ?step ; execution:taken true ; execution:takenAt ?taken } }
  OPTIONAL { GRAPH ?plan { ?step execution:notBefore ?due } }
  OPTIONAL { GRAPH ?plan { ?step execution:keptBelow ?kept } }
  OPTIONAL { GRAPH ?plan { ?step execution:landsAt ?lands } }
  OPTIONAL { GRAPH ?plan { ?step execution:notAfter ?after } }
  OPTIONAL { GRAPH ?plan { ?step execution:adds ?adds } }
  OPTIONAL { GRAPH ?plan { ?step execution:retracts ?retracts } } }
ORDER BY ?due ?intention";

const PREDICTED_Q: &str = "
SELECT ?adds ?retracts WHERE {
  OPTIONAL { GRAPH ?a { $step execution:adds ?adds } }
  OPTIONAL { GRAPH ?r { $step execution:retracts ?retracts } } } LIMIT 1";

const STEP_GRAPHS_Q: &str =
    "SELECT ?g ?side WHERE { GRAPH $plan { ?step ?side ?g . VALUES ?side { execution:adds execution:retracts } } }";

const ADDS_MISSING: &str = "{ GRAPH $adds { ?s ?p ?o } FILTER NOT EXISTS { ?s ?p ?x . FILTER(?x = ?o) } }";
const RETRACTS_STANDING: &str = "{ GRAPH $retracts { ?s ?p ?o } ?s ?p ?x . FILTER(?x = ?o) }";

const RETRACT_U: &str =
    "DELETE { GRAPH ?g { ?s ?p ?o } } WHERE { GRAPH $retracts { ?s ?p ?o } GRAPH ?g { ?s ?p ?o } VALUES ?g { $held } }";
const ADD_U: &str = "INSERT { GRAPH $into { ?s ?p ?o } } WHERE { GRAPH $adds { ?s ?p ?o } }";

const HELD_Q: &str = "
SELECT DISTINCT ?g WHERE {
  GRAPH $retracts { ?s ?p ?o }
  GRAPH $cat { ?g a orexis:BeliefGraph .
               ?g orexis:ownedBy ?owner .
               FILTER NOT EXISTS { ?g a belief:RevisionGraph }
               FILTER NOT EXISTS { ?g a execution:CommittedStepGraph } }
  GRAPH ?g { ?s ?p ?o } } ORDER BY ?g";

const CLASSIFIED_Q: &str = "SELECT ?k WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $graph a ?k } } LIMIT 1";
const PLANS_Q: &str = "
SELECT ?plan ?want WHERE { GRAPH $cat { ?plan a orexis:PlanGraph } GRAPH ?plan { ?plan execution:pursues ?want }
  FILTER NOT EXISTS { GRAPH ?g { ?i execution:adopts ?plan } } }
ORDER BY ?plan";

const BEGUN_Q: &str = "SELECT DISTINCT ?intention WHERE { GRAPH $intentions {
  ?intention a execution:Intention ; execution:step ?step . ?act execution:of ?step } }";

const KEPT_BY_Q: &str = "SELECT ?want WHERE { GRAPH ?g { $step execution:keptBy ?want } } LIMIT 1";
const ME_Q: &str = "SELECT ?me WHERE { ?me a orexis:Agent ; orexis:localId $id } LIMIT 1";

const REFINED_Q: &str = "
SELECT ?outcome WHERE { GRAPH $intentions { $act execution:refinedBy ?want .
  ?below a execution:Intention ; execution:pursues ?want .
  OPTIONAL { ?below execution:outcome ?outcome } } }";

const BELOW_Q: &str = "
SELECT DISTINCT ?below WHERE { GRAPH $intentions {
  $intention execution:step ?step . ?act execution:of ?step ; execution:refinedBy ?want .
  ?below a execution:Intention ; execution:pursues ?want .
  FILTER NOT EXISTS { ?below execution:resolvedAt ?at } } }";

/// THE WANT AN INTENTION PURSUES, and THE LATEST ACT RECORDED OF A STEP: what an event about a step carries.
const PURSUED_Q: &str = "SELECT ?want WHERE { GRAPH $intentions { $intention execution:pursues ?want } }";
const LAST_ACT_Q: &str = "
SELECT ?act WHERE { GRAPH $intentions { ?act a execution:Act ; execution:of $step ; execution:takenAt ?t } }
ORDER BY DESC(?t) LIMIT 1";

const STEP_Q: &str = "
SELECT ?p ?o WHERE {
  GRAPH ?plan { $step ?p ?o . FILTER(!STRSTARTS(STR(?p), STR(execution:)) && ?p != rdf:type) } }
ORDER BY ?p";

const NEXT_Q: &str = "SELECT ?next WHERE { GRAPH ?plan { $step execution:then ?next } } LIMIT 1";

const PLACED_Q: &str = "
SELECT ?opens ?lands ?after WHERE { GRAPH $plan {
  OPTIONAL { $step execution:notBefore ?opens } OPTIONAL { $step execution:landsAt ?lands }
  OPTIONAL { $step execution:notAfter ?after } } }";

const COMMITTED_Q: &str = "SELECT ?step WHERE { GRAPH $intentions { $intention execution:step ?step } }";

const IN_FLIGHT_Q: &str =
    "SELECT ?act WHERE { GRAPH $intentions { ?act execution:of $step ; execution:taken true } } LIMIT 1";

const RESOLVED_Q: &str = "SELECT ?at WHERE { GRAPH $intentions { $intention execution:resolvedAt ?at } } LIMIT 1";

const WAITS_Q: &str = "SELECT ?for WHERE { GRAPH $intentions { $intention execution:waitsFor ?for .
  FILTER NOT EXISTS { ?for execution:resolvedAt ?done } } } LIMIT 1";

const ENDS_AFTER_Q: &str =
    "SELECT ?i WHERE { GRAPH $intentions { $intention execution:endsAfter $step . BIND($intention AS ?i) } } LIMIT 1";
const ENDING_Q: &str = "SELECT ?step WHERE { GRAPH $intentions { $intention execution:endsAfter ?step } } LIMIT 1";

const WINDOW_Q: &str =
    "SELECT ?end WHERE { GRAPH $cat { $g a $kind ; dcterms:temporal ?p . OPTIONAL { ?p orexis:end ?end } } }";

const CLOSE_U: &str = "
DELETE { GRAPH $cat { ?p orexis:end ?old } }
INSERT { GRAPH $cat { ?p orexis:end $now } }
WHERE  { GRAPH $cat { $g dcterms:temporal ?p . OPTIONAL { ?p orexis:end ?old } } }";

const ENDED_Q: &str = "
SELECT ?g WHERE { GRAPH $cat { ?g a $kind $owned ; dcterms:temporal ?p . ?p orexis:end ?end . FILTER(?end <= $now) } }
ORDER BY ?g";

const ACT_U: &str = "
INSERT DATA { GRAPH $intentions { $act a execution:Act ; execution:of $step ;
                              execution:takenAt $taken_at ; execution:doneAt $done_at ;
                              execution:taken $taken } }";

const ADVANCE_U: &str = "
DELETE { GRAPH $intentions { $intention execution:by $step } }
INSERT { GRAPH $intentions { $intention execution:by $next } }
WHERE  { GRAPH $intentions { $intention execution:by $step } }";

/// What a step says of itself in words other than this layer's, keyed by the local part of each predicate, with
/// the step's own IRI under `step` — what a taker is handed.
pub type Said = BTreeMap<String, String>;

/// A taker: handed the step's rows and its intention, refusing where the step could not be taken, and answering what
/// it kept where anything reached the world — where nothing did, `None`, and the step is said in the log as the
/// executor alone says it.
pub type Take = Box<dyn FnMut(&Said, &str) -> Result<Option<Vec<String>>, Error> + Send>;

/// One commitment not resolved: what it pursues, where it has got to, and when it was adopted.
#[derive(Clone, Debug, PartialEq)]
pub struct Standing {
    pub uri: String,
    pub want: String,
    pub at: Option<String>,
    pub adopted: DateTime,
}

/// One agent's intentions, and what carries them out.
pub struct Executor {
    pub beliefs: Store,
    pub intentions: Store,
    pub id: String,
    pub holder: Option<String>,
    pub graph: String,
    /// How long a standing commitment absorbs another for its want, and how long past its latest landing a step may
    /// go unanswered: the agent's stance, the default where it states none.
    pub patience_s: f64,
    /// Every step taken by writing its own prediction, the shorthand for a pure simulation.
    pub all_fictive: bool,
    /// The taker, the seam to real code; none says the step in the log.
    pub take: Option<Take>,
    /// Whether a head about to be taken is ASKED first: said `execution:HeadAsked`, and taken or failed when the answer
    /// is heard (`judged`). Not asked, and every head is taken as it is due.
    pub asks: bool,
    /// The heads asked and not yet answered, each with its intention.
    asked: BTreeMap<String, String>,
    /// The graphs written as the world, in the order written, for the part to hand the runtime.
    pub written: Vec<String>,
    /// How many intentions were resolved, for the caller to ask for another pass.
    pub resolved: usize,
    /// When the next thing not yet due is, as the last tick found it.
    pub next_due: Option<DateTime>,
    /// Whether the last tick answered or failed a step taken, which moves an intention on with nothing handed over.
    moved: bool,
    /// Whoever watches the agent.
    pub watch: Watch,
    /// The desire each want adopted was derived under, as planning said it published the plan.
    pub desires: BTreeMap<String, String>,
    pub clock: Arc<dyn Clock>,
    replaced: BTreeMap<String, Vec<String>>,
    work: VecDeque<(String, String)>,
    inflight: BTreeSet<String>,
}

fn strs(names: &[String]) -> Vec<&str> {
    names.iter().map(String::as_str).collect()
}

fn later(a: DateTime, b: DateTime) -> DateTime {
    if b > a { b } else { a }
}

fn plus(at: DateTime, s: f64) -> Result<DateTime, Error> {
    if s < 0.0 {
        return at
            .checked_sub_day_time_duration(seconds(-s))
            .ok_or_else(|| Error::Evaluation(format!("{at} less {s}s")));
    }
    at.checked_add_day_time_duration(seconds(s))
        .ok_or_else(|| Error::Evaluation(format!("{at} plus {s}s")))
}

fn between(from: DateTime, to: DateTime) -> f64 {
    to.checked_sub(from).map_or(0.0, seconds_of)
}

fn at_of(row: &Row, variable: &str) -> Result<Option<DateTime>, Error> {
    value(row, variable).map(|v| parse_instant(&v)).transpose()
}

/// A stretch in seconds as the decimal a rule divides by.
fn decimal(s: f64) -> Term {
    let text = format!("{s:.3}");
    let text = text.trim_end_matches('0').trim_end_matches('.');
    let text = if text.is_empty() || text == "-" { "0" } else { text };
    Literal::new_typed_literal(text, xsd::DECIMAL).into()
}

/// An instant as Python's `strftime('%Y%m%dT%H%M%S%f')` spells it, which an act is named by.
fn stamp(at: DateTime) -> String {
    let iso = isoformat(at);
    let (date, time) = iso.split_once('T').unwrap_or((&iso, ""));
    let time = time.split(['+', 'Z']).next().unwrap_or(time);
    let time = match time.rfind('-') {
        Some(i) if i > 5 => &time[..i],
        _ => time,
    };
    let (whole, fraction) = time.split_once('.').unwrap_or((time, ""));
    format!("{}T{}{fraction:0<6}", date.replace('-', ""), whole.replace(':', ""))
}

fn short(iri: &str) -> &str {
    iri.rsplit('#').next().unwrap_or(iri)
}

fn named(iri: &str) -> Result<NamedNode, Error> {
    NamedNode::new(iri).map_err(|e| Error::Evaluation(e.to_string()))
}

impl Executor {
    /// The executor of `agent` over `beliefs`, its intentions a graph of the belief base unless `intentions` is
    /// another store, as a case may hand; `holder` the agent whose graphs they are, where the caller knows it.
    pub fn new(
        beliefs: &Store,
        agent: &str,
        intentions: Option<&Store>,
        holder: Option<&str>,
        clock: Arc<dyn Clock>,
    ) -> Result<Self, Error> {
        Ok(Executor {
            beliefs: beliefs.clone(),
            intentions: intentions.unwrap_or(beliefs).clone(),
            id: agent.to_string(),
            holder: holder.map(str::to_string),
            graph: intentions_graph(agent),
            patience_s: stance(beliefs, PATIENCE_S)?.unwrap_or(DEFAULT_PATIENCE_S),
            all_fictive: false,
            take: None,
            asks: false,
            asked: BTreeMap::new(),
            written: Vec::new(),
            resolved: 0,
            next_due: None,
            moved: false,
            watch: Watch::default(),
            desires: BTreeMap::new(),
            clock,
            replaced: BTreeMap::new(),
            work: VecDeque::new(),
            inflight: BTreeSet::new(),
        })
    }

    fn mine(&self) -> Value {
        Value::iri(self.graph.clone())
    }

    fn rows_of(&self, text: &str, values: &[(&str, Value)]) -> Result<Vec<Row>, Error> {
        self.intentions.rows(&bind(text, values)?, &[])
    }

    fn catalogue(&self) -> Result<Option<String>, Error> {
        self.beliefs.catalogue()
    }

    /// The agent the belief base holds with the id the executor was told, off what the world states.
    fn me(&self) -> Result<Option<String>, Error> {
        let common = self.beliefs.graphs_of(&[BELIEF], &Within::common())?;
        let text = bind(
            ME_Q,
            &[("id", Value::Term(Literal::new_simple_literal(&self.id).into()))],
        )?;
        Ok(self
            .beliefs
            .rows(&text, &strs(&common))?
            .first()
            .and_then(|r| iri(r, "me")))
    }

    fn owner(&self) -> Result<Option<String>, Error> {
        match &self.holder {
            Some(h) => Ok(Some(h.clone())),
            None => self.me(),
        }
    }

    // --- committing -------------------------------------------------------------------------------------------

    /// Adopt every plan published and adopted by no intention yet, as a caller with no planning part linked would.
    /// The intentions graph where anything was committed.
    pub fn commit_plans(&mut self) -> Result<Vec<String>, Error> {
        let Some(cat) = self.catalogue()? else {
            return Ok(Vec::new());
        };
        let plans = self.beliefs.rows(&bind(PLANS_Q, &[("cat", Value::iri(cat))])?, &[])?;
        let mut committed = false;
        for r in plans {
            if let (Some(plan), Some(want)) = (iri(&r, "plan"), iri(&r, "want")) {
                committed = self.commit(None, &plan, &want)?.is_some() || committed;
            }
        }
        Ok(if committed {
            vec![self.graph.clone()]
        } else {
            Vec::new()
        })
    }

    /// Adopt the plan `plan` published for `want`. The intentions graph where anything was committed.
    pub fn adopt(&mut self, plan: &str, want: &str) -> Result<Vec<String>, Error> {
        Ok(if self.commit(None, plan, want)?.is_some() {
            vec![self.graph.clone()]
        } else {
            Vec::new()
        })
    }

    /// End every standing intention pursuing `want` that has taken no step yet, with `outcome`.
    pub fn end_for(&mut self, want: &str, outcome: &str) -> Result<Vec<String>, Error> {
        let begun: BTreeSet<String> = self
            .rows_of(BEGUN_Q, &[("intentions", self.mine())])?
            .iter()
            .filter_map(|r| iri(r, "intention"))
            .collect();
        let ended: Vec<String> = self
            .standing()?
            .into_iter()
            .filter(|s| s.want == want && !begun.contains(&s.uri))
            .map(|s| s.uri)
            .collect();
        for intention in &ended {
            self.resolve(intention, outcome)?;
        }
        Ok(if ended.is_empty() {
            Vec::new()
        } else {
            vec![self.graph.clone()]
        })
    }

    /// End the standing intention that stands at `step`, with `outcome`.
    pub fn end_at(&mut self, step: &str, outcome: &str) -> Result<Vec<String>, Error> {
        let ended: Vec<String> = self
            .standing()?
            .into_iter()
            .filter(|s| s.at.as_deref() == Some(step))
            .map(|s| s.uri)
            .collect();
        for intention in &ended {
            self.resolve(intention, outcome)?;
        }
        Ok(if ended.is_empty() {
            Vec::new()
        } else {
            vec![self.graph.clone()]
        })
    }

    /// End the standing intention that stands at `step` AFTER it, `superseded`: the plan for `by` replaces its untaken
    /// steps, and waits for it when adopted. A step in flight is never cancelled; one untaken resolves at once.
    pub fn supersede_after(&mut self, step: &str, by: Option<&str>) -> Result<Vec<String>, Error> {
        for held in self.standing()? {
            if held.at.as_deref() != Some(step) {
                continue;
            }
            let taken = self.rows_of(IN_FLIGHT_Q, &[("intentions", self.mine()), ("step", Value::iri(step))])?;
            if taken.is_empty() {
                self.resolve(&held.uri, "superseded")?;
                continue;
            }
            self.intentions.update(&format!(
                "INSERT DATA {{ GRAPH <{}> {{ <{}> <{ENDS_AFTER}> <{step}> }} }}",
                self.graph, held.uri
            ))?;
            if let Some(by) = by {
                self.replaced.entry(by.to_string()).or_default().push(held.uri.clone());
            }
            let now = self.clock.now();
            let committed = self.rows_of(
                COMMITTED_Q,
                &[("intentions", self.mine()), ("intention", Value::iri(held.uri.clone()))],
            )?;
            for r in committed {
                let Some(other) = iri(&r, "step") else { continue };
                if other != step
                    && self
                        .rows_of(
                            IN_FLIGHT_Q,
                            &[("intentions", self.mine()), ("step", Value::iri(other.clone()))],
                        )?
                        .is_empty()
                {
                    self.close_window(&other, now)?;
                }
            }
            log::info!(
                "{}: {} ends after {}, its untaken steps replaced",
                self.id,
                short(&held.uri),
                local_of(step)
            );
        }
        Ok(vec![self.graph.clone()])
    }

    /// Adopt the plan in `graph`, found in `source` or published in the beliefs, unless one for `want` stands younger
    /// than the patience. The intention, or None: nothing was committed.
    pub fn commit(&mut self, source: Option<&Store>, graph: &str, want: &str) -> Result<Option<String>, Error> {
        if let Some(held) = self.standing_for(want)? {
            let age = between(held.adopted, self.clock.now());
            if age < self.patience_s {
                log::debug!(
                    "{}: absorbed a second plan for {} — {} stands, {age:.0}s of {:.0}s",
                    self.id,
                    short(want),
                    short(&held.uri),
                    self.patience_s
                );
                return Ok(None);
            }
            self.resolve(&held.uri, "superseded")?;
        }
        let intention = self.adopt_plan(source, graph, want)?;
        let replaced = self.replaced.remove(want).unwrap_or_default();
        if let Some(intention) = &intention {
            let mut waits = Vec::new();
            for ended in replaced {
                let resolved = self.rows_of(
                    RESOLVED_Q,
                    &[("intentions", self.mine()), ("intention", Value::iri(ended.clone()))],
                )?;
                if resolved.is_empty() {
                    waits.push(format!("<{intention}> <{WAITS_FOR}> <{ended}> ."));
                }
            }
            if !waits.is_empty() {
                self.intentions.update(&format!(
                    "INSERT DATA {{ GRAPH <{}> {{ {} }} }}",
                    self.graph,
                    waits.join(" ")
                ))?;
            }
            if self.watch.connected() {
                self.watch.emit(&IntentionAdopted {
                    intention: intention.clone(),
                    at: Some(self.clock.now()),
                    said: self.described(&[intention]),
                });
            }
        }
        Ok(intention)
    }

    fn adopt_plan(&mut self, source: Option<&Store>, graph: &str, want: &str) -> Result<Option<String>, Error> {
        let from = source.unwrap_or(&self.beliefs);
        let plan = Value::iri(graph);
        let mut steps: Vec<String> = from
            .rows(&bind(STEPS_Q, &[("plan", plan.clone()), ("root", plan.clone())])?, &[])?
            .iter()
            .filter_map(|r| iri(r, "step"))
            .collect();
        if steps.is_empty() {
            log::debug!("{}: the plan for {want} has no steps — nothing to commit", self.id);
            return Ok(None);
        }
        let head: Vec<String> = from
            .rows(&bind(HEAD_Q, &[("plan", plan.clone()), ("root", plan.clone())])?, &[])?
            .iter()
            .filter_map(|r| iri(r, "step"))
            .collect();
        if head.len() != 1 {
            return Err(Error::Evaluation(format!(
                "the plan in <{graph}> has {} heads — a plan is a chain, and a chain has one step nothing follows",
                head.len()
            )));
        }
        if !std::ptr::eq(from, &self.intentions) {
            let name = GraphName::NamedNode(named(graph)?);
            let quads: Vec<Quad> = from
                .quads(graph)?
                .into_iter()
                .map(|q| Quad::new(q.subject, q.predicate, q.object, name.clone()))
                .collect();
            self.intentions.add(quads)?;
        }
        if !std::ptr::eq(from, &self.beliefs) {
            let described = self.catalogue()?.is_some();
            let owner = if described { self.owner()? } else { None };
            for g in from.rows(&bind(STEP_GRAPHS_Q, &[("plan", plan.clone())])?, &[])? {
                let (Some(side_graph), Some(side)) = (iri(&g, "g"), iri(&g, "side")) else {
                    continue;
                };
                let into = GraphName::NamedNode(named(&side_graph)?);
                let quads: Vec<Quad> = from
                    .quads(&side_graph)?
                    .into_iter()
                    .map(|q| Quad::new(q.subject, q.predicate, q.object, into.clone()))
                    .collect();
                self.beliefs.add(quads)?;
                if described {
                    let kind = if side.ends_with("adds") {
                        ADDS_GRAPH
                    } else {
                        RETRACTS_GRAPH
                    };
                    let entry = self
                        .beliefs
                        .entry(&side_graph, &[kind], RECORDED, owner.as_deref(), None, None)?;
                    self.beliefs.update(&format!("INSERT DATA {{ {entry} }}"))?;
                }
            }
        }
        if self.intentions.catalogue()?.is_some()
            && self
                .intentions
                .rows(&bind(CLASSIFIED_Q, &[("graph", self.mine())])?, &[])?
                .is_empty()
        {
            let owner = self.owner()?;
            let entry =
                self.intentions
                    .entry(&self.graph, &[INTENTION_GRAPH], RECORDED, owner.as_deref(), None, None)?;
            self.intentions.update(&format!("INSERT DATA {{ {entry} }}"))?;
        }
        let mut random = [0u8; 4];
        getrandom::fill(&mut random).map_err(|e| Error::Evaluation(e.to_string()))?;
        let hex: String = random.iter().map(|b| format!("{b:02x}")).collect();
        let intention = named(&format!("{OREXIS}intention_{}_{hex}", self.id))?;
        let node = GraphName::NamedNode(named(&self.graph)?);
        let now = self.clock.now();
        let Value::Term(adopted) = instant(now) else {
            unreachable!("an instant is a term")
        };
        let subject = NamedOrBlankNode::from(intention.clone());
        let quad =
            |p: &str, o: Term| -> Result<Quad, Error> { Ok(Quad::new(subject.clone(), named(p)?, o, node.clone())) };
        let mut own = vec![
            Quad::new(subject.clone(), rdf::TYPE, named(INTENTION)?, node.clone()),
            quad(PURSUES, named(want)?.into())?,
            quad(ADOPTED_AT, adopted)?,
            quad(ADOPTS, named(graph)?.into())?,
            quad(BY, named(&head[0])?.into())?,
        ];
        steps.sort();
        for s in &steps {
            own.push(quad(STEP, named(s)?.into())?);
        }
        self.intentions.add(own)?;
        log::info!(
            "{}: committed a plan of {} step(s) for {}",
            self.id,
            steps.len(),
            short(want)
        );
        self.commit_windows(graph, &steps, now)?;
        Ok(Some(intention.into_string()))
    }

    // --- the committed steps, as beliefs over their landing windows -------------------------------------------

    fn commit_windows(&mut self, plan: &str, steps: &[String], now: DateTime) -> Result<(), Error> {
        if self.catalogue()?.is_none() {
            return Ok(());
        }
        let owner = self.owner()?;
        for step in steps {
            let placed = self
                .rows_of(
                    PLACED_Q,
                    &[("plan", Value::iri(plan)), ("step", Value::iri(step.clone()))],
                )?
                .into_iter()
                .next()
                .unwrap_or_default();
            let opens = at_of(&placed, "opens")?.unwrap_or(now);
            let lands = at_of(&placed, "lands")?.map_or(opens, |l| later(opens, l));
            let latest = at_of(&placed, "after")?.map_or(lands, |a| later(lands, a));
            let within = between(opens, lands);
            let by = between(opens, latest) + self.patience_s;
            let graph = committed_graph(&self.id, step);
            self.beliefs.forget_graph(&graph, Some(BELIEF))?;
            let end = plus(latest, self.patience_s)?;
            let entry = self.beliefs.entry(
                &graph,
                &[COMMITTED_STEP_GRAPH],
                RECORDED,
                owner.as_deref(),
                Some(opens),
                Some(end),
            )?;
            self.beliefs.update(&format!("INSERT DATA {{ {entry} }}"))?;
            let subject = named(step)?;
            let into = GraphName::NamedNode(named(&graph)?);
            let mut held = vec![
                Quad::new(subject.clone(), rdf::TYPE, named(STEP_CLASS)?, into.clone()),
                Quad::new(subject.clone(), named(LANDS_WITHIN_S)?, decimal(within), into.clone()),
                Quad::new(subject.clone(), named(ANSWERED_WITHIN_S)?, decimal(by), into.clone()),
            ];
            let plan_graph = named(plan)?;
            for q in self.intentions.engine().quads_for_pattern(
                Some(subject.as_ref().into()),
                None,
                None,
                Some(plan_graph.as_ref().into()),
            ) {
                let q = q.map_err(|e| Error::Evaluation(e.to_string()))?;
                if !q.predicate.as_str().starts_with(EXECUTION) && q.predicate.as_ref() != rdf::TYPE {
                    held.push(Quad::new(q.subject, q.predicate, q.object, into.clone()));
                }
            }
            self.beliefs.add(held)?;
            hash_named_graph(&self.beliefs, &graph, None)?;
            log::debug!(
                "{}: {} is committed from {}, landing within {within:.0}s and answered within {by:.0}s",
                self.id,
                local_of(step),
                isoformat(opens)
            );
            self.wrote(graph)?;
        }
        Ok(())
    }

    fn close_window(&mut self, step: &str, now: DateTime) -> Result<(), Error> {
        let Some(cat) = self.catalogue()? else {
            return Ok(());
        };
        let graph = committed_graph(&self.id, step);
        let found = self.beliefs.rows(
            &bind(
                WINDOW_Q,
                &[
                    ("cat", Value::iri(cat.clone())),
                    ("g", Value::iri(graph.clone())),
                    ("kind", Value::iri(COMMITTED_STEP_GRAPH)),
                ],
            )?,
            &[],
        )?;
        let Some(row) = found.first() else {
            return Ok(());
        };
        if let Some(end) = at_of(row, "end")?
            && end <= now
        {
            return Ok(());
        }
        self.beliefs.update(&bind(
            CLOSE_U,
            &[
                ("cat", Value::iri(cat)),
                ("g", Value::iri(graph.clone())),
                ("now", instant(now)),
            ],
        )?)?;
        self.wrote(graph)
    }

    fn sweep(&mut self, now: DateTime) -> Result<(), Error> {
        let Some(cat) = self.catalogue()? else {
            return Ok(());
        };
        let owner = self.owner()?;
        let owned = owner.map(|o| format!("; orexis:ownedBy <{o}>")).unwrap_or_default();
        let ended = self.beliefs.rows(
            &bind(
                ENDED_Q,
                &[
                    ("cat", Value::iri(cat)),
                    ("kind", Value::iri(COMMITTED_STEP_GRAPH)),
                    ("now", instant(now)),
                    ("owned", Value::raw(owned)),
                ],
            )?,
            &[],
        )?;
        for r in ended {
            if let Some(g) = iri(&r, "g") {
                self.beliefs.forget_graph(&g, Some(BELIEF))?;
            }
        }
        Ok(())
    }

    // --- what stands --------------------------------------------------------------------------------------------

    /// Every commitment adopted and not resolved, oldest first.
    pub fn standing(&self) -> Result<Vec<Standing>, Error> {
        let mut out = Vec::new();
        for r in self.rows_of(STANDING_Q, &[("intentions", self.mine())])? {
            let (Some(uri), Some(want), Some(adopted)) = (iri(&r, "intention"), iri(&r, "want"), at_of(&r, "adopted")?)
            else {
                continue;
            };
            out.push(Standing {
                uri,
                want,
                at: iri(&r, "at"),
                adopted,
            });
        }
        Ok(out)
    }

    /// Every want a standing commitment pursues — one this agent is walking.
    pub fn walking(&self) -> Result<Vec<String>, Error> {
        Ok(self
            .intentions
            .rows(WALKING_Q, &[])?
            .iter()
            .filter_map(|r| iri(r, "want"))
            .collect())
    }

    /// The commitment standing for `want`, or None — never one ending after its step in flight (#921).
    pub fn standing_for(&self, want: &str) -> Result<Option<Standing>, Error> {
        for s in self.standing()? {
            if s.want == want
                && self
                    .rows_of(
                        ENDING_Q,
                        &[("intentions", self.mine()), ("intention", Value::iri(s.uri.clone()))],
                    )?
                    .is_empty()
            {
                return Ok(Some(s));
            }
        }
        Ok(None)
    }

    // --- resolving ----------------------------------------------------------------------------------------------

    /// Say this commitment has ended, and how; it stays among the intentions, with its outcome.
    pub fn resolve(&mut self, intention: &str, outcome: &str) -> Result<(), Error> {
        let now = self.clock.now();
        self.intentions.update(&format!(
            "INSERT DATA {{ GRAPH <{}> {{ <{intention}> execution:resolvedAt \"{}\"^^xsd:dateTime ; execution:outcome \"{outcome}\" . }} }}",
            self.graph,
            isoformat(now)
        ))?;
        log::info!("{}: {} — {outcome}", self.id, short(intention));
        self.resolved += 1;
        let committed = self.rows_of(
            COMMITTED_Q,
            &[("intentions", self.mine()), ("intention", Value::iri(intention))],
        )?;
        for r in committed {
            if let Some(step) = iri(&r, "step") {
                self.close_window(&step, now)?;
            }
        }
        if self.watch.connected() {
            let want = self
                .rows_of(
                    PURSUED_Q,
                    &[("intentions", self.mine()), ("intention", Value::iri(intention))],
                )?
                .first()
                .and_then(|r| iri(r, "want"));
            self.watch.emit(&IntentionResolved {
                intention: intention.to_string(),
                desire: want.as_ref().and_then(|w| self.desires.get(w).cloned()),
                want,
                outcome: outcome.to_string(),
                at: Some(now),
                said: self.described(&[intention]),
            });
        }
        if outcome != "done" && outcome != "reached" {
            let below = self.rows_of(
                BELOW_Q,
                &[("intentions", self.mine()), ("intention", Value::iri(intention))],
            )?;
            for r in below {
                if let Some(b) = iri(&r, "below") {
                    self.resolve(&b, "abandoned")?;
                }
            }
        }
        Ok(())
    }

    // --- keeping time: one pass ---------------------------------------------------------------------------------

    /// One pass of the timekeeper at `now`: hand every head due to the queue, and hold every head taken to what it
    /// predicted. The steps handed over; what is not yet due is `next_due`.
    pub fn tick(&mut self, now: DateTime) -> Result<Vec<String>, Error> {
        self.sweep(now)?;
        self.moved = false;
        let mut due = Vec::new();
        let mut soonest: Option<DateTime> = None;
        let mut wake_at = |when: DateTime| {
            if soonest.is_none_or(|s| when < s) {
                soonest = Some(when);
            }
        };
        let mut heads = self.rows_of(HEADS_Q, &[("intentions", self.mine())])?;
        //  THE HEADS TAKEN FIRST, then the heads due: a step answered here may end an intention another waits for.
        heads.sort_by_key(|r| !r.contains_key("act"));
        for r in heads {
            let (Some(intention), Some(step)) = (iri(&r, "intention"), iri(&r, "step")) else {
                continue;
            };
            if self.inflight.contains(&step) {
                continue;
            }
            let act = iri(&r, "act");
            if act.is_none()
                && !self
                    .rows_of(
                        WAITS_Q,
                        &[
                            ("intentions", self.mine()),
                            ("intention", Value::iri(intention.clone())),
                        ],
                    )?
                    .is_empty()
            {
                continue;
            }
            let Some(act) = act else {
                let when = at_of(&r, "due")?;
                let ready = when.is_none_or(|w| w <= now);
                if ready && r.contains_key("kept") && self.kept_by(&step)?.is_none() {
                    continue;
                }
                if ready {
                    self.inflight.insert(step.clone());
                    self.work.push_back((intention, step.clone()));
                    due.push(step);
                } else if let Some(w) = when {
                    wake_at(w);
                }
                continue;
            };
            let (adds, retracts) = (iri(&r, "adds"), iri(&r, "retracts"));
            if adds.is_none() && retracts.is_none() {
                continue;
            }
            let (lands, latest) = landing(&r, now)?;
            let below: Vec<Option<String>> = self
                .rows_of(REFINED_Q, &[("intentions", self.mine()), ("act", Value::iri(act))])?
                .iter()
                .map(|b| value(b, "outcome"))
                .collect();
            let given_up = plus(latest, self.patience_s)?;
            if now < lands {
                wake_at(lands);
            } else if self.answered(adds.as_deref(), retracts.as_deref())? {
                self.verdict(&intention, &step, &r, now, true, false)?;
                self.advance(&intention, &step, Some(now))?;
                self.moved = true;
            } else if below.contains(&None) {
                continue;
            } else if !below.is_empty() && !below.contains(&Some("done".to_string())) {
                log::warn!(
                    "{}: {} could not be kept below — {} fails",
                    self.id,
                    local_of(&step),
                    short(&intention)
                );
                self.verdict(&intention, &step, &r, now, false, false)?;
                self.resolve(&intention, "failed")?;
                self.moved = true;
            } else if now >= given_up {
                log::warn!(
                    "{}: the world did not answer {} by {} — {} fails",
                    self.id,
                    local_of(&step),
                    isoformat(latest),
                    short(&intention)
                );
                self.verdict(&intention, &step, &r, now, false, true)?;
                self.resolve(&intention, "failed")?;
                self.moved = true;
            } else {
                wake_at(given_up);
            }
        }
        //  A TICK THAT MOVED AN INTENTION ON is due again at once: the head it moved to is handed over only by a
        //  tick after it, which the next pass's walk runs.
        self.next_due = if self.moved { Some(now) } else { soonest };
        Ok(due)
    }

    /// Does the present hold what a step predicted, over the agent's beliefs and their revisions?
    fn answered(&self, adds: Option<&str>, retracts: Option<&str>) -> Result<bool, Error> {
        let beliefs = self.beliefs.graphs_of(&[BELIEF], &Within::default())?;
        let mut present = beliefs.clone();
        present.extend(self.beliefs.revisions_of(&strs(&beliefs), BELIEF)?);
        let mut failing = Vec::new();
        if let Some(adds) = adds {
            failing.push(bind(ADDS_MISSING, &[("adds", Value::iri(adds))])?);
        }
        if let Some(retracts) = retracts {
            failing.push(bind(RETRACTS_STANDING, &[("retracts", Value::iri(retracts))])?);
        }
        Ok(!self
            .beliefs
            .ask(&format!("ASK {{ {} }}", failing.join(" UNION ")), &strs(&present))?)
    }

    fn advance(&mut self, intention: &str, step: &str, now: Option<DateTime>) -> Result<(), Error> {
        let now = now.unwrap_or_else(|| self.clock.now());
        let ends = self.rows_of(
            ENDS_AFTER_Q,
            &[
                ("intentions", self.mine()),
                ("intention", Value::iri(intention)),
                ("step", Value::iri(step)),
            ],
        )?;
        if !ends.is_empty() {
            self.close_window(step, now)?;
            return self.resolve(intention, "superseded");
        }
        let following = self
            .rows_of(NEXT_Q, &[("intentions", self.mine()), ("step", Value::iri(step))])?
            .first()
            .and_then(|r| iri(r, "next"));
        match following {
            None => self.resolve(intention, "done"),
            Some(next) => {
                self.intentions.update(&bind(
                    ADVANCE_U,
                    &[
                        ("intentions", self.mine()),
                        ("intention", Value::iri(intention)),
                        ("step", Value::iri(step)),
                        ("next", Value::iri(next)),
                    ],
                )?)?;
                self.close_window(step, now)
            }
        }
    }

    /// Tick and drain until nothing more happens at this instant: how many steps were taken. A head moved along in
    /// one tick is handed over only by the next, so the walk ends on two ticks in a row that hand nothing over, and
    /// the instant the last says is due is the soonest anything waits — at once where it moved an intention on.
    pub fn walk(&mut self, now: DateTime) -> Result<usize, Error> {
        let (mut taken, mut idle, mut now) = (0, 0, now);
        while idle < 2 {
            if self.tick(now)?.is_empty() {
                idle += 1;
            } else {
                taken += self.drain()?;
                idle = 0;
            }
            now = self.clock.now();
        }
        if self.watch.connected() {
            self.watch.emit(&Walked {
                standing: i64::try_from(self.walking()?.len()).ok(),
            });
        }
        Ok(taken)
    }

    // --- executing: one pass ------------------------------------------------------------------------------------

    /// Take every step in the queue: how many were taken — a head blocked as it was about to be is not.
    pub fn drain(&mut self) -> Result<usize, Error> {
        let mut taken = 0;
        while let Some((intention, step)) = self.work.pop_front() {
            if self.take_step(&intention, &step)? {
                taken += 1;
            }
        }
        Ok(taken)
    }

    fn take_step(&mut self, intention: &str, step: &str) -> Result<bool, Error> {
        let taken_at = self.clock.now();
        if self.asks {
            //  THE HEAD IS ASKED, NOT TAKEN: it stays in flight, so no tick hands it over again, until the answer
            //  is heard and `judged` takes it or fails it.
            self.asked.insert(step.to_string(), intention.to_string());
            self.watch.emit(&HeadAsked {
                step: step.to_string(),
                at: taken_at,
            });
            return Ok(false);
        }
        self.carry_out(intention, step, taken_at)
    }

    /// The answer to a head asked: BLOCKED, and the head ends `failed` as it was about to be taken; otherwise it is
    /// taken now. Whether it was taken; a step not asked, or answered already, is nothing.
    pub fn judged(&mut self, step: &str, blocked: bool) -> Result<bool, Error> {
        let Some(intention) = self.asked.remove(step) else {
            return Ok(false);
        };
        if blocked {
            self.end_at(step, "failed")?;
            log::info!(
                "{}: {} was not taken — {} ended as it was about to be",
                self.id,
                local_of(step),
                short(&intention)
            );
            self.inflight.remove(step);
            return Ok(false);
        }
        let taken_at = self.clock.now();
        self.carry_out(&intention, step, taken_at)
    }

    fn carry_out(&mut self, intention: &str, step: &str, taken_at: DateTime) -> Result<bool, Error> {
        let said = self.step_of(step)?;
        let refined = self.kept_by(step)?;
        let outcome = match refined {
            Some(_) => Ok(()),
            None => self.take_by(&said, intention),
        };
        let taken = match outcome {
            Ok(()) => true,
            Err(e) => {
                log::error!("{}: step {} could not be taken: {e}", self.id, local_of(step));
                false
            }
        };
        let done_at = self.clock.now();
        let act = format!("{step}.act.{}", stamp(taken_at));
        self.intentions.update(&bind(
            ACT_U,
            &[
                ("intentions", self.mine()),
                ("act", Value::iri(act.clone())),
                ("step", Value::iri(step)),
                ("taken_at", instant(taken_at)),
                ("done_at", instant(done_at)),
                ("taken", Value::raw(if taken { "true" } else { "false" })),
            ],
        )?)?;
        if let Some(refined) = refined {
            self.intentions.update(&format!(
                "INSERT DATA {{ GRAPH <{}> {{ <{act}> <{EXECUTION}refinedBy> <{refined}> }} }}",
                self.graph
            ))?;
        }
        if self.watch.connected() {
            let about = self.about(intention, step, Some(&act))?;
            self.watch.emit(&StepTaken {
                step: step.to_string(),
                at: taken_at,
                taken,
                about,
            });
        }
        if !taken {
            self.resolve(intention, "failed")?;
        } else if !self.predicts(step)? {
            self.advance(intention, step, Some(done_at))?;
        }
        self.inflight.remove(step);
        Ok(true)
    }

    /// Say the verdict on `step` at `now`, where anybody watches: landed or not, and how late the world answered it —
    /// `now` less the `landsAt` the plan placed — in the agent's own seconds.
    fn verdict(
        &self,
        intention: &str,
        step: &str,
        head: &Row,
        now: DateTime,
        landed: bool,
        timed_out: bool,
    ) -> Result<(), Error> {
        if !self.watch.connected() {
            return Ok(());
        }
        let late_s = match at_of(head, "lands")? {
            Some(lands) if landed || timed_out => Some((between(lands, now) * 1000.0).round() / 1000.0),
            _ => None,
        };
        let about = self.about(intention, step, None)?;
        let event: &dyn Event = &StepAnswered {
            step: step.to_string(),
            at: now,
            landed,
            late_s,
            timed_out,
            about,
        };
        self.watch.emit(event);
        Ok(())
    }

    /// What an event about `step` of `intention` carries: the want, its desire, the local name of the action the step
    /// fills, the act recorded of it — `act`, or the latest — and what the journal keeps: the act's own triples, the
    /// step's as its plan states them, and the want the intention pursues.
    fn about(&self, intention: &str, step: &str, act: Option<&str>) -> Result<About, Error> {
        let want = self
            .rows_of(
                PURSUED_Q,
                &[("intentions", self.mine()), ("intention", Value::iri(intention))],
            )?
            .first()
            .and_then(|r| iri(r, "want"));
        let act = match act {
            Some(act) => Some(act.to_string()),
            None => self
                .rows_of(LAST_ACT_Q, &[("intentions", self.mine()), ("step", Value::iri(step))])?
                .first()
                .and_then(|r| iri(r, "act")),
        };
        let mut nodes = vec![step];
        if let Some(act) = act.as_deref() {
            nodes.push(act);
        }
        let mut said = self.described(&nodes);
        if let Some(want) = want.as_deref() {
            said.push(Triple::new(named(intention)?, named(PURSUES)?, named(want)?));
        }
        let action = said
            .iter()
            .find(|t| {
                matches!(&t.subject, NamedOrBlankNode::NamedNode(s) if s.as_str() == step)
                    && local_of(t.predicate.as_str()) == "fills"
            })
            .and_then(|t| match &t.object {
                Term::NamedNode(a) => Some(local_of(a.as_str())),
                _ => None,
            });
        Ok(About {
            desire: want.as_ref().and_then(|w| self.desires.get(w).cloned()),
            want,
            action,
            act,
            said,
        })
    }

    /// Every triple the intentions and the plans hold of `nodes`, in whichever graph, once each.
    fn described(&self, nodes: &[&str]) -> Vec<Triple> {
        let mut out: BTreeMap<String, Triple> = BTreeMap::new();
        for n in nodes {
            let Ok(subject) = NamedNode::new(*n) else { continue };
            for q in self
                .intentions
                .engine()
                .quads_for_pattern(Some(subject.as_ref().into()), None, None, None)
                .flatten()
            {
                let t = Triple::new(q.subject, q.predicate, q.object);
                out.insert(t.to_string(), t);
            }
        }
        out.into_values().collect()
    }

    fn predicts(&self, step: &str) -> Result<bool, Error> {
        let found = self.rows_of(PREDICTED_Q, &[("step", Value::iri(step))])?;
        Ok(found.first().is_some_and(|r| !r.is_empty()))
    }

    fn kept_by(&self, step: &str) -> Result<Option<String>, Error> {
        let found = self
            .beliefs
            .rows(&bind(KEPT_BY_Q, &[("step", Value::iri(step))])?, &[])?;
        Ok(found.first().and_then(|r| iri(r, "want")))
    }

    /// Take the step by whoever takes it: fictively where its action is fictive or the executor is throughout,
    /// otherwise by the taker, which says it in the log where none is handed.
    fn take_by(&mut self, said: &Said, intention: &str) -> Result<(), Error> {
        let fictive = self.all_fictive
            || match said.get("fills") {
                Some(action) => operations(&self.beliefs, action)?.iter().any(|op| op.kind == FICTIVE),
                None => false,
            };
        if fictive {
            return self.fictive(said, intention);
        }
        match self
            .take
            .as_mut()
            .map(|take| take(said, intention))
            .transpose()?
            .flatten()
        {
            //  WHAT THE TAKER KEPT of what the step said goes with what the executor wrote.
            Some(kept) => self.written.extend(kept),
            None => self.say(said, intention),
        }
        Ok(())
    }

    /// A step's rows in words other than this layer's, keyed by the local part of each predicate.
    pub fn step_of(&self, step: &str) -> Result<Said, Error> {
        let mut said = Said::new();
        said.insert("step".to_string(), step.to_string());
        for r in self.rows_of(STEP_Q, &[("intentions", self.mine()), ("step", Value::iri(step))])? {
            if let (Some(p), Some(o)) = (iri(&r, "p"), value(&r, "o")) {
                said.insert(local_of(&p), o);
            }
        }
        Ok(said)
    }

    /// The default taking: the step's name, and what fills it, in the log.
    pub fn say(&self, said: &Said, intention: &str) {
        let filling: Vec<String> = said
            .iter()
            .filter(|(k, _)| k.as_str() != "step")
            .map(|(k, v)| format!("{k}={}", if v.contains("://") { local_of(v) } else { v.clone() }))
            .collect();
        log::info!(
            "{}: taking {} of {} — {}",
            self.id,
            local_of(said.get("step").map_or("", String::as_str)),
            short(intention),
            if filling.is_empty() {
                "nothing filled".to_string()
            } else {
                filling.join(" ")
            }
        );
    }

    /// The taking of a fictive step: say it, then write what it predicted into the beliefs — each retraction taken
    /// out wherever the agent holds it, each addition put where that stood, or in a belief of its own.
    fn fictive(&mut self, said: &Said, intention: &str) -> Result<(), Error> {
        self.say(said, intention);
        let step = said.get("step").cloned().unwrap_or_default();
        let predicted = self
            .rows_of(PREDICTED_Q, &[("step", Value::iri(step))])?
            .into_iter()
            .next()
            .unwrap_or_default();
        let (adds, retracts) = (iri(&predicted, "adds"), iri(&predicted, "retracts"));
        if adds.is_none() && retracts.is_none() {
            return Ok(());
        }
        let cat = self.catalogue()?.unwrap_or_default();
        let held: Vec<String> = match &retracts {
            Some(r) => self
                .beliefs
                .rows(
                    &bind(HELD_Q, &[("cat", Value::iri(cat)), ("retracts", Value::iri(r.clone()))])?,
                    &[],
                )?
                .iter()
                .filter_map(|row| iri(row, "g"))
                .collect(),
            None => Vec::new(),
        };
        let into = held.first().cloned().unwrap_or_else(|| fictive_graph(&self.id));
        let mut writes = Vec::new();
        if let (Some(r), false) = (&retracts, held.is_empty()) {
            let list = held.iter().map(|g| format!("<{g}>")).collect::<Vec<_>>().join(" ");
            writes.push(bind(
                RETRACT_U,
                &[("retracts", Value::iri(r.clone())), ("held", Value::raw(list))],
            )?);
        }
        if let Some(a) = &adds {
            writes.push(bind(
                ADD_U,
                &[("into", Value::iri(into.clone())), ("adds", Value::iri(a.clone()))],
            )?);
        }
        let beliefs = self.beliefs.graphs_of(&[BELIEF], &Within::default())?;
        if adds.is_some() && held.is_empty() && !beliefs.contains(&into) {
            let entry = self
                .beliefs
                .entry(&into, &[BELIEF], DERIVED, self.holder.as_deref(), None, None)?;
            writes.push(format!("INSERT DATA {{ {entry} }}"));
        }
        let mut touched: Vec<String> = held.clone();
        if adds.is_some() {
            touched.push(into);
        }
        let mut seen = BTreeSet::new();
        touched.retain(|g| seen.insert(g.clone()));
        if !writes.is_empty() {
            self.beliefs.update(&writes.join(" ;\n"))?;
            let beliefs = self.beliefs.graphs_of(&[BELIEF], &Within::default())?;
            for graph in &touched {
                if beliefs.contains(graph) {
                    hash_named_graph(&self.beliefs, graph, None)?;
                }
            }
        }
        for graph in touched {
            self.wrote(graph)?;
        }
        Ok(())
    }

    /// Keep `graph` as written as the world, for the part to hand the runtime.
    fn wrote(&mut self, graph: String) -> Result<(), Error> {
        self.written.push(graph);
        Ok(())
    }
}

/// When a taken head should show what it predicted, at the earliest and at the latest — each as long after it was
/// taken as the plan placed it after its opening.
fn landing(head: &Row, now: DateTime) -> Result<(DateTime, DateTime), Error> {
    let Some(lands) = at_of(head, "lands")? else {
        return Ok((now, now));
    };
    let latest = at_of(head, "after")?.map_or(lands, |a| later(lands, a));
    if let (Some(taken), Some(due)) = (at_of(head, "taken")?, at_of(head, "due")?) {
        let late = between(due, taken).max(0.0);
        return Ok((plus(lands, late)?, plus(latest, late)?));
    }
    Ok((lands, latest))
}

#[cfg(test)]
mod tests {
    //! The executor, held to what `agent/execution/tests/test_executor.py` asks of the Python one: a plan copied in,
    //! what stands, the patience that absorbs the second one, and the plan carried out step by step on the two doors
    //! a test drives. A plan graph is a handful of quads in execution's own words, so no world is needed. Not
    //! ported: the two threads, which the Rust agent has none of, and the log line a step is said in.

    use orexis::clock::{Manual, instant as at};
    use orexis::snapshots;

    use super::*;

    const AGENT: &str = "keeper";
    const ME: &str = "http://example.org/test#keeper";
    const WANT: &str = "http://example.org/test#want";
    const PLAN: &str = "http://example.org/test#plan";
    const STATE: &str = "http://example.org/test#sensed";
    const DISK: &str = "http://example.org/test#disk_1";
    const ON: &str = "http://example.org/test#on";
    const PEG_A: &str = "http://example.org/test#PegA";
    const PEG_B: &str = "http://example.org/test#PegB";

    fn now() -> DateTime {
        at("2026-01-01T12:00:00+00:00").unwrap()
    }

    fn store() -> Store {
        Store::new(snapshots::namespaces()).unwrap()
    }

    fn after(s: f64) -> DateTime {
        plus(now(), s).unwrap()
    }

    /// A plan of `steps` steps in execution's own words, chained.
    fn a_plan(steps: usize, plan: &str) -> Store {
        let st = store();
        let chain: Vec<String> = (0..steps)
            .map(|n| {
                let then = if n + 1 < steps {
                    format!("; execution:then <{plan}.{}> ", n + 1)
                } else {
                    String::new()
                };
                format!("<{plan}.{n}> a execution:Step ; execution:partOf <{plan}> {then}.")
            })
            .collect();
        st.update(&format!("INSERT DATA {{ GRAPH <{plan}> {{ {} }} }}", chain.join("\n")))
            .unwrap();
        st
    }

    /// A belief base whose one reading says where the disk is, with the catalogue saying the graph is a belief.
    fn beliefs(on: &str) -> Store {
        let st = store();
        st.put_trig(
            "http://example.org/test#world",
            &format!(
                "@prefix orexis: <http://example.org/orexis#> .
GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{on}> }}
GRAPH <http://example.org/test#catalogue> {{
  <http://example.org/test#catalogue> a orexis:CatalogueGraph .
  <{STATE}> a orexis:BeliefGraph ; orexis:ownedBy <{ME}> }}"
            ),
        )
        .unwrap();
        st
    }

    /// `source`, its `step` predicting `adds` gained and `retracts` lost, in the two graphs a step names.
    fn predicting(source: Store, step: &str, adds: &str, retracts: &str, plan: &str) -> Store {
        source
            .update(&format!(
                "INSERT DATA {{
  GRAPH <{plan}> {{ <{step}> execution:adds <{step}.adds> ; execution:retracts <{step}.retracts> }}
  GRAPH <{step}.adds> {{ {adds} }}
  GRAPH <{step}.retracts> {{ {retracts} }} }}"
            ))
            .unwrap();
        source
    }

    /// A plan whose first step predicts the disk moving from A to B, landing at now.
    fn predicting_move(steps: usize, plan: &str) -> Store {
        let source = predicting(
            a_plan(steps, plan),
            &format!("{plan}.0"),
            &format!("<{DISK}> <{ON}> <{PEG_B}>"),
            &format!("<{DISK}> <{ON}> <{PEG_A}>"),
            plan,
        );
        source
            .update(&format!(
                "INSERT DATA {{ GRAPH <{plan}> {{ <{plan}.0> execution:landsAt \"{}\"^^xsd:dateTime }} }}",
                isoformat(now())
            ))
            .unwrap();
        source
    }

    fn moved(beliefs: &Store) {
        beliefs
            .update(&format!(
                "DELETE DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_A}> }} }} ; INSERT DATA {{ GRAPH <{STATE}> {{ <{DISK}> <{ON}> <{PEG_B}> }} }}"
            ))
            .unwrap();
    }

    fn resolved(x: &Executor, intention: &str) -> Vec<String> {
        x.intentions
            .rows(
                &format!("SELECT ?o WHERE {{ <{intention}> execution:outcome ?o }}"),
                &[&x.graph],
            )
            .unwrap()
            .iter()
            .filter_map(|r| value(r, "o"))
            .collect()
    }

    fn acts(x: &Executor) -> Vec<(String, DateTime, DateTime)> {
        x.intentions
            .rows(
                "SELECT ?a ?taken ?at ?done WHERE { ?a a execution:Act ; execution:taken ?taken ; execution:takenAt ?at ; execution:doneAt ?done } ORDER BY ?a",
                &[&x.graph],
            )
            .unwrap()
            .iter()
            .map(|r| (value(r, "taken").unwrap(), at_of(r, "at").unwrap().unwrap(), at_of(r, "done").unwrap().unwrap()))
            .collect()
    }

    fn windows(beliefs: &Store) -> Vec<(String, DateTime, DateTime)> {
        beliefs
            .rows(
                &bind(
                    "SELECT ?g ?start ?end WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a $kind ; dcterms:temporal ?p .
  ?p orexis:start ?start ; orexis:end ?end } } ORDER BY ?g",
                    &[("kind", Value::iri(COMMITTED_STEP_GRAPH))],
                )
                .unwrap(),
                &[],
            )
            .unwrap()
            .iter()
            .map(|r| (iri(r, "g").unwrap(), at_of(r, "start").unwrap().unwrap(), at_of(r, "end").unwrap().unwrap()))
            .collect()
    }

    fn held_in(beliefs: &Store, graph: &str) -> BTreeSet<(String, String)> {
        beliefs
            .rows("SELECT ?p ?o WHERE { ?s ?p ?o }", &[graph])
            .unwrap()
            .iter()
            .map(|r| (value(r, "p").unwrap(), value(r, "o").unwrap()))
            .collect()
    }

    #[test]
    fn a_committed_plan_stands_at_its_head() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        assert!(x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().is_some());
        let standing = x.standing().unwrap();
        assert_eq!(standing.len(), 1);
        assert_eq!(standing[0].want, WANT);
        assert_eq!(
            standing[0].at.as_deref(),
            Some(format!("{PLAN}.0").as_str()),
            "the head, not the last step"
        );
    }

    #[test]
    fn a_plan_from_another_store_is_brought_in_whole_and_adopted_by_reference() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let intention = x.commit(Some(&a_plan(3, PLAN)), PLAN, WANT).unwrap().unwrap();
        let steps = |g: &str| i.rows("SELECT ?s WHERE { ?s a execution:Step }", &[g]).unwrap().len();
        assert_eq!(steps(PLAN), 3);
        assert_eq!(steps(&x.graph), 0, "no step is copied into the intentions");
        let adopts = i
            .rows(
                &format!("SELECT ?p WHERE {{ <{intention}> execution:adopts ?p }}"),
                &[&x.graph],
            )
            .unwrap();
        assert_eq!(iri(&adopts[0], "p").as_deref(), Some(PLAN));
    }

    #[test]
    fn a_second_plan_inside_the_patience_is_absorbed() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        assert!(x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().is_some());
        assert!(
            x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().is_none(),
            "a second plan was adopted"
        );
        assert_eq!(x.standing().unwrap().len(), 1);
    }

    /// Whoever reads the intentions begins on what the executor says of them: a plan adopted is said once, naming the
    /// intention, and a plan absorbed, which adopts nothing, says nothing.
    #[test]
    fn an_adoption_is_said_once_and_an_absorbed_plan_says_nothing() {
        use crate::events::IntentionAdopted;
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let said: Arc<std::sync::Mutex<Vec<String>>> = Default::default();
        let kept = said.clone();
        x.watch.connect(move |event, _| {
            if let Some(adopted) = orexis::events::as_of::<IntentionAdopted>(event) {
                kept.lock().unwrap().push(adopted.intention.clone());
            }
        });
        let intention = x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().unwrap();
        assert!(x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().is_none());
        assert_eq!(*said.lock().unwrap(), [intention]);
    }

    #[test]
    fn past_the_patience_a_new_plan_supersedes_the_old() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let first = x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().unwrap();
        clock.advance(DEFAULT_PATIENCE_S + 1.0);
        let second = x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().unwrap();
        assert_ne!(first, second);
        assert_eq!(
            x.standing().unwrap().iter().map(|s| s.uri.clone()).collect::<Vec<_>>(),
            [second]
        );
        assert_eq!(resolved(&x, &first), ["superseded"]);
    }

    #[test]
    fn a_resolved_commitment_stays_among_the_intentions() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let intention = x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().unwrap();
        x.resolve(&intention, "done").unwrap();
        assert!(x.standing().unwrap().is_empty());
        let kept = i
            .rows(&format!("SELECT ?p WHERE {{ <{intention}> ?p ?o }}"), &[&x.graph])
            .unwrap();
        assert!(
            !kept.is_empty(),
            "the resolved intention was removed rather than resolved"
        );
    }

    #[test]
    fn an_empty_plan_is_an_answer_and_not_a_commitment() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        assert!(x.commit(Some(&store()), PLAN, WANT).unwrap().is_none());
    }

    #[test]
    fn a_committed_plan_is_taken_step_by_step_and_resolved_done() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let intention = x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().unwrap();
        assert_eq!(
            x.tick(now()).unwrap(),
            [format!("{PLAN}.0")],
            "due at once where the plan states no instant"
        );
        assert!(
            x.tick(now()).unwrap().is_empty(),
            "and handed over once while it is in flight"
        );
        assert_eq!(x.drain().unwrap(), 1);
        assert_eq!(
            x.standing().unwrap()[0].at.as_deref(),
            Some(format!("{PLAN}.1").as_str())
        );
        assert_eq!(x.tick(now()).unwrap(), [format!("{PLAN}.1")]);
        assert_eq!(x.drain().unwrap(), 1);
        assert!(x.standing().unwrap().is_empty());
        assert_eq!(resolved(&x, &intention), ["done"]);
        let acts = acts(&x);
        assert_eq!(acts.iter().map(|a| a.0.as_str()).collect::<Vec<_>>(), ["true", "true"]);
        assert!(acts.iter().all(|(_, taken, done)| done >= taken));
    }

    #[test]
    fn a_step_waits_for_its_instant() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let source = a_plan(1, PLAN);
        let later = after(3600.0);
        source
            .update(&format!(
                "INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:notBefore \"{}\"^^xsd:dateTime }} }}",
                isoformat(later)
            ))
            .unwrap();
        x.commit(Some(&source), PLAN, WANT).unwrap();
        assert!(x.tick(now()).unwrap().is_empty());
        assert_eq!(x.tick(later).unwrap(), [format!("{PLAN}.0")]);
    }

    #[test]
    fn a_step_that_cannot_be_taken_fails_the_intention() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        x.take = Some(Box::new(|_, _| Err(Error::Evaluation("no valve answers".into()))));
        let intention = x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().unwrap();
        x.tick(now()).unwrap();
        assert_eq!(x.drain().unwrap(), 1);
        assert_eq!(resolved(&x, &intention), ["failed"]);
        assert_eq!(acts(&x).iter().map(|a| a.0.as_str()).collect::<Vec<_>>(), ["false"]);
        assert!(x.standing().unwrap().is_empty());
    }

    #[test]
    fn a_step_that_predicts_something_waits_for_the_world_to_answer() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let intention = x.commit(Some(&predicting_move(2, PLAN)), PLAN, WANT).unwrap().unwrap();
        x.tick(now()).unwrap();
        assert_eq!(x.drain().unwrap(), 1);
        let head = |x: &Executor| x.standing().unwrap()[0].at.clone().unwrap();
        assert_eq!(head(&x), format!("{PLAN}.0"), "taken, and still the head");
        assert!(x.tick(now()).unwrap().is_empty());
        assert_eq!(head(&x), format!("{PLAN}.0"));
        moved(&b);
        assert!(x.tick(now()).unwrap().is_empty());
        assert_eq!(head(&x), format!("{PLAN}.1"), "the world answered: the intention moved");
        assert_eq!(
            x.tick(now()).unwrap(),
            [format!("{PLAN}.1")],
            "and the next head is due on the pass after"
        );
        assert!(resolved(&x, &intention).is_empty());
    }

    #[test]
    fn a_step_predicting_a_conclusion_is_answered_by_the_states_revision() {
        let (soil, range) = ("http://example.org/test#soil", "http://example.org/test#bed_operating");
        let (below, inside) = ("http://example.org/test#below", "http://example.org/test#inside");
        let revisions = format!("{STATE}/revisions");
        let b = beliefs(PEG_A);
        b.update(&format!(
            "INSERT DATA {{ GRAPH <{revisions}> {{ <{soil}> <{below}> <{range}> }}
        GRAPH <http://example.org/test#catalogue> {{ <{revisions}> <http://www.w3.org/ns/prov#wasDerivedFrom> <{STATE}> ; a <http://example.org/orexis#BeliefGraph> }} }}"
        ))
        .unwrap();
        let source = predicting(
            a_plan(2, PLAN),
            &format!("{PLAN}.0"),
            &format!("<{soil}> <{inside}> <{range}>"),
            &format!("<{soil}> <{below}> <{range}>"),
            PLAN,
        );
        source
            .update(&format!(
                "INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:landsAt \"{}\"^^xsd:dateTime }} }}",
                isoformat(now())
            ))
            .unwrap();
        let (i, clock) = (store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        x.commit(Some(&source), PLAN, WANT).unwrap();
        x.tick(now()).unwrap();
        assert_eq!(x.drain().unwrap(), 1);
        assert!(x.tick(now()).unwrap().is_empty());
        assert_eq!(
            x.standing().unwrap()[0].at.clone().unwrap(),
            format!("{PLAN}.0"),
            "still below"
        );
        b.update(&format!(
            "DELETE DATA {{ GRAPH <{revisions}> {{ <{soil}> <{below}> <{range}> }} }} ; INSERT DATA {{ GRAPH <{revisions}> {{ <{soil}> <{inside}> <{range}> }} }}"
        ))
        .unwrap();
        assert!(x.tick(now()).unwrap().is_empty());
        assert_eq!(
            x.standing().unwrap()[0].at.clone().unwrap(),
            format!("{PLAN}.1"),
            "revised inside: moved"
        );
    }

    fn on(b: &Store) -> String {
        iri(
            &b.rows(&format!("SELECT ?on WHERE {{ <{DISK}> <{ON}> ?on }}"), &[STATE])
                .unwrap()[0],
            "on",
        )
        .unwrap()
    }

    #[test]
    fn a_step_of_a_fictive_action_is_taken_by_the_executor_itself() {
        let b = beliefs(PEG_A);
        let mv = "http://example.org/test#Move";
        b.update(&format!(
            "INSERT DATA {{
  GRAPH <http://example.org/test#actions> {{ <{mv}> a orexis:Action ;
      execution:implementation [ execution:operation [ a execution:Fictive ] ] }}
  GRAPH <http://example.org/test#catalogue> {{ <http://example.org/test#actions> a orexis:ActionGraph }} }}"
        ))
        .unwrap();
        let (i, clock) = (store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let source = predicting_move(1, PLAN);
        source
            .update(&format!(
                "INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> <http://example.org/orexis/planning#fills> <{mv}> }} }}"
            ))
            .unwrap();
        let intention = x.commit(Some(&source), PLAN, WANT).unwrap().unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        assert_eq!(on(&b), PEG_B);
        x.tick(now()).unwrap();
        assert_eq!(resolved(&x, &intention), ["done"]);
    }

    #[test]
    fn a_fictive_executor_is_the_world_of_its_own_steps() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        x.all_fictive = true;
        let intention = x.commit(Some(&predicting_move(1, PLAN)), PLAN, WANT).unwrap().unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        assert_eq!(on(&b), PEG_B, "the executor moved the disk, since nothing else could");
        x.tick(now()).unwrap();
        assert_eq!(resolved(&x, &intention), ["done"]);
    }

    #[test]
    fn a_world_that_does_not_answer_by_the_patience_fails_the_intention() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let intention = x.commit(Some(&predicting_move(1, PLAN)), PLAN, WANT).unwrap().unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        x.tick(after(DEFAULT_PATIENCE_S - 1.0)).unwrap();
        assert!(resolved(&x, &intention).is_empty());
        assert_eq!(x.standing().unwrap().len(), 1);
        x.tick(after(DEFAULT_PATIENCE_S)).unwrap();
        assert_eq!(resolved(&x, &intention), ["failed"]);
    }

    #[test]
    fn the_patience_is_the_agents_stance_where_its_self_graph_states_one() {
        let (i, clock) = (store(), Arc::new(Manual::at(now())));
        let plain = beliefs(PEG_A);
        assert_eq!(
            Executor::new(&plain, AGENT, Some(&i), None, clock.clone())
                .unwrap()
                .patience_s,
            DEFAULT_PATIENCE_S
        );
        let b = beliefs(PEG_A);
        let me_self = "http://example.org/test#self";
        b.update(&format!(
            "INSERT DATA {{
  GRAPH <{me_self}> {{ <{ME}> a orexis:Self ; <{PATIENCE_S}> 5 }}
  GRAPH <http://example.org/test#catalogue> {{ <{me_self}> a orexis:SelfGraph , orexis:BeliefGraph , orexis:Graph ; orexis:ownedBy <{ME}> }} }}"
        ))
        .unwrap();
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        assert_eq!(x.patience_s, 5.0);
        let intention = x.commit(Some(&predicting_move(1, PLAN)), PLAN, WANT).unwrap().unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        x.tick(after(4.0)).unwrap();
        assert!(resolved(&x, &intention).is_empty());
        x.tick(after(5.0)).unwrap();
        assert_eq!(resolved(&x, &intention), ["failed"]);
    }

    #[test]
    fn the_patience_runs_from_the_latest_landing_where_the_plan_states_one() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let source = predicting_move(1, PLAN);
        let latest = after(600.0);
        source
            .update(&format!(
                "INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:notAfter \"{}\"^^xsd:dateTime }} }}",
                isoformat(latest)
            ))
            .unwrap();
        let intention = x.commit(Some(&source), PLAN, WANT).unwrap().unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        x.tick(after(DEFAULT_PATIENCE_S)).unwrap();
        assert!(
            resolved(&x, &intention).is_empty(),
            "a patience past the earliest is still inside the band"
        );
        x.tick(plus(latest, DEFAULT_PATIENCE_S - 1.0).unwrap()).unwrap();
        assert!(resolved(&x, &intention).is_empty());
        x.tick(plus(latest, DEFAULT_PATIENCE_S).unwrap()).unwrap();
        assert_eq!(resolved(&x, &intention), ["failed"]);
    }

    #[test]
    fn a_step_is_not_held_to_the_world_before_it_lands() {
        let (b, i, clock) = (beliefs(PEG_B), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let source = predicting_move(1, PLAN);
        let later = after(3600.0);
        source
            .update(&format!(
                "DELETE {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:landsAt ?t }} }} INSERT {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:landsAt \"{}\"^^xsd:dateTime }} }} WHERE {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:landsAt ?t }} }}",
                isoformat(later)
            ))
            .unwrap();
        let intention = x.commit(Some(&source), PLAN, WANT).unwrap().unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        x.tick(now()).unwrap();
        assert!(resolved(&x, &intention).is_empty(), "not yet landed, so not yet asked");
        x.tick(later).unwrap();
        assert_eq!(resolved(&x, &intention), ["done"]);
    }

    #[test]
    fn a_step_taken_late_lands_late_by_as_much() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let source = predicting_move(1, PLAN);
        source
            .update(&format!(
                "INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:notBefore \"{}\"^^xsd:dateTime }} }}",
                isoformat(now())
            ))
            .unwrap();
        let intention = x.commit(Some(&source), PLAN, WANT).unwrap().unwrap();
        let late = after(100.0);
        clock.set(late);
        x.tick(late).unwrap();
        x.drain().unwrap();
        x.tick(plus(late, DEFAULT_PATIENCE_S - 1.0).unwrap()).unwrap();
        assert!(
            resolved(&x, &intention).is_empty(),
            "held to the landing it was placed at, it had failed"
        );
        x.tick(plus(late, DEFAULT_PATIENCE_S).unwrap()).unwrap();
        assert_eq!(resolved(&x, &intention), ["failed"]);
    }

    #[test]
    fn a_second_plan_for_a_want_is_walked_by_steps_of_its_own() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let first = x.commit(Some(&predicting_move(1, PLAN)), PLAN, WANT).unwrap().unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        x.tick(after(DEFAULT_PATIENCE_S)).unwrap();
        assert_eq!(resolved(&x, &first), ["failed"]);
        let second_plan = format!("{PLAN}2");
        let second = x
            .commit(Some(&predicting_move(1, &second_plan)), &second_plan, WANT)
            .unwrap()
            .unwrap();
        let standing = x.standing().unwrap();
        assert_eq!(standing.len(), 1);
        assert_eq!(standing[0].uri, second);
        assert_eq!(standing[0].at.as_deref(), Some(format!("{PLAN}2.0").as_str()));
        assert_eq!(
            x.tick(after(DEFAULT_PATIENCE_S)).unwrap(),
            [format!("{PLAN}2.0")],
            "due, never taken"
        );
    }

    /// The first step placed: due in five minutes, landing a quarter past, filling a disk.
    fn placed(plan: Store) -> Store {
        plan.update(&format!(
            "INSERT DATA {{ GRAPH <{PLAN}> {{
      <{PLAN}.0> execution:notBefore \"{}\"^^xsd:dateTime ;
                 execution:landsAt \"{}\"^^xsd:dateTime ;
                 <http://example.org/test#disk> <{DISK}> }} }}",
            isoformat(after(300.0)),
            isoformat(after(900.0))
        ))
        .unwrap();
        plan
    }

    #[test]
    fn a_committed_steps_window_closes_a_patience_past_its_latest_landing() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let plan = placed(predicting_move(1, PLAN));
        plan.update(&format!(
            "INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> execution:notAfter \"{}\"^^xsd:dateTime }} }}",
            isoformat(after(1500.0))
        ))
        .unwrap();
        Executor::new(&b, AGENT, Some(&i), None, clock.clone())
            .unwrap()
            .commit(Some(&plan), PLAN, WANT)
            .unwrap();
        let windows = windows(&b);
        assert_eq!(windows.len(), 1);
        assert_eq!(
            (windows[0].1, windows[0].2),
            (after(300.0), after(1500.0 + DEFAULT_PATIENCE_S))
        );
        let held = held_in(&b, &windows[0].0);
        assert!(held.contains(&(LANDS_WITHIN_S.into(), "600".into())), "{held:?}");
        assert!(held.contains(&(ANSWERED_WITHIN_S.into(), "1260".into())), "{held:?}");
    }

    #[test]
    fn a_committed_step_is_a_belief_over_its_landing_window() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        x.commit(Some(&placed(predicting_move(2, PLAN))), PLAN, WANT).unwrap();
        let windows = windows(&b);
        assert_eq!(
            windows.iter().map(|w| (w.1, w.2)).collect::<Vec<_>>(),
            [
                (after(300.0), after(900.0 + DEFAULT_PATIENCE_S)),
                (now(), after(DEFAULT_PATIENCE_S))
            ]
        );
        assert_eq!(
            x.written,
            windows.iter().map(|w| w.0.clone()).collect::<Vec<_>>(),
            "each said as written"
        );
        let held = held_in(&b, &windows[0].0);
        assert!(held.contains(&(LANDS_WITHIN_S.into(), "600".into())));
        assert!(held.contains(&(ANSWERED_WITHIN_S.into(), "660".into())));
        assert!(
            held.contains(&("http://example.org/test#disk".into(), DISK.into())),
            "the filling, as stated"
        );
        assert!(
            !held
                .iter()
                .any(|(p, _)| p.ends_with("#adds") || p.ends_with("#retracts")),
            "the prediction stays the plan's"
        );
        assert!(held.contains(&(rdf::TYPE.as_str().into(), STEP_CLASS.into())));
    }

    #[test]
    fn a_window_closes_when_the_world_answers_and_an_ended_one_is_swept() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        x.commit(Some(&predicting_move(2, PLAN)), PLAN, WANT).unwrap();
        assert_eq!(windows(&b).len(), 2);
        assert_eq!(x.written.len(), 2);
        x.tick(now()).unwrap();
        x.drain().unwrap();
        moved(&b);
        let then = after(10.0);
        x.tick(then).unwrap();
        assert_eq!(
            x.standing().unwrap()[0].at.clone().unwrap(),
            format!("{PLAN}.1"),
            "answered"
        );
        let closed: Vec<_> = windows(&b).into_iter().filter(|w| w.0.ends_with("plan_0")).collect();
        assert_eq!(closed[0].2, then, "closed at the instant the world answered");
        assert_eq!(x.written.last(), Some(&closed[0].0), "and said");
        x.tick(after(11.0)).unwrap();
        let first_two: Vec<String> = x.written[..2]
            .iter()
            .filter(|g| g.ends_with("plan_1"))
            .cloned()
            .collect();
        assert_eq!(
            windows(&b).into_iter().map(|w| w.0).collect::<Vec<_>>(),
            first_two,
            "swept; the next stands"
        );
    }

    #[test]
    fn an_intention_that_ends_closes_every_window_it_opened() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let intention = x
            .commit(Some(&placed(predicting_move(2, PLAN))), PLAN, WANT)
            .unwrap()
            .unwrap();
        x.resolve(&intention, "superseded").unwrap();
        assert_eq!(
            windows(&b).iter().map(|w| w.2).collect::<Vec<_>>(),
            [now(), now()],
            "both closed at the end"
        );
        assert_eq!(x.written.len(), 4, "written twice, closed twice");
        x.tick(now()).unwrap();
        assert!(windows(&b).is_empty());
    }

    #[test]
    fn a_plan_replacing_an_intentions_untaken_steps_waits_for_it_to_end_after_its_step_in_flight() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let first = x.commit(Some(&predicting_move(2, PLAN)), PLAN, WANT).unwrap().unwrap();
        assert_eq!(x.tick(now()).unwrap(), [format!("{PLAN}.0")]);
        assert_eq!(x.drain().unwrap(), 1);
        let joint = format!("{WANT}_joint");
        x.supersede_after(&format!("{PLAN}.0"), Some(&joint)).unwrap();
        let joint_plan = format!("{PLAN}_joint");
        let second = x
            .commit(Some(&a_plan(1, &joint_plan)), &joint_plan, &joint)
            .unwrap()
            .unwrap();
        let waits = i
            .rows(
                &format!("SELECT ?f WHERE {{ GRAPH ?g {{ <{second}> execution:waitsFor ?f }} }}"),
                &[],
            )
            .unwrap();
        assert_eq!(
            waits.iter().filter_map(|r| iri(r, "f")).collect::<Vec<_>>(),
            [first.as_str()]
        );
        assert!(
            x.tick(now()).unwrap().is_empty(),
            "due, and waiting for the intention its plan replaced"
        );
        assert!(resolved(&x, &first).is_empty());
        moved(&b);
        assert_eq!(
            x.tick(now()).unwrap(),
            [format!("{PLAN}_joint.0")],
            "answered, and the replacement walks"
        );
        assert_eq!(resolved(&x, &first), ["superseded"]);
    }

    #[test]
    fn a_plan_adopted_with_no_reconsideration_behind_it_waits_for_nothing() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        x.commit(Some(&predicting_move(2, PLAN)), PLAN, WANT).unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        x.supersede_after(&format!("{PLAN}.0"), Some(&format!("{WANT}_joint")))
            .unwrap();
        let other = format!("{PLAN}_other");
        x.commit(Some(&a_plan(1, &other)), &other, &format!("{WANT}_other"))
            .unwrap();
        assert_eq!(x.tick(now()).unwrap(), [format!("{PLAN}_other.0")]);
    }

    #[test]
    fn a_head_asked_waits_for_its_answer_and_one_blocked_is_not_taken_and_its_intention_fails() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        x.asks = true;
        let intention = x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap().unwrap();
        let head = format!("{PLAN}.0");
        assert_eq!(x.tick(now()).unwrap(), std::slice::from_ref(&head));
        assert_eq!(x.drain().unwrap(), 0, "asked, not taken");
        assert!(
            x.tick(now()).unwrap().is_empty(),
            "a head asked is not handed over again"
        );
        assert!(
            !x.judged("http://example.org/test#other", true).unwrap(),
            "nothing asked of it"
        );
        assert!(!x.judged(&head, true).unwrap(), "blocked as it was about to be taken");
        assert_eq!(resolved(&x, &intention), ["failed"]);
        assert!(acts(&x).is_empty(), "no act is recorded of a step not taken");
    }

    #[test]
    fn a_head_asked_and_admitted_is_taken() {
        let (b, i, clock) = (store(), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        x.asks = true;
        x.commit(Some(&a_plan(2, PLAN)), PLAN, WANT).unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        assert!(acts(&x).is_empty());
        assert!(x.judged(&format!("{PLAN}.0"), false).unwrap());
        assert_eq!(acts(&x).len(), 1);
    }

    #[test]
    fn an_act_is_named_for_the_instant_it_was_taken_as_python_spells_it() {
        assert_eq!(stamp(now()), "20260101T120000000000");
        assert_eq!(
            stamp(at("2026-01-01T12:00:00.25+00:00").unwrap()),
            "20260101T120000250000"
        );
        assert_eq!(
            committed_graph(AGENT, "http://example.org/test#plan.0"),
            "http://example.org/orexis/graph/committed/keeper/plan_0"
        );
    }

    // --- what the executor says happened: held to `agent/execution/tests/test_events.py` ----------------------

    const T: &str = "http://example.org/test#";
    const FILLS: &str = "http://example.org/orexis/planning#fills";

    /// Every event the executor says, kept in a journal as the history part keeps them.
    fn heard(x: &mut Executor) -> Arc<orexis::journal::Journal> {
        let journal = Arc::new(orexis::journal::Journal::new(None, 600.0, Arc::new(now)).unwrap());
        let kept = journal.clone();
        x.watch.connect(move |event, entry| {
            if let Some(triples) = event.statements(entry) {
                kept.record(entry, triples, event.at(), false).unwrap();
            }
        });
        journal
    }

    /// The move plan, its step filling `Move` with the disk and peg B.
    fn filled_move() -> Store {
        let plan = predicting_move(1, PLAN);
        plan.update(&format!(
            "INSERT DATA {{ GRAPH <{PLAN}> {{ <{PLAN}.0> <{FILLS}> <{T}Move> ; <{T}disk> <{DISK}> ; <{T}to> <{PEG_B}> }} }}"
        ))
        .unwrap();
        plan
    }

    /// Each step event, in time order: its kind, the act's `taken`, the verdict's `landed`, whether it failed, the
    /// action the step fills, the values it takes and the want its intention pursues.
    fn step_events(journal: &orexis::journal::Journal) -> Vec<Vec<String>> {
        let text = format!(
            "PREFIX execution: <http://example.org/orexis/execution#> PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?kind ?taken ?landed ?failed ?action ?disk ?to ?want WHERE {{ GRAPH ?e {{
  ?e a ?kind ; prov:atTime ?at ; execution:act ?act . ?act execution:of ?step ; execution:taken ?taken .
  ?step <{FILLS}> ?action ; <{T}disk> ?disk ; <{T}to> ?to . ?i execution:pursues ?want
  OPTIONAL {{ ?e execution:landed ?landed }}
  BIND(EXISTS {{ ?e a execution:StepFailed }} AS ?failed)
  FILTER(?kind IN (execution:StepTaken, execution:StepAnswered)) }} }} ORDER BY ?at ?kind"
        );
        let (_, body) = orexis::journal::answer(&journal.store, &text).unwrap();
        let json = String::from_utf8(body).unwrap();
        //  EACH BINDING'S VALUE, in the projected order, read off the results' JSON by hand.
        let mut out = Vec::new();
        for result in json.split("{\"kind\"").skip(1) {
            let mut row = Vec::new();
            for var in ["kind", "taken", "landed", "failed", "action", "disk", "to", "want"] {
                let key = format!("\"{var}\":");
                let found = if var == "kind" {
                    Some(result)
                } else {
                    result.split(&key).nth(1)
                };
                let v = found
                    .and_then(|f| f.split("\"value\":\"").nth(1))
                    .and_then(|v| v.split('"').next())
                    .unwrap_or("-");
                row.push(local_of(v));
            }
            out.push(row);
        }
        out
    }

    #[test]
    fn a_step_taken_carries_its_act_its_step_as_the_plan_states_it_and_its_want() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let journal = heard(&mut x);
        x.commit(Some(&filled_move()), PLAN, WANT).unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        assert_eq!(
            step_events(&journal),
            [["StepTaken", "true", "-", "false", "Move", "disk_1", "PegB", "want"]]
        );
    }

    #[test]
    fn a_step_taken_and_answered_is_said_taken_and_then_landed() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let journal = heard(&mut x);
        x.commit(Some(&filled_move()), PLAN, WANT).unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        moved(&b);
        x.tick(after(60.0)).unwrap();
        let said: Vec<Vec<String>> = step_events(&journal).into_iter().map(|r| r[..4].to_vec()).collect();
        assert_eq!(
            said,
            [
                ["StepTaken", "true", "-", "false"],
                ["StepAnswered", "true", "true", "false"]
            ]
        );
    }

    #[test]
    fn a_step_the_world_does_not_answer_by_the_patience_has_failed_and_says_how_late() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        let journal = heard(&mut x);
        let verdicts = std::sync::Arc::new(std::sync::Mutex::new(Vec::new()));
        let kept = verdicts.clone();
        x.watch.connect(move |e, _| {
            if let Some(v) = orexis::events::as_of::<StepAnswered>(e) {
                kept.lock().unwrap().push(v.clone());
            }
        });
        x.commit(Some(&filled_move()), PLAN, WANT).unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        x.tick(after(DEFAULT_PATIENCE_S - 1.0)).unwrap();
        assert_eq!(step_events(&journal).len(), 1, "waiting is no verdict");
        x.tick(after(DEFAULT_PATIENCE_S)).unwrap();
        let said: Vec<Vec<String>> = step_events(&journal).into_iter().map(|r| r[..4].to_vec()).collect();
        assert_eq!(
            said,
            [
                ["StepTaken", "true", "-", "false"],
                ["StepAnswered", "true", "false", "true"]
            ]
        );
        let verdict = verdicts.lock().unwrap()[0].clone();
        assert_eq!(
            (
                verdict.landed,
                verdict.timed_out,
                verdict.late_s,
                verdict.about.action.as_deref()
            ),
            (false, true, Some(DEFAULT_PATIENCE_S), Some("Move"))
        );
    }

    #[test]
    fn a_step_that_could_not_be_taken_says_so_and_fails_its_intention_an_incident() {
        let (b, i, clock) = (beliefs(PEG_A), store(), Arc::new(Manual::at(now())));
        let mut x = Executor::new(&b, AGENT, Some(&i), None, clock.clone()).unwrap();
        x.take = Some(Box::new(|_, _| Err(Error::Evaluation("no valve answers".into()))));
        let journal = heard(&mut x);
        x.commit(Some(&filled_move()), PLAN, WANT).unwrap();
        x.tick(now()).unwrap();
        x.drain().unwrap();
        x.tick(after(DEFAULT_PATIENCE_S)).unwrap();
        let said: Vec<Vec<String>> = step_events(&journal).into_iter().map(|r| r[..4].to_vec()).collect();
        assert_eq!(said, [["StepTaken", "false", "-", "false"]]);
        let (_, body) = orexis::journal::answer(
            &journal.store,
            "PREFIX execution: <http://example.org/orexis/execution#>
SELECT ?outcome WHERE { ?e a execution:IntentionResolved, execution:IntentionFailed ; execution:intention ?i .
                        ?i execution:outcome ?outcome }",
        )
        .unwrap();
        let body = String::from_utf8(body).unwrap();
        assert_eq!(
            body.matches("\"failed\"").count(),
            1,
            "the intention it failed is an IntentionFailed: {body}"
        );
    }
}
