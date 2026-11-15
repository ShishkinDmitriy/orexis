//! THE EMAIL TRANSPORT, in Rust: an agent's own mailbox over IMAP and SMTP — ported from `orexis-transport-email/` and
//! held to what its suite asks.
//!
//! - [`driver`]: polled for every unseen message, a chat's words said as prose, and told what the agent says;
//! - [`create`]: the member's part, polling as often as a role says (`email:polledEveryS`).

pub mod create;
pub mod driver;
