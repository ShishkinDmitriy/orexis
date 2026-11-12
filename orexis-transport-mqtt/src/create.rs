//! THE MQTT TRANSPORT'S PART, as `agent/transport/mqtt/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it subscribes what the world implies, asks after its sensors' missing readings
//! when one falls due (`Mqtt::nudge_until`) and waits until then, and holds the agent running, since what it senses goes on arriving whatever is
//! wanted. Every message a session's task receives waits in the member's inbox and is handed to the one executing
//! thread as a job that handles it — sensing writing a percept per sensor it is for, whose arrival the runtime tells
//! whoever listens. A document the agent said it hears said, beneath its telling trigger, and tells each agent it is
//! to that listens on the bus. The executor's commands reach the member through whoever links the parts, sharing it.

use std::collections::VecDeque;

use orexis::Error;
use orexis::task::{Arrived, Every, Handed, Heard, Hears, Package, Task, Turn, Woke, sooner};
use orexis_speech::prose::{ProseKept, carry, kept};

use orexis_speech::create::document_of;
use orexis_speech::ontology::{STATEMENT, TO};
use oxigraph::model::NamedNode;

use crate::driver::{Message, Mqtt};
use oxsdatatypes::DateTime;

/// The commands a command graph keeps, in the order kept: each actuator and its payload.
fn commands_of(store: &orexis::store::Store, graph: &str) -> Result<Vec<(String, serde_json::Value)>, Error> {
    let g = NamedNode::new(graph).map_err(|e| Error::Evaluation(e.to_string()))?;
    let engine = store.engine();
    let mut out = Vec::new();
    for q in engine
        .quads_for_pattern(
            None,
            Some(NamedNode::new_unchecked(ACTUATOR).as_ref()),
            None,
            Some(g.as_ref().into()),
        )
        .flatten()
    {
        let oxigraph::model::Term::NamedNode(actuator) = q.object else {
            continue;
        };
        let payload = engine
            .quads_for_pattern(
                Some(q.subject.as_ref()),
                Some(NamedNode::new_unchecked(PAYLOAD).as_ref()),
                None,
                Some(g.as_ref().into()),
            )
            .flatten()
            .find_map(|p| match p.object {
                oxigraph::model::Term::Literal(l) => serde_json::from_str(l.value()).ok(),
                _ => None,
            });
        if let Some(payload) = payload {
            out.push((actuator.as_str().to_string(), payload));
        }
    }
    Ok(out)
}

const NUDGE: usize = 0;
const HANDLE: usize = 1;
const CARRY: usize = 2;

/// What the member does as an activity, and what starts it.
const CARRYING: &str = "http://example.org/orexis/mqtt#Carrying";
const CARRYING_TRIGGER: &str = "http://example.org/orexis/mqtt#CarryingTrigger";
const TELL: usize = 3;
const TELLING: &str = "http://example.org/orexis/mqtt#Telling";
const TELLING_TRIGGER: &str = "http://example.org/orexis/mqtt#TellingTrigger";
const ACTUATE: usize = 4;
const ACTUATING: &str = "http://example.org/orexis/mqtt#Actuating";
const ACTUATING_TRIGGER: &str = "http://example.org/orexis/mqtt#ActuatingTrigger";
/// What a step's commands are kept as, in execution's words, which the member reads.
const COMMANDS: &str = "http://example.org/orexis/execution#commands";
const ACTUATOR: &str = "http://example.org/orexis/execution#actuator";
const PAYLOAD: &str = "http://example.org/orexis/execution#payload";

/// Who holds the agent running.
const HOLDER: &str = "transport/mqtt";

/// The member's part: the member, shared with whoever links to it, and the messages handed to the pass.
pub struct Transport {
    pub member: Mqtt,
    pending: VecDeque<Message>,
    /// Whether to nudge at the next pass whatever is due: the first, and one after a message arrived, which may move
    /// when a reading next falls due.
    nudge: bool,
    /// When the member asks after its sensors next, as the last nudge said.
    next: Option<DateTime>,
}

impl Transport {
    pub fn new(member: Mqtt) -> Self {
        Transport {
            member,
            pending: VecDeque::new(),
            nudge: true,
            next: None,
        }
    }
}

inventory::submit! { Package { name: "transport/mqtt", start } }

