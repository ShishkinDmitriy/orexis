//! THE PLANNING PACKAGE'S PART, as `agent/planning/create.py` made it: its Planner, planning at a pass where its policy
//! says so — a trigger heard, the present at the next ground the last planning laid, or a search cut short — and after each planning holding the agent or letting it go, saying how the wanting ended — `met` where no
//! want stands and nothing walks, `planned` where every want has a plan published and no part walks one,
//! `unreachable` where some stand that nothing this agent holds reaches. A desire held keeps it holding, since a
//! desire asks at every instant.
//!
//! WHAT A PASS DID IS SAID, not handed: a plan published, a want reached and a plan superseded are events beneath
//! execution's trigger, which execution's policy hears once the pass's job is done. Whether anything walks what it
//! publishes is the agent's roles' to say — one beneath `execution:Executor` — and a head execution asks
//! about as it is taken (`execution:HeadAsked`) is checked and answered, `planning:HeadChecked` beneath execution's
//! walking trigger (#916).

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::SELF_GRAPH;
use orexis_belief::ontology::{CHANGED, REVISED, REVISED_SOURCE};
use std::sync::{Arc, Mutex};

use orexis::runtime::{Heard, MET, PLANNED, Pass, Runtime, UNREACHABLE, Wait, Woke, long};
use orexis::store::{Store, Within, iri};

use crate::Planner;
use crate::admit::local_of;
use crate::events::HeadChecked;
use crate::ontology::{PLANNING_ACTIVITY, PLANNING_TRIGGER, REOPENS};

const PLAN: usize = 0;
const REOPEN: usize = 1;
const CHECK: usize = 2;

/// A head execution asks about as it is taken, and what that says: the head and the instant.
const HEAD_ASKED: &str = "http://example.org/orexis/execution#HeadAsked";
const HEAD: &str = "http://example.org/orexis/execution#head";
const INTENTION: &str = "http://example.org/orexis/execution#intention";
const AT_TIME: &str = "http://www.w3.org/ns/prov#atTime";

/// Whoever walks what planning publishes: a role of this class, or one beneath it.
const EXECUTOR: &str = "http://example.org/orexis/execution#Executor";
const ROLES_Q: &str = "SELECT DISTINCT ?kind WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role a ?kind }";

/// Planning's part: its Planner, whether any part walks what it publishes, and what its policy has heard since it
/// last planned.
pub struct Planning {
    pub planner: Planner,
    pub walked: bool,
    /// The events heard beneath its trigger since it last planned, which the planning names as what triggered it.
    triggers: Vec<oxigraph::model::NamedNode>,
    /// Whether to plan at the next pass whatever was heard: the first, and one after a search the budget cut short.
    due: bool,
    /// The instant the next ground the last planning laid begins, where it laid one.
    next: Option<oxsdatatypes::DateTime>,
    beliefs: Store,
    /// Whether nothing new was heard since planning last published: the present is the one its plans were found in.
    fresh: bool,
    /// Whether a plan failed in the present it was found in: planning holds back until news is heard.
    held: bool,
}

/// How the intention `$intention` ended, in execution's words.
const OUTCOME_Q: &str = "
SELECT ?o WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a execution:IntentionGraph }
                  GRAPH ?g { $intention execution:outcome ?o } }";

/// The graphs of `$revised` that are not the agent's own record of what it did: a belief that came to it.
const NEWS_Q: &str = "
SELECT ?g WHERE { GRAPH $cat { VALUES ?g { $revised } ?g a orexis:Graph .
                               FILTER NOT EXISTS { ?g orexis:arrivedBy orexis:Recorded } } } LIMIT 1";

impl Planning {
    /// The part, its budget the agent's stance unless the caller sizes one.
    pub fn new(beliefs: &Store, agent: &str, budget: Option<usize>) -> Result<Self, Error> {
        Ok(Planning {
            planner: Planner::new(beliefs, agent, budget)?,
            walked: walks(beliefs)?,
            triggers: Vec::new(),
            due: true,
            next: None,
            beliefs: beliefs.clone(),
            fresh: false,
            held: false,
        })
    }

