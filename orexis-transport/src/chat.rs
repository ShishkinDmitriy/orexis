//! A CHAT CARRIER: a member that carries a `speech:Chat`'s words — a person's, kept as prose for whoever translates,
//! and the agent's own, carried where they are on a channel it carries. Telegram and email are two, told apart by
//! how they poll, read a message and say a text (`ChatMember`); the core that runs them is one (`ChatTransport`).

use orexis::Error;
use orexis::store::Store;
use orexis::task::{Heard, Turn};
use orexis_speech::prose::{Carrier, Prose, ProseKept, carry, kept};
use oxsdatatypes::DateTime;

use crate::inbox::Inbox;
use crate::jobs::{Jobs, Pending};

/// The job that polls the member's channel for what is written there.
pub const POLL: usize = 0;
/// The job that handles one message the member handed on.
pub const HANDLE: usize = 1;
/// The job its policy runs on its carrying trigger.
pub const CARRY: usize = 2;

/// WHAT A CHAT CARRIER IS: a speech `Carrier` that polls its channel, reads a message as a person's prose, and says
/// in its own words what it does as an activity and who holds the agent running.
pub trait ChatMember: Carrier {
    /// Its activity of carrying the agent's words, in its own namespace.
    const CARRYING: &'static str;
    /// The name it holds the agent running under.
    const HOLDER: &'static str;

    /// The self it carries for.
    fn me(&self) -> &str;
    /// Where its thread leaves what it receives.
    fn inbox(&self) -> &Inbox;
    /// The agent's beliefs.
    fn beliefs(&self) -> &Store;
    /// Ask its channel for what is written there; what arrives is left in the inbox.
    fn poll(&self);
    /// A message read: a person's prose, where it is one.
    fn handle(&mut self, channel: &str, payload: &[u8], at: DateTime) -> Result<Option<Prose>, Error>;
}

/// The member's part: the member, and the messages handed to the pass.
pub struct ChatTransport<M> {
    pub member: M,
    pending: Pending,
}

impl<M: ChatMember> ChatTransport<M> {
    pub fn new(member: M) -> Self {
        ChatTransport {
            member,
            pending: Pending::default(),
        }
    }

    /// What the member's policy does of its trigger: the agent's own words carried where they are on a channel it
    /// carries, and the agent shown writing where the member can show it.
    pub fn heard_event(&mut self, _job: usize, event: &Heard, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        let store = self.member.beliefs().clone();
        carry(&store, &mut self.member, event, pass, M::CARRYING)?;
        Ok(Vec::new())
    }
}

impl<M: ChatMember> Jobs for ChatTransport<M> {
    fn submitted(&mut self) -> Vec<usize> {
        vec![HANDLE; self.pending.arrived(self.member.inbox())]
    }

    fn run(&mut self, job: usize, pass: &mut Turn<'_>) -> Result<Vec<String>, Error> {
        pass.hold(M::HOLDER);
        match job {
            POLL => {
                self.member.poll();
                Ok(Vec::new())
            }
            _ => {
                let Some(message) = self.pending.oldest() else {
                    return Ok(Vec::new());
                };
                let at = message.at.unwrap_or(pass.now);
                let Some(prose) = self.member.handle(&message.topic, &message.payload, at)? else {
                    return Ok(Vec::new());
                };
                //  A PERSON'S WORDS are kept, and said kept, for whoever translates.
                let graph = kept(self.member.beliefs(), self.member.me(), &prose)?;
                pass.emit(&ProseKept { prose: graph.clone() });
                Ok(vec![graph])
            }
        }
    }
}
