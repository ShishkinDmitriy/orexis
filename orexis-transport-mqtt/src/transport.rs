//! THE MEMBER'S PART: the member, and each message on the bus left with the row listening for it — and the bus as the
//! rows above listen and send on it (`Bus`).

use std::sync::{Arc, Mutex, MutexGuard};

use orexis::Error;
use orexis::task::{Arrived, Turn};
use orexis_transport::chat::Words;
use orexis_transport::{Exchange, Inbox, Jobs, Member, Pending};

use crate::driver::Mqtt;

pub(crate) const HOLD: usize = 0;
const HANDLE: usize = 1;

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

    /// The member, held for one use: the bus is shared with the rows above that listen and send on it (`Bus`).
    fn bus(&self) -> MutexGuard<'_, Mqtt> {
        self.member.lock().expect("a bus nobody poisoned")
    }

    /// Listen: the sessions spawned, every arrival waking the task; what is subscribed to is what a row listens to.
    pub(crate) fn listen(&mut self, arrived: &Arrived) {
        let listening = {
            let mut member = self.bus();
            member.inbox.wakes(arrived.wake());
            std::mem::take(&mut member.listening)
        };
        for session in listening {
            tokio::spawn(session);
        }
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
                //  A MEMBER KEEPS THE AGENT RUNNING: what it carries goes on arriving whatever is wanted.
                pass.hold(HOLDER);
                Ok(Vec::new())
            }
            HANDLE => {
                if let Some(message) = self.pending.oldest() {
                    self.bus()
                        .handle(&message.topic, &message.payload, message.at.unwrap_or(pass.now))?;
                }
                Ok(Vec::new())
            }
            _ => Ok(Vec::new()),
        }
    }
}

/// THE BUS AS THE ROWS ABOVE SEE IT (`orexis_transport::Member`): the agent itself where it listens to a topic, a chat's
/// topic and a sensor that publishes on one are channels LISTENED to, every message on one left in the listener's
/// inbox; a peer that listens to a topic, a chat's topic and a device that takes commands on one, its own or its board's,
/// are channels SENT on — a document to a peer published as it is, words on a chat as the chat's message, and what the
/// operator sends a device, a step's command or a nudge, as the JSON document the firmware reads; none retained.
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
            Exchange::Sent => Ok(member.is_chat(channel)? || member.takes_commands(channel)?),
            Exchange::Requested => Ok(false),
        }
    }

    fn listen(&self, channel: &str, inbox: Inbox) -> Result<(), Error> {
        self.member().listen_on(channel, inbox)?;
        Ok(())
    }

    fn send(&self, channel: &str, payload: &[u8], _reply: Option<Inbox>) -> Result<(), Error> {
        let mut member = self.member();
        if member.is_agent(channel)? {
            member.tell(channel, payload)?;
            return Ok(());
        }
        if member.is_chat(channel)? {
            let words = Words::of(payload)
                .ok_or_else(|| Error::Evaluation(format!("{channel}: words that are no JSON object")))?;
            member.say_on(channel, &words)?;
            return Ok(());
        }
        let document: serde_json::Value = serde_json::from_slice(payload)
            .map_err(|e| Error::Evaluation(format!("{channel}: a command that is no JSON document: {e}")))?;
        member.actuate(channel, &document)?;
        Ok(())
    }
}
