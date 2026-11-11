//! WHAT THE PLANNER SAYS HAPPENED, as `agent/planning/events.py` declares it, to whoever watches the agent. What the
//! executor acts on of a pass it reads off the shared Planner (`handed`, `reached`, `superseded`); these are what the
//! history and the metrics hear, each made only where somebody watches.
//!
//! WHAT IS HISTORY goes to the journal in planning's words: a plan published, `planning:PlanPublished`, carrying the
//! plan graph whole as the beliefs hold it, and a want nothing reaches, `planning:WantUnreachable`, beneath
//! `orexis:Incident`. A want's name is on no metric: what a want reports is tagged by the DESIRE it was derived under.

use oxigraph::model::{Literal, NamedNode, Term, Triple};
use oxsdatatypes::DateTime;

use orexis::events::{Event, Mark, Number, node, triple, typed};

pub const PLANNING: &str = "http://example.org/orexis/planning#";

/// EXECUTION'S WORDS, which planning, the higher package, says its events to execution in: its trigger is what these
/// events are beneath, by planning's ontology, and these are what each is about.
const ADOPTS: &str = "http://example.org/orexis/execution#adopts";
const PURSUES: &str = "http://example.org/orexis/execution#pursues";
const ENDS_AFTER: &str = "http://example.org/orexis/execution#endsAfter";
const OUTCOME: &str = "http://example.org/orexis/execution#outcome";
const DERIVED_FROM: &str = "http://www.w3.org/ns/prov#wasDerivedFrom";
const HEAD: &str = "http://example.org/orexis/execution#head";
const BLOCKED: &str = "http://example.org/orexis/execution#blocked";

fn named(iri: &str) -> Term {
    NamedNode::new_unchecked(iri).into()
}

fn term(name: &str) -> String {
    format!("{PLANNING}{name}")
}

/// A plan published into the beliefs for `want`, from the imaginarium of `scope`: in how many passes its want was
/// searched and what was weighed for it in all, the real seconds since it was first searched, the estimate at the
/// present ground against what the plan spent, and whether an intention pursued the want before; at `at`, and the plan
/// graph's own triples.
#[derive(Clone, Debug, PartialEq)]
pub struct PlanPublished {
    pub plan: String,
    pub want: String,
    pub desire: Option<String>,
    /// The desire itself, the want derived from it.
    pub derived_from: Option<String>,
    pub scope: Option<String>,
    pub passes: Option<f64>,
    pub weighed: Option<f64>,
    pub wall_s: Option<f64>,
    pub estimate: Option<f64>,
    pub cost: Option<f64>,
    pub replan: bool,
    pub at: Option<DateTime>,
    pub said: Vec<Triple>,
}

impl Event for PlanPublished {
    fn metric(&self) -> Option<&'static str> {
        Some("published")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("desire", Mark::Tag(self.desire.clone())),
            ("scope", Mark::Tag(self.scope.clone())),
            ("passes", Mark::Value(self.passes)),
            ("weighed", Mark::Value(self.weighed)),
            ("wall_s", Mark::Value(self.wall_s)),
            ("estimate", Mark::Value(self.estimate)),
            ("cost", Mark::Value(self.cost)),
            ("replan", Mark::Flag(self.replan)),
        ]
    }

    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        let mut out = vec![
            typed(entry.clone(), &term("PlanPublished")),
            triple(entry.clone(), &term("published"), node(&self.plan)),
        ];
        out.extend(self.said.iter().cloned());
        Some(out)
    }

    fn at(&self) -> Option<DateTime> {
        self.at
    }

    fn kind(&self) -> Option<&'static str> {
        Some("http://example.org/orexis/planning#PlanPublished")
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        let mut about = vec![(ADOPTS, named(&self.plan)), (PURSUES, named(&self.want))];
        about.extend(self.derived_from.as_deref().map(|d| (DERIVED_FROM, named(d))));
        about
    }
}

/// A walking want the present meets, at `at`: its unbegun intentions end `reached`. Said to execution; kept in no
/// journal yet, as a start and an end are not.
#[derive(Clone, Debug, PartialEq)]
pub struct WantReached {
    pub want: String,
    pub at: DateTime,
}

impl Event for WantReached {
    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }

    fn kind(&self) -> Option<&'static str> {
        Some("http://example.org/orexis/planning#WantReached")
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        vec![
            (PURSUES, named(&self.want)),
            (OUTCOME, Literal::new_simple_literal("reached").into()),
        ]
    }
}

/// A walking plan whose untaken steps a reconsideration replaced, at `at`: its intention ends after `head`, its step in
/// flight, and the plan replacing it pursues `by`. Said to execution; kept in no journal yet.
#[derive(Clone, Debug, PartialEq)]
pub struct PlanSuperseded {
    pub head: String,
    pub by: String,
    pub at: Option<DateTime>,
}

impl Event for PlanSuperseded {
    fn at(&self) -> Option<DateTime> {
        self.at
    }

    fn kind(&self) -> Option<&'static str> {
        Some("http://example.org/orexis/planning#PlanSuperseded")
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        vec![(ENDS_AFTER, named(&self.head)), (PURSUES, named(&self.by))]
    }
}

