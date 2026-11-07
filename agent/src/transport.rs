//! THE TRANSPORT FAMILY'S CONTRACT, as `agent/transport/transport.py` keeps what is the same of every member: a
//! member's thread leaves what it receives in an INBOX for the one executing thread to handle, and a CHANNEL IS THE
//! TRANSPORT'S — a member carries bytes on a topic, a chat, a mailbox or a url and knows nothing of what they mean. For a
//! `speech:Chat`'s channel a member says `Prose`, which translation hears when the parts are linked, and sends prose
//! back as a `Carrier`, so no member imports translation and translation imports no member.

use std::collections::VecDeque;
use std::sync::{Arc, Mutex};

use oxsdatatypes::DateTime;

use crate::Error;

/// A message on a channel, and the instant it arrived where whoever handed it knows one — a network thread knows none
/// of the agent's timeline, so it is stamped with the instant of the pass that handles it.
#[derive(Clone, Debug, PartialEq)]
pub struct Message {
    pub topic: String,
    pub payload: Vec<u8>,
    pub at: Option<DateTime>,
}

/// Where the clients' threads leave what they receive, for the one executing thread to handle.
#[derive(Clone, Default)]
pub struct Inbox(Arc<Mutex<VecDeque<Message>>>);

impl Inbox {
    /// A message arrived.
    pub fn deliver(&self, topic: &str, payload: &[u8], at: Option<DateTime>) {
        if let Ok(mut queue) = self.0.lock() {
            queue.push_back(Message {
                topic: topic.to_string(),
                payload: payload.to_vec(),
                at,
            });
        }
    }

    /// Everything arrived since the last take, oldest first.
    pub fn take(&self) -> Vec<Message> {
        self.0.lock().map(|mut q| q.drain(..).collect()).unwrap_or_default()
    }
}

/// A person's words on a channel at `at`: the channel's node in the world, the person who said them where the channel
/// tells, and the text. Where the carrier tells whom the words were for, `addressed` says so — true where they tagged
/// or replied to this agent's own account, false where they tagged or replied to someone else and not it — and
/// `message` is the carrier's id of the words, which an answer may reply to.
#[derive(Clone, Debug, PartialEq)]
pub struct Prose {
    pub channel: String,
    pub sender: Option<String>,
    pub text: String,
    pub at: Option<DateTime>,
    pub addressed: Option<bool>,
    pub message: Option<String>,
}

/// Whoever hears a person's prose: the graphs it wrote in answer.
pub type Hears<'a> = Box<dyn FnMut(&Prose) -> Result<Vec<String>, Error> + 'a>;

/// A member that carries a chat's channel: prose out on it, and the agent shown writing there.
pub trait Carrier {
    /// Prose out on `channel`, as a reply to the message `reply` names where the carrier threads one. Whether anything
    /// was SENT: a member that does not carry the channel sends nothing.
    fn say_to(&mut self, channel: &str, text: &str, reply: Option<&str>) -> bool;

    /// Show on `channel` that the agent is writing, where the channel can show it. Whether it was SHOWN.
    fn writing_in(&mut self, channel: &str) -> bool;
}
