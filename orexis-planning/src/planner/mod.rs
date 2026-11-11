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
//! WHAT A PASS SAYS IT DID is on the fields a caller reads — `handed`, `reached`, `blocked`, `superseded`, `published`
//! — for the executor it is linked to, and in the events said to whoever watches the agent (`events`), with the pass's
//! laps, where somebody does.

mod check;
mod kept;
mod reconsider;
mod search;

use std::collections::{BTreeMap, BTreeSet};
use std::sync::{Arc, Mutex};
use std::time::Instant;

use oxigraph::model::{NamedNode, Quad, Term, Triple};
use oxsdatatypes::{DateTime, DayTimeDuration};

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::events::{Laps, Watch, round6};
use orexis::foresight::{Foresees, Foresight};
use orexis::ontology::{ACTION, BELIEF, RECORD};
use orexis::store::{Store, Within, instant, iri, value};

use crate::admit::local_of;
use crate::derive_wants::derive_wants;
use crate::events::{Imagined, PlanPublished, Planned, Rerooted, SearchEnded, WantUnreachable};
use crate::find_scopes::{Scopes, find_scopes};
use crate::find_wants::{Finding, find_wants};
use crate::footprint::{actions_of, reads_of_shape, terms_of_shape, written};
use crate::lay_ground::{Landed, Laying, lay_ground, lay_ground_foreseeing};
use crate::memo::Memo;
use crate::ontology::{BUDGET_TERM, CONSTRAINT_GRAPH, DESIRE, PLANNING, SCOPE_GRAPH, SHAPES, WANT};
use crate::prepare_ground::prepare_ground;
use crate::publish_plan::publish_plan;
use crate::refine::refine;
use crate::reroot::reroot;
use crate::scope_actions::scope_actions;
use crate::shapes::Shapes;
use crate::unweighed::unweighed;
use crate::weigh::{shapes, weigh};
use crate::withdraw::withdraw;
use crate::world_at::{catalogue, lexical};

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

const REOPENING_Q: &str = r#"
SELECT ?w WHERE { GRAPH ?g { ?w planning:reopens ?w }
  FILTER NOT EXISTS { GRAPH ?p { ?p a planning:Plan ; planning:for ?w ; planning:outcome planning:Satisfied } } }"#;

const GROUND_HASHES_Q: &str = r#"SELECT ?h WHERE { GRAPH $cat { ?g a planning:GroundGraph ; orexis:hash ?h } }"#;

const HASHES_Q: &str = r#"SELECT DISTINCT ?h WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w orexis:hash ?h .
  { ?w a planning:GroundGraph } UNION { ?w a planning:PossibleGraph } } }"#;

const PREDICTS_Q: &str = r#"
SELECT ?step ?lands ?adds ?retracts WHERE { GRAPH $plan { ?step a execution:Step .
  OPTIONAL { ?step execution:landsAt ?lands } OPTIONAL { ?step execution:adds ?adds }
  OPTIONAL { ?step execution:retracts ?retracts } } }"#;

const KEPT_DUE_Q: &str = r#"
SELECT ?step WHERE {
  GRAPH ?g { ?i a execution:Intention ; execution:by ?step ; execution:adopts ?plan .
             FILTER NOT EXISTS { ?i execution:resolvedAt ?done } }
  GRAPH ?plan { ?step execution:keptBelow true .
                OPTIONAL { ?step execution:notBefore ?due } }
  FILTER(!BOUND(?due) || ?due <= $now)
  FILTER NOT EXISTS { GRAPH ?h { ?step execution:keptBy ?w } } }
ORDER BY ?step"#;

const MET_NOW_Q: &str = r#"
SELECT DISTINCT ?for WHERE {
  GRAPH ?cat { ?x planning:weighs $ground ; planning:for ?for ; planning:met true .
               ?cat a orexis:CatalogueGraph .
               ?d a planning:WantGraph . OPTIONAL { ?d dcterms:temporal/orexis:start ?ws } }
  GRAPH ?d { ?for a planning:Want }
  FILTER(!BOUND(?ws) || ?ws <= $now) }"#;

const GROUND_STARTS_Q: &str = r#"
SELECT ?s WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a planning:GroundGraph ; dcterms:temporal/orexis:start ?s } }
ORDER BY ?s"#;

const PURSUES_Q: &str = r#"SELECT ?want WHERE { GRAPH ?g { $plan execution:pursues ?want } } LIMIT 1"#;

/// WHAT IS SAID OF A SEARCH AND A PLAN, as the Python Planner reads it for its events: how the want's search ended and
/// what its plan spent, the desire it was derived under, what its estimate said was left at the present ground, and
/// how many intentions pursued it before.
const PLAN_OF_Q: &str = r#"
SELECT ?outcome ?spent WHERE { GRAPH ?g { ?p a planning:Plan ; planning:for $want ; planning:outcome ?outcome .
  OPTIONAL { ?p planning:spent ?spent } } } LIMIT 1"#;
const DESIRE_OF_Q: &str = r#"SELECT ?d WHERE { GRAPH ?g { $want a planning:Want ; prov:wasDerivedFrom ?d } } LIMIT 1"#;
const ESTIMATE_Q: &str = r#"
SELECT ?remaining WHERE { GRAPH $cat { ?x planning:weighs $ground ; planning:for $want ; planning:remaining ?remaining } } LIMIT 1"#;
const PURSUERS_Q: &str =
    r#"SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE { GRAPH ?g { ?i a execution:Intention ; execution:pursues $want } }"#;

/// WHAT AN IMAGINARIUM HOLDS: its possible worlds and the weighings of them, of those how many are on a frontier and
/// how many met their want; and its plans, by why each search ended — counted by OPTIONAL rows inside the catalogue,
/// as the Python Planner counts them.
const IMAGINED_Q: &str = r#"
SELECT ?worlds ?weighings ?open ?met WHERE {
  { SELECT (COUNT(?w) AS ?worlds) WHERE { GRAPH $cat { ?w a planning:PossibleGraph } } }
  { SELECT (COUNT(?x) AS ?weighings) (COUNT(?o) AS ?open) (COUNT(?m) AS ?met) WHERE {
      GRAPH $cat { ?x a planning:Weighing .
                   OPTIONAL { ?x planning:open true BIND(?x AS ?o) }
                   OPTIONAL { ?x planning:met true BIND(?x AS ?m) } } } } }"#;
const PLANS_HELD_Q: &str = r#"
SELECT (SUM(IF(?outcome = planning:Satisfied, 1, 0)) AS ?satisfied)
       (SUM(IF(?outcome = planning:Exhausted, 1, 0)) AS ?exhausted)
       (SUM(IF(?outcome = planning:NoCandidate, 1, 0)) AS ?noCandidate)
WHERE { GRAPH ?plan { ?p a planning:Plan ; planning:outcome ?outcome } }"#;

const CONSTRAINTS_Q: &str = r#"SELECT ?c WHERE { $holder planning:holds ?c . ?c a planning:Constraint } ORDER BY ?c"#;

const WEIGHED_IN_Q: &str =
    r#"SELECT ?x WHERE { GRAPH $cat { ?x planning:weighs $world ; planning:for $for } } LIMIT 1"#;

const ROWS_Q: &str = r#"
SELECT ?i ?c ?a ?o WHERE {
  GRAPH $cat { $x planning:violation ?v . ?v planning:instance ?i .
               OPTIONAL { ?v planning:constraint ?c } OPTIONAL { ?v planning:about ?a } OPTIONAL { ?v planning:offending ?o } } }
ORDER BY ?i ?c ?o"#;

