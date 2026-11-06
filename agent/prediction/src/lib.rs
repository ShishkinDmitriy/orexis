//! PREDICTION, in Rust: the agent's foresight, ported from `agent/prediction/` and held to what its suite asks.
//!
//! - [`foresee`]: the flows integrated from each ground as the planner lays them, every key advancing together, and
//!   a crossing of a range bound answered as the place the next ground is laid;
//! - [`ranges`]: the ranges that apply to what a sensor observes, and which side of one a number lies on;
//! - [`create`]: the package's part, which hears nothing and offers the foresight at link.

pub mod create;
pub mod foresee;
pub mod ontology;
pub mod ranges;