/// A head execution asked about, checked against the present at `at`: blocked or not. Said to execution beneath its
/// walking trigger; kept in no journal, since what is kept is the act or the failure execution makes of it.
#[derive(Clone, Debug, PartialEq)]
pub struct HeadChecked {
    pub head: String,
    pub blocked: bool,
    pub at: DateTime,
}

impl Event for HeadChecked {
    fn at(&self) -> Option<DateTime> {
        Some(self.at)
    }

    fn kind(&self) -> Option<&'static str> {
        Some("http://example.org/orexis/planning#HeadChecked")
    }

    fn about(&self) -> Vec<(&'static str, Term)> {
        vec![(HEAD, named(&self.head)), (BLOCKED, Literal::from(self.blocked).into())]
    }
}

/// A want standing, walked by nothing, no search cut short: nothing this agent holds reaches it.
#[derive(Clone, Debug, PartialEq)]
pub struct WantUnreachable {
    pub want: String,
    pub desire: Option<String>,
    pub at: Option<DateTime>,
}

impl Event for WantUnreachable {
    fn metric(&self) -> Option<&'static str> {
        Some("unreachable")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![("desire", Mark::Tag(self.desire.clone()))]
    }

    fn statements(&self, entry: &NamedNode) -> Option<Vec<Triple>> {
        Some(vec![
            typed(entry.clone(), &term("WantUnreachable")),
            triple(entry.clone(), &term("want"), node(&self.want)),
        ])
    }

    fn at(&self) -> Option<DateTime> {
        self.at
    }
}

/// One want's search in one pass, as it ends: its real seconds, the budget it had and the candidates it weighed, by
/// the desire, the scope and how it ended.
#[derive(Clone, Debug, PartialEq)]
pub struct SearchEnded {
    pub want: String,
    pub desire: Option<String>,
    pub scope: Option<String>,
    pub outcome: Option<String>,
    pub duration_s: Option<f64>,
    pub budget: Option<f64>,
    pub weighed: Option<f64>,
}

impl Event for SearchEnded {
    fn metric(&self) -> Option<&'static str> {
        Some("search")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("desire", Mark::Tag(self.desire.clone())),
            ("scope", Mark::Tag(self.scope.clone())),
            ("outcome", Mark::Tag(self.outcome.clone())),
            ("duration_s", Mark::Value(self.duration_s)),
            ("budget", Mark::Value(self.budget)),
            ("weighed", Mark::Value(self.weighed)),
        ]
    }
}

/// A pass of the Planner, in real seconds per part — laying the ground and finding the present in it, weighing the
/// desires, deriving and withdrawing the wants, searching, publishing — and how many wants it searched.
#[derive(Clone, Debug, PartialEq)]
pub struct Planned {
    pub wants: Option<f64>,
    pub laps: Vec<(String, f64)>,
}

impl Event for Planned {
    fn metric(&self) -> Option<&'static str> {
        Some("planner")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        let lap = |part: &str| self.laps.iter().find(|(n, _)| n == part).map(|(_, s)| *s);
        vec![
            ("wants", Mark::Value(self.wants)),
            ("ground_s", Mark::Value(lap("ground_s"))),
            ("weigh_s", Mark::Value(lap("weigh_s"))),
            ("derive_s", Mark::Value(lap("derive_s"))),
            ("search_s", Mark::Value(lap("search_s"))),
            ("publish_s", Mark::Value(lap("publish_s"))),
        ]
    }
}

/// Which world the present was found to be in `scope` — first, ground, child or surprise — and what of the cone was
/// kept and dropped.
#[derive(Clone, Debug, PartialEq)]
pub struct Rerooted {
    pub scope: String,
    pub present: String,
    pub kept: Option<f64>,
    pub dropped: Option<f64>,
}

impl Event for Rerooted {
    fn metric(&self) -> Option<&'static str> {
        Some("reroot")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        vec![
            ("scope", Mark::Tag(Some(self.scope.clone()))),
            ("present", Mark::Tag(Some(self.present.clone()))),
            ("kept", Mark::Value(self.kept)),
            ("dropped", Mark::Value(self.dropped)),
        ]
    }
}

/// What the imaginarium of `scope` holds at the end of a pass: its possible worlds and the weighings of them — of
/// those how many are on a frontier and how many met their want — and its plans, by why each search ended.
#[derive(Clone, Debug, PartialEq)]
pub struct Imagined {
    pub scope: String,
    pub worlds: i64,
    pub weighings: i64,
    pub open: i64,
    pub met: i64,
    pub satisfied: i64,
    pub exhausted: i64,
    pub no_candidate: i64,
}

impl Event for Imagined {
    fn metric(&self) -> Option<&'static str> {
        Some("imaginarium")
    }

    fn marks(&self) -> Vec<(&'static str, Mark)> {
        let level = |n: i64| Mark::Level(Some(Number::Int(n)));
        vec![
            ("scope", Mark::Tag(Some(self.scope.clone()))),
            ("worlds", level(self.worlds)),
            ("weighings", level(self.weighings)),
            ("open", level(self.open)),
            ("met", level(self.met)),
            ("satisfied", level(self.satisfied)),
            ("exhausted", level(self.exhausted)),
            ("no_candidate", level(self.no_candidate)),
        ]
    }
}
