//! THE PLANNER: the one thing the rest of the tree uses, and the one place the acts are sequenced — as
//! `agent/planning/planner.py` sequences them. **A STAR, NOT A CHAIN**: every act is a function over the store that
//! calls no other act, and `plan` is the pass, `search` one want's search, `expand` one iteration of it.
//!
//! One pass: per scope, an imaginarium kept from pass to pass — `prepare_ground` copies or refreshes, `lay_ground`
//! lays the grounds, `reroot` keeps the cone the present landed in; every desire weighed in every ground, a walking
//! want a belief makes impossible ahead reopened (#921), `derive_wants` and `withdraw`; per want no intention walks,
//! `search`, and `extract_plan`, and `_reconsider` against a walking intention's untaken steps; `publish_plan`. And
//! outside the pass, `check`, of a head about to be taken.
//!
//! NOT PORTED: the events the Python copy signals, its laps, and the predictor's foresight. What a pass says it did
//! is on the fields a caller reads — `handed`, `reached`, `blocked`, `superseded` — and whoever runs the pass says it.

use std::collections::{BTreeMap, BTreeSet, HashSet};
use std::sync::Arc;

use oxigraph::model::{GraphName, NamedNode, Quad, Term, Triple};
use oxsdatatypes::{DateTime, DayTimeDuration};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::{ACTION, BELIEF, RECORD, SELF_GRAPH};
use orexis::store::{Store, Within, instant, iri, value};

use crate::admit::{Scope, admit, local_of};
use crate::bridge::keeps;
use crate::derive_wants::derive_wants;
use crate::extract_plan::extract_plan;
use crate::find_scopes::{Scopes, find_scopes};
use crate::find_wants::{Finding, find_wants};
use crate::footprint::{actions_of, reads_of_shape, terms_of_shape, written};
use crate::lay_ground::{Landed, Laying, lay_ground};
use crate::memo::Memo;
use crate::ontology::{
    BUDGET_TERM, CONSTRAINT_GRAPH, DESIRE, EXHAUSTED, GROUND_GRAPH, PLAN_GRAPH, PLANNING, SATISFIED, SCOPE_GRAPH,
    SHAPES, WANT,
};
use crate::prepare_ground::prepare_ground;
use crate::publish_plan::publish_plan;
use crate::refine::refine;
use crate::reroot::reroot;
use crate::scope_actions::scope_actions;
use crate::shapes::Shapes;
use crate::take::take;
use crate::unweighed::unweighed;
use crate::weigh::{shapes, weigh};
use crate::withdraw::withdraw;
use crate::world_at::{Asking, catalogue, lexical, world_at};

const IN_SCOPE_Q: &str = r#"SELECT ?a WHERE { ?a planning:inScope $scope }"#;
const REFINED_Q: &str = r#"
SELECT ?want ?g ?step WHERE { GRAPH ?g { ?step execution:keptBy ?want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph } }"#;
const WALKING_Q: &str = r#"
SELECT DISTINCT ?want WHERE {
  { GRAPH ?g { ?i a execution:Intention ; execution:pursues ?want .
               FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }
  UNION
  { GRAPH $cat { ?plan a orexis:PlanGraph } GRAPH ?plan { ?plan execution:pursues ?want }
    FILTER NOT EXISTS { GRAPH ?h { ?i execution:adopts ?plan } } } }
ORDER BY ?want"#;
const STANDS_AT_Q: &str = r#"
SELECT ?intention ?want ?plan ?step ?action ?due ?taken ?lands ?ending WHERE {
  GRAPH ?g { ?intention a execution:Intention ; execution:pursues ?want ; execution:by ?step ; execution:adopts ?plan .
             FILTER NOT EXISTS { ?intention execution:resolvedAt ?done }
             OPTIONAL { ?act execution:of ?step ; execution:taken true ; execution:takenAt ?taken }
             OPTIONAL { ?intention execution:endsAfter ?ending } }
  GRAPH ?plan { ?step planning:fills ?action .
                OPTIONAL { ?step execution:notBefore ?due } OPTIONAL { ?step execution:landsAt ?lands } } }
ORDER BY ?intention"#;
const CHAIN_Q: &str = r#"
SELECT ?step ?next ?action ?p ?v WHERE { GRAPH $plan { ?step a execution:Step ; planning:fills ?action ; ?p ?v .
  OPTIONAL { ?step execution:then ?next } } }"#;
const TAKES_Q: &str = r#"SELECT ?takes WHERE { $action orexis:takes ?takes }"#;
const REOPENS_Q: &str = r#"SELECT ?w WHERE { GRAPH ?g { $want planning:reopens ?w } } ORDER BY ?w"#;
const PLAN_FOR_Q: &str = r#"SELECT ?plan ?outcome WHERE { GRAPH ?plan { ?plan a planning:Plan ; planning:for $want ; planning:outcome ?outcome } } LIMIT 1"#;
const REOPENING_Q: &str = r#"
SELECT ?w WHERE { GRAPH ?g { ?w planning:reopens ?w }
  FILTER NOT EXISTS { GRAPH ?p { ?p a planning:Plan ; planning:for ?w ; planning:outcome planning:Satisfied } } }"#;
const GROUND_HASHES_Q: &str = r#"SELECT ?h WHERE { GRAPH $cat { ?g a planning:GroundGraph ; orexis:hash ?h } }"#;
const HASHES_Q: &str = r#"SELECT DISTINCT ?h WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w orexis:hash ?h .
  { ?w a planning:GroundGraph } UNION { ?w a planning:PossibleGraph } } }"#;
const DERIVED_Q: &str = r#"
SELECT ?w WHERE { GRAPH ?g { ?w a planning:Want }
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:WantGraph ; orexis:arrivedBy orexis:Derived } }"#;
const PREDICTS_Q: &str = r#"
SELECT ?step ?lands ?adds ?retracts WHERE { GRAPH $plan { ?step a execution:Step .
  OPTIONAL { ?step execution:landsAt ?lands } OPTIONAL { ?step execution:adds ?adds }
  OPTIONAL { ?step execution:retracts ?retracts } } }"#;
