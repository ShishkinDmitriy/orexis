//! THE RUNTIME: one agent's process, a lifecycle container for its packages' parts, run pass by pass — as
//! `agent/runtime.py`'s `Runtime` runs them (a-package-starts-itself). A part is started, asks for what it waits for
//! — so far a timer, `every` so many seconds of the one timeline — and is run when that falls due; a pass runs every
//! part due, in the order of the pass, on the one thread, the mind. The run ends when nothing holds the agent, as the
//! last to let go said: `met`, `planned` or `unreachable`; or when the passes ran out, `unfinished`.
//!
//! A PART HEARS A KIND OF GRAPH WRITTEN (`on`), as Python's `runtime.on` offers it: every graph a job answers it
//! wrote is told to each part listening for a kind the catalogue says it is, and what that part writes in turn is
//! told the same way — how a package answers another's work with neither naming the other. And A PART QUEUES A JOB
//! (`submitted`), which runs after the jobs queued before it in the same drain, as Python's `submit` queues one.
//!
//! A TRANSPORT'S THREAD HANDS THE PASS WHAT ARRIVED through the member's inbox: what a client received waits there,
//! and the member's part queues a job per message when the runtime asks what it `submitted`, so a message is handled
//! on the one thread the store is written from.
//!
//! A PART HEARS AN EVENT BY ITS CLASS (`hears`), the class and every class the vocabulary puts beneath it, after the
//! job that said it, in the order said; and A PASS BEGINS AND ENDS AN ACTIVITY, saying its start and its end
//! (packages-meet-by-events-policies-and-activities).
//!
//! WHAT WAITS IS A TASK, AND THE MIND WAITS FOR AN ARRIVAL: a part asks for a `task` as it starts, which holds no part
//! and writes no belief, and runs among the tasks of the process, built the first time one is asked for. What arrives
//! rings the `Wake`, so a pass that moved nothing waits the poll or the next arrival, whichever comes first; a timer
//! still falls due only at a pass, so the poll stays as their ceiling (the-agent-moves-to-rust-one-package-at-a-time).

use std::cell::RefCell;
use std::collections::{BTreeMap, HashMap, VecDeque};
use std::future::Future;
use std::rc::Rc;
use std::sync::{Arc, Condvar, Mutex};
use std::time::Duration;

use oxsdatatypes::DateTime;

use oxigraph::model::{NamedNode, Term};

use crate::Error;
use crate::activity::{Activity, Ended, Started};
use crate::clock::{Clock, seconds};
use crate::events::{Event, Laps, Mark, Number, Watch, round6};
use crate::store::Store;

/// How a run ends.
pub const MET: &str = "met";
pub const PLANNED: &str = "planned";
pub const UNREACHABLE: &str = "unreachable";
pub const UNFINISHED: &str = "unfinished";

/// The measurement a pass is reported under, which the metrics part writes its window after.
pub const PASS_METRIC: &str = "pass";

/// A pass, in real seconds, whole and by part — the jobs queued run to the last (`drain`), planning, walking; a part
/// a pass does not reach is not in it — with how large the belief base is, in quads, and how long the process has run.
#[derive(Clone, Debug, PartialEq)]
pub struct Passed {
    pub duration_s: f64,
    pub laps: Vec<(String, f64)>,
    pub quads: Option<i64>,
    pub uptime_s: f64,
}

impl Event for Passed {
    fn metric(&self) -> Option<&'static str> {
        Some(PASS_METRIC)
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        let lap = |part: &str| self.laps.iter().find(|(n, _)| n == part).map(|(_, s)| *s);
        vec![
            ("duration_s", Mark::Value(Some(self.duration_s))),
            ("drain_s", Mark::Value(lap("drain_s"))),
            ("plan_s", Mark::Value(lap("plan_s"))),
            ("execute_s", Mark::Value(lap("execute_s"))),
            ("quads", Mark::Level(self.quads.map(Number::Int))),
            ("uptime_s", Mark::Level(Some(Number::Float(self.uptime_s)))),
        ]
    }
}