    /// Hold the agent, or let it go and say how the wanting ended.
    fn keep(&mut self, pass: &mut Pass<'_>) -> Result<(), Error> {
        let who = "planning";
        let planner = &self.planner;
        let standing = planner.standing(pass.now)?;
        let walking = planner.walking()?;
        let desire = planner.holds_a_desire()?;
        let settle = |pass: &mut Pass<'_>, outcome: &str| {
            if desire {
                pass.hold(who);
            } else {
                pass.release(who, Some(outcome));
            }
        };
        if standing.is_empty() && walking.is_empty() {
            settle(pass, MET);
            return Ok(());
        }
        if !walking.is_empty() && self.walked {
            pass.hold(who);
            return Ok(());
        }
        let unplanned: Vec<&String> = standing.iter().filter(|w| !walking.contains(*w)).collect();
        if unplanned.is_empty() {
            settle(pass, PLANNED);
            return Ok(());
        }
        if planner.exhausted()? {
            self.due = true;
            pass.again();
            pass.hold(who);
            return Ok(());
        }
        log::error!(
            "{}: {} want(s) stand and nothing this agent holds reaches them: {}",
            pass.agent,
            unplanned.len(),
            unplanned.iter().map(|w| local_of(w)).collect::<Vec<_>>().join(", ")
        );
        let unplanned: Vec<String> = unplanned.into_iter().cloned().collect();
        planner.unreachable(&unplanned, pass.now)?;
        settle(pass, UNREACHABLE);
        Ok(())
    }
}

/// Whether the self plays a role beneath `execution:Executor`, read off its self graph: what it publishes is walked.
fn walks(beliefs: &Store) -> Result<bool, Error> {
    let selves = beliefs.graphs_of(&[SELF_GRAPH], &Within::default())?;
    let selves: Vec<&str> = selves.iter().map(String::as_str).collect();
    for row in beliefs.rows(ROLES_Q, &selves)? {
        if let Some(kind) = iri(&row, "kind")
            && beliefs.closed(&kind)?.iter().any(|c| c == EXECUTOR)
        {
            return Ok(true);
        }
    }
    Ok(false)
}

/// PLANNING STARTING ITSELF on a runtime: its wait ends on its trigger's events and a head asked, its policy decides
/// after whatever it heard, and its task is spawned. The part is lent, so whoever keeps it reads it between runs.
pub fn start(runtime: &mut Runtime, part: &Arc<Mutex<Planning>>) -> Result<(), Error> {
    let part = part.clone();
    let mut wait = runtime.wait("planning");
    wait.every(0.0, PLAN);
    wait.hears(PLANNING_TRIGGER, REOPEN);
    wait.hears(HEAD_ASKED, CHECK);
    part.lock().expect("a part nobody poisoned").planner.watch = wait.watch();
    runtime.spawn(wait, move |wait| policy(part, wait));
    Ok(())
}

/// PLANNING'S TASK: it waits for an event beneath its trigger or the instant it is next due, and decides.
async fn policy(part: Arc<Mutex<Planning>>, mut wait: Wait) {
    while let Some((woke, mut pass)) = wait.next().await {
        let mut planning = part.lock().expect("a part nobody poisoned");
        let wrote = match woke {
            Woke::Due(_) => planning.plan(&mut pass),
            Woke::Event(tag, event) => planning.heard_event(tag, &event, &mut pass),
            _ => Ok(Vec::new()),
        };
        pass.done(wrote);
    }
}