const SPENT_Q: &str = r#"
SELECT (COUNT(?x) AS ?used) WHERE {
  GRAPH $cat { ?x a planning:Weighing ; planning:for $want ; planning:weighs ?u .
               FILTER NOT EXISTS { ?u a planning:GroundGraph } } }"#;

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
pub struct Planner {
    pub beliefs: Store,
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
    /// Which of the four each scope's present was in the last pass, as the Python Planner's `rerooted` says it.
    pub rerooted: Vec<&'static str>,
    /// The heads `check` refused as they were about to be taken.
    pub blocked: Vec<String>,
    /// The intentions a reconsideration replaced, to end after their steps in flight.
    pub superseded: Vec<Reconsidered>,
    /// The step of each walking want after which a world of its plan was last foreseen impossible.
    pub doomed: BTreeMap<String, String>,
    /// The wants a role above planning asked to have reopened, until the next pass reopens them.
    pub asked: BTreeSet<String>,
    /// THE PREDICTOR'S FORESIGHT, where the agent plays one: taken at link and asked at every pass, never imported.
    pub foresee: Option<Foresees>,
    /// The plans the last pass published, said whole with the desire each want was derived under.
    pub published: Vec<PlanPublished>,
    /// Whoever watches the agent.
    pub watch: Watch,
    /// How long each part of the pass in progress took, where anybody watches.
    laps: Option<Laps>,
    /// Each want searched and not yet published: when it was first searched, and in how many passes.
    searches: Mutex<BTreeMap<String, (Instant, usize)>>,
}

impl Planner {
    /// What the texts the last pass evaluated read, None where one of them could read anything.
    pub fn read(&self) -> Option<&BTreeSet<String>> {
        self.read.as_ref().and_then(|(_, r)| r.as_ref())
    }
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

/// What a search is scoped to: the scope's actions, the terms that are another scope's, what a world is hashed
/// within, and the pass's instant.
pub struct Searching<'s> {
    /// The scope searched in, for what is said of the search.
    pub scope: Option<&'s str>,
    pub only: Option<&'s BTreeSet<String>>,
    pub elsewhere: &'s BTreeSet<String>,
    pub within: Option<&'s BTreeSet<String>>,
    pub at: DateTime,
}

/// One way a world violates a constraint: (instance, constraint, about, offending).
pub type Violation = (String, Option<String>, Option<String>, Option<String>);