/// THE PACKAGE'S START: its part made and started - what it hears, what it does every so often - and its task.
fn start(handed: &Handed) -> Result<Option<Task>, Error> {
    let me = orexis::boot::selves(&handed.store)?
        .into_iter()
        .next()
        .unwrap_or_default();
    let member = match handed.outside.take::<crate::driver::Mqtt>() {
        Some(member) => member,
        None => crate::driver::connect(&handed.store, &me, &|name| std::env::var(name).ok())?,
    };
    let mut part = Transport::new(member);
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
    mut part: Transport,
    mut hears: Hears,
    mut arrived: Arrived,
    mut timers: Vec<(Every, usize)>,
) -> Result<(), Error> {
    let mut heard = None;
    let mut due = None;
    loop {
        let mut turn = handed.turn();
        if let Some(Woke::Event(tag, event)) = heard.take() {
            let wrote = part.heard_event(tag, &event, &mut turn);
            turn.done(wrote)?;
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
    part.stop();
    Ok(())
}

impl Transport {
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
        //  THE SESSIONS LISTEN BEFORE THE MEMBER SUBSCRIBES: a subscription waits in a queue only they empty.
        let listening = {
            let member = &mut self.member;
            member.inbox.wakes(arrived.wake());
            std::mem::take(&mut member.listening)
        };
        for session in listening {
            tokio::spawn(session);
        }
        self.member.open()?;
        timers.push((Every::new(0.0), NUDGE));
        hears.event(CARRYING_TRIGGER, CARRY);
        hears.event(TELLING_TRIGGER, TELL);
        hears.event(ACTUATING_TRIGGER, ACTUATE);
        Ok(())
    }

    /// What the member's policy does of its triggers: the agent's own words carried where they are on a channel it
    /// carries, and a document the agent said told to each agent it is to that listens on the bus, read back from the
    /// store as it was said.
    fn heard_event(&mut self, job: usize, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let store = self.member.beliefs().clone();
        match job {
            TELL => {
                let graphs: Vec<String> = event.all(STATEMENT).iter().map(|g| g.as_str().to_string()).collect();
                let to = event.all(TO);
                if graphs.is_empty() || to.is_empty() {
                    return Ok(Vec::new());
                }
                let payload = document_of(&store, &graphs)?.trig()?;
                let statements: Vec<NamedNode> = event.all(STATEMENT).into_iter().cloned().collect();
                let activity = pass.begin(TELLING, &statements);
                let told = to
                    .iter()
                    .try_for_each(|agent| self.member.tell(agent.as_str(), &payload).map(|_| ()));
                pass.end(activity);
                told?;
            }
            ACTUATE => {
                let Some(graph) = event.named(COMMANDS).cloned() else {
                    return Ok(Vec::new());
                };
                let commands = commands_of(&store, graph.as_str())?;
                let activity = pass.begin(ACTUATING, std::slice::from_ref(&graph));
                let sent = commands
                    .iter()
                    .try_for_each(|(actuator, payload)| self.member.command(actuator, payload));
                pass.end(activity);
                sent?;
            }
            _ => carry(&store, &mut self.member, event, pass, CARRYING)?,
        }
        Ok(Vec::new())
    }

    fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        match job {
            NUDGE => {
                //  A MEMBER KEEPS THE AGENT RUNNING: what it senses goes on arriving whatever is wanted.
                pass.hold(HOLDER);
                //  THE MEMBER'S POLICY: ask after its sensors when a reading has fallen due, or a message arrived
                //  since, and otherwise wait until one falls due.
                if self.nudge || self.next.is_some_and(|next| next <= pass.now) {
                    self.nudge = false;
                    self.next = self.member.nudge_until(pass.now)?;
                }
                if let Some(next) = self.next {
                    pass.wake_at(next);
                }
                Ok(Vec::new())
            }
            HANDLE => {
                let Some(message) = self.pending.pop_front() else {
                    return Ok(Vec::new());
                };
                self.nudge = true;
                let (written, heard, store, me) = {
                    let member = &mut self.member;
                    let written = member.handle(&message.topic, &message.payload, message.at.unwrap_or(pass.now))?;
                    let (store, me) = (member.beliefs().clone(), member.me.clone());
                    (written, std::mem::take(&mut member.prose), store, me)
                };
                let mut written: Vec<String> = written.into_iter().map(|(_, graph)| graph).collect();
                //  A PERSON'S WORDS ON A CHAT'S TOPIC are kept, and said kept, for whoever translates.
                for prose in &heard {
                    let graph = kept(&store, &me, prose)?;
                    pass.emit(&ProseKept { prose: graph.clone() });
                    written.push(graph);
                }
                Ok(written)
            }
            _ => Ok(Vec::new()),
        }
    }

    fn submitted(&mut self) -> Vec<usize> {
        let arrived = self.member.inbox.take();
        let n = arrived.len();
        self.pending.extend(arrived);
        vec![HANDLE; n]
    }

    fn stop(&mut self) {
        self.member.stop();
    }
}
