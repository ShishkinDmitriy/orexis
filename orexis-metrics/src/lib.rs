//! METRICS, as `orexis-metrics/` keeps them: every reported event tallied in memory, and written once a window with
//! every level as it last stood — reading an event only through its marks (`orexis::events`), so nothing here names a
//! package's word. Created only where a metrics sink is loaded.
//!
//! AN EVENT IS NOT A POINT. A counted event is added to the window's TALLY for its measurement and its tags: how many
//! (`count`), for each VALUE its sum, mean and max, all floats so a field never changes type between windows, and for
//! each FLAG how many raised it, nought where none did. A LEVEL is kept as it last stood, in the type it was said in.
//! At the end of the window the tallies and the levels are written, every point stamped at the flush's own instant,
//! and the next opens.
//!
//! REAL TIME, NEVER THE AGENT'S: the window is kept by a monotonic real clock and a flush is stamped by the wall, so
//! nothing here reads the agent's timeline, which may run fast or tick per read. The window's length is the
//! meter's role's to say (`metrics:windowS`), sixty seconds where it says nothing. Every point is tagged with the world and the
//! agent. The window is written when a pass ends on the first pass by which it has run its length, so a window holds
//! whole passes, and as the part stops, since a stop is an exit.
//!
//! - [`meter`]: the meter the self plays, a struct with a field for each thing its role may state, which reads
//!   itself off the store;
//! - [`create`]: the package's start, which every package this binary holds is given, and its task.

pub mod create;
pub mod meter;
pub mod window;

pub use meter::Meter;
pub use window::{Metrics, Window};