const FORESEEN_U: &str = r#"
INSERT { GRAPH ?cat { $world dcterms:temporal [ a dcterms:PeriodOfTime ; orexis:start $start ] } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph } }"#;
const UNWEIGH_U: &str = r#"
DELETE { GRAPH ?cat { ?x ?p ?o . ?v ?vp ?vo } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      ?x planning:weighs $world ; ?p ?o .
                      OPTIONAL { ?x planning:violation ?v . ?v ?vp ?vo } } }"#;
const HOLDS_CONSTRAINT_Q: &str = r#"SELECT ?c WHERE { $holder planning:holds ?c . ?c a planning:Constraint } LIMIT 1"#;
const STANDING_AT_Q: &str = r#"
SELECT DISTINCT ?step WHERE { GRAPH ?g { ?i a execution:Intention ; execution:by ?step .
                                         FILTER NOT EXISTS { ?i execution:resolvedAt ?done } } }"#;
const KEPT_DUE_Q: &str = r#"
SELECT ?step WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:by ?step ; execution:adopts ?plan .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done } }
  GRAPH ?plan { ?step execution:keptBelow true .
                OPTIONAL { ?step execution:notBefore ?due } }
  FILTER(!BOUND(?due) || ?due <= $now)
  FILTER NOT EXISTS { GRAPH ?h { ?step execution:keptBy ?w } } }
ORDER BY ?step"#;
const HEAD_Q: &str = r#"
SELECT ?action WHERE { GRAPH ?p { $step planning:fills ?action }
  FILTER NOT EXISTS { GRAPH ?k { $step execution:keptBelow true } } } LIMIT 1"#;
const PRECONDITION_Q: &str =
    r#"SELECT ?text ?takes WHERE { $action planning:precondition ?text . OPTIONAL { $action orexis:takes ?takes } }"#;
const FILLING_Q: &str = r#"SELECT ?p ?v WHERE { GRAPH ?plan { $step ?p ?v } }"#;
const FICTIVE_STEPS_Q: &str = r#"
SELECT ?step WHERE {
  GRAPH $plan { ?step a execution:Step ; planning:fills ?action }
  ?action execution:implementation/execution:operation ?op . ?op a execution:Fictive }
ORDER BY ?step"#;
const MET_NOW_Q: &str = r#"
SELECT DISTINCT ?for WHERE {
  GRAPH ?cat { ?x planning:weighs $ground ; planning:for ?for ; planning:met true .
               ?cat a orexis:CatalogueGraph .
               ?d a planning:WantGraph . OPTIONAL { ?d dcterms:temporal/orexis:start ?ws } }
  GRAPH ?d { ?for a planning:Want }
  FILTER(!BOUND(?ws) || ?ws <= $now) }"#;
const OUTCOMES_Q: &str = r#"SELECT ?o WHERE { GRAPH $plan { ?p a planning:Plan ; planning:outcome ?o } }"#;
const GROUND_STARTS_Q: &str = r#"
SELECT ?s WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?s } }
ORDER BY ?s"#;
const PURSUES_Q: &str = r#"SELECT ?want WHERE { GRAPH ?g { $plan execution:pursues ?want } } LIMIT 1"#;
const FRONTIER_Q: &str = r#"
SELECT ?w ?spent ?remaining ?minted ?weighing ?late ?lands ?best ?bestLate ?bestLands WHERE {
  GRAPH $cat { ?weighing a planning:Weighing ; planning:for $want ; planning:open true ; planning:weighs ?w .
    OPTIONAL { ?w planning:spent ?s } OPTIONAL { ?w planning:minted ?m }
    OPTIONAL { ?weighing planning:remaining ?r }
    OPTIONAL { ?weighing planning:late ?lands } }
  OPTIONAL { SELECT ?best ?bestLate ?bestLands WHERE {
    GRAPH $cat { ?y a planning:Weighing ; planning:for $want ; planning:met true ; planning:weighs ?bw .
      ?bw planning:spent ?best
      OPTIONAL { ?y planning:late ?bestLands } }
    BIND(IF(BOUND(?bestLands), 1, 0) AS ?bestLate) }
    ORDER BY ?bestLate ?bestLands ?best LIMIT 1 }
  BIND(COALESCE(?s, 0.0) AS ?spent) BIND(COALESCE(?m, 0) AS ?minted) BIND(COALESCE(?r, 0.0) AS ?remaining)
  BIND(IF(BOUND(?lands), 1, 0) AS ?late) }
ORDER BY ?late ?lands (?spent + ?remaining) ?minted LIMIT 1"#;
const CLOSE_U: &str = r#"
DELETE { GRAPH ?cat { $weighing planning:open ?o } }
INSERT { GRAPH ?cat { $weighing planning:expanded true } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph . $weighing planning:open ?o } }"#;
const CONSTRAINTS_Q: &str = r#"SELECT ?c WHERE { $holder planning:holds ?c . ?c a planning:Constraint } ORDER BY ?c"#;
const REACHED_Q: &str = r#"
SELECT ?w ?marked WHERE { GRAPH $cat { $x planning:weighs ?w . ?w a planning:PossibleGraph .
                                       OPTIONAL { ?w planning:impossible ?marked } } } LIMIT 1"#;
const WEIGHED_IN_Q: &str =
    r#"SELECT ?x WHERE { GRAPH $cat { ?x planning:weighs $world ; planning:for $for } } LIMIT 1"#;
const ROWS_Q: &str = r#"
SELECT ?i ?c ?a ?o WHERE {
  GRAPH $cat { $x planning:violation ?v . ?v planning:instance ?i .
               OPTIONAL { ?v planning:constraint ?c } OPTIONAL { ?v planning:about ?a } OPTIONAL { ?v planning:offending ?o } } }
ORDER BY ?i ?c ?o"#;
const MARK_U: &str = r#"
DELETE { GRAPH ?cat { $weighing planning:open ?o . $weighing planning:met ?m . $weighing planning:remaining ?r .
                      $weighing planning:late ?l . $weighing planning:violation ?v . ?v ?p ?x } }
