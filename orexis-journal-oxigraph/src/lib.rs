//! THE JOURNAL'S ARCHIVE: the half of the pair that keeps house. `orexis-journal/` writes what happens into the
//! journal, in memory, as it is said; this takes what the journal keeps for good out of it into a triplestore on
//! disk, on a timer, and has the journal forget what it took. One crate does a thing and another keeps house, as
//! `orexis-sensing-influxdb/` does for sensing's readings and `orexis-journal-otlp/` for the activities.
//!
//! WHAT IS TAKEN is what lasts (`Journal::lasting`): each event, and each log record and activity an incident kept.
//! An entry is a named graph in the archive as it is in the journal, so a text reads either alike. The log and the
//! activities no incident kept are never taken: the journal sweeps them past its window.
//!
//! WHAT THE JOURNAL THEN FORGETS is an event at once, and a kept log record or activity once the window has passed
//! it: until then a later incident keeps it again, and what ships the activities reads it there. One that changes
//! after it was taken, an activity told the graphs it wrote, is taken again whole.
//!
//! WHEN: every two of the agent's seconds where anything was written; at once as an incident is kept; and once more as the run ends. So an agent killed outright
//! loses what it said in its last stretch, and one that stops, nothing.
//!
//! THE ARCHIVE IS WHAT A READER OF THE PAST IS HANDED: the endpoint's `/sparql`, a chat's journal tool and a stopped
//! agent's store opened read-only all read it, a stretch behind the journal at most.
//!
//! - [`create`]: the package's start, which every package this binary holds is given, and its task.

pub mod archive;
pub mod create;

pub use archive::Archive;
pub use create::Archives;
