//! SENSING, TO INFLUXDB: the half of the pair that keeps house. `orexis-sensing/` observes, and keeps in the kind its
//! rules read exactly the readings they are about; an older one it files past and forgets nothing. This is what
//! writes a reading to the agent's series store, and nothing else does: on a timer it archives every reading sensing
//! holds that the store has not yet taken, read or past, and removes the past ones the store holds.
//!
//! OPTIONAL, AND THE DEPLOYMENT'S: the package has a task only where it is handed a series store to archive to. An
//! agent with none - a test, a world nobody monitors - keeps every reading where it lies, in its beliefs, and
//! nothing of sensing's logic differs, since no rule reads a past reading.
//!
//! ARCHIVED ONCE, THEN REMOVED WHEN PAST: what the store took is remembered by the point it took (`Shipped`), so a
//! reading is written once, and again only where its point has changed since - one read while sensing was still
//! concluding it. A past reading is forgotten only once the store holds its point. A store that refuses leaves all
//! as it lies for the next time, so nothing is lost for a store being away, and the beliefs grow by the readings it
//! missed and no more. What was shipped is remembered for the run alone: after a restart each reading still held is
//! written again, on its own instant, measurement and tags, so the series holds it once. The point is sensing's to
//! say (`past::point`) and the graphs are sensing's to remove (`past::forget`): this asks, and names no word of an
//! observation.
//!
//! AS OFTEN AS THE OBSERVER'S ROLE SAYS (`sensing:archivedEveryS`), in the agent's seconds, every ten where it says
//! nothing, which is how far the series lags a reading; and a stretch in which sensing observed nothing asks the
//! beliefs nothing.
//!
//! - [`role`]: the role the package keeps house for and what it says of it, read as one struct;
//! - [`create`]: the package's start, which every package this binary holds is given, and its task.

pub mod archive;
pub mod create;
pub mod role;

pub use archive::{Due, Shipped, archive, due, took};
pub use create::Archives;