/// When the process began, for how long it has run.
fn started() -> std::time::Instant {
    static STARTED: std::sync::OnceLock<std::time::Instant> = std::sync::OnceLock::new();
    *STARTED.get_or_init(std::time::Instant::now)
}

/// What ends the mind's wait: rung from any thread or task, and remembered until the mind next waits, so an arrival
/// during a pass is not slept through.
#[derive(Clone, Default)]
pub struct Wake(Arc<(Mutex<bool>, Condvar)>);

impl Wake {
    /// Something arrived.
    pub fn ring(&self) {
        let (rung, ringing) = &*self.0;
        if let Ok(mut rung) = rung.lock() {
            *rung = true;
            ringing.notify_one();
        }
    }

    /// Wait until rung, or `longest` passed.
    fn wait(&self, longest: Duration) {
        let (rung, ringing) = &*self.0;
        let Ok(guard) = rung.lock() else { return };
        if let Ok((mut guard, _)) = ringing.wait_timeout_while(guard, longest, |rung| !*rung) {
            *guard = false;
        }
    }
}

/// What a part asks for as it starts.
pub struct Starting<'c> {
    timers: Vec<(f64, usize)>,
    hears: Vec<(String, usize)>,
    events: Vec<(String, usize)>,
    clock: &'c dyn Clock,
    wake: &'c Wake,
    tasks: &'c mut Option<tokio::runtime::Runtime>,
}

impl Starting<'_> {
    /// The instant the part starts at, read off the one timeline — a tick in a test, so read only where needed.
    pub fn now(&self) -> DateTime {
        self.clock.now()
    }

    /// Run the part's `job` for every graph of `kind` written, handed the graph (`Part::heard`).
    pub fn on(&mut self, kind: &str, job: usize) {
        self.hears.push((kind.to_string(), job));
    }

    /// Run the part's `job` for every event of `class` said, or of a class the vocabulary puts beneath it, handed the
    /// event (`Part::heard_event`).
    pub fn hears(&mut self, class: &str, job: usize) {
        self.events.push((class.to_string(), job));
    }

    /// Run the part's `job` at the first pass and again every `seconds` of the one timeline after — every pass where
    /// `seconds` is nought.
    pub fn every(&mut self, seconds: f64, job: usize) {
        self.timers.push((seconds, job));
    }

    /// What ends the mind's wait, for whatever hands it an arrival.
    pub fn wake(&self) -> Wake {
        self.wake.clone()
    }

    /// Run `work` among the process's tasks, from now until it ends or the process does. It waits on the outside and
    /// hands the mind what arrived: it holds no part and writes no belief.
    pub fn task(&mut self, work: impl Future<Output = ()> + Send + 'static) -> Result<(), Error> {
        if self.tasks.is_none() {
            let built = tokio::runtime::Builder::new_multi_thread()
                .worker_threads(1)
                .thread_name("orexis-tasks")
                .enable_all()
                .build()
                .map_err(|e| Error::Evaluation(format!("the tasks could not start: {e}")))?;
            *self.tasks = Some(built);
        }
        if let Some(tasks) = self.tasks.as_ref() {
            tasks.spawn(work);
        }
        Ok(())
    }
}

/// What a part is handed when it runs: the instant the pass stands at, and the agent's life to keep or let go.
pub struct Pass<'r> {
    pub now: DateTime,
    pub agent: &'r str,
    held: &'r mut BTreeMap<String, ()>,
    outcome: &'r mut Option<String>,
    again: &'r mut bool,
    laps: &'r mut Option<Laps>,
    watch: &'r Watch,
}

