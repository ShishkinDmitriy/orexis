//! ONE AGENT'S PROCESS, as `agent/runtime.py`'s `main` assembles it: the world booted into a store, the parts of the
//! packages its roles load made — each a feature of this binary, so a package an agent does not run is compiled out —
//! and run until nothing holds it. What is each package's at boot is said here, where the packages are known:
//! planning writes the scopes a pass reads.

use std::path::Path;

use orexis::Error;
use orexis::boot::{Booting, boot};
use orexis::store::Store;

/// Boot `agent` of `world` into `store` from the documents of `tree`: the packages it loads, each one this binary
/// holds — refused where it plays a role whose package this binary was built without.
pub fn booted(
    store: &Store,
    tree: &Path,
    world: &Path,
    agent: &str,
    now: oxsdatatypes::DateTime,
) -> Result<Vec<String>, Error> {
    let loaded = boot(store, &Booting { tree, world, agent })?;
    let held: Vec<&str> = loaded.iter().map(String::as_str).filter(|p| !built(p)).collect();
    if !held.is_empty() {
        return Err(Error::Evaluation(format!(
            "{agent} plays a role whose package this binary was built without: {}",
            held.join(", ")
        )));
    }
    #[cfg(feature = "planning")]
    if loaded.iter().any(|p| p == "planning") {
        orexis_planning::Planner::scope(store, now)?;
    }
    let _ = now;
    Ok(loaded)
}

/// Whether this binary holds `package`'s part.
pub fn built(package: &str) -> bool {
    package == "planning" && cfg!(feature = "planning")
}
