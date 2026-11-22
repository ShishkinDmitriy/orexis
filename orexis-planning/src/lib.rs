//! PLANNING, in Rust: the acts a pass runs over the imaginarium, ported from `orexis-planning/` one act at a time
//! and held to the same cases. A STAR, NOT A CHAIN, as there: an act calls no other act, and what one needs of
//! another's work it reads off the rows the other wrote.
//!
//! - `world_at`: the graphs a rule is answered over in one world, or in the present;
//! - `next_ground`: the instant the next ground the search can tell apart begins, where a wait lands;
//! - `admit`: every candidate a world admits, one per action per legal filling, written as the edges leaving it;
//! - `take`: one candidate taken, the world it reaches forked with the action's effect applied, and what it is;
//! - `prepare_ground`: what crosses from the belief base into the store a search over one scope stands in;
//! - `lay_ground`: one ground world per period the agent can see, cut to what the search can change;
//! - `scope_actions`: the actions clustered into the scopes their effects join, written as the store's partition;
//! - `find_scopes`: every scope each predicate, term and action is in, read back;
//! - `find_wants`: the wants a store holds at an instant, narrowed by the criteria a caller names;
//! - `derive_wants`: a want minted for every cluster of what a desire's met-test reads unmet, read off the weighings;
//! - `couplings`: which instances a holder's constraints can make collide, over what the actions can reach;
//! - `withdraw`: every derived want the derivation no longer implies, and every want reached, taken away.
//! - `planner`: the package's core, the planner the self plays: the pass, its search, and its policy;
//! - the start, below the modules, and nothing else: the scopes written, the planner made, and the task that wakes it.

use orexis::foresight::Foresees;
use orexis::task::{Handed, Package, Woke};

use crate::admit::local_of;
use crate::ontology::PLANNING_TRIGGER;
use crate::planner::{CHECK, CHECKING_TRIGGER, REOPEN};

mod admit;
mod bridge;
mod couplings;
mod derive_wants;
pub mod events;
mod extract_plan;
mod find_scopes;
mod find_wants;
mod footprint;
mod fork;
mod lay_ground;
mod memo;
mod next_ground;
pub mod ontology;
pub mod planner;
mod prepare_ground;
mod publish_plan;
mod refine;
mod reroot;
mod scope;
mod scope_actions;
mod shapes;
mod take;
mod terms;
mod unweighed;
mod violation;
mod weigh;
mod withdraw;
mod world_at;

pub use memo::Memo;
pub use planner::{Budget, Planner};

inventory::submit! { Package { name: "planning", start } }

/// THE DOCUMENTS THIS PACKAGE BRINGS as it joins, in the order it puts them in.
const DOCUMENTS: orexis::task::Documents = orexis::documents!("ontology.ttl", "wait.ttl");

/// THE ROLE THIS PACKAGE IS LOADED FOR, its own word: the self playing one joins it to the agent.
const ROLE: &str = "http://example.org/orexis/planning#Planner";

/// PLANNING'S START, which every package this binary holds is given: it joins where the self plays a planner and
/// declines otherwise; joined, it writes the scopes a pass reads and makes its planner; checked, it says what a check
/// asks of it and ends there as it boots; otherwise what follows is ITS TASK, which takes the
/// foresight offered, then waits for an event beneath its trigger, a head asked or the instant it is next due, and
/// plans once nothing more waits to be heard.
fn start(handed: Handed) -> orexis::task::Starting {
    Box::pin(async move {
        if !handed.plays(&[ROLE])? {
            return Ok(());
        }
        handed.joins(&DOCUMENTS).await?;
        //  THE SCOPES A PASS READS are written as planning starts, over the store as the boot left it: the boot's
        //  act, and planning's own.
        let now = handed.clock.now();
        Planner::scope(&handed.store, now)?;
        let budget = handed.provided.take::<Budget>().map(|b| b.0);
        let mut planner = Planner::new(&handed.store, &handed.id, budget)?;
        //  CHECKED, it says what a check asks of it: that a desire holds the agent, and each constraint the agent
        //  holds that the world as posed violates, which no agent repairs (constraint.md).
        if let Some(checking) = handed.checking() {
            if planner.holds_a_desire()? {
                checking.holds("planning");
            }
            for (constraint, rows) in planner.contradictions(now)? {
                let said =
                    |term: &Option<String>| term.as_deref().map_or("none".to_string(), |t| local_of(t).to_string());
                let rows: Vec<String> = rows
                    .iter()
                    .map(|(instance, component, _, offending)| {
                        format!(
                            "({}, {}, {})",
                            local_of(instance),
                            component.as_deref().unwrap_or("none"),
                            said(offending)
                        )
                    })
                    .collect();
                checking.refuses(format!(
                    "holds {}, which the world as posed violates: {}",
                    local_of(&constraint),
                    rows.join(", ")
                ));
            }
        }
        planner.watch = handed.events.watch().clone();
        let mut hears = handed.events.hears();
        hears.event(PLANNING_TRIGGER, REOPEN);
        hears.event(CHECKING_TRIGGER, CHECK);
        if !handed.booted().await? {
            return Ok(());
        }
        //  PREDICTION'S FORESIGHT, where the agent plays a predictor: offered at its start, taken as the run begins.
        planner.foresee = handed.provided.take::<Foresees>();
        //  ON THE RUNTIME A DEPLOYED AGENT RUNS, OF SEVERAL THREADS, each scope's search is set going on one of its
        //  own and the task hears what it found; on one thread, as a world's test runs it, each is searched on the
        //  task, in scope order, as before.
        let (back, mut found) = tokio::sync::mpsc::unbounded_channel::<planner::Found>();
        if tokio::runtime::Handle::current().runtime_flavor() == tokio::runtime::RuntimeFlavor::MultiThread {
            planner.threads = Some(planner::Threads {
                events: handed.events.clone(),
                back,
            });
        }
        let mut heard = None;
        let mut arrived: Option<planner::Found> = None;
        let mut due = None;
        loop {
            let mut turn = handed.turn();
            //  WHAT A SEARCH FOUND keeps the agent busy until the task next waits, as anything it hears does.
            if let Some((searched, working)) = arrived.take() {
                working.back();
                let wrote = planner.found(searched, &mut turn);
                turn.done(wrote)?;
            }
            if let Some(Woke::Event(tag, event)) = heard.take() {
                let wrote = planner.heard_event(tag, &event, &mut turn);
                turn.done(wrote)?;
            }
            if hears.is_empty() {
                let wrote = planner.planning(&mut turn);
                turn.done(wrote)?;
                due = turn.next();
            }
            heard = tokio::select! {
                biased;
                _ = handed.stopped() => break,
                woke = hears.next() => match woke {
                    Some(woke) => Some(woke),
                    None => break,
                },
                searched = found.recv() => {
                    arrived = searched;
                    None
                },
                _ = handed.sleep_until(due) => None,
            };
        }
        Ok(())
    })
}
