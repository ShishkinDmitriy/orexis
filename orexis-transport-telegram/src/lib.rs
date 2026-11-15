//! THE TELEGRAM TRANSPORT, in Rust: an agent's own bot over the Bot API — ported from `orexis-transport-telegram/` and
//! held to what its suite asks.
//!
//! - [`driver`]: polled for what is written to the bot, a chat's words said as prose, and told what the agent says;
//! - [`create`]: the member's part, polling as often as a role says (`telegram:polledEveryS`).
//! - [`role`]: what a role the self plays says of this transport, read as one struct with its ontology's defaults;

pub mod create;
pub mod driver;
pub mod role;