INSERT { GRAPH ?cat { $world planning:impossible $by } }
WHERE  { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
                      OPTIONAL { $weighing planning:open ?o } OPTIONAL { $weighing planning:met ?m }
                      OPTIONAL { $weighing planning:remaining ?r } OPTIONAL { $weighing planning:late ?l }
                      OPTIONAL { $weighing planning:violation ?v . ?v ?p ?x } } }"#;
const SPENT_Q: &str = r#"
SELECT (COUNT(?x) AS ?used) WHERE {
  GRAPH $cat { ?x a planning:Weighing ; planning:for $want ; planning:weighs ?u .
               FILTER NOT EXISTS { ?u a planning:GroundGraph } } }"#;
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

/// THE CEILING ON WHAT A SEARCH MAY SPEND where the self graph states no `planning:budget`, in candidates weighed.
pub const BUDGET: usize = 32;

/// THE WORLD OF A STORE THAT SCOPED NOTHING.
pub const UNSCOPED: &str = "unscoped";

/// An intention a reconsideration replaced: its head, the want it walked, and the want whose plan replaces it.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Reconsidered {
    pub head: String,
    pub walked: String,
    pub by: String,
}

/// Where one standing intention stands, by the want it pursues.
#[derive(Clone, Debug)]
struct Flight {
    plan: String,
    head: String,
    action: String,
    in_flight: bool,
    ending: bool,
    late: DayTimeDuration,
    landing: DateTime,
    landings: Vec<(String, DateTime)>,
    in_flight_steps: Vec<(String, DateTime, String, String)>,
}

type Flights = BTreeMap<String, Flight>;

/// What one step says: the action it fills and the values of the parameters that action takes.
type Said = (String, Vec<(String, String)>);

/// One agent's planning: the pass, one want's search, and one iteration of it, each a method that sequences the
/// package's acts and reads the store between them. What the Python copy signals, a caller reads off the fields.
pub struct Planner<'a> {
    pub beliefs: &'a Store,
    pub id: String,
    pub uri: String,
    pub budget: usize,
    /// THE PLANNER'S IMAGINARIA, one per scope, kept from pass to pass and refreshed at every `plan`.
    pub imaginaria: BTreeMap<String, Store>,
    /// What the texts a pass evaluates read, remembered while the graphs they live in stand.
    read: Option<(BTreeSet<String>, Option<BTreeSet<String>>)>,
    /// The plans the last pass published, each with its want.
    pub handed: Vec<(String, String)>,
    /// The walking wants the present meets.
    pub reached: BTreeSet<String>,
    /// The heads `check` refused as they were about to be taken.
    pub blocked: Vec<String>,
    /// The intentions a reconsideration replaced, to end after their steps in flight.
    pub superseded: Vec<Reconsidered>,
    /// The step of each walking want after which a world of its plan was last foreseen impossible.
    pub doomed: BTreeMap<String, String>,
    /// The wants a role above planning asked to have reopened, until the next pass reopens them.
    pub asked: BTreeSet<String>,
}

fn strs(names: &[String]) -> Vec<&str> {
    names.iter().map(String::as_str).collect()
}

fn graphs(beliefs: &Store, kinds: &[&str]) -> Result<Vec<String>, Error> {
    beliefs.graphs_of(kinds, &Within::default())
}

fn cat(store: &Store, memo: &mut Memo) -> Result<Value, Error> {
    Ok(Value::Raw(format!("<{}>", catalogue(store, memo)?)))
}

fn later(a: DateTime, b: DateTime) -> DateTime {
    if b > a { b } else { a }
}

fn zero() -> DayTimeDuration {
    DayTimeDuration::new(0)
}

impl<'a> Planner<'a> {
    /// The beliefs, the one identifier a process is told, and how much a search may spend — the agent's stance,
    /// `planning:budget` off its self graph, where the caller hands none, and `BUDGET` where it states none.
    pub fn new(beliefs: &'a Store, agent_id: &str, budget: Option<usize>) -> Result<Self, Error> {
        let budget = match budget {
            Some(b) => b,
            None => stance(beliefs, BUDGET_TERM)?.map_or(BUDGET, |n| n as usize),
        };
        let common = beliefs.graphs_of(&[BELIEF], &Within::common())?;
        let text = format!("SELECT ?a WHERE {{ ?a a orexis:Agent ; orexis:localId \"{agent_id}\" }} LIMIT 1");
        let uri = beliefs
            .rows(&text, &strs(&common))?
            .first()
            .and_then(|r| iri(r, "a"))
            .ok_or_else(|| {
                Error::Evaluation(format!(
                    "no agent with localId '{agent_id}' in this store — was the world loaded before the planner was built?"
                ))
            })?;
        Ok(Planner {
            beliefs,
            id: agent_id.to_string(),
            uri,
            budget,
            imaginaria: BTreeMap::new(),
            read: None,
            handed: Vec::new(),
            reached: BTreeSet::new(),
            blocked: Vec::new(),
            superseded: Vec::new(),
            doomed: BTreeMap::new(),
            asked: BTreeSet::new(),
        })
    }

    // --- the pass ------------------------------------------------------------------------------------------------

