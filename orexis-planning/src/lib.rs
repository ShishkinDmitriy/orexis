//! PLANNING, in Rust: the acts a pass runs over the imaginarium, ported from `orexis-planning/` one act at a time
//! and held to the same cases. A STAR, NOT A CHAIN, as there: an act calls no other act, and what one needs of
//! another's work it reads off the rows the other wrote.
//!
//! - `world_at`: the graphs a rule is answered over in one world, or in the present;
//! - `next_ground`: the instant the next ground the search can tell apart begins, where a wait lands;
//! - `admit`: every candidate a world admits, one per action per legal filling, written as the edges leaving it;
//! - `take`: one candidate taken, the world it reaches forked with the action's effect applied, and its row;
//! - `prepare_ground`: what crosses from the belief base into the store a search over one scope stands in;
//! - `lay_ground`: one ground world per period the agent can see, cut to what the search can change;
//! - `scope_actions`: the actions clustered into the scopes their effects join, written as the store's partition;
//! - `find_scopes`: every scope each predicate, term and action is in, read back;
//! - `find_wants`: the wants a store holds at an instant, narrowed by the criteria a caller names;
//! - `derive_wants`: a want minted for every cluster of what a desire's met-test reads unmet, read off the weighings;
//! - `couplings`: which instances a holder's constraints can make collide, over what the actions can reach;
//! - `withdraw`: every derived want the derivation no longer implies, and every want reached, taken away.

mod admit;
mod bridge;
mod couplings;
pub mod create;
mod derive_wants;
pub mod events;
mod extract_plan;
mod find_scopes;
mod find_wants;
mod footprint;
mod lay_ground;
mod memo;
mod next_ground;
pub mod ontology;
pub mod planner;
mod prepare_ground;
mod publish_plan;
mod refine;
mod reroot;
mod scope_actions;
mod shapes;
mod take;
mod terms;
mod unweighed;
mod violation;
mod weigh;
mod withdraw;
mod world_at;

pub use memo::Memo;
pub use planner::Planner;
