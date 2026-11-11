//! EXECUTION, in Rust: the intentions this agent is committed to, and what carries a commitment out — ported from
//! `crates/orexis-execution/` and held to what its suite asks.
//!
//! - `executor`: the intentions, adopted by reference from a plan published, walked step by step, each step held to
//!   what it predicts, and ended by the doors planning knocks at;
//! - `implementation`: the operations taking a step does, read off the action's row;
//! - `create`: the package's part, walking what is due every pass.
//!
//! - `events`: what it says happened — a step taken and answered, an intention resolved — to whoever watches.
//!
//! NOT PORTED: the two threads, which the runtime's pass replaces.

pub mod command;
pub mod create;
pub mod events;
mod executor;
mod implementation;
pub mod ontology;
pub mod says;

pub use executor::{Executor, Said, Standing, Take};
