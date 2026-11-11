//! THE TELEGRAM TRANSPORT, in Rust: an agent's own bot over the Bot API — ported from `crates/orexis-transport-telegram/` and
//! held to what its suite asks.
//!
//! - [`driver`]: polled for what is written to the bot, a chat's words said as prose, and told what the agent says;
//! - [`create`]: the member's part, polling every `TELEGRAM_POLL_S`.

pub mod create;
pub mod driver;