/// Every quad of `graph` — none where no graph is named.
fn quads_of(store: &Store, graph: Option<String>) -> Result<Vec<Quad>, Error> {
    match graph {
        Some(g) => store.quads(&g),
        None => Ok(Vec::new()),
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
/// The local name of the desire `want` was derived under in `store`, or None — for a want the world authored, or a
/// step kept below.
fn desire_of(store: &Store, want: &str) -> Result<Option<String>, Error> {
    Ok(derived_from(store, want)?.map(|d| local_of(&d)))
}

/// The desire `want` was derived under in `store`, or None.
fn derived_from(store: &Store, want: &str) -> Result<Option<String>, Error> {
    Ok(store
        .rows(&bind(DESIRE_OF_Q, &[("want", Value::iri(want))])?, &[])?
        .first()
        .and_then(|r| iri(r, "d")))
}

/// What the imaginarium of `scope` holds now.
fn imagined(store: &Store, scope: &str, memo: &mut Memo) -> Result<Imagined, Error> {
    let cone = store.rows(&bind(IMAGINED_Q, &[("cat", cat(store, memo)?)])?, &[])?;
    let held = store.rows(PLANS_HELD_Q, &[])?;
    let number = |rows: &[orexis::store::Row], key: &str| -> i64 {
        rows.first()
            .and_then(|r| value(r, key))
            .and_then(|v| v.parse().ok())
            .unwrap_or(0)
    };
    Ok(Imagined {
        scope: local_of(scope),
        worlds: number(&cone, "worlds"),
        weighings: number(&cone, "weighings"),
        open: number(&cone, "open"),
        met: number(&cone, "met"),
        satisfied: number(&held, "satisfied"),
        exhausted: number(&held, "exhausted"),
        no_candidate: number(&held, "noCandidate"),
    })
}

fn spent(store: &Store, want: &str, memo: &mut Memo) -> Result<usize, Error> {
    let c = cat(store, memo)?;
    Ok(store
        .rows(&bind(SPENT_Q, &[("want", Value::iri(want)), ("cat", c)])?, &[])?
        .first()
        .and_then(|r| value(r, "used"))
        .and_then(|n| n.parse().ok())
        .unwrap_or(0))
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

/// THE EARLIEST GROUND BEGINNING AFTER `$at`, off an imaginarium's catalogue.
const NEXT_GROUND_Q: &str = "SELECT (MIN(?start) AS ?start) WHERE { GRAPH $cat {
  ?g a planning:GroundGraph ; dcterms:temporal ?period . ?period orexis:start ?start . FILTER (?start > $at) } }";

impl Planner {
    /// The beliefs, the one identifier a process is told, and how much a search may spend — the agent's stance,
    /// `planning:budget` off its self graph, where the caller hands none, and `BUDGET` where it states none.
    pub fn new(beliefs: &Store, agent_id: &str, budget: Option<usize>) -> Result<Self, Error> {
        let budget = match budget {
            Some(b) => b,
            None => orexis::stance::stance(beliefs, BUDGET_TERM)?.map_or(BUDGET, |n| n as usize),
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
            beliefs: beliefs.clone(),
            id: agent_id.to_string(),
            uri,
            budget,
            imaginaria: BTreeMap::new(),
            read: None,
            handed: Vec::new(),
            reached: BTreeSet::new(),
            rerooted: Vec::new(),
            published: Vec::new(),
            watch: Watch::default(),
            laps: None,
            searches: Mutex::new(BTreeMap::new()),
            blocked: Vec::new(),
            superseded: Vec::new(),
            doomed: BTreeMap::new(),
            asked: BTreeSet::new(),
            foresee: None,
        })
    }

    /// One pass: an imaginarium per scope, every desire weighed in every ground, the wants derived, each searched,
    /// and the plans published. The graphs written in the beliefs — the plans published and the wants that keep a
    /// step below.
    pub fn plan(&mut self, at: DateTime) -> Result<Vec<String>, Error> {
        let beliefs = &self.beliefs.clone();
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
        self.rerooted.clear();
        self.blocked.clear();
        self.superseded.clear();
        self.published.clear();
        //  HOW LONG EACH PART OF THE PASS TOOK, where anybody watches: real seconds, never the agent's.
        self.laps = self.watch.connected().then(Laps::default);
        let mut searched = BTreeSet::new();
        let texts: BTreeSet<String> = graphs(beliefs, &[ACTION, DESIRE, WANT, RECORD, SHAPES, CONSTRAINT_GRAPH])?
            .into_iter()
            .collect();
        if self.read.as_ref().is_none_or(|(t, _)| *t != texts) {
            self.read = Some((texts, read_anywhere(beliefs, at)?));
        }
        let read = self.read.as_ref().and_then(|(_, r)| r.clone());
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
                &walking,
                &mut searched,
                at,
            );
            self.imaginaria.insert(scope.clone(), store);
            written.extend(result?);
        }
        self.asked.clear();
        //  A WANT NO LONGER SEARCHED — reached, withdrawn, or walked — takes its tally with it.
        self.searches.lock().unwrap().retain(|w, _| searched.contains(w));
        if let Some(laps) = self.laps.take() {
            self.watch.emit(&Planned {
                wants: Some(searched.len() as f64),
                laps: laps.spent,
            });
        }
        Ok(written)
    }

    /// One scope's part of the pass, in its imaginarium; the plans published. NOTHING ANOTHER SCOPE DID THIS PASS IS
    /// READ HERE: no action of one writes a fact a want of another reads, so what is walking is as the pass began.
    #[allow(clippy::too_many_arguments)]
    fn pass_in(
        &mut self,
        store: &Store,
        scope: &str,
        scopes: &Scopes,
        read: Option<&BTreeSet<String>>,
        flights: &Flights,
        walking: &BTreeSet<String>,
        searched: &mut BTreeSet<String>,
        at: DateTime,
    ) -> Result<Vec<String>, Error> {
        let beliefs = &self.beliefs.clone();
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
            //  AND WHAT MOVES FROM EACH GROUND: the flows, integrated by the predictor's foresight as the grounds are
            //  laid (#1000) — every key advanced, and a crossing laid here where the key is this scope's, as a reading
            //  is placed: the scopes its feature and property meet in, or every scope where none.
            let placed = |feature: &str, property: &str| {
                let met = scopes.meet([feature, property]);
                met.is_empty() || met.contains(scope.as_str())
            };
            let mut foresight = match &self.foresee {
                Some(foresee) => foresee(beliefs, at, if unscoped { None } else { Some(&placed) })?,
                None => None,
            };
            let laid = lay_ground_foreseeing(
                store,
                at,
                &Laying {
                    within: within.as_ref(),
                    landings: &landings,
                    landed: &landed,
                    actions: only.as_ref(),
                },
                foresight.as_mut().map(|f| f.as_mut() as &mut dyn Foresight),
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
            let rerooting = reroot(store, &present)?;
            self.rerooted.push(rerooting.present);
            if self.watch.connected() {
                self.watch.emit(&Rerooted {
                    scope: local_of(&scope),
                    present: rerooting.present.to_string(),
                    kept: Some(rerooting.kept.len() as f64),
                    dropped: Some(rerooting.dropped.len() as f64),
                });
            }
            self.lap("ground");
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
            self.lap("weigh");
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
            for met in met_now.intersection(walking) {
                if self.reached.insert(met.clone()) && self.watch.connected() {
                    self.watch.emit(&crate::events::WantReached { want: met.clone(), at });
                }
            }
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
            self.lap("derive");
            //  THE SHAPES ARE FORGOTTEN AFTER THE DERIVATION, because the derivation WRITES them.
            memo.shapes = None;
            memo.selects.clear();
            let shapes = shapes(store, &mut memo)?;
            let mut kept: BTreeMap<String, Vec<String>> = BTreeMap::new();
            let mut here = BTreeSet::new();
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
                    scope: Some(scope.as_str()),
                    only: only.as_ref(),
                    elsewhere: &elsewhere,
                    within: within.as_ref(),
                    at,
                };
                self.search(store, &want, self.budget, &scoped, &mut memo)?;
                here.insert(want.clone());
                self.reconsider(store, &want, &flights, &mut kept)?;
            }
            self.lap("search");
            let mut unwalked: BTreeSet<String> = walking.clone();
            for w in reopening.intersection(&here) {
                unwalked.remove(w);
            }
            searched.extend(here);
            let handed = publish_plan(store, beliefs, &self.uri, &unwalked, &kept)?;
            self.mark_kept(&handed)?;
            let published = self.said_published(store, &handed, &present, &scope, &mut memo, at)?;
            self.lap("publish");
            for event in published {
                self.handed.push((event.plan.clone(), event.want.clone()));
                if self.watch.connected() {
                    self.watch.emit(&event);
                }
                self.published.push(event);
            }
            if self.watch.connected() {
                let imagined = imagined(store, &scope, &mut memo)?;
                self.watch.emit(&imagined);
            }
            Ok(handed)
        }
    }

    /// Mark the end of a part of the pass, where anybody watches.
    fn lap(&mut self, part: &str) {
        if let Some(laps) = self.laps.as_mut() {
            laps.lap(part);
        }
    }

    /// What is said of each plan this pass published from `store` at `at`: the want it pursues, the tally of the want's
    /// searches, which goes with it, what the want's estimate said was left at the `present` ground against what the
    /// plan spent, whether an intention pursued the want before — a replan — and its plan graph's triples.
    fn said_published(
        &self,
        store: &Store,
        handed: &[String],
        present: &str,
        scope: &str,
        memo: &mut Memo,
        at: DateTime,
    ) -> Result<Vec<PlanPublished>, Error> {
        let beliefs = &self.beliefs;
        let mut out = Vec::new();
        for plan in handed {
            let found = beliefs.rows(&bind(PURSUES_Q, &[("plan", Value::iri(plan.as_str()))])?, &[])?;
            let Some(want) = found.first().and_then(|r| iri(r, "want")) else {
                continue;
            };
            let tally = self.searches.lock().unwrap().remove(&want);
            let spent_by = store
                .rows(&bind(PLAN_OF_Q, &[("want", Value::iri(want.as_str()))])?, &[])?
                .first()
                .and_then(|r| value(r, "spent"))
                .and_then(|v| v.parse::<f64>().ok());
            let estimate = store
                .rows(
                    &bind(
                        ESTIMATE_Q,
                        &[
                            ("want", Value::iri(want.as_str())),
                            ("ground", Value::iri(present)),
                            ("cat", cat(store, memo)?),
                        ],
                    )?,
                    &[],
                )?
                .first()
                .and_then(|r| value(r, "remaining"))
                .and_then(|v| v.parse::<f64>().ok());
            let pursued: i64 = beliefs
                .rows(&bind(PURSUERS_Q, &[("want", Value::iri(want.as_str()))])?, &[])?
                .first()
                .and_then(|r| value(r, "n"))
                .and_then(|v| v.parse().ok())
                .unwrap_or(0);
            let said: Vec<Triple> = match NamedNode::new(plan.as_str()) {
                Ok(graph) => beliefs
                    .engine()
                    .quads_for_pattern(None, None, None, Some(graph.as_ref().into()))
                    .flatten()
                    .map(|q| Triple::new(q.subject, q.predicate, q.object))
                    .collect(),
                Err(_) => Vec::new(),
            };
            out.push(PlanPublished {
                plan: plan.clone(),
                desire: desire_of(store, &want)?,
                derived_from: derived_from(store, &want)?,
                scope: Some(local_of(scope)),
                passes: Some(tally.map_or(0, |(_, n)| n) as f64),
                weighed: Some(spent(store, &want, memo)? as f64),
                wall_s: tally.map(|(first, _)| round6(first.elapsed().as_secs_f64())),
                estimate,
                cost: spent_by,
                replan: pursued > 0,
                at: Some(at),
                said,
                want,
            });
        }
        Ok(out)
    }

    /// Say that nothing this agent holds reaches `wants`, each by the desire it was derived under.
    pub fn unreachable(&self, wants: &[String], at: DateTime) -> Result<(), Error> {
        if !self.watch.connected() {
            return Ok(());
        }
        for want in wants {
            let mut desire = None;
            for store in self.imaginaria.values() {
                if let Some(d) = desire_of(store, want)? {
                    desire = Some(d);
                    break;
                }
            }
            self.watch.emit(&WantUnreachable {
                want: want.clone(),
                desire,
                at: Some(at),
            });
        }
        Ok(())
    }

    /// Tally a search of `want` begun at `started`, and say how it ended where anybody watches.
    pub(crate) fn searched(
        &self,
        store: &Store,
        want: &str,
        started: Instant,
        budget: usize,
        weighed: usize,
        scope: Option<&str>,
    ) -> Result<(), Error> {
        self.searches
            .lock()
            .unwrap()
            .entry(want.to_string())
            .or_insert((started, 0))
            .1 += 1;
        if !self.watch.connected() {
            return Ok(());
        }
        let outcome = store
            .rows(&bind(PLAN_OF_Q, &[("want", Value::iri(want))])?, &[])?
            .first()
            .and_then(|r| iri(r, "outcome"))
            .map(|o| local_of(&o));
        self.watch.emit(&SearchEnded {
            want: want.to_string(),
            desire: desire_of(store, want)?,
            scope: scope.map(local_of),
            outcome,
            duration_s: Some(round6(started.elapsed().as_secs_f64())),
            budget: Some(budget as f64),
            weighed: Some(weighed as f64),
        });
        Ok(())
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
            if let Some(want) = refine(&self.beliefs, &self.uri, &step, at)? {
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

    /// Every want that stands after the last pass, across the imaginaria.
    pub fn standing(&self, at: DateTime) -> Result<Vec<String>, Error> {
        let mut out = BTreeSet::new();
        for store in self.imaginaria.values() {
            out.extend(find_wants(store, at, &Finding::default())?);
        }
        Ok(out.into_iter().collect())
    }

    /// The earliest instant after `at` a ground the last pass laid begins, in any imaginarium: where the present
    /// reaches it, the world the derivation stands in has moved though nothing arrived.
    pub fn next_ground(&self, at: DateTime) -> Result<Option<DateTime>, Error> {
        let mut next: Option<DateTime> = None;
        for store in self.imaginaria.values() {
            let Some(cat) = store.catalogue()? else { continue };
            let text = bind(NEXT_GROUND_Q, &[("cat", Value::iri(cat)), ("at", instant(at))])?;
            for row in store.rows(&text, &[])? {
                if let Some(start) = value(&row, "start").and_then(|s| s.parse::<DateTime>().ok())
                    && next.is_none_or(|n| start < n)
                {
                    next = Some(start);
                }
            }
        }
        Ok(next)
    }

    /// Whether the agent holds any desire.
    pub fn holds_a_desire(&self) -> Result<bool, Error> {
        let desires = graphs(&self.beliefs, &[DESIRE])?;
        Ok(!self
            .beliefs
            .rows("SELECT ?d WHERE { ?d a planning:Desire } LIMIT 1", &strs(&desires))?
            .is_empty())
    }

    /// Write the scopes a pass reads — the boot's act.
    pub fn scope(beliefs: &Store, now: DateTime) -> Result<(), Error> {
        scope_actions(beliefs, now)
    }

    /// Every constraint this agent holds that its present violates, as (constraint, rows), asked of a throwaway
    /// imaginarium over the whole store. Writes nothing to the beliefs.
    pub fn contradictions(&self, at: DateTime) -> Result<Vec<(String, BTreeSet<Violation>)>, Error> {
        let scopes = find_scopes(&self.beliefs)?
            .ok_or_else(|| Error::Evaluation("the store holds no scope graph — scope_actions has not run".into()))?;
        let store = Store::new(Arc::new(self.beliefs.namespaces().clone()))?;
        let mut memo = Memo::default();
        prepare_ground(&self.beliefs, &store, None, Some(&scopes))?;
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

#[cfg(test)]
mod tests {
    //! The Planner, held to `plans/`'s cases (the imaginarium a pass leaves),
    //! `expand/`'s (one iteration), and the tests of `test_planner.py`, `test_search.py`, `test_extract_plan.py` and
    //! `test_publish_plan.py` that need no executor. Those that walk steps through an executor wait for execution: a
    //! plan published and adopted by nobody is walked, as `walking` reads it, which is what the rest stand on.

    use std::collections::HashSet;
    use std::path::{Path, PathBuf};

    use oxigraph::model::Literal;

    use orexis::ontology::FORECAST;
    use orexis::snapshots;

    use super::*;
    use crate::extract_plan::extract_plan;
    use crate::footprint::changeable;
    use crate::ontology::POSSIBLE_GRAPH;
    use crate::ontology::{EXHAUSTED, GROUND_GRAPH, PLAN_GRAPH, SATISFIED};
    use crate::world_at::{Asking, world_at};

    fn cases() -> PathBuf {
        snapshots::tree().join("orexis-planning/tests/plans")
    }

    fn bench(name: &str) -> PathBuf {
        snapshots::tree().join(format!("orexis-planning/tests/bench/{name}.trig"))
    }

    fn minutes(n: i64) -> DateTime {
        snapshots::now()
            .checked_add_day_time_duration(DayTimeDuration::new(60 * n))
            .unwrap()
    }

    fn imagined(planner: &Planner) -> &Store {
        assert_eq!(planner.imaginaria.len(), 1, "one scope");
        planner.imaginaria.values().next().unwrap()
    }

    #[test]
    fn the_pass_leaves_the_imaginarium_the_diff_says() {
        for case in snapshots::cases_in(&cases()) {
            let store = snapshots::stand_in(&case);
            let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
            planner
                .plan(snapshots::now())
                .unwrap_or_else(|e| panic!("{}: {e}", case.display()));
            snapshots::held_to_diff(&case, imagined(&planner), "planner");
        }
    }

    #[test]
    fn every_case_is_read_and_no_diff_is_orphaned() {
        for dir in [cases(), snapshots::tree().join("orexis-planning/tests/expand")] {
            snapshots::all_read(&dir, 3);
        }
    }

    const OPEN_Q: &str = "
SELECT DISTINCT ?want WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    ?x a planning:Weighing ; planning:for ?want ; planning:open true } }
ORDER BY ?want";

    #[test]
    fn one_iteration_adds_the_layer_the_diff_says() {
        for case in snapshots::cases_in(&snapshots::tree().join("orexis-planning/tests/expand")) {
            let store = snapshots::stand_in(&case);
            let planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
            let wants: Vec<String> = store
                .rows(OPEN_Q, &[])
                .unwrap()
                .iter()
                .filter_map(|r| iri(r, "want"))
                .collect();
            assert!(!wants.is_empty(), "{} has nothing to expand", case.display());
            let none = BTreeSet::new();
            let scoped = Searching {
                scope: None,
                only: None,
                elsewhere: &none,
                within: None,
                at: snapshots::now(),
            };
            for want in wants {
                planner
                    .expand(&store, &want, BUDGET, &scoped, &mut Memo::default())
                    .unwrap();
            }
            snapshots::held_to_diff(&case, &store, "expand");
        }
    }

    // --- what a world is made of (#953) ----------------------------------------------------------------------------------

    fn world_cases() -> Vec<PathBuf> {
        let mut out = snapshots::cases_in(&cases());
        out.push(bench("two_disk_hanoi"));
        out
    }

    /// What the writers of a one-scope imaginarium can write: predicates any object of which may be written, and
    /// `(predicate, object)` pairs written with a fixed object.
    fn writes(store: &Store) -> (BTreeSet<String>, HashSet<(String, Term)>) {
        let mut anything = BTreeSet::new();
        let mut fixed = HashSet::new();
        for p in changeable(store, None, snapshots::now())
            .unwrap()
            .expect("every writer reads")
        {
            match p.object {
                Some(o) => {
                    fixed.insert((p.predicate, o));
                }
                None => {
                    anything.insert(p.predicate);
                }
            }
        }
        let predictions = store.graphs_of(&[FORECAST], &Within::default()).unwrap();
        let mut graphs = predictions.clone();
        graphs.extend(store.revisions_of(&strs(&predictions), BELIEF).unwrap());
        for g in graphs {
            for t in store.triples(&g).unwrap() {
                anything.insert(t.predicate.as_str().to_string());
            }
        }
        (anything, fixed)
    }

    fn written_by(t: &Triple, anything: &BTreeSet<String>, fixed: &HashSet<(String, Term)>) -> bool {
        anything.contains(t.predicate.as_str()) || fixed.contains(&(t.predicate.as_str().to_string(), t.object.clone()))
    }

    fn worlds_of(store: &Store) -> Vec<String> {
        let mut out = store.graphs_of(&[GROUND_GRAPH], &Within::default()).unwrap();
        out.extend(store.graphs_of(&[POSSIBLE_GRAPH], &Within::default()).unwrap());
        out
    }

    #[test]
    fn nothing_read_beside_a_world_is_what_a_step_can_write_and_everything_in_one_is() {
        for case in world_cases() {
            let store = snapshots::stand_in(&case);
            let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
            planner.plan(snapshots::now()).unwrap();
            for im in planner.imaginaria.values() {
                let (anything, fixed) = writes(im);
                let worlds = worlds_of(im);
                assert!(!worlds.is_empty(), "{}", case.display());
                for world in &worlds {
                    for t in im.triples(world).unwrap() {
                        assert!(
                            written_by(&t, &anything, &fixed),
                            "{}: {world} holds {t}",
                            case.display()
                        );
                    }
                    for graph in world_at(im, Some(world), &Asking::default(), &mut Memo::default()).unwrap() {
                        if graph == *world {
                            continue;
                        }
                        for t in im.triples(&graph).unwrap() {
                            assert!(
                                !written_by(&t, &anything, &fixed),
                                "{}: {graph} beside {world} holds {t}",
                                case.display()
                            );
                        }
                    }
                }
            }
        }
    }

    // --- reruns: the imaginarium outlives the pass ----------------------------------------------------------------------

    const STEPS_Q: &str = "SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?p { ?p a planning:Plan . ?s a execution:Step ; execution:partOf ?p } }";
    const ROOTS_Q: &str = "
SELECT DISTINCT ?root WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?w a planning:PossibleGraph ; (planning:by/planning:from)+ ?root .
               ?root a planning:GroundGraph } }";
    const WEIGHED_Q: &str = "
