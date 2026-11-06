//! A WANT MINTED: its name, off the desire and what the cluster is about, its graph, and the shape it is held to —
//! the desire's narrowed to its instances and its estimate with `$this` bound.

use std::collections::BTreeSet;
use std::sync::LazyLock;

use oxigraph::model::{Literal, NamedNode, Term};
use oxsdatatypes::DateTime;
use regex::Regex;

use orexis::Error;
use orexis::bind::{Value, bind};
use orexis::clock::isoformat;
use orexis::store::Store;

use super::clusters::clusters;
use super::{MET_WHEN, SH, Said, UNMET_WHEN, Witness, covering, keys_of, node, spelled};
use crate::couplings::Couplings;
use crate::find_scopes::Scopes;
use crate::ontology::ABOUT;
use crate::shapes::Shapes;

pub const RECOGNIZED: &str = "http://example.org/orexis/planning#Recognized";

const ESTIMATES: &str = "http://example.org/orexis/planning#estimates";

const KEYED_BY: &str = "http://example.org/orexis/planning#keyedBy";

const REOPENS: &str = "http://example.org/orexis/planning#reopens";

const RDFS_LABEL: &str = "http://www.w3.org/2000/01/rdf-schema#label";

static THIS: LazyLock<Regex> = LazyLock::new(|| Regex::new(r"\$this\b").expect("a valid pattern"));

