//! THE HTTP TRANSPORT, in Rust: how an agent reaches a service over the web, in the words of the W3C Web of Things
//! Thing Description, adopted as it stands — ported from `orexis-transport-http/` and held to what its suite asks.
//!
//! - [`driver`]: which sensors are the member's, where each is read, a fetch on a thread of its own, and the body handed
//!   to sensing;
//! - [`create`]: the member's part, polling each of its sensors at the frequency the sensor states.
//! - [`role`]: what a role the self plays says of this transport, read as one struct with its ontology's defaults;

pub mod create;
pub mod driver;
pub mod role;