impl Pass<'_> {
    /// Begin an activity of `kind`, triggered by the entities `triggers` names - what the events heard were about -
    /// and say that it started.
    pub fn begin(&mut self, kind: &'static str, triggers: &[NamedNode]) -> Activity {
        let activity = Activity::begin(kind);
        if self.watch.connected() {
            self.watch.emit(&Started {
                activity: activity.node.clone(),
                kind,
                triggers: triggers.to_vec(),
                at: self.now,
            });
        }
        activity
    }

    /// Say `event` happened, to whoever watches the agent.
    pub fn emit(&self, event: &dyn crate::events::Event) {
        self.watch.emit(event);
    }

    /// End `activity`, and say that it ended.
    pub fn end(&mut self, activity: Activity) {
        if self.watch.connected() {
            self.watch.emit(&Ended {
                activity: activity.node.clone(),
                kind: activity.kind,
                at: self.now,
                duration_s: activity.took(),
            });
        }
    }

    /// Mark the end of a part of the pass, for the pass's event, where anybody watches.
    pub fn lap(&mut self, part: &str) {
        if let Some(laps) = self.laps.as_mut() {
            laps.lap(part);
        }
    }

    /// `who` keeps the agent running.
    pub fn hold(&mut self, who: &str) {
        self.held.insert(who.to_string(), ());
    }

    /// `who` no longer keeps the agent running, and says how its part ended.
    pub fn release(&mut self, who: &str, outcome: Option<&str>) {
        self.held.remove(who);
        if let Some(outcome) = outcome {
            *self.outcome = Some(outcome.to_string());
        }
    }

    /// Pass once more at once, without waiting the poll.
    pub fn again(&mut self) {
        *self.again = true;
    }
}

/// A package's part: started once, run when what it asked for falls due, stopped at the end, the last first.
pub trait Part {
    fn start(&mut self, _starting: &mut Starting) -> Result<(), Error> {
        Ok(())
    }

    /// Run `job` at the pass; the graphs written.
    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error>;

    /// Run `job` for `graph`, written and of a kind the part listens for; the graphs written in turn.
    fn heard(&mut self, _job: usize, _graph: &str, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        Ok(Vec::new())
    }

    /// Run `job` for `event`, said and of a class the part hears; the graphs written in turn.
    fn heard_event(&mut self, _job: usize, _event: &Heard, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
        Ok(Vec::new())
    }

    /// The jobs the part queued since it was last asked, to run in this drain after those queued before them.
    fn submitted(&mut self) -> Vec<usize> {
        Vec::new()
    }

    /// The watch the part says its events to, where it says any: the runtime listens on that one, so what a part says
    /// is heard by the parts that listen whoever assembled them.
    fn watch(&self) -> Option<Watch> {
        None
    }

    fn stop(&mut self) {}
}

/// An event as a part hears it: the name it was said under, its class, and the activity it starts or ends.
#[derive(Clone, Debug, PartialEq)]
pub struct Heard {
    pub node: NamedNode,
    pub kind: String,
    pub activity: Option<(NamedNode, String)>,
    /// What it is about, each under the predicate that says its part (`Event::about`).
    pub about: Vec<(String, Term)>,
}

impl Heard {
    /// The first thing it is about under `predicate`, where it names a node there.
    pub fn named(&self, predicate: &str) -> Option<&NamedNode> {
        self.about.iter().find_map(|(p, t)| match t {
            Term::NamedNode(n) if p == predicate => Some(n),
            _ => None,
        })
    }

    /// Every node it is about under `predicate`, in the order said.
    pub fn all(&self, predicate: &str) -> Vec<&NamedNode> {
        self.about
            .iter()
            .filter_map(|(p, t)| match t {
                Term::NamedNode(n) if p == predicate => Some(n),
                _ => None,
            })
            .collect()
    }
}

struct Timer {
    seconds: f64,
    due: Option<DateTime>,
    part: usize,
    job: usize,
}

