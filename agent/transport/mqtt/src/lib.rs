//! THE MQTT TRANSPORT, in Rust, ported from `agent/transport/mqtt/`: the agent's side of the bus, in MQTT4SSN's
//! words, answering what the container needs of a transport.
//!
//! - [`driver`]: what the agent subscribes to, whose a message is, where a command goes and as what, MQTT's own
//!   filter matching, and the client per broker the environment names;
//! - [`create`]: the member's part, which listens, hands each message to sensing as a job, asks after missing
//!   readings every minute and holds the agent.
//!
//! NOT PORTED: a person's prose on a chat's topic, which waits for translation.

pub mod create;
pub mod driver;
