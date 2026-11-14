//! COORDINATION'S PART, as `agent/coordination/create.py` makes it (a-package-starts-itself). What it asks
//! and answers it believes it said by speech's `said`, beneath it, and says as `coordination:Told` beneath speech's
//! speaking trigger, so speech tells it. A draw it has won is said as `coordination:DrawWon`, beneath
//! planning's trigger, naming in planning's words the walking wants to plan again. STARTED, it mints the agent's secret where it holds none; answers every question heard as it
//! arrives; concludes its conflicts and lays what it yields to as each question or answer arrives; and every pass asks
//! the peers in range, concludes and lays again — after planning and execution, so what it says of its future is what
//! the pass left walking. A draw the agent concludes it has WON reopens the walking wants whose plans change a value
//! on the key of the constraint the draw was over, since nothing a belief makes impossible reopens a plan that has
//! only been made slower than it need be.
//!
//! WHAT IT SAYS HAPPENED goes to whoever watches the agent, each set where it changed since it was last said: the
//! holdings it asked with, those it laid of each peer as said or foreseen, and every conflict as concluded.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::Arc;

use orexis::Error;
use orexis::document::Document;
use orexis::events::Watch;
use orexis::ontology::local_of;
use orexis::store::Store;
use orexis::task::{Arrived, Every, Handed, Heard, Hears, Package, Task, Turn, Woke, sooner};
use oxsdatatypes::DateTime;

use crate::answer::answer;
use crate::ask::ask;
use crate::conclude::{conclude, conflicts, wins};
use crate::events::{ASKED, Concluded, DrawWon, FORESEEN, Held, SAID, Told};
use crate::holdings::{heard, walking_over};
use crate::lay::{laid, lay};
use crate::mint::mint;
use crate::ontology::{ANSWER_GRAPH, QUESTION_GRAPH};
use crate::ontology::{COORDINATING, COORDINATING_TRIGGER, COORDINATION};

const PASS: usize = 0;
const QUESTIONED: usize = 1;
const ANSWERED: usize = 2;
const MINTED: usize = 3;

/// Coordination's part.
pub struct Coordination {
    beliefs: Store,
    me: String,
    pending: Vec<String>,
    /// Whoever watches the agent.
    pub watch: Watch,
    /// What was last said of each set, so a set is said where it changed.
    told: BTreeMap<(String, String, String), Vec<crate::holdings::Holding>>,
    concluded: Option<Vec<crate::events::Conflict>>,
    /// The events heard beneath its trigger since it last coordinated.
    triggers: Vec<oxigraph::model::NamedNode>,
    /// Whether it has coordinated yet, when it last asked anything, and the instant a patience running calls for it
    /// next, while it is asking or in conflict.
    started: bool,
    asked: Option<DateTime>,
    next: Option<DateTime>,
}

impl Coordination {
    pub fn new(beliefs: &Store, me: &str) -> Self {
        Coordination {
            beliefs: beliefs.clone(),
            me: me.to_string(),
            pending: Vec::new(),
            watch: Watch::default(),
            told: BTreeMap::new(),
            concluded: None,
            triggers: Vec::new(),
            started: false,
            asked: None,
            next: None,
        }
    }

    fn said(&mut self, peer: &str, document: &Document, at: DateTime) -> Result<Vec<String>, Error> {
        if self.watch.connected() {
            let scratch = Store::new(Arc::new(self.beliefs.namespaces().clone()))?;
            scratch
                .engine()
                .extend(document.quads().iter().cloned())
                .map_err(|e| Error::Evaluation(e.to_string()))?;
            let over = format!("{COORDINATION}over");
            let mut asked: BTreeMap<String, String> = BTreeMap::new();
            for q in document.quads() {
                if q.predicate.as_str() == over
                    && let (oxigraph::model::GraphName::NamedNode(g), oxigraph::model::Term::NamedNode(c)) =
                        (&q.graph_name, &q.object)
                {
                    asked
                        .entry(g.as_str().to_string())
                        .or_insert_with(|| c.as_str().to_string());
                }
            }
            for (graph, constraint) in asked {
                let holdings = heard(&scratch, &graph)?;
                self.tell_held(Held {
                    at,
                    origin: ASKED,
                    peer: peer.to_string(),
                    constraint,
                    holdings,
                });
            }
        }
        let graphs: Vec<String> = document.kinds().into_keys().collect();
        log::info!(
            "{}: says {} to {}",
            local_of(&self.me),
            graphs
                .iter()
                .map(|g| g.split("/coordination/").last().unwrap_or(g))
                .collect::<Vec<_>>()
                .join(", "),
            local_of(peer)
        );
        let statements = orexis_speech::said::said(&self.beliefs, &self.me, document)?;
        self.watch.emit(&Told {
            statements: statements.clone(),
            to: peer.to_string(),
        });
        Ok(statements)
    }

