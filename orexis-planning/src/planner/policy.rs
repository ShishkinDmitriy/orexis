//! PLANNING'S POLICY, the planner's as the package's core: what it does of a trigger heard and of a head asked, when
//! it plans, and whether it holds the agent once it has.

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::ontology::SELF_GRAPH;
use orexis::store::{Store, Within, iri};
use orexis::task::{Heard, MET, PLANNED, Turn, UNREACHABLE, long};
use orexis_belief::ontology::{CHANGED, REVISED, REVISED_SOURCE};

use orexis::activity::Activity;

use super::{Out, Planner, Searched};
use crate::admit::local_of;
use crate::events::HeadChecked;
use crate::ontology::{PLANNING_ACTIVITY, REOPENS};

pub(crate) const REOPEN: usize = 1;
pub(crate) const CHECK: usize = 2;

/// A head execution asks about as it is taken, and what that says: the head and the instant.
pub(crate) const HEAD_ASKED: &str = "http://example.org/orexis/execution#HeadAsked";
const HEAD: &str = "http://example.org/orexis/execution#head";
const INTENTION: &str = "http://example.org/orexis/execution#intention";
const AT_TIME: &str = "http://www.w3.org/ns/prov#atTime";

/// Whoever walks what planning publishes: a role of this class, or one beneath it.
const EXECUTOR: &str = "http://example.org/orexis/execution#Executor";