/// One agent's process over its beliefs, its parts lent to it in the order a pass runs them.
pub struct Runtime<'p> {
    pub beliefs: &'p Store,
    pub id: String,
    clock: &'p dyn Clock,
    parts: Vec<(String, &'p mut dyn Part)>,
    timers: Vec<Timer>,
    /// (part, kind, job): who hears a kind of graph written, in the order they asked.
    hears: Vec<(usize, String, usize)>,
    /// (part, class, job): who hears an event of a class, in the order they asked.
    listens: Vec<(usize, String, usize)>,
    /// What the watch said since the runtime last looked, once anybody listens.
    said: Rc<RefCell<VecDeque<Heard>>>,
    listening: bool,
    /// Every class each class said is beneath, asked once.
    closed: HashMap<String, Vec<String>>,
    jobs: VecDeque<(usize, usize)>,
    held: BTreeMap<String, ()>,
    outcome: Option<String>,
    again: bool,
    /// WHOEVER WATCHES THE AGENT, hearing each pass where anybody does.
    pub watch: Watch,
    laps: Option<Laps>,
    /// RAISED TO STOP THE RUN, by a signal the process was sent: the run ends before its next pass, `unfinished`, so
    /// whoever runs it stops every part and the last window is written.
    pub halt: Option<Arc<std::sync::atomic::AtomicBool>>,
    wake: Wake,
    /// WHAT WAITS ON THE OUTSIDE, there once a part asks for a task; a run with none builds nothing.
    tasks: Option<tokio::runtime::Runtime>,
}

