//! THE MQTT TRANSPORT, in Rust, ported from `crates/orexis-transport-mqtt/`: the agent's side of the bus, in MQTT4SSN's
//! words, answering what the container needs of a transport.
//!
//! - [`driver`]: what the agent subscribes to, whose a message is, where a command goes and as what, MQTT's own
//!   filter matching, and the client per broker the environment names;
//! - [`create`]: the member's part, which listens, hands each message to sensing as a job, asks after missing
//!   readings every minute and holds the agent.
//!
//! A CHAT ON A TOPIC is carried too: a person's prose heard there is kept for translation, which the part hands it to,
//! and words said back are published as `{"from": the agent, "text": …}`.

pub mod create;
pub mod driver;