impl Planner {
    /// What planning's policy does of a trigger: plan at the pass, keeping the walking wants it names to search
    /// again; and ask for the pass at once where it names any.
    pub(crate) fn heard_event(&mut self, job: usize, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
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
            let blocked = self.check(head.as_str(), at)?;
            pass.emit(&HeadChecked {
                head: head.as_str().to_string(),
                blocked,
                at,
            });
            return Ok(Vec::new());
        }
        let wants: Vec<String> = event.all(REOPENS).iter().map(|w| w.as_str().to_string()).collect();
        let news = self.news(event)?;
        if !wants.is_empty() || self.calls(event)? {
            self.triggers.push(event.node.clone());
        }
        if !wants.is_empty() || news {
            (self.fresh, self.held) = (false, false);
        } else if self.fresh && self.failed(event)? {
            self.held = true;
        }
        if !wants.is_empty() {
            self.reopen(wants);
        }
        Ok(Vec::new())
    }

    /// Whether `event` is news to planning: a revision that changed a state, or revised a belief that is not the
    /// agent's own record of what it did - a committed step the executor wrote of a plan is none. What execution
    /// says of a plan is none either.
    fn news(&self, event: &Heard) -> Result<bool, Error> {
        /// The graphs of `$revised` that are not the agent's own record of what it did: a belief that came to it.
        const NEWS_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
        SELECT ?g WHERE { GRAPH $cat { VALUES ?g { $revised } ?g a orexis:Graph .
                                       FILTER NOT EXISTS { ?g orexis:arrivedBy orexis:Recorded } } } LIMIT 1";
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
        //  WHERE THE AGENT FORESEES, A READING'S NUMBER IS READ: the flows are integrated from the latest, so a
        //  percept revised is news though it changed no state - a reading a hair below its bound brought a foreseen
        //  crossing to the present. Where it does not, nothing planning reads is in a percept.

        let graphs = revised
            .iter()
            .map(|g| format!("<{}>", g.as_str()))
            .collect::<Vec<_>>()
            .join(" ");
        let text = bind(NEWS_Q, &[("cat", Value::iri(cat)), ("revised", Value::Raw(graphs))])?;
        Ok(!self.beliefs.rows(&text, &[])?.is_empty())
    }

    /// THE POLICY'S JUDGMENT: whether `event` calls for a planning. Every event beneath the trigger but a revision was
    /// said to planning on purpose, and does. A revision does where it changed a state, or revised a belief a search
    /// reads - a peer's places laid, the world as a step wrote it - never a percept, which is no belief, nor the
    /// executor's own committed step, a forecast of what the plan already says. AND WHERE THE AGENT FORESEES, EVERY
    /// REVISION DOES: its flows are integrated from the latest reading's number and over each committed step, so either
    /// moves the grounds ahead though no state changed - with no planning after a dose was committed, planning woke at
    /// a ground the dose had taken away and read the want reached.
    fn calls(&self, event: &Heard) -> Result<bool, Error> {
        /// Whether any of the graphs revised is a belief a search reads: no percept, which is no belief, and no
        /// forecast the agent recorded of its own act, the executor's committed step. What a step wrote of the world as
        /// the agent took it is recorded too, and is the present.
        const BELIEVED_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
        SELECT ?g WHERE { GRAPH $cat { VALUES ?g { $revised } ?g a orexis:BeliefGraph .
                                       FILTER NOT EXISTS { ?g a orexis:ForecastGraph ; orexis:arrivedBy orexis:Recorded } } } LIMIT 1";
        if event.kind != REVISED || !event.all(CHANGED).is_empty() || self.foresee.is_some() {
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
        let text = bind(BELIEVED_Q, &[("cat", Value::iri(cat)), ("revised", Value::Raw(graphs))])?;
        Ok(!self.beliefs.rows(&text, &[])?.is_empty())
    }

    /// Whether `event` says an intention ended `failed` with no step of it taken, read off the intention's own rows.
    fn failed(&self, event: &Heard) -> Result<bool, Error> {
        /// How the intention `$intention` ended where none of its steps was taken, in execution's words: it ended
        /// before the agent acted, so neither the world nor the hour is other than the plan was found in. One that
        /// failed after a step was taken - a landing waited out - is planned again, since time has passed.
        const OUTCOME_Q: &str = "PREFIX execution: <http://example.org/orexis/execution#>
        PREFIX orexis: <http://example.org/orexis#>
        SELECT ?o WHERE { GRAPH ?cat { ?cat a orexis:CatalogueGraph . ?g a execution:IntentionGraph }
                          GRAPH ?g { $intention execution:outcome ?o .
                                     FILTER NOT EXISTS { $intention execution:step ?step .
                                                         ?act execution:of ?step ; execution:taken true } } }";
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
    pub(crate) fn planning(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        //  A PLANNING WHOSE SEARCHES ARE OUT is finished as they come back (`found`), and what was heard meanwhile is
        //  planned once it is.
        if self.out.is_some() {
            pass.lap("plan");
            return Ok(Vec::new());
        }
        let reached = self.next.is_some_and(|next| next <= pass.now);
        let reached = reached || self.continues.is_some_and(|at| at <= pass.now);
        let again = !self.triggers.is_empty() && !self.held;
        if !self.due && !reached && !again {
            if let Some(next) = self.next {
                pass.wake_at(next);
            }
            if let Some(at) = self.continues {
                pass.wake_at(at);
            }
            pass.lap("plan");
            return Ok(Vec::new());
        }
        self.due = false;
        let triggers = std::mem::take(&mut self.triggers);
        let activity = pass.begin(PLANNING_ACTIVITY, &triggers);
        if self.threads.is_some() {
            return self.send_out(activity, pass);
        }
        //  A SEARCH IS SECONDS: the tasks beside it keep their workers.
        let written = long(|| self.plan(pass.now))?;
        self.planned(activity, pass)?;
        Ok(written)
    }

    /// EVERY SCOPE PREPARED AND ITS SEARCH SET GOING ON A THREAD OF ITS OWN, where the agent runs on several: the
    /// task steps out of the planning, which goes on until the last search is back, and holds the agent meanwhile.
    fn send_out(&mut self, activity: Activity, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let (planning, written) = self.begin_pass(pass.now)?;
        let mut handed = Vec::new();
        for scope in planning.scopes_all.clone() {
            handed.push(self.prepare(&scope, &planning)?);
        }
        let threads = self.threads.as_ref().expect("threads to send a search out on");
        let waiting = handed.len();
        log::debug!("{}: {} scope(s) searched on threads of their own", self.id, waiting);
        for mut searching in handed {
            searching.searcher.within = Some(activity.node.clone());
            let (back, working) = (threads.back.clone(), threads.events.working());
            tokio::task::spawn_blocking(move || {
                let _ = back.send((searching.search(), working));
            });
        }
        pass.step_out(&activity);
        pass.hold("planning");
        pass.lap("plan");
        self.out = Some(Out {
            activity,
            pass: planning,
            waiting,
        });
        Ok(written)
    }

    /// WHAT A SCOPE'S SEARCH FOUND, BACK FROM ITS THREAD: applied within the planning it is part of, unless what
    /// crossed into its imaginarium has moved in the beliefs while it was out — then it is dropped and planning is
    /// due again; and the planning finished once the last is back.
    pub(crate) fn found(&mut self, found: Result<Searched, Error>, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let found = found?;
        let Some(mut out) = self.out.take() else {
            return Ok(Vec::new());
        };
        pass.step_in(&out.activity);
        let moved = match &found.crossed {
            Some(crossed) => crossed.moved(&self.beliefs)?,
            None => None,
        };
        let written = match moved {
            None => {
                log::debug!("{}: {}'s search is back", self.id, local_of(&found.scope));
                self.apply(found, &mut out.pass.searched)?
            }
            Some(graph) => {
                log::info!(
                    "{}: {} moved while {}'s search was out, so what it found is dropped and it is planned again",
                    self.id,
                    graph,
                    local_of(&found.scope)
                );
                self.due = true;
                Vec::new()
            }
        };
        out.waiting -= 1;
        if out.waiting > 0 {
            pass.step_out(&out.activity);
            self.out = Some(out);
            return Ok(written);
        }
        self.end_pass(&out.pass.searched);
        self.planned(out.activity, pass)?;
        Ok(written)
    }

    /// THE PLANNING IS DONE: the agent held or let go, the next ground it laid waited for, and its activity ended.
    fn planned(&mut self, activity: Activity, pass: &mut Turn<'_>) -> Result<(), Error> {
        if !self.published.is_empty() {
            self.fresh = true;
        }
        self.keep(pass)?;
        self.next = self.next_ground(pass.now)?;
        if let Some(next) = self.next {
            pass.wake_at(next);
        }
        if self.due {
            pass.again();
        }
        pass.lap("plan");
        pass.end(activity);
        Ok(())
    }

    /// Hold the agent, or let it go and say how the wanting ended.
    fn keep(&mut self, pass: &mut Turn<'_>) -> Result<(), Error> {
        let who = "planning";
        //  WHEN A SEARCH CUT SHORT IS NEXT DUE is this planning's to say, and nothing an earlier one said stands.
        self.continues = None;
        let standing = self.standing(pass.now)?;
        let walking = self.walking()?;
        let desire = self.holds_a_desire()?;
        let settle = |pass: &mut Turn<'_>, outcome: &str| {
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
        let unplanned: Vec<&String> = standing.iter().filter(|w| !walking.contains(*w)).collect();
        //  A SEARCH THE BUDGET CUT SHORT IS CONTINUED WHEN ITS NEXT BUDGET IS DUE, whatever else is walking: with a plan
        //  walked beside it, nothing else would ask for the next planning, and the want stood unplanned until
        //  something was heard. Continued at once, the budget was no ceiling.
        if !unplanned.is_empty() && self.exhausted()? {
            self.continues = self.continues_at();
            match self.continues {
                Some(at) => pass.wake_at(at),
                None => {
                    self.due = true;
                    pass.again();
                }
            }
            pass.hold(who);
            return Ok(());
        }
        if !walking.is_empty() && self.walked {
            pass.hold(who);
            return Ok(());
        }
        if unplanned.is_empty() {
            settle(pass, PLANNED);
            return Ok(());
        }
        log::error!(
            "{}: {} want(s) stand and nothing this agent holds reaches them: {}",
            pass.agent,
            unplanned.len(),
            unplanned.iter().map(|w| local_of(w)).collect::<Vec<_>>().join(", ")
        );
        let unplanned: Vec<String> = unplanned.into_iter().cloned().collect();
        self.unreachable(&unplanned, pass.now)?;
        settle(pass, UNREACHABLE);
        Ok(())
    }
}

/// Whether the self plays a role beneath `execution:Executor`, read off its self graph: what it publishes is walked.
pub(super) fn walks(beliefs: &Store) -> Result<bool, Error> {
    const ROLES_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
        SELECT DISTINCT ?kind WHERE { ?me a orexis:Self ; orexis:plays ?role . ?role a ?kind }";
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
