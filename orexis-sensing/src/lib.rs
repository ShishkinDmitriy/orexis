//! SENSING, in Rust: the translation row of the agent stack, and nothing above it — ported from `orexis-sensing/`
//! and held to what its suite asks.
//!
//! - [`received`]: a transport hands it the bytes it read for a sensor, and a percept is written per reading,
//!   linked to the one before it — or, for a sensor reading a series, a forecast per stretch ahead;
//! - [`pipeline`]: bytes to a document by the codec, to a number by the pointer;
//! - [`cadence`]: how often a sensor reports, which sensors are the agent's, and which have lapsed;
//! - [`missed`]: which sensors have gone silent, computed and never written;
//! - [`create`]: the package's part, which asks after silence every minute and hands each percept to belief;
//! - [`events`]: what it says happened — each observation, a point of the history, and the sensors silent and doubted.
//!
//! The Python copy's `account`, sensing's word of itself for a person, is read by nothing, and is not ported.

pub mod cadence;
pub mod create;
pub mod events;
pub mod missed;
pub mod ontology;
pub mod pipeline;
pub mod received;
