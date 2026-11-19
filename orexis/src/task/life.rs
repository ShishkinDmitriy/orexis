//! THE LIFECYCLE: what a package is handed, how it joins, boots, runs and stops, and the agent's booting, running
//! and stopping that hold every package's.

use super::*;
use std::cell::RefCell;
use std::collections::BTreeSet;
use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};

use oxsdatatypes::DateTime;

use oxigraph::model::{Literal, NamedNode, Term};
use tokio::sync::{Notify, watch};

use crate::Error;
use crate::activity::{Activity, Ended, Lasting, Started};
use crate::bind::{Value, bind};
use crate::boot::brought_uri;
use crate::clock::Clock;
use crate::events::{Event, Watch};
use crate::ontology::ONTOLOGY;
use crate::rdf::round6;
use crate::store::{Store, Within, iri};

/// WHAT A PACKAGE'S TASK IS HANDED: the agent's services, and nothing of its own - its store, its id, the clock, the
/// events, what is provided, and the run it is part of; and, handed to a package's start, THE PACKAGE'S LIFECYCLE,
/// which the kernel begins and the package goes on with: it joins (`joins`), says it booted (`booted`) and, where it
/// has work left once the agent's running ends, stops (`stopping`).
#[derive(Clone)]
pub struct Handed {
    pub store: Store,
    pub id: String,
    pub clock: Arc<dyn Clock>,
    pub events: Events,
    pub provided: Provided,
    pub(super) run: Run,
    pub(super) life: Option<Arc<tokio::sync::Mutex<Life>>>,
}

/// THE AGENT'S LIFECYCLE AND EACH PACKAGE'S, as activities of the kernel's classes, each said by one start and one end
/// (`activity::Lasting`): the agent's booting holds every package's, its running every running package's, its stopping
/// every package's that stops - and a check is the agent's booting alone.
pub const AGENT_BOOTING: &str = "http://example.org/orexis#AgentBooting";
pub const AGENT_RUNNING: &str = "http://example.org/orexis#AgentRunning";
pub const AGENT_STOPPING: &str = "http://example.org/orexis#AgentStopping";
pub const PACKAGE_BOOTING: &str = "http://example.org/orexis#PackageBooting";
pub const PACKAGE_RUNNING: &str = "http://example.org/orexis#PackageRunning";
pub const PACKAGE_STOPPING: &str = "http://example.org/orexis#PackageStopping";
/// A package joined the agent, its documents brought: said inside its booting.
pub const PACKAGE_JOINED: &str = "http://example.org/orexis#PackageJoined";
pub(super) const PACKAGE: &str = "http://example.org/orexis#package";
pub(super) const SERVES: &str = "http://example.org/orexis#serves";
pub(super) const RUNS: &str = "http://example.org/orexis#runs";

/// What a lifecycle is told under: a package's booting ended, a package joined, the agent's booting ended, the agent's
/// running ended, and a package's running ended.
pub(super) const BOOTED: usize = 0;
pub(super) const JOINED: usize = 1;
pub(super) const AGENT_BOOTED: usize = 2;
pub(super) const AGENT_RAN: usize = 3;
pub(super) const RAN: usize = 4;

/// THE RUN THE PACKAGES ARE PART OF, a service each is handed: the signal that stops it, whether the packages run
/// once booted - not where the agent is checked or booted without starting - how many packages boot, the packages
/// that booted with a core, in the order they did, the boot the bootings finish, and the agent's own activities,
/// named as the run begins so each package's is said part of its.
#[derive(Clone)]
pub(super) struct Run {
    pub(super) stop: watch::Receiver<bool>,
    pub(super) runs: bool,
    pub(super) packages: usize,
    pub(super) started: Arc<Mutex<Vec<String>>>,
    pub(super) boot: Arc<Mutex<Boot>>,
    pub(super) booting: NamedNode,
    pub(super) running: NamedNode,
    pub(super) stopping: Arc<Mutex<Option<Span>>>,
}

/// THE BOOT AS THE BOOTINGS FINISH IT: what is begun and not yet finished, where the agent was booted by `boot`; the
/// packages that joined and brought their documents, each with its crate; and why the boot was refused as it finished.
#[derive(Default)]
pub(super) struct Boot {
    pub(super) begun: Option<crate::boot::Begun>,
    pub(super) joined: Vec<(String, &'static str)>,
    pub(super) refused: Option<String>,
}

impl Run {
    pub(super) fn new(stop: watch::Receiver<bool>) -> Self {
        Run {
            stop,
            runs: true,
            packages: 0,
            started: Arc::default(),
            boot: Arc::default(),
            booting: crate::rdf::mint(),
            running: crate::rdf::mint(),
            stopping: Arc::default(),
        }
    }