    /// One pass: an imaginarium per scope, every desire weighed in every ground, the wants derived, each searched,
    /// and the plans published. The graphs written in the beliefs — the plans published and the wants that keep a
    /// step below.
    pub fn plan(&mut self, at: DateTime) -> Result<Vec<String>, Error> {
        let beliefs = self.beliefs;
        let scopes = find_scopes(beliefs)?
            .ok_or_else(|| Error::Evaluation("the store holds no scope graph — scope_actions has not run".into()))?;
        let walking = self.walking()?;
        self.withdraw_orphaned_refinements(&walking)?;
        let mut written = self.keep_below(at)?;
        let flights = if self.holds_a_constraint()? {
            self.flights(at)?
        } else {
            Flights::new()
        };
        self.handed.clear();
        self.reached.clear();
        self.blocked.clear();
        self.superseded.clear();
        let mut searched = BTreeSet::new();
        let texts: BTreeSet<String> = graphs(beliefs, &[ACTION, DESIRE, WANT, RECORD, SHAPES, CONSTRAINT_GRAPH])?
            .into_iter()
            .collect();
        if self.read.as_ref().is_none_or(|(t, _)| *t != texts) {
            self.read = Some((texts, read_anywhere(beliefs, at)?));
        }
        let read = self.read.as_ref().and_then(|(_, r)| r.clone());
        let mut walking = walking;
        let mut all: Vec<String> = scopes.all().into_iter().collect();
        if all.is_empty() {
            all.push(UNSCOPED.to_string());
        }
        for scope in all {
            let store = match self.imaginaria.remove(&scope) {
                Some(store) => store,
                None => Store::new(Arc::new(beliefs.namespaces().clone()))?,
            };
            let result = self.pass_in(
                &store,
                &scope,
                &scopes,
                read.as_ref(),
                &flights,
                &mut walking,
                &mut searched,
                at,
            );
            self.imaginaria.insert(scope.clone(), store);
            written.extend(result?);
        }
        self.asked.clear();
        Ok(written)
    }

    /// One scope's part of the pass, in its imaginarium; the plans published.
    #[allow(clippy::too_many_arguments)]
    fn pass_in(
        &mut self,
        store: &Store,
        scope: &str,
        scopes: &Scopes,
        read: Option<&BTreeSet<String>>,
        flights: &Flights,
        walking: &mut BTreeSet<String>,
        searched: &mut BTreeSet<String>,
        at: DateTime,
    ) -> Result<Vec<String>, Error> {
        let beliefs = self.beliefs;
        let flights = flights.clone();
        let scope = scope.to_string();
        let unscoped = scope == UNSCOPED;
        {
            let only: Option<BTreeSet<String>> = if unscoped {
                None
            } else {
                let scope_graphs = graphs(beliefs, &[SCOPE_GRAPH])?;
                Some(
                    beliefs
                        .rows(
                            &bind(IN_SCOPE_Q, &[("scope", Value::iri(scope.as_str()))])?,
                            &strs(&scope_graphs),
                        )?
                        .iter()
                        .filter_map(|r| iri(r, "a"))
                        .collect(),
                )
            };
            let elsewhere: BTreeSet<String> = if unscoped {
                BTreeSet::new()
            } else {
                scopes
                    .0
                    .iter()
                    .filter(|(_, ss)| !ss.contains(&scope))
                    .map(|(m, _)| m.clone())
                    .collect()
            };
            prepare_ground(beliefs, store, (!unscoped).then_some(scope.as_str()), Some(scopes))?;
            let mut memo = Memo::default();
            let within: Option<BTreeSet<String>> = read.map(|r| {
                let mut w = r.clone();
                w.extend(
                    scopes
                        .0
                        .iter()
                        .filter(|(_, ss)| ss.contains(&scope))
                        .map(|(m, _)| m.clone()),
                );
                w
            });
            let in_only = |action: &str| only.as_ref().is_none_or(|o| o.contains(action));
            let landings: Vec<DateTime> = flights
                .values()
                .flat_map(|f| f.landings.iter())
                .filter(|(action, _)| in_only(action))
                .map(|(_, lands)| *lands)
                .collect();
            let landed = landed(beliefs, &flights, only.as_ref())?;
            let foreseen: BTreeSet<String> = if flights.is_empty() {
                BTreeSet::new()
            } else {
                store
                    .rows(HASHES_Q, &[])?
                    .iter()
                    .filter_map(|r| value(r, "h"))
                    .collect()
            };
            let laid = lay_ground(
                store,
                at,
                &Laying {
                    within: within.as_ref(),
                    landings: &landings,
                    landed: &landed,
                    actions: only.as_ref(),
                },
            )?;
            let present = laid
                .first()
                .cloned()
                .ok_or_else(|| Error::Evaluation("no ground was laid".into()))?;
            let arrived = !flights.is_empty() && {
                let c = cat(store, &mut memo)?;
                store
                    .rows(&bind(GROUND_HASHES_Q, &[("cat", c)])?, &[])?
                    .iter()
                    .filter_map(|r| value(r, "h"))
                    .any(|h| !foreseen.contains(&h))
            };
            reroot(store, &present)?;
            let constraints = held_constraints(store, &self.uri, only.as_ref(), at, &mut memo)?;
            for constraint in &constraints {
                let broken = broken(store, constraint, &present, &mut memo)?;
                if !broken.is_empty() {
                    log::warn!(
                        "{}: the present violates {}, a constraint of this world, and nothing repairs it: {}",
                        self.id,
                        local_of(constraint),
                        said(&broken)
                    );
                }
            }
            for pair in unweighed(store, None, None, &mut memo)? {
                if !pair.contains_key("from")
                    && let (Some(for_), Some(about)) = (iri(&pair, "for"), iri(&pair, "about"))
                {
                    weigh(store, &for_, &about, &mut memo)?;
                }
            }
            let mut reopen = if arrived && !flights.is_empty() && !constraints.is_empty() {
                self.impossible_ahead(store, &flights, &constraints, only.as_ref(), &mut memo)?
            } else {
                BTreeSet::new()
            };
            reopen.extend(self.asked_here(store, &flights, only.as_ref())?);
            let met_now: BTreeSet<String> = store
                .rows(
                    &bind(
                        MET_NOW_Q,
                        &[("ground", Value::iri(present.as_str())), ("now", instant(at))],
                    )?,
                    &[],
                )?
                .iter()
                .filter_map(|r| iri(r, "for"))
                .collect();
            self.reached.extend(met_now.intersection(walking).cloned());
            let reached: BTreeSet<String> = met_now.difference(walking).cloned().collect();
            let opens: BTreeMap<String, DateTime> = walking
                .iter()
                .map(|w| (w.clone(), flights.get(w).map_or(at, |f| f.landing)))
                .collect();
            let none = BTreeSet::new();
            if !reopen.is_empty() {
                withdraw(store, None, &none, &reopen)?;
            }
            let mut wanted = derive_wants(store, at, &opens, &reopen)?;
            wanted.extend(walking.iter().cloned());
            withdraw(store, Some(&wanted), &reached, &none)?;
            if !reached.is_empty() {
                withdraw(beliefs, None, &reached, &none)?;
            }
            //  THE SHAPES ARE FORGOTTEN AFTER THE DERIVATION, because the derivation WRITES them.
            memo.shapes = None;
            memo.selects.clear();
            let shapes = shapes(store, &mut memo)?;
            let mut kept: BTreeMap<String, Vec<String>> = BTreeMap::new();
            let reopening: BTreeSet<String> = if flights.is_empty() {
                BTreeSet::new()
            } else {
                store
                    .rows(REOPENING_Q, &[])?
                    .iter()
                    .filter_map(|r| iri(r, "w"))
                    .filter(|w| walking.contains(w))
                    .collect()
            };
            for want in of_scope(store, &shapes, &self.uri, &scope, scopes, at)? {
                if walking.contains(&want) && !reopening.contains(&want) {
                    continue;
                }
                let scoped = Searching {
                    only: only.as_ref(),
                    elsewhere: &elsewhere,
                    within: within.as_ref(),
                    at,
                };
                self.search(store, &want, self.budget, &scoped, &mut memo)?;
                searched.insert(want.clone());
                self.reconsider(store, &want, &flights, &mut kept)?;
            }
            let mut unwalked: BTreeSet<String> = walking.clone();
            for w in reopening.intersection(searched) {
                unwalked.remove(w);
            }
            let handed = publish_plan(store, beliefs, &self.uri, &unwalked, &kept)?;
            self.mark_kept(&handed)?;
            for plan in &handed {
                let found = beliefs.rows(&bind(PURSUES_Q, &[("plan", Value::iri(plan.as_str()))])?, &[])?;
                if let Some(want) = found.first().and_then(|r| iri(r, "want")) {
                    self.handed.push((plan.clone(), want));
                }
            }
            *walking = self.walking()?;
            Ok(handed)
        }
    }