/// The names the clusters of `found` come to — what minting would call them, or the standing want already about
/// every instance of a cluster. One namer for both halves.
pub(super) fn named(
    shapes: &Shapes,
    scopes: Option<&Scopes>,
    desire: &str,
    said: &Said,
    found: &[Witness],
    coupled: Option<&Couplings>,
    standing: &BTreeSet<String>,
) -> Result<BTreeSet<String>, Error> {
    let mut out = BTreeSet::new();
    for cluster in clusters(scopes, found, coupled)? {
        let about: Vec<String> = cluster
            .iter()
            .filter_map(|w| w.about.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let instances: Vec<String> = cluster
            .iter()
            .map(|w| w.instance.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        let instance = (instances.len() == 1).then(|| instances[0].as_str());
        let name = name_of(shapes, desire, said, &about, instance, &keys_of(&cluster));
        if standing.contains(&name) {
            out.insert(name);
        } else {
            out.insert(covering(shapes, standing, &instances, &about).unwrap_or(name));
        }
    }
    Ok(out)
}

fn tail(iri: &str) -> &str {
    let tail = iri.rsplit('#').next().unwrap_or(iri);
    tail.rsplit('/').next().unwrap_or(tail)
}

/// The name of the want minted under `desire` for one cluster: the desire's, suffixed by the key that placed it,
/// what it is about where that is narrower than the desire, and the instance where the desire ranges over several.
pub(super) fn name_of(
    shapes: &Shapes,
    desire: &str,
    said: &Said,
    about: &[String],
    instance: Option<&str>,
    keys: &[String],
) -> String {
    let declared: BTreeSet<String> = said
        .iter()
        .filter(|(p, _)| p == ABOUT)
        .map(|(_, o)| spelled(o))
        .collect();
    let abouts: BTreeSet<String> = about.iter().cloned().collect();
    let mut tails: Vec<&str> = keys.iter().map(|k| tail(k)).collect();
    if !about.is_empty() && abouts != declared {
        tails.extend(about.iter().map(|a| tail(a)));
    }
    if let Some(instance) = instance
        && !about.iter().any(|a| a == instance)
        && !targets_one_node(shapes, said)
    {
        tails.insert(0, tail(instance));
    }
    let mut out = format!("{desire}.pursued");
    for t in tails {
        out.push('.');
        out.push_str(t);
    }
    out
}

/// Does the desire's met-test name the one node it is about (`sh:targetNode`)?
fn targets_one_node(shapes: &Shapes, said: &Said) -> bool {
    said.iter().any(|(p, o)| {
        (p == MET_WHEN || p == UNMET_WHEN)
            && matches!(o, Term::NamedNode(_))
            && shapes.has(o, &format!("{SH}targetNode"))
    })
}

/// The graph the wants in trouble over ONE STRETCH live in, named for that stretch.
fn graph_of(agent: &str, at: DateTime, until: Option<DateTime>) -> String {
    let until = until.map_or("open".to_string(), stamp);
    format!("http://example.org/orexis/graph/pursued/{agent}/{}--{until}", stamp(at))
}

fn stamp(at: DateTime) -> String {
    isoformat(at).replace(':', "").replace('+', "p")
}

/// An instant as Python's `isoformat(timespec='minutes')` spells it.
fn to_the_minute(at: DateTime) -> String {
    let full = isoformat(at);
    let (date, time) = full.split_once('T').expect("an isoformat has a T");
    let zone = time.find(['+', '-']).map_or("", |i| &time[i..]);
    format!("{date}T{}{zone}", &time[..5])
}

/// A string as a SPARQL literal, quoted and escaped.
fn quoted(text: &str) -> String {
    let mut out = String::from("\"");
    for c in text.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// Write one derived want: taken out of its stretch's graph and put back, the graph's row and its period once.
#[allow(clippy::too_many_arguments)]
fn write(
    store: &Store,
    agent: &str,
    uri: &str,
    holder: &str,
    desire: &str,
    label: &str,
    now: DateTime,
    at: DateTime,
    until: Option<DateTime>,
    points: &[(String, String)],
    shape: &[String],
) -> Result<(), Error> {
    let graph = graph_of(agent, at, until);
    let said_points: Vec<String> = points.iter().map(|(p, o)| format!("<{uri}> <{p}> <{o}> .")).collect();
    let found_at = format!(" ; prov:generatedAtTime \"{}\"^^xsd:dateTime", isoformat(now));
    let mut period = format!(" ; orexis:start \"{}\"^^xsd:dateTime", isoformat(at));
    if let Some(until) = until {
        period.push_str(&format!(" ; orexis:end \"{}\"^^xsd:dateTime", isoformat(until)));
    }
    let forget = bind(
        crate::withdraw::FORGET_ONE_U,
        &[("graph", Value::iri(graph.as_str())), ("want", Value::iri(uri))],
    )?;
    store.update(&format!(
        "{forget} ;
INSERT {{
  GRAPH <{graph}> {{
  <{holder}> planning:holds <{uri}> .
  <{uri}> a planning:Want{found_at} ;
      planning:state <{RECOGNIZED}> ;
      prov:wasDerivedFrom <{desire}> ;
      rdfs:label {label} .
  {points}
  {shape} }}
  GRAPH ?cat {{ <{graph}> a planning:WantGraph ; orexis:arrivedBy orexis:Derived ;
      orexis:ownedBy <{holder}> . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> dcterms:temporal
      [ a dcterms:PeriodOfTime{period} ] . }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph }}
         FILTER NOT EXISTS {{ GRAPH ?cat {{ <{graph}> dcterms:temporal ?held }} }} }} ;
INSERT {{ GRAPH ?cat {{ <{graph}> a ?kind }} }}
WHERE {{ GRAPH ?cat {{ ?cat a orexis:CatalogueGraph . ?vocabulary a orexis:OntologyGraph }}
        GRAPH ?vocabulary {{ planning:WantGraph rdfs:subClassOf ?kind }} }}",
        label = quoted(label),
        points = said_points.join(" "),
        shape = shape.join("\n  "),
    ))
}

/// Derive the want pursued under `desire` and write it — None, and the desire stays the goal, where the desire
/// states its met-test inline, since a blank node has no name another graph could point at.
#[allow(clippy::too_many_arguments)]
pub(super) fn mint(
    store: &Store,
    shapes: &Shapes,
    holder: &str,
    desire: &str,
    now: DateTime,
    at: DateTime,
    until: Option<DateTime>,
    said: &Said,
    about: &[String],
    instances: &[String],
    keys: &[String],
    reopens: &[String],
) -> Result<Option<String>, Error> {
    let instance = (instances.len() == 1).then(|| instances[0].as_str());
    let child = name_of(shapes, desire, said, about, instance, keys);
    let mut points: Vec<(String, String)> = keys.iter().map(|k| (KEYED_BY.to_string(), k.clone())).collect();
    points.extend(reopens.iter().map(|w| (REOPENS.to_string(), w.clone())));
    let (mut met_test, mut estimate) = (None, None);
    for (p, o) in said {
        if matches!(o, Term::BlankNode(_)) {
            log::warn!("{} states its {} inline; it is pursued itself", tail(desire), tail(p));
            return Ok(None);
        }
        match p.as_str() {
            ABOUT | RDFS_LABEL => {}
            MET_WHEN | UNMET_WHEN => met_test = Some((p.clone(), spelled(o))),
            ESTIMATES => estimate = Some(spelled(o)),
            _ => points.push((p.clone(), spelled(o))),
        }
    }
    let mut shape_lines = Vec::new();
    if let Some((polarity, shape)) = met_test {
        let own = format!("{child}{}", if polarity == MET_WHEN { ".met" } else { ".avoided" });
        shape_lines = narrowed(shapes, &shape, &own, instances, about);
        points.push((polarity, own));
    }
    if let Some(estimate) = estimate {
        let own = format!("{child}.estimate");
        let lines = instantiated(shapes, &estimate, &own, instance)?;
        let pointed = if lines.is_empty() { estimate } else { own };
        shape_lines.extend(lines);
        points.push((ESTIMATES.to_string(), pointed));
    }
    let labels: Vec<String> = said
        .iter()
        .filter(|(p, _)| p == RDFS_LABEL)
        .map(|(_, o)| spelled(o))
        .collect();
    let named = labels
        .first()
        .cloned()
        .unwrap_or_else(|| desire.rsplit('#').next().unwrap_or(desire).to_string());
    let label = if at > now {
        format!("foreseen: {named} at {}", to_the_minute(at))
    } else {
        format!("pursued: {named}")
    };
    write(
        store,
        tail(holder),
        &child,
        holder,
        desire,
        &label,
        now,
        at,
        until,
        &points,
        &shape_lines,
    )?;
    log::info!("{} reads unmet: pursuing {}", tail(desire), tail(&child));
    Ok(Some(child))
}

fn line(s: &Term, p: &NamedNode, o: &Term) -> String {
    format!("{s} {p} {o} .")
}

/// The desire's met-test as THIS want's: the same shape under the want's own name, its targets the instances the
/// want is about, and only the blocks and constraints about what it is about. N-Triples lines.
pub(super) fn narrowed(
    shapes: &Shapes,
    shape: &str,
    own: &str,
    instances: &[String],
    abouts: &[String],
) -> Vec<String> {
    let targets = [
        "targetNode",
        "targetClass",
        "targetSubjectsOf",
        "targetObjectsOf",
        "target",
    ]
    .map(|t| format!("{SH}{t}"));
    let (property, sparql, this) = (format!("{SH}property"), format!("{SH}sparql"), format!("{SH}this"));
    let root = node(shape);
    let own_node = NamedNode::new_unchecked(own);
    let own_term: Term = own_node.clone().into();
    let cbd = shapes.cbd(&root);
    let keep: BTreeSet<&str> = abouts.iter().map(String::as_str).collect();
    let mut out: Vec<String> = Vec::new();
    let mut dropped: BTreeSet<String> = BTreeSet::new();
    let add = |l: String, out: &mut Vec<String>| {
        if !out.contains(&l) {
            out.push(l);
        }
    };
    for (p, o) in cbd.predicate_objects(&root) {
        if targets.iter().any(|t| t == p.as_str()) && !instances.is_empty() {
            continue;
        }
        if p.as_str() == property || p.as_str() == sparql {
            let mut about = cbd.value(&o, ABOUT).map(|a| spelled(&a));
            if about.as_deref() == Some(this.as_str()) {
                if !instances.is_empty() && !keep.is_empty() && !instances.iter().any(|i| keep.contains(i.as_str())) {
                    dropped.extend(cbd.cbd(&o).triples().iter().map(|(s, p, o)| line(s, p, o)));
                    continue;
                }
                about = None;
            }
            if !keep.is_empty()
                && let Some(about) = &about
                && !keep.contains(about.as_str())
            {
                dropped.extend(cbd.cbd(&o).triples().iter().map(|(s, p, o)| line(s, p, o)));
                continue;
            }
        }
        add(line(&own_term, &p, &o), &mut out);
    }
    let target = NamedNode::new_unchecked(format!("{SH}targetNode"));
    for instance in instances {
        add(line(&own_term, &target, &node(instance)), &mut out);
    }
    for (s, p, o) in cbd.triples() {
        let l = line(&s, &p, &o);
        if s != root && !dropped.contains(&l) {
            add(l, &mut out);
        }
    }
    out
}

/// The desire's estimate as THIS want's: its `sh:select` with `$this` bound to the one instance — nothing where the
/// want is about no one instance or the select never speaks of `$this`.
fn instantiated(shapes: &Shapes, estimate: &str, own: &str, instance: Option<&str>) -> Result<Vec<String>, Error> {
    let select = format!("{SH}select");
    let root = node(estimate);
    let (Some(instance), Some(text)) = (instance, shapes.value(&root, &select)) else {
        return Ok(Vec::new());
    };
    if !THIS.is_match(&spelled(&text)) {
        return Ok(Vec::new());
    }
    let own: Term = node(own);
    let mut out = Vec::new();
    for (p, o) in shapes.predicate_objects(&root) {
        let o = if p.as_str() == select {
            Literal::new_simple_literal(bind(&spelled(&o), &[("this", Value::iri(instance))])?).into()
        } else {
            o
        };
        let l = line(&own, &p, &o);
        if !out.contains(&l) {
            out.push(l);
        }
    }
    Ok(out)
}