    pub(super) fn refused(&self) -> Option<String> {
        self.boot.lock().expect("a boot nobody poisoned").refused.clone()
    }
}

/// AN ACTIVITY OF THE LIFECYCLE, OPEN: said as it begins and as it ends, naming the activity it is part of
/// (`activity::Lasting`). It is never what a turn's events are said within: a running is open for the agent's life,
/// and what its task says outside a turn's activity is no part of it.
pub(super) struct Span {
    pub(super) activity: Activity,
    pub(super) lasting: Lasting,
}

impl Span {
    pub(super) fn begin(
        events: &Events,
        kind: &'static str,
        node: NamedNode,
        part_of: Option<NamedNode>,
        about: Vec<(&'static str, Term)>,
        at: DateTime,
    ) -> Span {
        let lasting = Lasting { part_of, about };
        events.say(&Started {
            activity: node.clone(),
            kind,
            triggers: Vec::new(),
            at,
            lasting: Some(lasting.clone()),
        });
        Span {
            activity: Activity::named(node, kind),
            lasting,
        }
    }

    /// End it at `at`, saying `more` of it besides what it began saying.
    pub(super) fn end(self, events: &Events, at: DateTime, more: Vec<(&'static str, Term)>) {
        let duration_s = self.activity.took();
        let mut lasting = self.lasting;
        lasting.about.extend(more);
        events.say(&Ended {
            activity: self.activity.node,
            kind: self.activity.kind,
            at,
            duration_s,
            lasting: Some(lasting),
        });
    }
}

/// A PACKAGE'S LIFECYCLE: which package, what it hears of the others' and of the agent's, which of its activities is
/// open, and the crate whose documents it brought.
pub(super) struct Life {
    pub(super) package: String,
    pub(super) hears: Hears,
    pub(super) booting: Option<Span>,
    pub(super) running: Option<Span>,
    pub(super) stopping: Option<Span>,
    pub(super) krate: Option<&'static str>,
}

impl Life {
    /// End whichever of its activities is open, as its start ends: a booting that never said it booted ends having
    /// made no core.
    pub(super) fn end(&mut self, events: &Events, at: DateTime) {
        if let Some(booting) = self.booting.take() {
            booting.end(events, at, vec![(RUNS, Literal::from(false).into())]);
        }
        for span in [self.running.take(), self.stopping.take()].into_iter().flatten() {
            span.end(events, at, Vec::new());
        }
    }
}

/// WHAT A PACKAGE JOINING HAS HEARD OF THE OTHERS: which have joined or ended their booting, which have ended it,
/// and the roles those that ended serve.
#[derive(Default)]
pub(super) struct Settling {
    pub(super) settled: BTreeSet<String>,
    pub(super) ended: BTreeSet<String>,
    pub(super) served: BTreeSet<String>,
}

impl Settling {
    pub(super) fn hear(&mut self, woke: Woke) {
        if let Woke::Event(tag, heard) = woke
            && let Some(package) = package_of(&heard)
        {
            if tag == BOOTED {
                self.served
                    .extend(heard.all(SERVES).into_iter().map(|c| c.as_str().to_string()));
                self.ended.insert(package.clone());
            }
            if tag == BOOTED || tag == JOINED {
                self.settled.insert(package);
            }
        }
    }
}

/// The name of the package a lifecycle event says it is of.
pub(super) fn package_of(heard: &Heard) -> Option<String> {
    heard.about.iter().find_map(|(p, t)| match t {
        Term::Literal(l) if p == PACKAGE => Some(l.value().to_string()),
        _ => None,
    })
}

/// Whether a booting ended having made the package's core, which then runs.
pub(super) fn runs(heard: &Heard) -> bool {
    heard
        .about
        .iter()
        .any(|(p, t)| p == RUNS && *t == Term::from(Literal::from(true)))
}

/// A PACKAGE JOINED THE AGENT: its documents brought, said inside its booting, so a package that waits on another's
/// knows when every package's vocabulary is in.
pub struct Joined {
    pub package: String,
    pub at: DateTime,
}

impl Event for Joined {
    fn statements(&self, entry: &NamedNode) -> Option<Vec<oxigraph::model::Triple>> {
        Some(vec![
            oxigraph::model::Triple::new(
                entry.clone(),
                NamedNode::new_unchecked("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                NamedNode::new_unchecked(PACKAGE_JOINED),
            ),
            oxigraph::model::Triple::new(
                entry.clone(),
                NamedNode::new_unchecked(PACKAGE),
                Literal::new_simple_literal(&self.package),
            ),
        ])
    }

    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }

    fn kind(&self) -> Option<&'static str> {
        Some(PACKAGE_JOINED)
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        vec![(PACKAGE, Literal::new_simple_literal(&self.package).into())]
    }
}

impl Handed {
    /// A turn at the instant the clock reads.
    pub fn turn(&self) -> Turn<'_> {
        Turn {
            now: self.clock.now(),
            agent: &self.id,
            events: &self.events,
            next: None,
            last: None,
        }
    }

