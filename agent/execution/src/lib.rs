//! EXECUTION, in Rust: the intentions this agent is committed to, and what carries a commitment out — ported from
//! `agent/execution/` and held to what its suite asks.
//!
//! - `executor`: the intentions, adopted by reference from a plan published, walked step by step, each step held to
//!   what it predicts, and ended by the doors planning knocks at;
//! - `implementation`: the operations taking a step does, read off the action's row;
//! - `create`: the package's part, walking what is due every pass.
//!
//! NOT PORTED: the two threads, which the runtime's pass replaces, the events the Python copy signals, and the
//! command and the saying an implementation's operations make, which wait for a transport and for speech.

pub mod create;
mod executor;
mod implementation;
pub mod ontology;

pub use executor::{Executor, Said, Standing};