impl Planning {
    /// What planning's policy does of a trigger: plan at the pass, keeping the walking wants it names to search
    /// again; and ask for the pass at once where it names any.
    fn heard_event(&mut self, job: usize, event: &Heard, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        //  A HEAD ASKED IS CHECKED against the present at the instant it is taken, and answered: no planning, and
        //  no trigger of one.
        if job == CHECK {
            let Some(head) = event.named(HEAD) else {
                return Ok(Vec::new());
            };
            let at = event
                .about
                .iter()
                .find_map(|(p, t)| match t {
                    oxigraph::model::Term::Literal(l) if p == AT_TIME => l.value().parse().ok(),
                    _ => None,
                })
                .unwrap_or(pass.now);
            let blocked = self.planner.check(head.as_str(), at)?;
            pass.emit(&HeadChecked {
                head: head.as_str().to_string(),
                blocked,
                at,
            });
            return Ok(Vec::new());
        }
        self.triggers.push(event.node.clone());
        let wants: Vec<String> = event.all(REOPENS).iter().map(|w| w.as_str().to_string()).collect();
        if !wants.is_empty() || self.news(event)? {
            (self.fresh, self.held) = (false, false);
        } else if self.fresh && self.failed(event)? {
            self.held = true;
        }
        if !wants.is_empty() {
            self.planner.reopen(wants);
            pass.again();
        }
        Ok(Vec::new())
    }

    /// Whether `event` is news to planning: a revision that changed a state, or revised a belief that is not the
    /// agent's own record of what it did - a committed step the executor wrote of a plan is none. What execution
    /// says of a plan is none either.
    fn news(&self, event: &Heard) -> Result<bool, Error> {
        if event.kind != REVISED {
            return Ok(false);
        }
        if !event.all(CHANGED).is_empty() {
            return Ok(true);
        }
        let revised = event.all(REVISED_SOURCE);
        let Some(cat) = self.beliefs.catalogue()? else {
            return Ok(!revised.is_empty());
        };
        if revised.is_empty() {
            return Ok(false);
        }
        let graphs = revised
            .iter()
            .map(|g| format!("<{}>", g.as_str()))
            .collect::<Vec<_>>()
            .join(" ");
        let text = bind(NEWS_Q, &[("cat", Value::iri(cat)), ("revised", Value::Raw(graphs))])?;
        Ok(!self.beliefs.rows(&text, &[])?.is_empty())
    }

    /// Whether `event` says an intention ended `failed`, read off the intention's own row.
    fn failed(&self, event: &Heard) -> Result<bool, Error> {
        let Some(intention) = event.named(INTENTION) else {
            return Ok(false);
        };
        let text = bind(OUTCOME_Q, &[("intention", Value::iri(intention.as_str()))])?;
        Ok(self
            .beliefs
            .rows(&text, &[])?
            .iter()
            .any(|r| orexis::store::value(r, "o").as_deref() == Some("failed")))
    }

    /// PLANNING'S POLICY: plan where a trigger was heard since the last planning, the present reached the next ground
    /// it laid, or it is due whatever was heard; and otherwise nothing, the agent held or let go as it last was. A
    /// PLAN THAT FAILED IN THE PRESENT IT WAS FOUND IN IS NOT PLANNED AGAIN UNTIL NEWS IS HEARD (#1145): the search
    /// would find it again, and a step that fails as it is taken would be planned, taken and failed for ever.
    fn plan(&mut self, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        let reached = self.next.is_some_and(|next| next <= pass.now);
        let again = !self.triggers.is_empty() && !self.held;
        if !self.due && !reached && !again {
            if let Some(next) = self.next {
                pass.wake_at(next);
            }
            pass.lap("plan");
            return Ok(Vec::new());
        }
        self.due = false;
        let triggers = std::mem::take(&mut self.triggers);
        let activity = pass.begin(PLANNING_ACTIVITY, &triggers);
        //  A SEARCH IS SECONDS: the tasks beside it keep their workers.
        let written = long(|| self.planner.plan(pass.now))?;
        if !self.planner.published.is_empty() {
            self.fresh = true;
        }
        self.keep(pass)?;
        self.next = self.planner.next_ground(pass.now)?;
        if let Some(next) = self.next {
            pass.wake_at(next);
        }
        pass.lap("plan");
        pass.end(activity);
        Ok(written)
    }
}
