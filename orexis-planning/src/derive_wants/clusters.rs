//! THE CLUSTERS A WANT IS MINTED PER: the witnesses grouped by scope, instance and stretch, and the groups a held
//! constraint couples merged into one.

use oxsdatatypes::DateTime;

use orexis::Error;
use orexis::clock::isoformat;

use super::Witness;
use crate::couplings::Couplings;
use crate::find_scopes::Scopes;

/// An instant as Python's `str(datetime)` spells it, which the coupled groups are ordered by.
fn py_str(at: Option<DateTime>) -> String {
    at.map_or("None".to_string(), |t| isoformat(t).replacen('T', " ", 1))
}

type GroupKey = (Option<String>, String, DateTime, Option<DateTime>);

/// The witnesses grouped by SCOPE, by instance and by stretch — and where a constraint can make two instances'
/// plans collide, the two as one. A witness its scope cannot place joins every group over its own stretch.
pub(super) fn clusters(
    scopes: Option<&Scopes>,
    witnesses: &[Witness],
    coupled: Option<&Couplings>,
) -> Result<Vec<Vec<Witness>>, Error> {
    if witnesses.is_empty() {
        return Ok(Vec::new());
    }
    let Some(scopes) = scopes else {
        return Err(Error::Evaluation(
            "the store holds no scope graph — scope_actions has not run".into(),
        ));
    };
    let mut groups: Vec<(GroupKey, Vec<Witness>)> = Vec::new();
    let mut loose = Vec::new();
    for w in witnesses {
        let mut w = w.clone();
        let about: Vec<&str> = w.about.iter().map(String::as_str).collect();
        let mut placed = scopes.meet(about.iter().copied());
        w.placed = Vec::new();
        if placed.len() != 1 && !w.key.is_empty() {
            let narrowed = scopes.meet(about.iter().copied().chain(w.key.iter().map(String::as_str)));
            if narrowed.len() == 1 {
                placed = narrowed;
                w.placed = w.key.clone();
            }
        }
        let scope = (placed.len() == 1).then(|| placed.into_iter().next().expect("one"));
        if scope.is_some() || w.about.as_deref() == Some(w.instance.as_str()) {
            let key = (scope, w.instance.clone(), w.at, w.until);
            match groups.iter_mut().find(|(k, _)| *k == key) {
                Some((_, group)) => group.push(w),
                None => groups.push((key, vec![w])),
            }
        } else {
            loose.push(w);
        }
    }
    if let Some(coupled) = coupled
        && groups.len() > 1
    {
        groups = merged(groups, coupled);
    }
    if groups.is_empty() {
        return Ok(vec![loose]);
    }
    for w in loose {
        let shared: Vec<usize> = (0..groups.len())
            .filter(|&i| (groups[i].0.2, groups[i].0.3) == (w.at, w.until))
            .collect();
        let into: Vec<usize> = if shared.is_empty() {
            (0..groups.len()).collect()
        } else {
            shared
        };
        for i in into {
            groups[i].1.push(w.clone());
        }
    }
    Ok(groups.into_iter().map(|(_, g)| g).collect())
}

/// The groups a constraint couples merged, transitively: two of one scope over one stretch whose instances
/// `coupled.joins`, under the first's key in Python's order of the keys.
fn merged(groups: Vec<(GroupKey, Vec<Witness>)>, coupled: &Couplings) -> Vec<(GroupKey, Vec<Witness>)> {
    let spelled = |k: &GroupKey| {
        (
            k.0.clone().unwrap_or_else(|| "None".into()),
            k.1.clone(),
            py_str(Some(k.2)),
            py_str(k.3),
        )
    };
    let mut groups = groups;
    groups.sort_by_cached_key(|(k, _)| spelled(k));
    let mut parent: Vec<usize> = (0..groups.len()).collect();
    fn find(parent: &mut [usize], mut k: usize) -> usize {
        while parent[k] != k {
            parent[k] = parent[parent[k]];
            k = parent[k];
        }
        k
    }
    for i in 0..groups.len() {
        for j in i + 1..groups.len() {
            let (a, b) = (&groups[i].0, &groups[j].0);
            if (&a.0, a.2, a.3) == (&b.0, b.2, b.3) && coupled.joins(&a.1, &b.1) {
                let (ra, rb) = (find(&mut parent, i), find(&mut parent, j));
                if ra != rb {
                    parent[rb] = ra;
                }
            }
        }
    }
    let mut out: Vec<(usize, GroupKey, Vec<Witness>)> = Vec::new();
    let roots: Vec<usize> = (0..groups.len()).map(|i| find(&mut parent, i)).collect();
    for (i, (key, group)) in groups.into_iter().enumerate() {
        let root = roots[i];
        match out.iter_mut().find(|(r, _, _)| *r == root) {
            Some((_, _, held)) => held.extend(group),
            None => out.push((root, key, group)),
        }
    }
    out.into_iter().map(|(_, k, g)| (k, g)).collect()
}
