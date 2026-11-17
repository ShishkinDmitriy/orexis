//! THE TRANSPORT FAMILY'S CONTRACT: what is the same of every member, `orexis-transport-mqtt`, `-http`, `-telegram`
//! and `-email`, and read by nothing else. A member's thread leaves what it receives in an INBOX for its task to
//! handle, ringing it awake, and A CHANNEL IS THE TRANSPORT'S — a member carries bytes on a topic, a chat, a mailbox or
//! a url and knows nothing of what they mean. Words on a `speech:Chat`'s channel are speech's
//! (`orexis_speech::prose`), and a member that carries them is a CHAT CARRIER (`chat`, behind the feature of that
//! name).
//!
//! - [`inbox`]: a message, and the inbox a member's thread leaves it in;
//! - [`member`]: what a member offers the rows above it — a channel it reaches, to listen on it or send on it — and
//!   the agent's members, which a row reads and names none of;
//! - [`jobs`]: the messages handed on, and the jobs a member's core runs until none is left;
//! - [`wired`]: whether the world wires the self through a member, which each asks as its start begins;
//! - [`chat`]: a member carrying a person's prose and the agent's, the core whole.

pub mod inbox;
pub mod jobs;
pub mod member;
mod wired;

#[cfg(feature = "chat")]
pub mod chat;

pub use inbox::{Inbox, Message};
pub use jobs::{Jobs, Pending};
pub use member::{Exchange, Member, Members, Reached};
pub use wired::wired;
