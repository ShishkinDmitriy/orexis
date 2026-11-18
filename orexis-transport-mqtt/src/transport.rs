//! THE MEMBER'S PART: the member, the messages it handed on for a turn to hand to sensing, and when it next asks after
//! its sensors; a document the agent said told on the bus and a chat's words carried — and the bus as the rows above
//! send on it (`Bus`).

use std::sync::{Arc, Mutex, MutexGuard};

use oxigraph::model::NamedNode;
use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::task::{Arrived, Heard, Turn};
use orexis_speech::document_of;
use orexis_speech::ontology::{STATEMENT, TO};
use orexis_speech::prose::{ProseKept, carry, kept};

use orexis_transport::{Exchange, Inbox, Jobs, Member, Pending};

use crate::driver::Mqtt;

pub(crate) const NUDGE: usize = 0;
const HANDLE: usize = 1;
pub(crate) const CARRY: usize = 2;

/// What the member does as an activity, and what starts it.
const CARRYING: &str = "http://example.org/orexis/mqtt#Carrying";
pub(crate) const CARRYING_TRIGGER: &str = "http://example.org/orexis/mqtt#CarryingTrigger";
pub(crate) const TELL: usize = 3;
const TELLING: &str = "http://example.org/orexis/mqtt#Telling";
pub(crate) const TELLING_TRIGGER: &str = "http://example.org/orexis/mqtt#TellingTrigger";

/// Who holds the agent running.
const HOLDER: &str = "transport/mqtt";

/// The member's part: the member, shared with whoever links to it, and the messages handed to the pass.
pub struct Transport {
    pub member: Arc<Mutex<Mqtt>>,
    pending: Pending,
    /// Whether to nudge at the next pass whatever is due: the first, and one after a message arrived, which may move
    /// when a reading next falls due.
    nudge: bool,
    /// When the member asks after its sensors next, as the last nudge said.
    next: Option<DateTime>,
}

impl Transport {
    pub fn new(member: Mqtt) -> Self {
        Transport {
            member: Arc::new(Mutex::new(member)),
            pending: Pending::default(),
            nudge: true,
            next: None,
        }
    }

    /// The member, held for one use: the bus is shared with the rows above that send on it (`Bus`).
    fn bus(&self) -> MutexGuard<'_, Mqtt> {
        self.member.lock().expect("a bus nobody poisoned")
    }

    /// Listen: the sessions spawned before the member subscribes, since a subscription waits in a queue only they
    /// empty, and every arrival waking the task.
    pub(crate) fn listen(&mut self, arrived: &Arrived) -> Result<(), Error> {
        //  THE SESSIONS LISTEN BEFORE THE MEMBER SUBSCRIBES: a subscription waits in a queue only they empty.
        let listening = {
            let mut member = self.bus();
            member.inbox.wakes(arrived.wake());
            std::mem::take(&mut member.listening)
        };
        for session in listening {
            tokio::spawn(session);
        }
        self.bus().open()?;
        Ok(())
    }

    /// What the member's policy does of its triggers: the agent's own words carried where they are on a channel it
    /// carries, and a document the agent said told to each agent it is to that listens on the bus, read back from the
    /// store as it was said.
    pub(crate) fn heard_event(&mut self, job: usize, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let store = self.bus().beliefs().clone();
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
                    .try_for_each(|agent| self.bus().tell(agent.as_str(), &payload).map(|_| ()));
                pass.end(activity);
                told?;
            }
            _ => carry(&store, &mut *self.bus(), event, pass, CARRYING)?,
        }
        Ok(Vec::new())
    }

    pub(crate) fn stop(&mut self) {
        self.bus().stop();
    }
}

impl Jobs for Transport {
    fn submitted(&mut self) -> Vec<usize> {
        let inbox = self.bus().inbox.clone();
        vec![HANDLE; self.pending.arrived(&inbox)]
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
                    let next = self.bus().nudge_until(pass.now)?;
                    self.next = next;
                }
                if let Some(next) = self.next {
                    pass.wake_at(next);
                }
                Ok(Vec::new())
            }
            HANDLE => {
                let Some(message) = self.pending.oldest() else {
                    return Ok(Vec::new());
                };
                self.nudge = true;
                let (written, heard, store, me) = {
                    let mut member = self.bus();
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
}

/// THE BUS AS THE ROWS ABOVE SEE IT (`orexis_transport::Member`): a device that takes commands on a topic, its own or its
/// board's, is a channel sent on; what a step commands is published there as the document it is, not retained.
pub struct Bus(pub Arc<Mutex<Mqtt>>);

impl Member for Bus {
    fn reaches(&self, channel: &str) -> Result<Option<Exchange>, Error> {
        let member = self.0.lock().expect("a bus nobody poisoned");
        Ok(member.takes_commands(channel)?.then_some(Exchange::Sent))
    }

    fn listen(&self, channel: &str, _inbox: Inbox) -> Result<(), Error> {
        Err(Error::Evaluation(format!(
            "{channel}: the bus is not yet listened to through the contract (#1220)"
        )))
    }

    fn send(&self, channel: &str, payload: &[u8], _reply: Option<Inbox>) -> Result<(), Error> {
        let document: serde_json::Value = serde_json::from_slice(payload)
            .map_err(|e| Error::Evaluation(format!("{channel}: a command that is no JSON document: {e}")))?;
        self.0
            .lock()
            .expect("a bus nobody poisoned")
            .actuate(channel, &document)?;
        Ok(())
    }
}