SELECT (COUNT(?x) AS ?n) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?x a planning:Weighing ; planning:weighs ?w .
               FILTER NOT EXISTS { ?w a planning:GroundGraph } } }";
    const OUTCOME_Q: &str = "SELECT ?o WHERE { GRAPH ?p { ?p a planning:Plan ; planning:outcome ?o } }";

    fn count(store: &Store, text: &str) -> usize {
        value(&store.rows(text, &[]).unwrap()[0], "n").unwrap().parse().unwrap()
    }

    fn possible(planner: &Planner) -> BTreeSet<String> {
        imagined(planner)
            .graphs_of(&[POSSIBLE_GRAPH], &Within::default())
            .unwrap()
            .into_iter()
            .collect()
    }

    fn steps(planner: &Planner) -> usize {
        count(imagined(planner), STEPS_Q)
    }

    fn outcome(planner: &Planner) -> String {
        local_of(&iri(&imagined(planner).rows(OUTCOME_Q, &[]).unwrap()[0], "o").unwrap())
    }

    /// The world moves a disk: its `hanoi:on` row replaced in the belief graph holding it.
    fn move_disk(store: &Store, disk: &str, onto: &str) {
        let found = store
            .rows(
                &format!(
                "SELECT ?d ?p ?o ?g WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph }}
        GRAPH ?g {{ ?d ?p ?o }} FILTER(STRENDS(STR(?d), \"{disk}\") && STRENDS(STR(?p), \"#on\")) }}"
            ),
                &[],
            )
            .unwrap();
        let r = &found[0];
        let (d, p, o, g) = (
            iri(r, "d").unwrap(),
            iri(r, "p").unwrap(),
            r["o"].to_string(),
            iri(r, "g").unwrap(),
        );
        store
        .update(&format!(
            "DELETE DATA {{ GRAPH <{g}> {{ <{d}> <{p}> {o} }} }} ; INSERT DATA {{ GRAPH <{g}> {{ <{d}> <{p}> <{onto}> }} }}"
        ))
        .unwrap();
    }

    /// Forget every plan handed down, as if nobody took it up and nothing walks it.
    fn forget_handed(store: &Store) {
        for handed in store.graphs_of(&[orexis::ontology::PLAN], &Within::default()).unwrap() {
            store.forget_graph(&handed, Some(BELIEF)).unwrap();
        }
    }

    #[test]
    fn a_pass_a_minute_later_hands_down_nothing_again_and_forks_nothing() {
        let store = snapshots::stand_in(&bench("two_disk_hanoi"));
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        assert_eq!(planner.plan(snapshots::now()).unwrap().len(), 1);
        assert_eq!(planner.walking().unwrap().len(), 1, "the plan handed down is walked");
        let (worlds, made) = (possible(&planner), steps(&planner));
        assert_eq!(made, 3);
        assert!(
            planner.plan(minutes(1)).unwrap().is_empty(),
            "and not handed down again"
        );
        assert_eq!(possible(&planner), worlds, "nothing forked for a want being walked");
    }

    #[test]
    fn nothing_happened_and_the_next_pass_forks_nothing() {
        let store = snapshots::stand_in(&bench("two_disk_hanoi"));
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        planner.plan(snapshots::now()).unwrap();
        forget_handed(&store);
        let worlds = possible(&planner);
        assert_eq!(steps(&planner), 3);
        planner.plan(minutes(1)).unwrap();
        assert_eq!((possible(&planner), steps(&planner)), (worlds, 3));
    }

    fn stamp(store: &Store, disk: &str, at: &str) {
        let found = store
            .rows(
                &format!(
                    "SELECT ?d ?g WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph }}
        GRAPH ?g {{ ?d ?p ?o }} FILTER(STRENDS(STR(?d), \"{disk}\") && STRENDS(STR(?p), \"#on\")) }}"
                ),
                &[],
            )
            .unwrap();
        let (d, g) = (iri(&found[0], "d").unwrap(), iri(&found[0], "g").unwrap());
        store
            .update(&format!(
                "DELETE WHERE {{ GRAPH <{g}> {{ <{d}> <http://www.w3.org/ns/sosa/resultTime> ?t }} }} ; \
             INSERT DATA {{ GRAPH <{g}> {{ <{d}> <http://www.w3.org/ns/sosa/resultTime> \"{at}\" }} }}"
            ))
            .unwrap();
    }

    #[test]
    fn a_reading_re_stamped_with_its_instant_is_no_surprise() {
        let store = snapshots::stand_in(&bench("two_disk_hanoi"));
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        stamp(&store, "disk_1", "2026-01-01T12:00:00Z");
        planner.plan(snapshots::now()).unwrap();
        forget_handed(&store);
        let worlds = possible(&planner);
        stamp(&store, "disk_1", "2026-01-01T12:01:00Z");
        planner.plan(minutes(1)).unwrap();
        assert_eq!((possible(&planner), steps(&planner)), (worlds, 3));
    }

    #[test]
    fn a_surprise_starts_the_search_afresh() {
        let store = snapshots::stand_in(&bench("two_disk_hanoi"));
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        planner.plan(snapshots::now()).unwrap();
        forget_handed(&store);
        let old: BTreeSet<String> = imagined(&planner)
            .graphs_of(&[GROUND_GRAPH], &Within::default())
            .unwrap()
            .into_iter()
            .collect();
        assert!(!old.is_empty() && !possible(&planner).is_empty());
        let found = store
        .rows(
            "SELECT ?d WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?d ?p ?o } \
             FILTER(STRENDS(STR(?d), \"disk_1\") && STRENDS(STR(?p), \"#on\")) }",
            &[],
        )
        .unwrap();
        let disk_1 = iri(&found[0], "d").unwrap();
        move_disk(&store, "disk_1", "http://example.org/orexis/hanoi#PegB");
        move_disk(&store, "disk_2", &disk_1);
        planner.plan(minutes(1)).unwrap();
        let im = imagined(&planner);
        let new: BTreeSet<String> = im
            .graphs_of(&[GROUND_GRAPH], &Within::default())
            .unwrap()
            .into_iter()
            .collect();
        assert!(
            !new.is_empty() && old.is_disjoint(&new),
            "the ground the last pass stood in went"
        );
        let roots: BTreeSet<String> = im
            .rows(ROOTS_Q, &[])
            .unwrap()
            .iter()
            .filter_map(|r| iri(r, "root"))
            .collect();
        assert!(
            !roots.is_empty() && roots.is_subset(&new),
            "every world standing was forked from the new ground"
        );
        assert_eq!(steps(&planner), 2, "disk 2 to C, disk 1 to C");
    }

    /// Hanoi planned once: candidates weighed, and the plan's steps.
    fn weighed(case: &Path, budget: usize, estimate: bool) -> (usize, usize) {
        let store = snapshots::stand_in(case);
        if !estimate {
            store
                .update(
                    "DELETE { GRAPH ?g { ?d <http://example.org/orexis/planning#estimates> ?e } } \
                 WHERE { GRAPH ?g { ?d <http://example.org/orexis/planning#estimates> ?e } }",
                )
                .unwrap();
        }
        let mut planner = Planner::new(&store, snapshots::AGENT, Some(budget)).unwrap();
        planner.plan(snapshots::now()).unwrap();
        (count(imagined(&planner), WEIGHED_Q), steps(&planner))
    }

    #[test]
    fn an_estimate_refuses_forks_a_uniform_cost_search_pays_for() {
        let with_it = weighed(&bench("three_disk_hanoi"), 128, true);
        let without = weighed(&bench("three_disk_hanoi"), 128, false);
        assert!(with_it.1 == 7 && without.1 == 7, "the same optimal plan either way");
        assert!(
            with_it.0 < without.0,
            "fewer candidates weighed: {} against {}",
            with_it.0,
            without.0
        );
    }

    #[test]
    fn a_search_the_budget_cuts_short_is_finished_by_the_passes_after() {
        let (whole, _) = weighed(&bench("three_disk_hanoi"), 128, true);
        let store = snapshots::stand_in(&bench("three_disk_hanoi"));
        let mut planner = Planner::new(&store, snapshots::AGENT, Some(20)).unwrap();
        let mut passes = Vec::new();
        for i in 0..3 {
            planner.plan(minutes(i)).unwrap();
            assert_eq!(
                planner.standing(minutes(i)).unwrap().len(),
                1,
                "the want stands until its desire reads met"
            );
            assert_eq!(planner.exhausted().unwrap(), i < 2, "cut short twice, then satisfied");
            passes.push((outcome(&planner), planner.walking().unwrap().len()));
        }
        let expected: Vec<(String, usize)> = [("Exhausted", 0), ("Exhausted", 0), ("Satisfied", 1)]
            .iter()
            .map(|(o, n)| (o.to_string(), *n))
            .collect();
        assert_eq!(passes, expected);
        assert_eq!(steps(&planner), 7);
        assert_eq!(
            count(imagined(&planner), WEIGHED_Q),
            whole,
            "no candidate weighed twice, and none skipped"
        );
    }

    #[test]
    fn the_budget_is_the_agents_stance_where_its_self_graph_states_one() {
        let store = snapshots::stand_in(&bench("three_disk_hanoi"));
        assert_eq!(Planner::new(&store, snapshots::AGENT, None).unwrap().budget, BUDGET);
        let cat = store.catalogue().unwrap().unwrap();
        let (me, own) = (snapshots::ME, "http://example.org/test#self");
        store
            .update(&format!(
                "INSERT DATA {{ GRAPH <{own}> {{ <{me}> a orexis:Self ; <{BUDGET_TERM}> 20 }}
  GRAPH <{cat}> {{ <{own}> a orexis:SelfGraph , orexis:BeliefGraph , orexis:Graph ; orexis:ownedBy <{me}> }} }}"
            ))
            .unwrap();
        assert_eq!(Planner::new(&store, snapshots::AGENT, Some(64)).unwrap().budget, 64);
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        assert_eq!(planner.budget, 20);
        planner.plan(snapshots::now()).unwrap();
        assert_eq!(
            (outcome(&planner), count(imagined(&planner), WEIGHED_Q)),
            ("Exhausted".to_string(), 20)
        );
    }

    #[test]
    fn scope_is_the_boots_act_and_writes_what_a_pass_reads() {
        let store = snapshots::stand_in(&bench("two_disk_hanoi"));
        let scopes = "SELECT (COUNT(?s) AS ?n) WHERE { GRAPH ?g { ?s a <http://example.org/orexis/planning#Scope> } }";
        store
            .update("DELETE WHERE { GRAPH ?g { ?s ?p <http://example.org/orexis/planning#Scope> } }")
            .unwrap();
        assert_eq!(count(&store, scopes), 0);
        Planner::scope(&store, snapshots::now()).unwrap();
        assert!(
            count(&store, scopes) >= 1,
            "the scopes are written again, from the actions"
        );
        Planner::new(&store, snapshots::AGENT, None)
            .unwrap()
            .plan(snapshots::now())
            .unwrap();
    }

    #[test]
    fn a_candidate_a_cut_left_untaken_is_taken_by_the_next_pass() {
        let (whole, made) = weighed(&bench("courier_corner"), 128, true);
        assert_eq!(made, 8);
        let store = snapshots::stand_in(&bench("courier_corner"));
        let mut planner = Planner::new(&store, snapshots::AGENT, Some(16)).unwrap();
        let mut outcomes = Vec::new();
        for i in 0..8 {
            planner.plan(minutes(i)).unwrap();
            outcomes.push(outcome(&planner));
            if outcomes.last().map(String::as_str) == Some("Satisfied") {
                break;
            }
        }
        assert!(
            outcomes.last().map(String::as_str) == Some("Satisfied") && outcomes.len() > 1,
            "{outcomes:?}"
        );
        assert_eq!(steps(&planner), 8);
        assert_eq!(
            count(imagined(&planner), WEIGHED_Q),
            whole,
            "no candidate weighed twice, and none skipped"
        );
    }

    #[test]
    fn a_want_the_world_meets_before_the_plan_begins_is_reached() {
        let store = snapshots::stand_in(&bench("two_disk_hanoi"));
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        planner.plan(snapshots::now()).unwrap();
        let walked = planner.walking().unwrap();
        let found = store
        .rows(
            "SELECT ?d WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a orexis:BeliefGraph } GRAPH ?g { ?d ?p ?o } \
             FILTER(STRENDS(STR(?d), \"disk_2\") && STRENDS(STR(?p), \"#on\")) }",
            &[],
        )
        .unwrap();
        let disk_2 = iri(&found[0], "d").unwrap();
        move_disk(&store, "disk_2", "http://example.org/orexis/hanoi#PegC");
        move_disk(&store, "disk_1", &disk_2);
        planner.plan(minutes(1)).unwrap();
        assert_eq!(planner.reached, walked);
    }

    const PREDICTED_Q: &str = "
SELECT DISTINCT ?side ?s ?o WHERE {
  GRAPH ?p { ?step a execution:Step ; ?side ?g . VALUES ?side { execution:adds execution:retracts } }
  GRAPH ?g { ?s ?pred ?o } }";

    #[test]
    fn a_step_landing_across_a_prediction_predicts_its_own_effect_alone() {
        let store = snapshots::stand_in(&cases().join("a_step_lands_across_a_prediction_it_does_not_touch.trig"));
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        planner.plan(snapshots::now()).unwrap();
        let predicted: BTreeSet<(String, String, String)> = store
            .rows(PREDICTED_Q, &[])
            .unwrap()
            .iter()
            .map(|r| {
                (
                    local_of(&iri(r, "side").unwrap()),
                    local_of(&iri(r, "s").unwrap()),
                    value(r, "o").unwrap(),
                )
            })
            .collect();
        let expected: BTreeSet<(String, String, String)> = [("adds", "tank1", "11"), ("retracts", "tank1", "6")]
            .iter()
            .map(|(a, b, c)| (a.to_string(), b.to_string(), c.to_string()))
            .collect();
        assert_eq!(
            predicted, expected,
            "the fill's own change, and nothing of the tank the prediction drains"
        );
    }

    const CHANGES_Q: &str = "
SELECT ?g ?w WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph .
  ?g prov:wasDerivedFrom ?w ; a ?side . VALUES ?side { execution:AddsGraph execution:RetractsGraph } } }";

    #[test]
    fn a_world_the_re_root_drops_takes_what_its_step_changed_with_it() {
        let t = "http://example.org/test#";
        let store = snapshots::stand_in(&cases().join("a_step_lands_across_a_prediction_it_does_not_touch.trig"));
        let mut planner = Planner::new(&store, snapshots::AGENT, None).unwrap();
        planner.plan(snapshots::now()).unwrap();
        let first: Vec<String> = imagined(&planner)
            .rows(CHANGES_Q, &[])
            .unwrap()
            .iter()
            .filter_map(|r| iri(r, "g"))
            .collect();
        assert_eq!(first.len(), 2, "the fill's world was forked in the later ground");
        store
        .update(&format!(
            "DELETE DATA {{ GRAPH <{t}sensed> {{ <{t}tank1> <{t}level> 6 }} }} ; INSERT DATA {{ GRAPH <{t}sensed> {{ <{t}tank1> <{t}level> 7 }} }}"
        ))
        .unwrap();
        planner.plan(minutes(1)).unwrap();
        let im = imagined(&planner);
        assert!(
            im.rows(CHANGES_Q, &[]).unwrap().is_empty(),
            "no graph of what a step changed outlives its world"
        );
        for g in first {
            assert!(im.quads(&g).unwrap().is_empty(), "{g}");
        }
    }

    fn top(
        late: i64,
        lands: Option<&str>,
        spent: &str,
        best: Option<&str>,
        best_late: i64,
        best_lands: Option<&str>,
    ) -> orexis::store::Row {
        let mut row = orexis::store::Row::new();
        let int =
            |n: i64| -> Term { Literal::new_typed_literal(n.to_string(), oxigraph::model::vocab::xsd::INTEGER).into() };
        let dec = |s: &str| -> Term { Literal::new_typed_literal(s, oxigraph::model::vocab::xsd::DECIMAL).into() };
        let at = |s: &str| -> Term { Literal::new_typed_literal(s, oxigraph::model::vocab::xsd::DATE_TIME).into() };
        row.insert("late".into(), int(late));
        row.insert("spent".into(), dec(spent));
        row.insert("remaining".into(), dec("0"));
        row.insert("bestLate".into(), int(best_late));
        if let Some(l) = lands {
            row.insert("lands".into(), at(l));
        }
        if let Some(b) = best {
            row.insert("best".into(), dec(b));
        }
        if let Some(b) = best_lands {
            row.insert("bestLands".into(), at(b));
        }
        row
    }

    #[test]
    fn the_bound_ranks_on_time_before_late_and_a_late_world_soonest_first() {
        let (at, sooner) = (Some("2026-01-01T12:40:00+00:00"), Some("2026-01-01T12:35:00+00:00"));
        let b = |r| beaten(&r).unwrap();
        assert!(!b(top(0, None, "1", None, 0, None)), "no achiever yet refuses nothing");
        assert!(
            b(top(1, at, "0", Some("5"), 0, None)),
            "an on-time achiever refuses a late world"
        );
        assert!(b(top(0, None, "5", Some("5"), 0, None)) && !b(top(0, None, "4", Some("5"), 0, None)));
        assert!(
            !b(top(0, None, "9", Some("1"), 1, at)),
            "a late achiever refuses nothing on time"
        );
        assert!(
            !b(top(1, sooner, "9", Some("1"), 1, at)),
            "nor a late world landing sooner"
        );
        assert!(b(top(1, at, "0", Some("1"), 1, sooner)));
        assert!(b(top(1, at, "1", Some("1"), 1, at)) && !b(top(1, at, "0", Some("1"), 1, at)));
    }

    // --- one want's search ------------------------------------------------------------------------------------------------

    const MADE_Q: &str = "