    /// Every want this agent is walking: pursued by a standing intention, or by a plan published and not yet adopted.
    pub fn walking(&self) -> Result<BTreeSet<String>, Error> {
        let Some(catalogue) = self.beliefs.catalogue()? else {
            return Ok(BTreeSet::new());
        };
        Ok(self
            .beliefs
            .rows(&bind(WALKING_Q, &[("cat", Value::Raw(format!("<{catalogue}>")))])?, &[])?
            .iter()
            .filter_map(|r| iri(r, "want"))
            .collect())
    }

    /// Give every step an intention stands at that is kept below and has fallen due the want that keeps it.
    fn keep_below(&self, at: DateTime) -> Result<Vec<String>, Error> {
        let mut minted = Vec::new();
        for r in self.beliefs.rows(&bind(KEPT_DUE_Q, &[("now", instant(at))])?, &[])? {
            let Some(step) = iri(&r, "step") else { continue };
            if let Some(want) = refine(self.beliefs, &self.uri, &step, at)? {
                minted.extend(
                    self.beliefs
                        .rows(REFINED_Q, &[])?
                        .iter()
                        .filter(|g| iri(g, "want").as_deref() == Some(want.as_str()))
                        .filter_map(|g| iri(g, "g")),
                );
            }
        }
        Ok(minted)
    }

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
        let beliefs = self.beliefs;
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
        let beliefs = self.beliefs;
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

    // --- commitment: the step in flight, and the triggers that reopen a walking want -------------------------------

    /// Ask that each of `wants` an intention walks be searched again in the next pass.
    pub fn reopen(&mut self, wants: impl IntoIterator<Item = String>) {
        self.asked.extend(wants);
    }

