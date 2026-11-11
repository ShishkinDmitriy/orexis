//! TRANSLATION, in Rust: the agent's chats with people, heard and answered through a language model at a run-time
//! edge, never in a pass — ported from `crates/orexis-translation/` and held to what its suite asks.
//!
//! - [`chat`]: the chats an agent is in, each its channel, its people, its agents, what its model may read and state;
//! - [`briefing`]: what the model is handed before a person's words;
//! - [`readable`]: what a chat may read of the agent, copied, and the two tools that read it;
//! - [`stated`]: what a person may state in a chat, held to its words' bounds, and believed as the world's word;
//! - [`past`]: what happened to the agent — its journal, its series, its metrics — and the tools that read them;
//! - [`model`]: the model client, the one place a language model is asked;
//! - [`events`]: what translation says happened — the model used, and each conversation;
//! - [`create`]: the package's part.

pub mod briefing;
pub mod chat;
pub mod create;
pub mod events;
pub mod model;
pub mod past;
pub mod readable;
pub mod stated;
