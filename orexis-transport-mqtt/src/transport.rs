//! THE MEMBER'S PART: the member, each message on the bus left with the row listening for it or, on the agent's own
//! topic, kept by speech; a document the agent said told on the bus and a chat's words carried — and the bus as the rows above
//! send on it (`Bus`).

use std::sync::{Arc, Mutex, MutexGuard};

use oxigraph::model::NamedNode;

use orexis::Error;
use orexis::task::{Arrived, Heard, Turn};
use orexis_speech::document_of;
use orexis_speech::ontology::{STATEMENT, TO};
use orexis_speech::prose::{ProseKept, carry, kept};

use orexis_transport::{Exchange, Inbox, Jobs, Member, Pending};

use crate::driver::Mqtt;

pub(crate) const HOLD: usize = 0;
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
}

impl Transport {
    pub fn new(member: Mqtt) -> Self {
        Transport {
            member: Arc::new(Mutex::new(member)),
            pending: Pending::default(),
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
            HOLD => {
                //  A MEMBER KEEPS THE AGENT RUNNING: what it senses goes on arriving whatever is wanted. When a reading
                //  is due, and telling its board to sense, are sensing's and actuation's (#1220).
                pass.hold(HOLDER);
                Ok(Vec::new())
            }
            HANDLE => {
                let Some(message) = self.pending.oldest() else {
                    return Ok(Vec::new());
                };
                let (written, heard, store, me) = {
                    let mut member = self.bus();
                    let written = member.handle(&message.topic, &message.payload, message.at.unwrap_or(pass.now))?;
                    let (store, me) = (member.beliefs().clone(), member.me.clone());
                    (written, std::mem::take(&mut member.prose), store, me)
                };
                let mut written = written;
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

/// THE BUS AS THE ROWS ABOVE SEE IT (`orexis_transport::Member`): a sensor that publishes on a topic is a channel
/// LISTENED to, every message on it left in the listener's inbox; a device that takes commands on a topic, its own or
/// its board's, is a channel SENT on, what the operator sends there, a step's command or a nudge, published as the JSON
/// document the firmware reads, not retained.
pub struct Bus(pub Arc<Mutex<Mqtt>>);

impl Bus {
    fn member(&self) -> MutexGuard<'_, Mqtt> {
        self.0.lock().expect("a bus nobody poisoned")
    }
}

impl Member for Bus {
    fn reaches(&self, channel: &str, exchange: Exchange) -> Result<bool, Error> {
        let member = self.member();
        match exchange {
            Exchange::Listened => member.listened(channel),
            Exchange::Sent => member.takes_commands(channel),
            Exchange::Requested => Ok(false),
        }
    }

    fn listen(&self, channel: &str, inbox: Inbox) -> Result<(), Error> {
        self.member().listen_on(channel, inbox)?;
        Ok(())
    }

    fn send(&self, channel: &str, payload: &[u8], _reply: Option<Inbox>) -> Result<(), Error> {
        let document: serde_json::Value = serde_json::from_slice(payload)
            .map_err(|e| Error::Evaluation(format!("{channel}: a command that is no JSON document: {e}")))?;
        self.member().actuate(channel, &document)?;
        Ok(())
    }
}