    /// Where the task waits for what arrives from outside, and what rings it.
    pub fn arrived(&self) -> Arrived {
        Arrived {
            ring: Arc::new(Ring {
                notify: Notify::new(),
                rung: AtomicBool::new(false),
                gone: AtomicBool::new(false),
                busy: self.events.0.busy.clone(),
            }),
            events: self.events.clone(),
        }
    }

    /// Wait until the clock reads `at`, at its pace; for ever where no instant is given.
    pub async fn sleep_until(&self, at: Option<DateTime>) {
        self.events.rest();
        let Some(at) = at else {
            return std::future::pending().await;
        };
        let ahead = at.checked_sub(self.clock.now()).map_or(0.0, crate::clock::seconds_of);
        tokio::time::sleep(self.clock.real_delay(ahead.max(0.0))).await;
        self.events.woke();
    }

    /// WHETHER THE SELF PLAYS A ROLE of one of `roles`, the package's own classes, by the vocabulary the store holds:
    /// what a package asks first, deciding for itself whether it runs. No package's role is beneath another
    /// package's, so its own class decides before any package has brought its documents, and a domain's role class
    /// beneath it is the world's to say, put in as the boot began.
    pub fn plays(&self, roles: &[&str]) -> Result<bool, Error> {
        crate::boot::plays(&self.store, roles)
    }

    pub(super) fn life(&self) -> Result<Arc<tokio::sync::Mutex<Life>>, Error> {
        self.life.clone().ok_or_else(|| {
            Error::Evaluation("nothing was handed a lifecycle: only a package's start joins, boots and stops".into())
        })
    }

    /// THE PACKAGE JOINS THE AGENT, BRINGING `documents`, AND WAITS FOR WHAT ITS ROLES DEPEND ON, inside its booting:
    /// its documents, which it names in the order it wants them, are put in and every graph of the world passed over
    /// until now offered again, and it says it joined (`orexis:PackageJoined`); then, once every package has joined or
    /// ended its booting, so the vocabulary is whole, it waits to hear the end of the booting of each package serving
    /// a role its roles depend on (`orexis:dependsOn`) - a role depending on nothing waiting on nobody, and none
    /// waiting once every other booting has ended. The order is the vocabulary's: the package names no other.
    pub async fn joins(&self, documents: &Documents) -> Result<(), Error> {
        self.joins_with(documents, &[]).await
    }

    /// THE PACKAGE JOINS BRINGING THE DOCUMENTS OF A FAMILY IT IS OF BESIDE ITS OWN, `beside` first, as `joins`: a
    /// family's crate registers no package, so the words its members share are brought by each member that speaks
    /// them, `orexis-llm/`'s by a package asking a model; brought twice, a document is one graph, named by its crate.
    pub async fn joins_with(&self, documents: &Documents, beside: &[&Documents]) -> Result<(), Error> {
        let life = self.life()?;
        let mut life = life.lock().await;
        {
            let mut boot = self.run.boot.lock().expect("a boot nobody poisoned");
            if let Some(begun) = boot.begun.as_mut() {
                for family in beside {
                    begun.bring(&self.store, family)?;
                }
                begun.bring(&self.store, documents)?;
            }
            boot.joined.push((life.package.clone(), documents.krate));
        }
        life.krate = Some(documents.krate);
        self.events.say(&Joined {
            package: life.package.clone(),
            at: self.clock.now(),
        });
        let mut heard = Settling::default();
        heard.settled.insert(life.package.clone());
        while heard.settled.len() < self.run.packages {
            let Some(woke) = life.hears.next_busy().await else {
                break;
            };
            heard.hear(woke);
        }
        let needs = self.needs(documents.krate)?;
        while !needs.iter().all(|n| heard.served.contains(n)) && heard.ended.len() + 1 < self.run.packages {
            let Some(woke) = life.hears.next_busy().await else {
                break;
            };
            heard.hear(woke);
        }
        Ok(())
    }

    /// THE ROLES THE PACKAGE OF `krate` WAITS FOR: each a role it serves and the self plays depends on, that the self
    /// plays and it does not serve; refused where they depend back on its own round a cycle, which no booting could
    /// wait out. A role depended on that the self plays none of is waited for by nobody: that the self plays it is
    /// onboarding's to hold (`onboarding/requirements.ttl`), not the boot's.
    pub(super) fn needs(&self, krate: &str) -> Result<BTreeSet<String>, Error> {
        let played = |role: &str| crate::boot::plays(&self.store, &[role]);
        let mut mine = Vec::new();
        for role in served(&self.store, krate)? {
            if played(&role)? {
                mine.push(role);
            }
        }
        let mut needs = BTreeSet::new();
        for role in &mine {
            for needed in depended(&self.store, role)? {
                if !mine.contains(&needed) && played(&needed)? {
                    needs.insert(needed);
                }
            }
        }
        let (mut seen, mut frontier): (BTreeSet<String>, Vec<String>) =
            (needs.clone(), needs.iter().cloned().collect());
        while let Some(role) = frontier.pop() {
            for needed in depended(&self.store, &role)? {
                if mine.contains(&needed) {
                    return Err(Error::Evaluation(format!(
                        "the roles of {krate} depend on each other round a cycle through {role}, so none could boot"
                    )));
                }
                if played(&needed)? && seen.insert(needed.clone()) {
                    frontier.push(needed);
                }
            }
        }
        Ok(needs)
    }