    /// When to coordinate again with nothing heard: a quarter patience on while the agent asked within the last two
    /// patiences or stands in a conflict, since a question expires and a peer turns silent by the patience alone.
    fn wait(&mut self, asking: bool, now: DateTime) -> Result<(), Error> {
        let patience = crate::ask::patience(&self.beliefs)?;
        self.started = true;
        if asking {
            self.asked = Some(now);
        }
        let recent = self
            .asked
            .and_then(|l| l.checked_add_day_time_duration(orexis::clock::seconds(2.0 * patience)))
            .is_some_and(|until| now <= until);
        let engaged = recent || !conflicts(&self.beliefs, &self.me)?.is_empty();
        self.next = if engaged {
            now.checked_add_day_time_duration(orexis::clock::seconds(patience / 4.0))
        } else {
            None
        };
        Ok(())
    }

    /// Say `event` where what it says differs from what was last said of the same set.
    fn tell_held(&mut self, event: Held) {
        let key = (event.origin.to_string(), event.peer.clone(), event.constraint.clone());
        if self.told.get(&key) != Some(&event.holdings) {
            self.told.insert(key, event.holdings.clone());
            self.watch.emit(&event);
        }
    }

    /// Conclude the conflicts and lay what the agent yields to; a draw won reopens what it decides.
    fn yielded(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let (store, me, at) = (&self.beliefs.clone(), self.me.clone(), pass.now);
        let before = wins(store, &me)?;
        let mut written = conclude(store, &me, at)?;
        if self.watch.connected() {
            let now = conflicts(store, &me)?;
            if self.concluded.as_ref() != Some(&now) {
                self.concluded = Some(now.clone());
                self.watch.emit(&Concluded { at, conflicts: now });
            }
        }
        let won: Vec<String> = wins(store, &me)?
            .into_iter()
            .filter(|(draw, _)| !before.contains_key(draw))
            .map(|(_, constraint)| constraint)
            .collect();
        written.extend(lay(store, &me, at)?);
        if self.watch.connected() {
            for ((peer, constraint), (said, foreseen)) in laid(store, &me)? {
                for (origin, holdings) in [(SAID, said), (FORESEEN, foreseen)] {
                    self.tell_held(Held {
                        at,
                        origin,
                        peer: peer.clone(),
                        constraint: constraint.clone(),
                        holdings,
                    });
                }
            }
        }
        let mut wants = BTreeSet::new();
        for constraint in &won {
            wants.extend(walking_over(store, constraint)?);
        }
        if !wants.is_empty() {
            log::info!(
                "{}: won a draw, so asks that {} be planned again",
                local_of(&me),
                wants.iter().map(|w| local_of(w)).collect::<Vec<_>>().join(", ")
            );
            self.watch.emit(&DrawWon {
                wants: wants.into_iter().collect(),
            });
            pass.again();
        }
        Ok(written)
    }
}

inventory::submit! { Package { name: "coordination", documents: orexis::documents!("ontology.ttl"), start } }

/// THE PACKAGE'S START: its part made and started - what it hears, what it does every so often - and its task.
fn start(handed: &Handed) -> Result<Option<Task>, Error> {
    let me = orexis::boot::selves(&handed.store)?
        .into_iter()
        .next()
        .unwrap_or_default();
    let mut part = Coordination::new(&handed.store, &me);
    let mut hears = handed.events.hears();
    let arrived = handed.arrived();
    let mut timers = Vec::new();
    part.start(handed, &mut hears, &arrived, &mut timers)?;
    Ok(Some(Box::pin(task(handed.clone(), part, hears, arrived, timers))))
}