SELECT (COUNT(DISTINCT ?w) AS ?worlds) (COUNT(DISTINCT ?x) AS ?weighings) WHERE {
  GRAPH ?cat { ?cat a orexis:CatalogueGraph .
    { ?w a planning:PossibleGraph } UNION { ?x a planning:Weighing ; planning:for $want } } }";
    const PLAN_Q: &str = "
SELECT ?outcome (COUNT(?step) AS ?steps) WHERE {
  GRAPH ?g { ?g a planning:Plan ; planning:for $want ; planning:outcome ?outcome .
             OPTIONAL { ?step a execution:Step ; execution:partOf ?g } } }
GROUP BY ?outcome";

    /// The low tank's imaginarium with its want derived — the store `search` is handed.
    fn derived_into(beliefs: &Store) -> (Store, String) {
        let store = Store::new(snapshots::namespaces()).unwrap();
        prepare_ground(beliefs, &store, None, None).unwrap();
        lay_ground(&store, snapshots::now(), &Laying::default()).unwrap();
        let mut memo = Memo::default();
        for pair in unweighed(&store, None, None, &mut memo).unwrap() {
            weigh(
                &store,
                &iri(&pair, "for").unwrap(),
                &iri(&pair, "about").unwrap(),
                &mut memo,
            )
            .unwrap();
        }
        derive_wants(&store, snapshots::now(), &BTreeMap::new(), &BTreeSet::new()).unwrap();
        let wants = find_wants(&store, snapshots::now(), &Finding::default()).unwrap();
        assert_eq!(wants.len(), 1);
        let want = wants[0].clone();
        (store, want)
    }

    fn made(store: &Store, want: &str) -> (usize, usize) {
        let r = &store
            .rows(&bind(MADE_Q, &[("want", Value::iri(want))]).unwrap(), &[])
            .unwrap()[0];
        (
            value(r, "worlds").unwrap().parse().unwrap(),
            value(r, "weighings").unwrap().parse().unwrap(),
        )
    }

    fn plan_of(store: &Store, want: &str) -> (String, usize) {
        let r = &store
            .rows(&bind(PLAN_Q, &[("want", Value::iri(want))]).unwrap(), &[])
            .unwrap()[0];
        (iri(r, "outcome").unwrap(), value(r, "steps").unwrap().parse().unwrap())
    }

    #[test]
    fn a_search_the_budget_cut_short_is_finished_by_the_next_call() {
        let beliefs = snapshots::stand_in(&snapshots::cases_in(&cases())[0]);
        let (store, want) = derived_into(&beliefs);
        let planner = Planner::new(&beliefs, snapshots::AGENT, None).unwrap();
        let none = BTreeSet::new();
        let scoped = Searching {
            scope: None,
            only: None,
            elsewhere: &none,
            within: None,
            at: snapshots::now(),
        };
        planner.search(&store, &want, 1, &scoped, &mut Memo::default()).unwrap();
        assert_eq!(plan_of(&store, &want), (EXHAUSTED.to_string(), 0));
        assert_eq!(
            made(&store, &want),
            (1, 2),
            "the ground weighed, and one world forked and weighed"
        );
        planner
            .search(&store, &want, 32, &scoped, &mut Memo::default())
            .unwrap();
        assert_eq!(plan_of(&store, &want), (SATISFIED.to_string(), 2));
        assert_eq!(
            made(&store, &want),
            (2, 3),
            "one more world, on top of the first — not beside it"
        );
    }

    #[test]
    fn a_finished_search_asked_again_makes_nothing_new() {
        let beliefs = snapshots::stand_in(&snapshots::cases_in(&cases())[0]);
        let (store, want) = derived_into(&beliefs);
        let planner = Planner::new(&beliefs, snapshots::AGENT, None).unwrap();
        let none = BTreeSet::new();
        let scoped = Searching {
            scope: None,
            only: None,
            elsewhere: &none,
            within: None,
            at: snapshots::now(),
        };
        planner
            .search(&store, &want, BUDGET, &scoped, &mut Memo::default())
            .unwrap();
        let held = |s: &Store| -> BTreeSet<String> { s.engine().iter().map(|q| q.unwrap().to_string()).collect() };
        let before = held(&store);
        planner
            .search(&store, &want, BUDGET, &scoped, &mut Memo::default())
            .unwrap();
        assert_eq!(held(&store), before, "not one quad differs");
        assert_eq!(plan_of(&store, &want), (SATISFIED.to_string(), 2));
    }

    // --- the plan read out, and handed down --------------------------------------------------------------------------------

    const CHAIN_STEPS_Q: &str = "
