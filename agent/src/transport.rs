//! THE TRANSPORT FAMILY'S CONTRACT, as `agent/transport/transport.py` keeps what is the same of every member: a
//! member's task or thread leaves what it receives in an INBOX for the one executing thread to handle, ringing the mind awake, and a CHANNEL IS THE
//! TRANSPORT'S — a member carries bytes on a topic, a chat, a mailbox or a url and knows nothing of what they mean. Words
//! on a `speech:Chat`'s channel are speech's (`orexis_speech::prose`).

use std::collections::VecDeque;
use std::sync::{Arc, Mutex, OnceLock};

use oxsdatatypes::DateTime;

use crate::runtime::Wake;

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
pub struct Inbox {
    queue: Arc<Mutex<VecDeque<Message>>>,
    wake: Arc<OnceLock<Wake>>,
}

impl Inbox {
    /// Ring `wake` at every message from now on; a part says so as it starts.
    pub fn wakes(&self, wake: Wake) {
        let _ = self.wake.set(wake);
    }

    /// A message arrived.
    pub fn deliver(&self, topic: &str, payload: &[u8], at: Option<DateTime>) {
        if let Ok(mut queue) = self.queue.lock() {
            queue.push_back(Message {
                topic: topic.to_string(),
                payload: payload.to_vec(),
                at,
            });
        }
        if let Some(wake) = self.wake.get() {
            wake.ring();
        }
    }

    /// Everything arrived since the last take, oldest first.
    pub fn take(&self) -> Vec<Message> {
        self.queue.lock().map(|mut q| q.drain(..).collect()).unwrap_or_default()
    }
}