impl<'p> Runtime<'p> {
    /// The runtime of `id` over `beliefs`, reading the one timeline off `clock`, its parts each started.
    pub fn new(
        beliefs: &'p Store,
        id: &str,
        clock: &'p dyn Clock,
        parts: Vec<(String, &'p mut dyn Part)>,
    ) -> Result<Self, Error> {
        let mut runtime = Runtime {
            beliefs,
            id: id.to_string(),
            clock,
            parts,
            timers: Vec::new(),
            hears: Vec::new(),
            listens: Vec::new(),
            said: Rc::default(),
            listening: false,
            closed: HashMap::new(),
            jobs: VecDeque::new(),
            held: BTreeMap::new(),
            outcome: None,
            again: false,
            watch: Watch::default(),
            laps: None,
            halt: None,
            wake: Wake::default(),
            tasks: None,
        };
        started();
        if let Some(watch) = runtime.parts.iter().find_map(|(_, part)| part.watch()) {
            runtime.watch = watch;
        }
        for (i, (_, part)) in runtime.parts.iter_mut().enumerate() {
            let mut starting = Starting {
                timers: Vec::new(),
                hears: Vec::new(),
                events: Vec::new(),
                clock,
                wake: &runtime.wake,
                tasks: &mut runtime.tasks,
            };
            part.start(&mut starting)?;
            runtime
                .hears
                .extend(starting.hears.into_iter().map(|(kind, job)| (i, kind, job)));
            runtime
                .listens
                .extend(starting.events.into_iter().map(|(class, job)| (i, class, job)));
            runtime
                .timers
                .extend(starting.timers.into_iter().map(|(seconds, job)| Timer {
                    seconds,
                    due: None,
                    part: i,
                    job,
                }));
        }
        Ok(runtime)
    }

    /// The packages whose parts run, in the order a pass runs them.
    pub fn parts(&self) -> Vec<&str> {
        self.parts.iter().map(|(p, _)| p.as_str()).collect()
    }

    /// Run every job queued, and what their writes set off, until none is left; then every part due at `now`, in
    /// the order they asked, the same way: the graphs written.
    pub fn drain(&mut self, now: DateTime) -> Result<Vec<String>, Error> {
        self.watch.stand(now);
        self.listen();
        let mut written = Vec::new();
        self.queue_submitted();
        self.run_jobs(now, &mut written)?;
        if let Some(laps) = self.laps.as_mut() {
            laps.lap("drain");
        }
        for timer in &mut self.timers {
            if timer.due.is_some_and(|due| now < due) {
                continue;
            }
            timer.due = Some(now.checked_add_day_time_duration(seconds(timer.seconds)).unwrap_or(now));
            self.jobs.push_back((timer.part, timer.job));
        }
        self.run_jobs(now, &mut written)?;
        Ok(written)
    }

    fn run_jobs(&mut self, now: DateTime, written: &mut Vec<String>) -> Result<(), Error> {
        while let Some((part, job)) = self.jobs.pop_front() {
            let mut pass = Pass {
                now,
                agent: &self.id,
                held: &mut self.held,
                outcome: &mut self.outcome,
                again: &mut self.again,
                laps: &mut self.laps,
                watch: &self.watch,
            };
            let wrote = self.parts[part].1.run(job, &mut pass)?;
            self.queue_submitted();
            self.wrote(now, wrote, written)?;
            self.tell(now, written)?;
        }
        Ok(())
    }

    /// Hear what the watch says from here on, where any part listens for an event — the watch the runtime has as
    /// its first drain begins, which whoever runs it may have replaced since it was made.
    fn listen(&mut self) {
        if self.listening || self.listens.is_empty() {
            return;
        }
        self.listening = true;
        let said = self.said.clone();
        self.watch.connect(move |event, named| {
            if let Some(kind) = event.kind() {
                said.borrow_mut().push_back(Heard {
                    node: named.clone(),
                    kind: kind.to_string(),
                    activity: event.activity().map(|(a, k)| (a.clone(), k.to_string())),
                    about: event.about().into_iter().map(|(p, t)| (p.to_string(), t)).collect(),
                });
            }
        });
    }

    /// Tell every part listening what was said, in the order said, and what it says in turn.
    fn tell(&mut self, now: DateTime, written: &mut Vec<String>) -> Result<(), Error> {
        loop {
            let Some(event) = self.said.borrow_mut().pop_front() else {
                return Ok(());
            };
            if !self.closed.contains_key(&event.kind) {
                let closed = self.beliefs.closed(&event.kind)?;
                self.closed.insert(event.kind.clone(), closed);
            }
            let classes = &self.closed[&event.kind];
            let due: Vec<(usize, usize)> = self
                .listens
                .iter()
                .filter(|(_, class, _)| classes.contains(class))
                .map(|(part, _, job)| (*part, *job))
                .collect();
            for (part, job) in due {
                let mut pass = Pass {
                    now,
                    agent: &self.id,
                    held: &mut self.held,
                    outcome: &mut self.outcome,
                    again: &mut self.again,
                    laps: &mut self.laps,
                    watch: &self.watch,
                };
                let wrote = self.parts[part].1.heard_event(job, &event, &mut pass)?;
                self.queue_submitted();
                self.wrote(now, wrote, written)?;
            }
        }
    }

    /// Say that `graphs` were written, so whoever listens for their kinds hears it now, and what they write in turn.
    fn wrote(&mut self, now: DateTime, graphs: Vec<String>, written: &mut Vec<String>) -> Result<(), Error> {
        for graph in graphs {
            let mut answered = Vec::new();
            if !self.hears.is_empty() {
                let kinds = self.kinds(&graph)?;
                for h in 0..self.hears.len() {
                    let (part, kind, job) = self.hears[h].clone();
                    if !kinds.contains(&kind) {
                        continue;
                    }
                    let mut pass = Pass {
                        now,
                        agent: &self.id,
                        held: &mut self.held,
                        outcome: &mut self.outcome,
                        again: &mut self.again,
                        laps: &mut self.laps,
                        watch: &self.watch,
                    };
                    answered.extend(self.parts[part].1.heard(job, &graph, &mut pass)?);
                    self.queue_submitted();
                }
            }
            written.push(graph);
            self.wrote(now, answered, written)?;
        }
        Ok(())
    }

    /// Every kind the catalogue says `graph` is.
    fn kinds(&self, graph: &str) -> Result<Vec<String>, Error> {
        let Some(cat) = self.beliefs.catalogue()? else {
            return Ok(Vec::new());
        };
        let text = crate::bind::bind(
            "SELECT ?k WHERE { GRAPH $cat { $g a ?k } }",
            &[
                ("cat", crate::bind::Value::iri(cat)),
                ("g", crate::bind::Value::iri(graph)),
            ],
        )?;
        Ok(self
            .beliefs
            .rows(&text, &[])?
            .iter()
            .filter_map(|r| crate::store::iri(r, "k"))
            .collect())
    }

    fn queue_submitted(&mut self) {
        for (i, (_, part)) in self.parts.iter_mut().enumerate() {
            self.jobs.extend(part.submitted().into_iter().map(|job| (i, job)));
        }
    }

    /// Pass after pass until nobody holds the agent, ending as the last to let go said, or `passes` ran out. A pass
    /// that moved nothing waits the poll or the next arrival, unless a part asked to go again. THE POLL IS REAL SECONDS, as the Python
    /// runtime sleeps it: divided by a fast clock's pace, a courier at pace 30 passed 119 times where it passes 14.
    pub fn run(&mut self, passes: Option<usize>, poll_s: f64) -> Result<String, Error> {
        let mut n = 0;
        while passes.is_none_or(|p| n < p) {
            if self
                .halt
                .as_ref()
                .is_some_and(|h| h.load(std::sync::atomic::Ordering::Relaxed))
            {
                log::info!("{}: stopped, after {n} pass(es)", self.id);
                return Ok(UNFINISHED.to_string());
            }
            n += 1;
            let now = self.clock.now();
            //  THE PASS BEGINS BEFORE ITS LAPS DO, so the first part carries no gap between two reads.
            let began = std::time::Instant::now();
            self.laps = self.watch.connected().then(Laps::default);
            self.again = false;
            self.drain(now)?;
            self.passed(began.elapsed().as_secs_f64())?;
            if self.held.is_empty() {
                log::info!("{}: nothing holds it, after {n} pass(es)", self.id);
                return Ok(self.outcome.clone().unwrap_or_else(|| MET.to_string()));
            }
            if !self.again {
                self.wake.wait(Duration::from_secs_f64(poll_s));
            }
        }
        Ok(UNFINISHED.to_string())
    }

    /// Say the pass, where anybody watches.
    fn passed(&mut self, took: f64) -> Result<(), Error> {
        let Some(laps) = self.laps.take() else { return Ok(()) };
        let quads = i64::try_from(self.beliefs.len()?).ok();
        self.watch.emit(&Passed {
            duration_s: round6(took),
            laps: laps.spent,
            quads,
            uptime_s: (started().elapsed().as_secs_f64() * 1000.0).round() / 1000.0,
        });
        Ok(())
    }

    /// Stop every part, the last first.
    pub fn stop(&mut self) {
        for (_, part) in self.parts.iter_mut().rev() {
            part.stop();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::clock::Manual;
    use crate::transport::Inbox;

    /// Holds the agent for one pass and lets go at the second; a task delivers a message soon after it starts.
    struct Waiting {
        inbox: Inbox,
        passes: usize,
    }

    impl Part for Waiting {
        fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
            self.inbox.wakes(starting.wake());
            let inbox = self.inbox.clone();
            starting.every(0.0, 0);
            starting.task(async move {
                tokio::time::sleep(Duration::from_millis(50)).await;
                inbox.deliver("topic", b"payload", None);
            })
        }

        fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            self.passes += 1;
            if self.passes == 1 {
                pass.hold("waiting");
            } else {
                pass.release("waiting", None);
            }
            Ok(Vec::new())
        }
    }

    #[test]
    fn an_arrival_from_a_task_ends_the_minds_wait() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = Manual::at("2026-11-09T12:00:00Z".parse().unwrap());
        let mut part = Waiting {
            inbox: Inbox::default(),
            passes: 0,
        };
        let parts: Vec<(String, &mut dyn Part)> = vec![("waiting".to_string(), &mut part)];
        let mut runtime = Runtime::new(&store, "urn:test:me", &clock, parts).unwrap();
        let began = std::time::Instant::now();
        assert_eq!(runtime.run(None, 60.0).unwrap(), MET);
        assert!(began.elapsed() < Duration::from_secs(30), "the poll was slept out");
    }