SELECT ?step ?fills ?of (COUNT(?before) AS ?n) WHERE {
  GRAPH $plan { ?step a execution:Step ; planning:fills ?fills ; planning:of ?of .
                OPTIONAL { ?before execution:then+ ?step } } }
GROUP BY ?step ?fills ?of ORDER BY ?n";

    fn walked(beliefs: &Store) -> Planner {
        let mut planner = Planner::new(beliefs, snapshots::AGENT, None).unwrap();
        planner.plan(snapshots::now()).unwrap();
        planner
    }

    fn plan_steps(store: &Store, graph: &str) -> Vec<orexis::store::Row> {
        store
            .rows(&bind(CHAIN_STEPS_Q, &[("plan", Value::iri(graph))]).unwrap(), &[])
            .unwrap()
    }

    #[test]
    fn every_step_names_the_candidate_it_was_minted_from_and_the_chain_is_the_worlds_ancestry() {
        let beliefs = snapshots::stand_in(&cases().join("a_low_tank_is_filled.trig"));
        let planner = walked(&beliefs);
        let im = imagined(&planner);
        let graphs = im.graphs_of(&[PLAN_GRAPH], &Within::default()).unwrap();
        let steps = plan_steps(im, &graphs[0]);
        assert_eq!(steps.len(), 2);
        let cat = im.catalogue().unwrap().unwrap();
        for step in &steps {
            let of = iri(step, "of").unwrap();
            let found = im
                .rows(
                    &format!(
                        "SELECT ?a WHERE {{ GRAPH <{cat}> {{ <{of}> a planning:Candidate ; planning:fills ?a }} }}"
                    ),
                    &[],
                )
                .unwrap();
            assert_eq!(
                iri(&found[0], "a"),
                iri(step, "fills"),
                "a step fills what its candidate filled"
            );
        }
        let by_chain: Vec<String> = steps.iter().filter_map(|s| iri(s, "of")).collect();
        let deepest = im
        .rows(
            &format!(
                "SELECT ?w (COUNT(?above) AS ?depth) WHERE {{ GRAPH <{cat}> {{ ?w a planning:PossibleGraph ; (planning:by/planning:from)+ ?above }} }}
                 GROUP BY ?w ORDER BY DESC(?depth) LIMIT 1"
            ),
            &[],
        )
        .unwrap();
        let (mut ancestry, mut world) = (Vec::new(), iri(&deepest[0], "w").unwrap());
        loop {
            let found = im
            .rows(&format!("SELECT ?parent ?by WHERE {{ GRAPH <{cat}> {{ <{world}> planning:by ?by . ?by planning:from ?parent }} }}"), &[])
            .unwrap();
            let Some(r) = found.first() else { break };
            ancestry.push(iri(r, "by").unwrap());
            world = iri(r, "parent").unwrap();
        }
        ancestry.reverse();
        assert_eq!(ancestry, by_chain, "root first, and the same candidates");
    }

    #[test]
    fn extracting_again_leaves_the_same_plan() {
        let beliefs = snapshots::stand_in(&cases().join("a_low_tank_is_filled.trig"));
        let planner = walked(&beliefs);
        let im = imagined(&planner);
        let graph = im.graphs_of(&[PLAN_GRAPH], &Within::default()).unwrap()[0].clone();
        let before = plan_steps(im, &graph);
        let found = im
            .rows(
                &format!("SELECT ?w WHERE {{ GRAPH <{graph}> {{ <{graph}> planning:for ?w }} }}"),
                &[],
            )
            .unwrap();
        assert_eq!(extract_plan(im, &iri(&found[0], "w").unwrap()).unwrap(), graph);
        assert_eq!(plan_steps(im, &graph), before);
        let outcome = im
            .rows(
                &format!("SELECT ?o WHERE {{ GRAPH <{graph}> {{ <{graph}> planning:outcome ?o }} }}"),
                &[],
            )
            .unwrap();
        assert_eq!(iri(&outcome[0], "o").as_deref(), Some(SATISFIED));
    }

    #[test]
    fn a_plan_handed_down_is_walked_and_not_handed_down_again() {
        let beliefs = snapshots::stand_in(&cases().join("a_low_tank_is_filled.trig"));
        let mut planner = Planner::new(&beliefs, snapshots::AGENT, None).unwrap();
        let written = planner.plan(snapshots::now()).unwrap();
        let handed = beliefs
            .graphs_of(&[orexis::ontology::PLAN], &Within::default())
            .unwrap();
        assert_eq!(handed, written);
        assert_eq!(written.len(), 1);
        let pursues = beliefs
            .rows(
                &format!(
                    "SELECT ?w WHERE {{ GRAPH <{0}> {{ <{0}> execution:pursues ?w }} }}",
                    written[0]
                ),
                &[],
            )
            .unwrap();
        let want = iri(&pursues[0], "w").unwrap();
        assert!(want.ends_with("keeper.in_range.pursued.tank1"), "{want}");
        assert_eq!(planner.walking().unwrap(), BTreeSet::from([want]));
        assert!(planner.plan(snapshots::now()).unwrap().is_empty());
    }

    #[test]
    fn an_answer_is_not_handed_down() {
        let beliefs = snapshots::stand_in(&cases().join("a_low_tank_is_filled.trig"));
        beliefs
            .update("DELETE WHERE { GRAPH <http://example.org/test#actions> { ?s ?p ?o } }")
            .unwrap();
        scope_actions(&beliefs, snapshots::now()).unwrap();
        let mut planner = Planner::new(&beliefs, snapshots::AGENT, None).unwrap();
        assert!(planner.plan(snapshots::now()).unwrap().is_empty());
        assert!(
            planner
                .imaginaria
                .values()
                .any(|im| !im.graphs_of(&[PLAN_GRAPH], &Within::default()).unwrap().is_empty()),
            "the pass still wrote down what it concluded"
        );
        assert!(
            beliefs
                .graphs_of(&[orexis::ontology::PLAN], &Within::default())
                .unwrap()
                .is_empty(),
            "and handed down nothing"
        );
    }
}
