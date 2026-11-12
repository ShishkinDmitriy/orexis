//! THE MQTT TRANSPORT'S PART, as `agent/transport/mqtt/create.py` and the family's `Transport.start` make it
//! (a-package-starts-itself): started, it subscribes what the world implies, asks after its sensors' missing readings
//! when one falls due (`Mqtt::nudge_until`) and waits until then, and holds the agent running, since what it senses goes on arriving whatever is
//! wanted. Every message a session's task receives waits in the member's inbox and is handed to the one executing
//! thread as a job that handles it — sensing writing a percept per sensor it is for, whose arrival the runtime tells
//! whoever listens. A document the agent said it hears said, beneath its telling trigger, and tells each agent it is
//! to that listens on the bus. The executor's commands reach the member through whoever links the parts, sharing it.

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

use orexis::Error;
use orexis::runtime::{Heard, Pass, Runtime, Wait, Woke};
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

/// THE PACKAGE STARTING ITSELF on a runtime: it says what ends its wait and spawns its task. The part is lent, so
/// whoever keeps it reads it between runs.
pub fn start(runtime: &mut Runtime, part: &Arc<Mutex<Transport>>) -> Result<(), Error> {
    let part = part.clone();
    let mut wait = runtime.wait("transport/mqtt");
    part.lock().expect("a part nobody poisoned").start(&mut wait)?;
    runtime.spawn(wait, move |wait| policy(part, wait));
    Ok(())
}

/// THE MQTT MEMBER'S TASK: it waits for the pass, an event beneath one of its triggers, or a message a session
/// received, and does what its policy says of each, until the run is over and it stops.
async fn policy(part: Arc<Mutex<Transport>>, mut wait: Wait) {
    while let Some((woke, mut pass)) = wait.next().await {
        let mut transport = part.lock().expect("a part nobody poisoned");
        let wrote = match woke {
            Woke::Due(tag) => transport.run(tag, &mut pass),
            Woke::Event(tag, event) => transport.heard_event(tag, &event, &mut pass),
            Woke::Arrived => transport.queued(&mut pass),
            _ => Ok(Vec::new()),
        };
        pass.done(wrote);
    }
    part.lock().expect("a part nobody poisoned").stop();
}

impl Transport {
    /// What it queued for itself, each in turn and what each wrote told, until nothing is left.
    fn queued(&mut self, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
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

    fn start(&mut self, wait: &mut Wait) -> Result<(), Error> {
        //  THE SESSIONS LISTEN BEFORE THE MEMBER SUBSCRIBES: a subscription waits in a queue only they empty.
        let listening = {
            let member = &mut self.member;
            member.inbox.wakes(wait.wake());
            std::mem::take(&mut member.listening)
        };
        for session in listening {
            wait.task(session)?;
        }
        self.member.open()?;
        wait.every(0.0, NUDGE);
        wait.hears(CARRYING_TRIGGER, CARRY);
        wait.hears(TELLING_TRIGGER, TELL);
        wait.hears(ACTUATING_TRIGGER, ACTUATE);
        Ok(())
    }

    /// What the member's policy does of its triggers: the agent's own words carried where they are on a channel it
    /// carries, and a document the agent said told to each agent it is to that listens on the bus, read back from the
    /// store as it was said.
    fn heard_event(&mut self, job: usize, event: &Heard, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
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

    fn run(&mut self, job: usize, pass: &mut Pass<'_>) -> Result<Vec<String>, Error> {
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