    #[test]
    fn a_ring_during_a_pass_is_not_slept_through() {
        let wake = Wake::default();
        wake.ring();
        let began = std::time::Instant::now();
        wake.wait(Duration::from_secs(60));
        assert!(began.elapsed() < Duration::from_secs(30));
    }

    #[test]
    fn a_run_with_no_task_builds_none() {
        struct Idle;
        impl Part for Idle {
            fn run(&mut self, _job: usize, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
                Ok(Vec::new())
            }
        }
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = Manual::at("2026-11-09T12:00:00Z".parse().unwrap());
        let mut part = Idle;
        let parts: Vec<(String, &mut dyn Part)> = vec![("idle".to_string(), &mut part)];
        assert!(
            Runtime::new(&store, "urn:test:me", &clock, parts)
                .unwrap()
                .tasks
                .is_none()
        );
    }

    const STEP: &str = "http://example.org/test#Stepping";

    /// Begins and ends an activity at every pass.
    struct Begins;
    impl Part for Begins {
        fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
            starting.every(0.0, 0);
            Ok(())
        }
        fn run(&mut self, _job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            let activity = pass.begin(STEP, &[]);
            pass.end(activity);
            Ok(Vec::new())
        }
    }

    /// Hears every event beneath `orexis:Event`'s kernel classes it is told of: here, a start.
    struct Hears(Rc<RefCell<Vec<Heard>>>);
    impl Part for Hears {
        fn start(&mut self, starting: &mut Starting) -> Result<(), Error> {
            starting.hears(crate::activity::STARTED, 0);
            Ok(())
        }
        fn run(&mut self, _job: usize, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            Ok(Vec::new())
        }
        fn heard_event(&mut self, _job: usize, event: &Heard, _pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
            self.0.borrow_mut().push(event.clone());
            Ok(Vec::new())
        }
    }

    #[test]
    fn an_activitys_start_is_heard_by_class_under_the_name_it_was_said_with() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = Manual::at("2026-11-10T12:00:00Z".parse().unwrap());
        let heard = Rc::new(RefCell::new(Vec::new()));
        let said: Rc<RefCell<Vec<NamedNode>>> = Rc::default();
        let (mut begins, mut hears) = (Begins, Hears(heard.clone()));
        let parts: Vec<(String, &mut dyn Part)> = vec![("begins".into(), &mut begins), ("hears".into(), &mut hears)];
        let mut runtime = Runtime::new(&store, "urn:test:me", &clock, parts).unwrap();
        let watch = Watch::default();
        let kept = said.clone();
        watch.connect(move |event, named| {
            if event.kind() == Some(crate::activity::STARTED) {
                kept.borrow_mut().push(named.clone());
            }
        });
        runtime.watch = watch;
        runtime.drain(clock.now()).unwrap();
        let heard = heard.borrow();
        assert_eq!(heard.len(), 1, "one start, and the end is no start: {heard:?}");
        assert_eq!(heard[0].node, said.borrow()[0], "heard under the name it was said with");
        assert_eq!(heard[0].activity.as_ref().map(|(_, k)| k.as_str()), Some(STEP));
    }

    #[test]
    fn nobody_listening_connects_nothing() {
        let store = Store::new(crate::snapshots::namespaces()).unwrap();
        let clock = Manual::at("2026-11-10T12:00:00Z".parse().unwrap());
        let mut begins = Begins;
        let parts: Vec<(String, &mut dyn Part)> = vec![("begins".into(), &mut begins)];
        let mut runtime = Runtime::new(&store, "urn:test:me", &clock, parts).unwrap();
        runtime.drain(clock.now()).unwrap();
        assert!(
            !runtime.watch.connected(),
            "an emitter that asks whether anybody watches is still told no"
        );
    }
}