/// THE PACKAGE'S TASK: it decides as the run begins, then waits for what it hears, an arrival or the instant it is
/// next due; once nothing more waits to be heard it does what it queued for itself and what has fallen due.
async fn task(
    handed: Handed,
    mut part: Coordination,
    mut hears: Hears,
    mut arrived: Arrived,
    mut timers: Vec<(Every, usize)>,
) -> Result<(), Error> {
    let mut heard = None;
    let mut due = None;
    loop {
        let mut turn = handed.turn();
        match heard.take() {
            Some(Woke::Event(tag, event)) => {
                let wrote = part.heard_event(tag, &event, &mut turn);
                turn.done(wrote)?;
            }
            Some(Woke::Graphs(tag, graphs)) => {
                let wrote = part.heard(tag, &graphs, &mut turn);
                turn.done(wrote)?;
            }
            _ => {}
        }
        if hears.is_empty() {
            let wrote = part.queued(&mut turn);
            turn.done(wrote)?;
            for (every, tag) in &mut timers {
                if every.due(turn.now) {
                    let wrote = part.run(*tag, &mut turn);
                    turn.done(wrote)?;
                    let wrote = part.queued(&mut turn);
                    turn.done(wrote)?;
                }
            }
            due = timers
                .iter()
                .fold(turn.next(), |soonest, (every, _)| sooner(soonest, every.at()));
        }
        heard = tokio::select! {
            biased;
            _ = handed.stopped() => break,
            woke = hears.next() => match woke {
                Some(woke) => Some(woke),
                None => break,
            },
            _ = arrived.wait() => None,
            _ = handed.sleep_until(due) => None,
        };
    }
    Ok(())
}

impl Coordination {
    /// What it queued for itself, each in turn and what each wrote told, until nothing is left.
    fn queued(&mut self, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        loop {
            let jobs = self.submitted();
            if jobs.is_empty() {
                return Ok(Vec::new());
            }
            for job in jobs {
                let wrote = self.run(job, pass)?;
                pass.told(wrote)?;
            }
        }
    }

    fn start(
        &mut self,
        handed: &Handed,
        hears: &mut Hears,
        arrived: &Arrived,
        timers: &mut Vec<(Every, usize)>,
    ) -> Result<(), Error> {
        let _ = (&handed, &hears, &arrived, &timers);
        self.watch = handed.events.watch().clone();
        self.pending.extend(mint(&self.beliefs, &self.me)?);
        hears.graph(QUESTION_GRAPH, QUESTIONED);
        hears.graph(ANSWER_GRAPH, ANSWERED);
        timers.push((Every::new(0.0), PASS));
        hears.event(COORDINATING_TRIGGER, PASS);
        Ok(())
    }

    /// What coordination's policy does of a trigger: coordinate at the pass.
    fn heard_event(&mut self, _job: usize, event: &Heard, _pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        self.triggers.push(event.node.clone());
        Ok(Vec::new())
    }

    fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match job {
            MINTED => Ok(std::mem::take(&mut self.pending)),
            PASS => {
                //  COORDINATION'S POLICY: coordinate where a trigger was heard since, at the first pass, or where a
                //  patience it is waiting on may have run; and otherwise nothing.
                let due = !self.started || self.next.is_some_and(|n| n <= pass.now);
                if !due && self.triggers.is_empty() {
                    if let Some(next) = self.next {
                        pass.wake_at(next);
                    }
                    return Ok(Vec::new());
                }
                let triggers = std::mem::take(&mut self.triggers);
                let activity = pass.begin(COORDINATING, &triggers);
                let mut written = Vec::new();
                let asked = ask(&self.beliefs, &self.me, pass.now)?;
                let asking = !asked.is_empty();
                for (peer, document) in asked {
                    written.extend(self.said(&peer, &document, pass.now)?);
                }
                written.extend(self.yielded(pass)?);
                self.wait(asking, pass.now)?;
                if let Some(next) = self.next {
                    pass.wake_at(next);
                }
                pass.end(activity);
                Ok(written)
            }
            _ => Ok(Vec::new()),
        }
    }

    /// The questions or answers written together: each question answered, and what they make of the draws
    /// concluded once.
    fn heard(&mut self, job: usize, graphs: &[String], pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let mut written = Vec::new();
        if job == QUESTIONED {
            for graph in graphs {
                if let Some((peer, document)) = answer(&self.beliefs, &self.me, graph, pass.now)? {
                    written.extend(self.said(&peer, &document, pass.now)?);
                }
            }
        }
        written.extend(self.yielded(pass)?);
        Ok(written)
    }

    fn submitted(&mut self) -> Vec<usize> {
        if self.pending.is_empty() {
            Vec::new()
        } else {
            vec![MINTED]
        }
    }
}