    /// The asked wants a walking plan of this scope pursues, derived here and not ending; each taken from the asked.
    fn asked_here(
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
    fn holds_a_constraint(&self) -> Result<bool, Error> {
        let held = graphs(self.beliefs, &[CONSTRAINT_GRAPH])?;
        Ok(!self
            .beliefs
            .rows(
                &bind(HOLDS_CONSTRAINT_Q, &[("holder", Value::iri(self.uri.as_str()))])?,
                &strs(&held),
            )?
            .is_empty())
    }

    /// Where every standing intention stands, by the want it pursues.
    fn flights(&self, at: DateTime) -> Result<Flights, Error> {
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
    fn impossible_ahead(
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
                .chain(self.beliefs, &flight.plan)?
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
                        quads_of(self.beliefs, row.and_then(|r| iri(r, "retracts")))?,
                        quads_of(self.beliefs, row.and_then(|r| iri(r, "adds")))?,
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
    fn reconsider(
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
            let steps = self.chain(self.beliefs, &flight.plan)?;
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
        }
        Ok(())
    }

    /// The steps of `plan` in `store`, in the order walked, each with the action it fills and its filling.
    fn chain(&self, store: &Store, plan: &str) -> Result<Vec<(String, Said)>, Error> {
        let actions = graphs(self.beliefs, &[ACTION])?;
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
    fn mark_kept(&self, handed: &[String]) -> Result<(), Error> {
        let actions = graphs(self.beliefs, &[ACTION])?;
        for plan in handed {
            for r in self.beliefs.rows(
                &bind(FICTIVE_STEPS_Q, &[("plan", Value::iri(plan.as_str()))])?,
                &strs(&actions),
            )? {
                let Some(step) = iri(&r, "step") else { continue };
                if keeps(self.beliefs, &step)? {
                    self.beliefs.update(&format!(
                        "INSERT DATA {{ GRAPH <{plan}> {{ <{step}> execution:keptBelow true }} }}"
                    ))?;
                }
            }
        }
        Ok(())
    }

    /// A want kept below for a step no intention stands at any more is nothing's: withdrawn, here and everywhere.
    fn withdraw_orphaned_refinements(&self, walking: &BTreeSet<String>) -> Result<(), Error> {
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

    // --- what a runtime asks after a pass ---------------------------------------------------------------------------

    /// Every want that stands after the last pass, across the imaginaria.
    pub fn standing(&self, at: DateTime) -> Result<Vec<String>, Error> {
        let mut out = BTreeSet::new();
        for store in self.imaginaria.values() {
            out.extend(find_wants(store, at, &Finding::default())?);
        }
        Ok(out.into_iter().collect())
    }

    /// Whether the agent holds any desire.
    pub fn holds_a_desire(&self) -> Result<bool, Error> {
        let desires = graphs(self.beliefs, &[DESIRE])?;
        Ok(!self
            .beliefs
            .rows("SELECT ?d WHERE { ?d a planning:Desire } LIMIT 1", &strs(&desires))?
            .is_empty())
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

    /// Write the scopes a pass reads — the boot's act.
    pub fn scope(beliefs: &Store, now: DateTime) -> Result<(), Error> {
        scope_actions(beliefs, now)
    }

    // --- one want ---------------------------------------------------------------------------------------------------

    /// Plan for `want` from the ground holding at its instant, spending at most `budget` candidates beyond what its
    /// search spent before, and write the plan, whatever the search concluded.
    pub fn search(
        &self,
        store: &Store,
        want: &str,
        budget: usize,
        scoped: &Searching<'_>,
        memo: &mut Memo,
    ) -> Result<(), Error> {
        for pair in unweighed(store, Some(want), None, memo)? {
            if !pair.contains_key("from")
                && let Some(about) = iri(&pair, "about")
            {
                weigh(store, want, &about, memo)?;
            }
        }
        let ceiling = spent(store, want, memo)? + budget;
        while let Some(spent) = self.expand(store, want, ceiling, scoped, memo)? {
            if spent >= ceiling {
                break;
            }
        }
        extract_plan(store, want)?;
        Ok(())
    }

    /// Open the top of `want`'s frontier: admit what it admits, take each candidate this want has not yet weighed,
    /// weigh what it reached — for the want and every constraint the scope's actions can write — and close it. What the
    /// search has spent afterwards, or None where there was nothing to open or the cheapest achiever refuses the top.
    pub fn expand(
        &self,
        store: &Store,
        want: &str,
        budget: usize,
        scoped: &Searching<'_>,
        memo: &mut Memo,
    ) -> Result<Option<usize>, Error> {
        let c = cat(store, memo)?;
        let top = store.rows(
            &bind(FRONTIER_Q, &[("want", Value::iri(want)), ("cat", c.clone())])?,
            &[],
        )?;
        let Some(top) = top.into_iter().next() else {
            return Ok(None);
        };
        if beaten(&top)? {
            return Ok(None);
        }
        let world = iri(&top, "w").ok_or_else(|| Error::Evaluation("a frontier row naming no world".into()))?;
        let constraints = held_constraints(store, &self.uri, scoped.only, scoped.at, memo)?;
        let only: Option<HashSet<String>> = scoped.only.map(|o| o.iter().cloned().collect());
        let elsewhere: HashSet<String> = scoped.elsewhere.iter().cloned().collect();
        admit(
            store,
            &world,
            &Scope {
                only: only.as_ref(),
                elsewhere: Some(&elsewhere),
            },
            memo,
        )?;
        let mut used = spent(store, want, memo)?;
        for pair in unweighed(store, Some(want), Some(&world), memo)? {
            if used >= budget {
                return Ok(Some(used));
            }
            let Some(about) = iri(&pair, "about") else { continue };
            if !pair.contains_key("child") {
                take(store, &about, scoped.within, memo)?;
            }
            let weighing = weigh(store, want, &about, memo)?;
            if !constraints.is_empty() {
                self.mark(store, &weighing, &constraints, memo)?;
            }
            used += 1;
        }
        let weighing =
            iri(&top, "weighing").ok_or_else(|| Error::Evaluation("a frontier row naming no weighing".into()))?;
        store.update(&bind(CLOSE_U, &[("weighing", Value::iri(weighing.as_str()))])?)?;
        Ok(Some(used))
    }

    /// Mark the world `weighing` is of impossible where some constraint yields a row there.
    fn mark(&self, store: &Store, weighing: &str, constraints: &[String], memo: &mut Memo) -> Result<(), Error> {
        let c = cat(store, memo)?;
        let reached = store.rows(&bind(REACHED_Q, &[("x", Value::iri(weighing)), ("cat", c)])?, &[])?;
        let Some(r) = reached.first() else { return Ok(()) };
        if r.contains_key("marked") {
            return Ok(());
        }
        let Some(world) = iri(r, "w") else { return Ok(()) };
        for constraint in constraints {
            let rows = broken(store, constraint, &world, memo)?;
            if !rows.is_empty() {
                store.update(&bind(
                    MARK_U,
                    &[
                        ("weighing", Value::iri(weighing)),
                        ("world", Value::iri(world.as_str())),
                        ("by", Value::iri(constraint.as_str())),
                    ],
                )?)?;
                log::info!(
                    "{}: {} is impossible — it violates {}: {}",
                    self.id,
                    world.rsplit('/').next().unwrap_or(&world),
                    local_of(constraint),
                    said(&rows)
                );
            }
        }
        Ok(())
    }

    /// Every constraint this agent holds that its present violates, as (constraint, rows), asked of a throwaway
    /// imaginarium over the whole store. Writes nothing to the beliefs.
    pub fn contradictions(&self, at: DateTime) -> Result<Vec<(String, BTreeSet<Violation>)>, Error> {
        let scopes = find_scopes(self.beliefs)?
            .ok_or_else(|| Error::Evaluation("the store holds no scope graph — scope_actions has not run".into()))?;
        let store = Store::new(Arc::new(self.beliefs.namespaces().clone()))?;
        let mut memo = Memo::default();
        prepare_ground(self.beliefs, &store, None, Some(&scopes))?;
        let laid = lay_ground(&store, at, &Laying::default())?;
        let present = laid
            .first()
            .cloned()
            .ok_or_else(|| Error::Evaluation("no ground was laid".into()))?;
        let held = graphs(&store, &[CONSTRAINT_GRAPH])?;
        let constraints: Vec<String> = store
            .rows(
                &bind(CONSTRAINTS_Q, &[("holder", Value::iri(self.uri.as_str()))])?,
                &strs(&held),
            )?
            .iter()
            .filter_map(|r| iri(r, "c"))
            .collect();
        let mut out = Vec::new();
        for c in constraints {
            let rows = broken(&store, &c, &present, &mut memo)?;
            if !rows.is_empty() {
                out.push((c, rows));
            }
        }
        Ok(out)
    }
}

/// What a search is scoped to: the scope's actions, the terms that are another scope's, what a world is hashed
/// within, and the pass's instant.
pub struct Searching<'s> {
    pub only: Option<&'s BTreeSet<String>>,
    pub elsewhere: &'s BTreeSet<String>,
    pub within: Option<&'s BTreeSet<String>>,
    pub at: DateTime,
}

/// One way a world violates a constraint: (instance, constraint, about, offending).
pub type Violation = (String, Option<String>, Option<String>, Option<String>);

const SCRATCH: &str = "urn:orexis:world";

/// Every quad of `graph` — none where no graph is named.
fn quads_of(store: &Store, graph: Option<String>) -> Result<Vec<Quad>, Error> {
    match graph {
        Some(g) => store.quads(&g),
        None => Ok(Vec::new()),
    }
}

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

/// The rows of a violated constraint as one line of the log.
fn said(broken: &BTreeSet<Violation>) -> String {
    broken
        .iter()
        .map(|(i, c, _, o)| {
            let o = o.as_deref().map_or("None".to_string(), |o| {
                if o.contains('#') { local_of(o) } else { o.to_string() }
            });
            format!("({}, {}, {o})", local_of(i), c.as_deref().unwrap_or("None"))
        })
        .collect::<Vec<_>>()
        .join(", ")
}

/// Whether the cheapest achiever found refuses the top of the frontier, by the order the frontier keeps.
fn beaten(top: &orexis::store::Row) -> Result<bool, Error> {
    let Some(best) = value(top, "best") else {
        return Ok(false);
    };
    let number = |k: &str| value(top, k).and_then(|v| v.parse::<f64>().ok()).unwrap_or(0.0);
    let (late, best_late) = (number("late") as i64, number("bestLate") as i64);
    if late != best_late {
        return Ok(late > best_late);
    }
    if late != 0 && value(top, "lands") != value(top, "bestLands") {
        let (lands, best_lands) = (top.get("lands"), top.get("bestLands"));
        if let (Some(l), Some(b)) = (lands, best_lands) {
            return Ok(lexical(l)? > lexical(b)?);
        }
    }
    Ok(number("spent") + number("remaining") >= best.parse::<f64>().unwrap_or(0.0))
}

/// What a want's search has spent: every weighing for it but a ground's.
fn spent(store: &Store, want: &str, memo: &mut Memo) -> Result<usize, Error> {
    let c = cat(store, memo)?;
    Ok(store
        .rows(&bind(SPENT_Q, &[("want", Value::iri(want)), ("cat", c)])?, &[])?
        .first()
        .and_then(|r| value(r, "used"))
        .and_then(|n| n.parse().ok())
        .unwrap_or(0))
}

/// A figure the self states of itself in its self graph, or None where it states none or several.
fn stance(store: &Store, term: &str) -> Result<Option<f64>, Error> {
    let selves = graphs(store, &[SELF_GRAPH])?;
    let found = store.rows(
        &bind(
            "SELECT ?n WHERE { ?me a orexis:Self ; $stance ?n }",
            &[("stance", Value::iri(term))],
        )?,
        &strs(&selves),
    )?;
    if found.len() != 1 {
        if !found.is_empty() {
            log::warn!(
                "the self states {} figures for {}: the default holds",
                found.len(),
                local_of(term)
            );
        }
        return Ok(None);
    }
    Ok(value(&found[0], "n").and_then(|n| n.parse().ok()))
}

/// Every predicate a text a pass evaluates reads or writes — what a world is hashed within; None for anything.
fn read_anywhere(beliefs: &Store, at: DateTime) -> Result<Option<BTreeSet<String>>, Error> {
    let mut out = BTreeSet::new();
    for (reads, writes) in actions_of(beliefs, at)?.into_values() {
        let (Some(reads), Some(writes)) = (reads, writes) else {
            return Ok(None);
        };
        out.extend(reads);
        out.extend(writes);
    }
    let held = graphs(beliefs, &[DESIRE, WANT, RECORD, SHAPES, CONSTRAINT_GRAPH])?;
    let shapes = Shapes::of(beliefs, &held)?;
    for term in ["metWhen", "unmetWhen", "estimates"] {
        let predicate = format!("{PLANNING}{term}");
        let mut nodes: Vec<Term> = Vec::new();
        for (_, p, o) in shapes.triples() {
            if p.as_str() == predicate && !nodes.contains(&o) {
                nodes.push(o);
            }
        }
        for node in nodes {
            match reads_of_shape(beliefs, &shapes, &node) {
                Some(reads) => out.extend(reads),
                None => return Ok(None),
            }
        }
    }
    Ok(Some(out))
}

/// The constraints `holder` holds that a search among the actions `only` must hold its worlds to, once a pass.
fn held_constraints(
    store: &Store,
    holder: &str,
    only: Option<&BTreeSet<String>>,
    at: DateTime,
    memo: &mut Memo,
) -> Result<Vec<String>, Error> {
    if let Some(known) = &memo.constraints {
        return Ok(known.clone());
    }
    let held = graphs(store, &[CONSTRAINT_GRAPH])?;
    let found: Vec<String> = store
        .rows(&bind(CONSTRAINTS_Q, &[("holder", Value::iri(holder))])?, &strs(&held))?
        .iter()
        .filter_map(|r| iri(r, "c"))
        .collect();
    let mut out = Vec::new();
    if !found.is_empty() {
        let mut writes: Option<BTreeSet<String>> = Some(BTreeSet::new());
        for (action, (_, written)) in actions_of(store, at)? {
            if only.is_some_and(|o| !o.contains(&action)) {
                continue;
            }
            match (written, writes.as_mut()) {
                (Some(w), Some(all)) => all.extend(w),
                _ => {
                    writes = None;
                    break;
                }
            }
        }
        let shapes = shapes(store, memo)?;
        for c in found {
            let node: Term = NamedNode::new_unchecked(c.clone()).into();
            let test = shapes
                .value(&node, &format!("{PLANNING}metWhen"))
                .or_else(|| shapes.value(&node, &format!("{PLANNING}unmetWhen")));
            let reads = match &test {
                Some(t) => reads_of_shape(store, &shapes, t),
                None => Some(BTreeSet::new()),
            };
            let kept = match (&writes, &reads) {
                (None, _) | (_, None) => true,
                (Some(w), Some(r)) => r.iter().any(|p| w.contains(p)),
            };
            if kept {
                out.push(c);
            }
        }
    }
    memo.constraints = Some(out.clone());
    Ok(out)
}

/// The ways `world` violates `constraint`, off its weighing there — weighing it first where no pass has.
fn broken(store: &Store, constraint: &str, world: &str, memo: &mut Memo) -> Result<BTreeSet<Violation>, Error> {
    let key = (constraint.to_string(), world.to_string());
    if let Some(known) = memo.broken.get(&key) {
        return Ok(known.clone());
    }
    let c = cat(store, memo)?;
    let found = store.rows(
        &bind(
            WEIGHED_IN_Q,
            &[
                ("world", Value::iri(world)),
                ("cat", c.clone()),
                ("for", Value::iri(constraint)),
            ],
        )?,
        &[],
    )?;
    let node = match found.first().and_then(|r| iri(r, "x")) {
        Some(x) => x,
        None => weigh(store, constraint, world, memo)?,
    };
    let rows: BTreeSet<Violation> = store
        .rows(&bind(ROWS_Q, &[("x", Value::iri(node.as_str())), ("cat", c)])?, &[])?
        .iter()
        .filter_map(|r| Some((value(r, "i")?, value(r, "c"), value(r, "a"), value(r, "o"))))
        .collect();
    memo.broken.insert(key, rows.clone());
    Ok(rows)
}

/// What each step in flight of this scope changes where it lands, off the published plan.
fn landed(beliefs: &Store, flights: &Flights, only: Option<&BTreeSet<String>>) -> Result<Vec<Landed>, Error> {
    let mut out = Vec::new();
    for flight in flights.values() {
        for (action, lands, plan, step) in &flight.in_flight_steps {
            if only.is_some_and(|o| !o.contains(action)) {
                continue;
            }
            let found = beliefs.rows(&bind(PREDICTS_Q, &[("plan", Value::iri(plan.as_str()))])?, &[])?;
            let said = found.iter().find(|r| iri(r, "step").as_deref() == Some(step.as_str()));
            let triples = |side: &str| -> Result<Vec<Triple>, Error> {
                Ok(quads_of(beliefs, said.and_then(|r| iri(r, side)))?
                    .into_iter()
                    .map(|q| Triple::new(q.subject, q.predicate, q.object))
                    .collect())
            };
            let (retracts, adds) = (triples("retracts")?, triples("adds")?);
            if !retracts.is_empty() || !adds.is_empty() {
                out.push(Landed {
                    at: *lands,
                    retracts,
                    adds,
                });
            }
        }
    }
    Ok(out)
}

/// The wants this imaginarium is the world for: placed by what their met-tests read that some action can change,
/// and by the terms they name where the predicates leave a tie; one it cannot read joins the first scope.
fn of_scope(
    store: &Store,
    shapes: &Shapes,
    holder: &str,
    scope: &str,
    scopes: &Scopes,
    at: DateTime,
) -> Result<Vec<String>, Error> {
    let all: Vec<String> = scopes.all().into_iter().collect();
    let first = all.first().cloned().unwrap_or_else(|| UNSCOPED.to_string());
    let written = written(store, at)?;
    let mut instants = vec![at];
    for r in store.rows(GROUND_STARTS_Q, &[])? {
        if let Some(s) = r.get("s") {
            instants.push(lexical(s)?);
        }
    }
    let mut found: Vec<String> = Vec::new();
    for instant in instants {
        for w in find_wants(
            store,
            instant,
            &Finding {
                holder: Some(holder),
                ..Finding::default()
            },
        )? {
            if !found.contains(&w) {
                found.push(w);
            }
        }
    }
    let mut mine = Vec::new();
    for want in found {
        let node: Term = NamedNode::new_unchecked(want.clone()).into();
        let met = shapes
            .value(&node, &format!("{PLANNING}metWhen"))
            .or_else(|| shapes.value(&node, &format!("{PLANNING}unmetWhen")));
        let reads = met.as_ref().and_then(|m| reads_of_shape(store, shapes, m));
        let Some(reads) = reads else {
            if scope == first {
                mine.push(want);
            }
            continue;
        };
        let changeable: Vec<&String> = {
            let c: Vec<&String> = reads.iter().filter(|p| written.contains(*p)).collect();
            if c.is_empty() { reads.iter().collect() } else { c }
        };
        let mut placed = scopes.meet(changeable.iter().map(|p| p.as_str()));
        if placed.len() != 1 {
            let mut terms = met.as_ref().map(|m| terms_of_shape(shapes, m)).unwrap_or_default();
            terms.extend(
                shapes
                    .objects(&node, &format!("{PLANNING}keyedBy"))
                    .iter()
                    .filter_map(|t| match t {
                        Term::NamedNode(n) => Some(n.as_str().to_string()),
                        _ => None,
                    }),
            );
            let narrowed = scopes.meet(terms.iter().map(String::as_str));
            let both: BTreeSet<String> = placed.intersection(&narrowed).cloned().collect();
            placed = if !both.is_empty() {
                both
            } else if !placed.is_empty() {
                placed
            } else {
                narrowed
            };
        }
        let reached: Vec<&String> = placed.iter().collect();
        if reached.first().map(|s| s.as_str()) == Some(scope) || (reached.is_empty() && scope == first) {
            mine.push(want);
        }
    }
    Ok(mine)
}

#[cfg(test)]
mod tests;