    /// THE PACKAGE HAS BOOTED: its core is made, and its booting ends, saying the roles it serves. It WAITS HERE UNTIL
    /// THE AGENT'S BOOTING HAS ENDED - every package booted or declined, and the boot finished - so each is listening
    /// before any speaks; then, where the agent runs, its running begins, and it goes on as its task. False where the
    /// agent does not run - it is checked, or booted without starting - and the package ends there; refused where the
    /// boot was.
    pub async fn booted(&self) -> Result<bool, Error> {
        let life = self.life()?;
        let mut life = life.lock().await;
        let mut serves = Vec::new();
        if let Some(krate) = life.krate {
            for role in served(&self.store, krate)? {
                if crate::boot::plays(&self.store, &[&role])? {
                    serves.push(role);
                }
            }
        }
        self.run
            .started
            .lock()
            .expect("starts nobody poisoned")
            .push(life.package.clone());
        if let Some(booting) = life.booting.take() {
            let mut more: Vec<(&'static str, Term)> = vec![(RUNS, Literal::from(true).into())];
            more.extend(serves.iter().map(|c| (SERVES, NamedNode::new_unchecked(c).into())));
            booting.end(&self.events, self.clock.now(), more);
        }
        while let Some(woke) = life.hears.next_busy().await {
            if matches!(woke, Woke::Event(AGENT_BOOTED, _)) {
                break;
            }
        }
        if let Some(why) = self.run.refused() {
            return Err(Error::Evaluation(why));
        }
        if !self.run.runs {
            return Ok(false);
        }
        let about = vec![(PACKAGE, Literal::new_simple_literal(&life.package).into())];
        life.running = Some(Span::begin(
            &self.events,
            PACKAGE_RUNNING,
            crate::rdf::mint(),
            Some(self.run.running.clone()),
            about,
            self.clock.now(),
        ));
        Ok(true)
    }

    /// THE PACKAGE STOPS: its running ends, and it WAITS UNTIL THE AGENT'S RUNNING HAS ENDED - every running package's
    /// ended - so what it does next comes after the others' last word, inside its stopping, which ends with its start:
    /// what archives the journal takes what they said while they stopped.
    pub async fn stopping(&self) -> Result<(), Error> {
        let life = self.life()?;
        let mut life = life.lock().await;
        if let Some(running) = life.running.take() {
            running.end(&self.events, self.clock.now(), Vec::new());
        }
        while let Some(woke) = life.hears.next_busy().await {
            if matches!(woke, Woke::Event(AGENT_RAN, _)) {
                break;
            }
        }
        let about = vec![(PACKAGE, Literal::new_simple_literal(&life.package).into())];
        let stopping = self.run.stopping.lock().expect("a stopping nobody poisoned");
        let part_of = stopping.as_ref().map(|s| s.activity.node.clone());
        drop(stopping);
        life.stopping = Some(Span::begin(
            &self.events,
            PACKAGE_STOPPING,
            crate::rdf::mint(),
            part_of,
            about,
            self.clock.now(),
        ));
        Ok(())
    }

    /// WHETHER THE AGENT IS BEING CHECKED, and where to say what the check asks: provided by whoever checks an
    /// agent before anything is granted. A package being checked says what it found as it makes its core - that it
    /// holds the agent, why it refuses the world as posed; a check is the agent's booting alone, so nothing runs.
    pub fn checking(&self) -> Option<Checking> {
        self.provided.read::<Checking>()
    }

    /// Wait until the run is over: the task stops itself.
    pub async fn stopped(&self) {
        self.events.rest();
        let mut stop = self.run.stop.clone();
        let _ = stop.wait_for(|stopped| *stopped).await;
    }
}

/// A task: what a package runs once it has started, where a package keeps that apart from its making.
pub type Task = Pin<Box<dyn Future<Output = Result<(), Error>> + Send>>;

/// A package's start, running: the whole of what the package does, from deciding whether it runs to the end of its
/// task - its booting, its running and its stopping.
pub type Starting = Pin<Box<dyn Future<Output = Result<(), Error>> + Send>>;

/// A PACKAGE, AS IT REGISTERS ITSELF: its name and ITS START. THE AGENT STARTS EVERY PACKAGE IT HOLDS, each inside a
/// booting of its own, and each is responsible for its own: it decides whether it runs (`Handed::plays`, or a reason of
/// its own), and declined, it ends; it joins (`Handed::joins`), bringing its documents and waiting until the packages
/// serving the roles its own depend on have booted; it makes its core, says it booted (`Handed::booted`), and where the
/// agent does not run, ends there; otherwise it goes on as its task, its running. Nothing decides for a package,
/// knows which run, or keeps an order between two.
pub struct Package {
    pub name: &'static str,
    pub start: fn(Handed) -> Starting,
}

inventory::collect!(Package);

/// THE DOCUMENTS A PACKAGE BRINGS as it joins, of its crate, each named as the file it is, in the order the package
/// wants them put in: read as the crate is compiled, so a binary holds the documents of the packages built into it
/// and of no other, and the boot reads no tree.
pub struct Documents {
    pub krate: &'static str,
    pub files: &'static [(&'static str, &'static str)],
}

/// THE DOCUMENTS OF THE CRATE THIS IS WRITTEN IN, each a file of it: `documents!("ontology.ttl", "rules.ttl")`.
#[macro_export]
macro_rules! documents {
    ($($name:literal),* $(,)?) => {
        $crate::task::Documents {
            krate: env!("CARGO_PKG_NAME"),
            files: &[$(($name, include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/", $name)))),*],
        }
    };
}

/// An agent's tasks, running.
pub struct Running {
    pub handed: Handed,
    pub(super) names: Vec<String>,
    pub(super) joins: Vec<tokio::task::JoinHandle<()>>,
    pub(super) agent: Option<tokio::task::JoinHandle<()>>,
    pub(super) stop: watch::Sender<bool>,
    /// RAISED TO STOP THE RUN, by a signal the process was sent.
    pub halt: Option<Arc<AtomicBool>>,
    pub(super) halted: Arc<Notify>,
}

/// THE PACKAGES A TEST NAMES, provided by whoever starts the agent for a test (`Booted::first`): a test's member runs
/// where it is named, as a package runs where the self plays its role.
#[cfg(any(test, feature = "snapshots"))]
#[derive(Clone, Default)]
pub struct Named(pub Vec<String>);

/// THE START OF A TEST'S MEMBER, which no role loads: it runs where whoever starts the agent names `name`, and its
/// core is what `make` makes.
#[cfg(any(test, feature = "snapshots"))]
pub fn named(handed: Handed, name: &'static str, make: fn(&Handed) -> Result<Option<Task>, Error>) -> Starting {
    Box::pin(async move {
        if !handed
            .provided
            .read::<Named>()
            .is_some_and(|named| named.0.iter().any(|n| n == name))
        {
            return Ok(());
        }
        let task = make(&handed)?;
        if !handed.booted().await? {
            return Ok(());
        }
        match task {
            Some(task) => task.await,
            None => Ok(()),
        }
    })
}

/// What every package of an agent is handed.
pub(super) fn handed(
    store: &Store,
    id: &str,
    clock: Arc<dyn Clock>,
    provided: Provided,
    stop: watch::Receiver<bool>,
) -> Handed {
    Handed {
        store: store.clone(),
        id: id.to_string(),
        clock,
        events: Events::new(store),
        provided,
        run: Run::new(stop),
        life: None,
    }
}

/// AN AGENT BOOTED AND NOT YET STARTED: its boot begun, the world's documents and the self in, and no package's. Its
/// packages' bootings finish the boot, which is why booting is the tasks' and not the boot's alone: which packages'
/// documents an agent holds is what each booting decides (`Handed::joins`), and a role no package declares is refused
/// once every booting has ended.
pub struct Booted {
    pub(super) handed: Handed,
    pub(super) stop: watch::Sender<bool>,
    pub(super) first: Vec<String>,
}

/// BEGIN TO BOOT `agent` of `world` INTO `store`, handed `provided`: the kernel's vocabulary, the world's documents and
/// the self. Nothing runs until `Booted::start`.
pub fn boot(
    store: &Store,
    world: &std::path::Path,
    agent: &str,
    clock: Arc<dyn Clock>,
    provided: Provided,
) -> Result<Booted, Error> {
    let begun = crate::boot::begin(store, &crate::boot::Booting { world, agent })?;
    let (stop, stopped) = watch::channel(false);
    let handed = handed(store, agent, clock, provided, stopped);
    handed.run.boot.lock().expect("a boot nobody poisoned").begun = Some(begun);
    Ok(Booted {
        handed,
        stop,
        first: Vec::new(),
    })
}

impl Booted {
    /// THOSE `names` NAMES START FIRST, and in that order, the rest after them, and a test's member runs where it is
    /// named (`Named`): for a test, which holds a run the same whichever package hears first. A name no package
    /// registered under is an error: its crate was not built in.
    #[cfg(any(test, feature = "snapshots"))]
    pub fn first(mut self, names: &[String]) -> Result<Self, Error> {
        let every = every();
        if let Some(name) = names.iter().find(|n| !every.contains(n)) {
            return Err(Error::Evaluation(format!(
                "no package registered itself as {name}: this binary was built without it"
            )));
        }
        self.handed.provided.provide(Named(names.to_vec()));
        self.first = names.to_vec();
        Ok(self)
    }

    /// START THE AGENT, on the Tokio runtime this is called in: its booting, every package this binary holds booting
    /// inside it, each deciding for itself whether it runs, and then its running. This ends once the booting has -
    /// refused where a package could not boot, or where the boot it finished was.
    pub async fn start(self) -> Result<Running, Error> {
        self.go(true).await
    }

    /// BOOT THE AGENT AND START NOTHING: its booting alone, every package booting inside it and ending there, its core
    /// made and nothing run. What a check does, and a test that calls a package's core itself.
    pub async fn without_starting(self) -> Result<Running, Error> {
        self.go(false).await
    }

    pub(super) async fn go(mut self, runs: bool) -> Result<Running, Error> {
        started();
        let rest: Vec<String> = every().into_iter().filter(|n| !self.first.contains(n)).collect();
        let order = [std::mem::take(&mut self.first), rest].concat();
        self.handed.run.runs = runs;
        self.handed.run.packages = order.len();
        let (said, booted) = tokio::sync::oneshot::channel();
        let running = spawn(self.handed, self.stop, order, said);
        let _ = booted.await;
        running.booted()
    }
}

/// THE AGENT'S OWN TASK: it hears every package's booting end, finishes the boot once all have and ends its booting -
/// telling whoever started it - and where the agent runs, begins its running, hears every running package's running
/// end, and ends its running as its stopping begins.
pub(super) async fn agent(handed: Handed, mut hears: Hears, booting: Span, said: tokio::sync::oneshot::Sender<()>) {
    let run = &handed.run;
    let (mut bootings, mut running) = (0, 0);
    while bootings < run.packages {
        match hears.next().await {
            Some(Woke::Event(BOOTED, heard)) => {
                bootings += 1;
                if runs(&heard) {
                    running += 1;
                }
            }
            Some(_) => {}
            None => break,
        }
    }
    {
        let mut boot = run.boot.lock().expect("a boot nobody poisoned");
        if let Some(begun) = boot.begun.take() {
            let joined: Vec<String> = boot.joined.iter().map(|(p, _)| p.clone()).collect();
            if let Err(e) = begun.finish(&handed.store, &joined) {
                boot.refused = Some(e.to_string());
            }
        }
    }
    booting.end(&handed.events, handed.clock.now(), Vec::new());
    handed.events.0.watch.forget();
    let runs = run.runs && run.refused().is_none();
    let agent_running = runs.then(|| {
        Span::begin(
            &handed.events,
            AGENT_RUNNING,
            run.running.clone(),
            None,
            Vec::new(),
            handed.clock.now(),
        )
    });
    handed.events.spoke();
    let _ = said.send(());
    let Some(agent_running) = agent_running else {
        handed.events.rest();
        return;
    };
    let mut ran = 0;
    while ran < running {
        match hears.next().await {
            Some(Woke::Event(RAN, _)) => ran += 1,
            Some(_) => {}
            None => break,
        }
    }
    agent_running.end(&handed.events, handed.clock.now(), Vec::new());
    *run.stopping.lock().expect("a stopping nobody poisoned") = Some(Span::begin(
        &handed.events,
        AGENT_STOPPING,
        crate::rdf::mint(),
        None,
        Vec::new(),
        handed.clock.now(),
    ));
    handed.events.rest();
}

/// EVERY START IS SPAWNED AS A TASK, in `order`, inside a booting of its own the kernel begins: each is the whole of
/// its package's life. What every lifecycle hears is asked before any task runs, so none misses what another says
/// first; and a start that ends with its booting, running or stopping open ends it.
pub(super) fn spawn(
    handed: Handed,
    stop: watch::Sender<bool>,
    order: Vec<String>,
    said: tokio::sync::oneshot::Sender<()>,
) -> Running {
    let events = handed.events.clone();
    let mut hears = events.hears();
    hears.activity(crate::activity::ENDED, PACKAGE_BOOTING, BOOTED);
    hears.activity(crate::activity::ENDED, PACKAGE_RUNNING, RAN);
    let lives: Vec<Arc<tokio::sync::Mutex<Life>>> = order
        .iter()
        .map(|name| {
            let mut hears = events.hears();
            hears.activity(crate::activity::ENDED, PACKAGE_BOOTING, BOOTED);
            hears.said(PACKAGE_JOINED, JOINED);
            hears.activity(crate::activity::ENDED, AGENT_BOOTING, AGENT_BOOTED);
            hears.activity(crate::activity::ENDED, AGENT_RUNNING, AGENT_RAN);
            Arc::new(tokio::sync::Mutex::new(Life {
                package: name.clone(),
                hears,
                booting: None,
                running: None,
                stopping: None,
                krate: None,
            }))
        })
        .collect();
    //  WHAT IS SAID AS THE AGENT BOOTS IS REMEMBERED, for whoever connects to the watch inside the booting.
    events.0.watch.remember();
    let booting = Span::begin(
        &events,
        AGENT_BOOTING,
        handed.run.booting.clone(),
        None,
        Vec::new(),
        handed.clock.now(),
    );
    let mut running = Running {
        handed: handed.clone(),
        names: Vec::new(),
        joins: Vec::new(),
        agent: None,
        stop,
        halt: None,
        halted: Arc::new(Notify::new()),
    };
    events.0.busy.up();
    running.agent = Some(tokio::spawn(TURN.scope(
        RefCell::new(Local {
            in_hand: 1,
            ..Local::default()
        }),
        agent(handed.clone(), hears, booting, said),
    )));
    for (name, life) in order.into_iter().zip(lives) {
        let package = inventory::iter::<Package>()
            .find(|p| p.name == name)
            .expect("a package found is registered");
        let mut own = handed.clone();
        own.life = Some(life.clone());
        let start = (package.start)(own);
        let (events, clock, part_of) = (handed.events.clone(), handed.clock.clone(), handed.run.booting.clone());
        //  A TASK IS BUSY FROM ITS START until it first waits: the run is not over before every policy decided once.
        events.0.busy.up();
        let named = name.clone();
        let scoped = TURN.scope(
            RefCell::new(Local {
                in_hand: 1,
                ..Local::default()
            }),
            async move {
                let about = vec![(PACKAGE, Literal::new_simple_literal(&named).into())];
                life.lock().await.booting = Some(Span::begin(
                    &events,
                    PACKAGE_BOOTING,
                    crate::rdf::mint(),
                    Some(part_of),
                    about,
                    clock.now(),
                ));
                let ended = start.await;
                life.lock().await.end(&events, clock.now());
                if let Err(e) = ended {
                    events.failed(e);
                }
                events.rest();
            },
        );
        running.names.push(name);
        running.joins.push(tokio::spawn(scoped));
    }
    running
}

impl Running {
    /// The packages that booted with a core, in the order they did.
    pub fn parts(&self) -> Vec<String> {
        self.handed.run.started.lock().expect("starts nobody poisoned").clone()
    }

    /// The run once the agent's booting has ended: refused where a package could not boot, or the boot was.
    pub(super) fn booted(self) -> Result<Self, Error> {
        if let Some(why) = self.handed.run.refused() {
            return Err(Error::Evaluation(why));
        }
        self.checked()?;
        Ok(self)
    }

    /// The packages whose starts have not ended: what goes on running.
    pub fn going_on(&self) -> Vec<String> {
        self.names
            .iter()
            .zip(&self.joins)
            .filter(|(_, join)| !join.is_finished())
            .map(|(name, _)| name.clone())
            .collect()
    }

    /// Whoever watches the agent: what a test or a tool connects to, to hear everything its packages say.
    pub fn watch(&self) -> &Watch {
        self.handed.events.watch()
    }

    /// What ends the run's wait, for whoever halts the run from outside it.
    pub fn wake(&self) -> Wake {
        Wake {
            ring: None,
            halt: Some(self.halted.clone()),
        }
    }

    pub(super) fn halted(&self) -> bool {
        self.halt.as_ref().is_some_and(|h| h.load(Ordering::Relaxed))
    }

    pub(super) fn checked(&self) -> Result<(), Error> {
        let bus = &self.handed.events.0;
        match bus.error.lock().expect("an error nobody poisoned").take() {
            Some(e) => Err(e),
            None => Ok(()),
        }
    }

    /// Whether no task is busy now.
    pub fn idle(&self) -> bool {
        *self.handed.events.0.busy.0.borrow() == 0
    }

    /// Wait until no task is busy: everything said was heard and done with, and the stretch said where anybody
    /// watches. A task's failure is the run's.
    pub async fn settled(&self) -> Result<(), Error> {
        let bus = &self.handed.events.0;
        let mut seen = bus.busy.0.subscribe();
        let _ = seen.wait_for(|n| *n == 0).await;
        self.checked()?;
        self.passed(bus.busy.took())
    }

    /// UNTIL NOTHING HOLDS THE AGENT, ending as the last to let go said, or it is halted, `unfinished`. Each stretch
    /// with something busy is said as it ends, where anybody watches.
    pub async fn released(&self) -> Result<String, Error> {
        let bus = &self.handed.events.0;
        let mut seen = bus.busy.0.subscribe();
        loop {
            //  UNTIL NOTHING IS BUSY, OR THE RUN IS HALTED WHILE SOMETHING STILL IS: a signal stops an agent that
            //  never comes to rest.
            tokio::select! {
                _ = seen.wait_for(|n| *n == 0) => {}
                _ = self.halted.notified() => {}
            }
            self.checked()?;
            self.passed(bus.busy.took())?;
            if self.halted() {
                log::info!("{}: stopped", self.handed.id);
                return Ok(UNFINISHED.to_string());
            }
            if bus.held.lock().expect("holders nobody poisoned").is_empty() {
                log::info!("{}: nothing holds it", self.handed.id);
                let outcome = bus.outcome.lock().expect("an outcome nobody poisoned").clone();
                return Ok(outcome.unwrap_or_else(|| MET.to_string()));
            }
            //  ANY CHANGE, so a task that woke and was done between two looks is still a stretch it sees.
            tokio::select! {
                _ = seen.changed() => {}
                _ = self.halted.notified() => {}
            }
            if self.halted() {
                log::info!("{}: stopped", self.handed.id);
                return Ok(UNFINISHED.to_string());
            }
        }
    }

    /// Say the stretch, where anybody watches.
    pub(super) fn passed(&self, took: f64) -> Result<(), Error> {
        let bus = &self.handed.events.0;
        if !bus.watch.connected() {
            return Ok(());
        }
        let laps = bus
            .laps
            .lock()
            .expect("laps nobody poisoned")
            .take()
            .unwrap_or_default();
        let quads = i64::try_from(self.handed.store.len()?).ok();
        bus.watch.emit(&Passed {
            duration_s: round6(took),
            laps: laps.spent,
            quads,
            uptime_s: (started().elapsed().as_secs_f64() * 1000.0).round() / 1000.0,
        });
        Ok(())
    }

    /// STOP EVERY TASK, each stopping itself where it waits, and wait for them to end: every package's running ends,
    /// then the agent's, and what stops does so inside the agent's stopping, which ends as the last task does.
    pub async fn stop(self) {
        let _ = self.stop.send(true);
        for join in self.joins {
            let _ = join.await;
        }
        if let Some(agent) = self.agent {
            let _ = agent.await;
        }
        let stopping = self
            .handed
            .run
            .stopping
            .lock()
            .expect("a stopping nobody poisoned")
            .take();
        if let Some(stopping) = stopping {
            stopping.end(&self.handed.events, self.handed.clock.now(), Vec::new());
        }
    }
}

/// Every package this binary holds, by its name: the kernel keeps no order between them, and each decides in its own
/// start whether it runs.
pub(super) fn every() -> Vec<String> {
    inventory::iter::<Package>()
        .map(|p| p.name.to_string())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect()
}

/// THE ROLE CLASSES THE DOCUMENTS OF `krate` DECLARE, each beneath `orexis:Role` in a graph it brought: the roles its
/// package serves, as the kernel learns it once the package has joined, reading no code of the package's.
fn served(store: &Store, krate: &str) -> Result<Vec<String>, Error> {
    const SERVED_Q: &str = "PREFIX orexis: <http://example.org/orexis#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?class WHERE { ?class rdfs:subClassOf orexis:Role }";
    let own = brought_uri(krate, "");
    let vocabularies = store.graphs_of(&[ONTOLOGY], &Within::default())?;
    let mut out = BTreeSet::new();
    for graph in vocabularies.iter().filter(|g| g.starts_with(&own)) {
        out.extend(
            store
                .rows(SERVED_Q, &[graph.as_str()])?
                .iter()
                .filter_map(|r| iri(r, "class")),
        );
    }
    Ok(out.into_iter().collect())
}

/// EVERY ROLE CLASS `role` DEPENDS ON (`orexis:dependsOn`), or a class it is beneath does, by the vocabulary the
/// store holds as it is asked: what `task::Handed::joins` orders the starts by.
fn depended(store: &Store, role: &str) -> Result<Vec<String>, Error> {
    const DEPENDS_Q: &str =
        "PREFIX orexis: <http://example.org/orexis#> SELECT ?needed WHERE { $class orexis:dependsOn ?needed }";
    let vocabularies = store.graphs_of(&[ONTOLOGY], &Within::default())?;
    let vocabularies: Vec<&str> = vocabularies.iter().map(String::as_str).collect();
    let mut classes = vec![role.to_string()];
    classes.extend(store.closed(role)?);
    let mut out = BTreeSet::new();
    for class in classes {
        let text = bind(DEPENDS_Q, &[("class", Value::iri(&class))])?;
        out.extend(
            store
                .rows(&text, &vocabularies)?
                .iter()
                .filter_map(|r| iri(r, "needed")),
        );
    }
    Ok(out.into_iter().collect())
}
