//! ONE AGENT'S PROCESS, as `agent/runtime.py`'s `main` assembles it: the world booted into a store, the parts of the
//! packages its roles load made — each a feature of this binary, so a package an agent does not run is compiled out —
//! and run until nothing holds it. What is each package's at boot is said here, where the packages are known:
//! planning writes the scopes a pass reads.

use std::path::Path;

use orexis::Error;
use orexis::boot::{Booting, boot};
use orexis::clock::Clock;
use orexis::runtime::Part;
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
    (package == "belief" && cfg!(feature = "belief"))
        || (package == "planning" && cfg!(feature = "planning"))
        || (package == "execution" && cfg!(feature = "execution"))
        || (package == "sensing" && cfg!(feature = "sensing"))
}

/// Link planning's part to execution's, as the Python parts' `link` connects their signals: what a pass reached
/// ends the unbegun intentions pursuing it, what it reconsidered ends after its step in flight, and what it
/// published is adopted, in the order the Python Planner says them; and a head about to be taken is asked of the
/// Planner, which says where the present no longer admits it (#916). Whatever walks what planning publishes makes
/// it hold the agent while something is walked.
#[cfg(all(feature = "planning", feature = "execution"))]
pub fn link<'a>(
    planning: &mut orexis_planning::create::Planning<'a>,
    execution: &orexis_execution::create::Execution<'a>,
) {
    planning.walked = true;
    let executor = execution.executor.clone();
    planning.heard = Some(Box::new(move |planner| {
        let mut executor = executor.borrow_mut();
        let mut written = Vec::new();
        for want in &planner.reached {
            written.extend(executor.end_for(want, "reached")?);
        }
        for replaced in &planner.superseded {
            written.extend(executor.supersede_after(&replaced.head, Some(&replaced.by))?);
        }
        for (plan, want) in &planner.handed {
            written.extend(executor.adopt(plan, want)?);
        }
        Ok(written)
    }));
    let planner = planning.planner.clone();
    execution.executor.borrow_mut().taking = Some(Box::new(move |step, at| planner.borrow_mut().check(step, at)));
}

/// Link execution's part to belief's, as the Python executor's `on_write` tells the runtime and execution hears the
/// deliberator's `revised`: every graph the executor writes as the world is revised as it is written, before its
/// walk goes on, and a pass that revised the present queues a walk, since the world may have answered a step.
#[cfg(all(feature = "belief", feature = "execution"))]
pub fn hear<'a>(
    store: &'a Store,
    belief: &orexis_belief::create::Belief<'a>,
    execution: &orexis_execution::create::Execution<'a>,
) {
    execution.executor.borrow_mut().on_write = Some(Box::new(belief.hears()));
    let soon = execution.soon.clone();
    belief.deliberator.borrow_mut().revised = Some(Box::new(move |revised| {
        if orexis_execution::create::present(store, &revised.graphs, &revised.changed)? {
            soon.set(true);
        }
        Ok(())
    }));
}

/// Link sensing's part to belief's, as the Python part's `link` takes belief's: every percept sensing writes, and at
/// start each one nothing was concluded of, is revised by belief's deliberator into sensing's own kind (#944).
#[cfg(all(feature = "belief", feature = "sensing"))]
pub fn observe<'a>(belief: &orexis_belief::create::Belief<'a>, sensing: &mut orexis_sensing::create::Sensing<'a>) {
    let belief = belief.clone();
    sensing.revise = Some(Box::new(move |graphs, kind, at| belief.revise(graphs, kind, at)));
}

/// The parts an agent runs, each named by its package, in the order a pass runs them.
pub type Parts<'a> = Vec<(String, Box<dyn Part + 'a>)>;

/// The parts of the packages `loaded` names, made, linked and in the order a pass runs them: belief, so its rules
/// have concluded of a graph written before anything else hears it, then planning, then execution walking what it
/// adopted, then sensing. `budget` sizes planning's search where a caller states one; none reads the
/// agent's stance.
pub fn assemble<'a>(
    store: &'a Store,
    agent: &str,
    clock: &'a dyn Clock,
    loaded: &[String],
    budget: Option<usize>,
) -> Result<Parts<'a>, Error> {
    let mut parts: Parts<'a> = Vec::new();
    let holds = |package: &str| loaded.iter().any(|p| p == package);
    #[cfg(feature = "belief")]
    let belief = if holds("belief") {
        Some(orexis_belief::create::Belief::new(store, agent)?)
    } else {
        None
    };
    #[cfg(feature = "planning")]
    let mut planning = if holds("planning") {
        Some(orexis_planning::create::Planning::new(store, agent, budget)?)
    } else {
        None
    };
    #[cfg(feature = "execution")]
    let execution = if holds("execution") {
        Some(orexis_execution::create::Execution::new(store, agent, clock)?)
    } else {
        None
    };
    #[cfg(feature = "sensing")]
    let mut sensing = if holds("sensing") {
        Some(orexis_sensing::create::Sensing::new(store, agent)?)
    } else {
        None
    };
    #[cfg(all(feature = "belief", feature = "sensing"))]
    if let (Some(belief), Some(sensing)) = (belief.as_ref(), sensing.as_mut()) {
        observe(belief, sensing);
    }
    #[cfg(all(feature = "planning", feature = "execution"))]
    if let (Some(planning), Some(execution)) = (planning.as_mut(), execution.as_ref()) {
        link(planning, execution);
    }
    #[cfg(all(feature = "belief", feature = "execution"))]
    if let (Some(belief), Some(execution)) = (belief.as_ref(), execution.as_ref()) {
        hear(store, belief, execution);
    }
    #[cfg(feature = "belief")]
    if let Some(belief) = belief {
        parts.push(("belief".into(), Box::new(belief)));
    }
    #[cfg(feature = "planning")]
    if let Some(planning) = planning {
        parts.push(("planning".into(), Box::new(planning)));
    }
    #[cfg(feature = "execution")]
    if let Some(execution) = execution {
        parts.push(("execution".into(), Box::new(execution)));
    }
    #[cfg(feature = "sensing")]
    if let Some(sensing) = sensing {
        parts.push(("sensing".into(), Box::new(sensing)));
    }
    let _ = (store, agent, clock, budget, holds);
    Ok(parts)
}
