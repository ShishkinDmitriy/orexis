"""What the binary reports, and how the dashboards draw it: every event that is a metric, per package, as its `events.rs`
states it — its measurement, what it is, its levels, its flags, its values, and whether it is counted. An event not
named here is still written, and drawn in no panel. The table is by hand because the binary has no registry to ask:
an event says its marks only when one happens."""

from __future__ import annotations

from dataclasses import dataclass

FIELD = "value"


@dataclass(frozen=True)
class Reported:
    """One event a package reports under `measurement`, by the fields the dashboards draw."""
    measurement: str
    about: str
    levels: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    values: tuple[str, ...] = ()
    counted: bool = True


#  IN THE ORDER A PASS RUNS THE PARTS, the runtime first.
REPORTED: dict[str, tuple[Reported, ...]] = {
    'runtime': (
        Reported('pass',
                 'A stretch of the run with something busy, in real seconds, whole and by part — planning, '
                 "walking; a part a stretch does not reach is not in it, and the planner's own parts are its event — with "
                 'how large the belief base is, in quads, and how long the process has run.',
                 levels=('quads', 'uptime_s'), values=('duration_s', 'plan_s', 'execute_s')),
    ),
    'belief': (
        Reported('revise',
                 "A revision pass: the sources it revised or transitioned on, the agent's own state graphs the "
                 "transitions they triggered changed — the present changing, whichever package's arrival triggered "
                 'them, a graph emptied and forgotten among them — how many it was handed, the rule executions it '
                 'spent on both, how many it left cut short for the next pass, and its real seconds.',
                 values=('sources', 'executions', 'cut', 'duration_s')),
        Reported('revisions',
                 "The revisions the belief base's catalogue describes, and how many a budget cut short — settled "
                 'false, which the next pass continues. A revision unsettled window after window is a rule set that '
                 'never settles.',
                 levels=('revisions', 'unsettled'), counted=False),
    ),
    'planning': (
        Reported('published',
                 'A plan published into the beliefs for `want`, from the imaginarium of `scope`: in how many passes '
                 'its want was searched and what was weighed for it in all, the real seconds since it was first '
                 'searched, the estimate at the present ground against what the plan spent — how honest the estimate '
                 "is — and whether an intention pursued the want before, a replan; at `at`, and the plan graph's own "
                 'triples, `said`.',
                 flags=('replan',), values=('passes', 'weighed', 'wall_s', 'estimate', 'cost')),
        Reported('unreachable',
                 'A want standing, walked by nothing, no search cut short: nothing this agent holds reaches it.',
                 ),
        Reported('search',
                 "One want's search in one pass, as it ends: its real seconds, the budget it had and the candidates it "
                 'weighed, by the desire, the scope and how it ended.',
                 values=('duration_s', 'budget', 'weighed')),
        Reported('planner',
                 'A pass of the Planner, in real seconds per part — laying the ground and finding the present in it, '
                 'weighing the desires, deriving and withdrawing the wants, searching, publishing — and how many wants '
                 'it searched.',
                 values=('wants', 'ground_s', 'weigh_s', 'derive_s', 'search_s', 'publish_s')),
        Reported('reroot',
                 'Which world the present was found to be in `scope` — first, ground, child or surprise — and what of '
                 'the cone was kept and dropped. A surprise is the one a pass names.',
                 values=('kept', 'dropped')),
        Reported('imaginarium',
                 'What the imaginarium of `scope` holds at the end of a pass: its possible worlds and the weighings of '
                 'them — of those how many are on a frontier and how many met their want — and its plans, by why each '
                 'search ended. `exhausted` is the one to watch: a budget that keeps cutting searches short is a '
                 'budget too small for the problem, and `no_candidate` is a want nothing this agent holds points at.',
                 levels=('worlds', 'weighings', 'open', 'met', 'satisfied', 'exhausted', 'no_candidate'), counted=False),
    ),
    'execution': (
        Reported('intention',
                 'An intention ended: the want it pursued and how — done, reached, failed, superseded, abandoned — by '
                 'the desire the want was derived under.',
                 ),
        Reported('act',
                 'A step taken — or not, where its taker raised — at `at`, recorded as an act.',
                 flags=('taken',)),
        Reported('landing',
                 "The verdict on a taken step at `at`: landed or not, how late the world answered it in the agent's "
                 'seconds — the instant it was seen to, less the `landsAt` the plan placed — and whether the patience '
                 'ran out on it.',
                 flags=('landed', 'timed_out'), values=('late_s',)),
        Reported('intentions',
                 'How many intentions stand after a walk.',
                 levels=('standing',), counted=False),
    ),
    'sensing': (
        Reported('received',
                 "An observation of `observed_property` by the sensor, reading `value` at `at`: the sensor's and its "
                 "feature of interest's tags, the local names of their IRIs, the raw number the sensor gave where the "
                 'observation has one, and how long after the percept before it it came beside the cadence the world '
                 'states, where either is known.',
                 values=('interval_s', 'cadence_s')),
        Reported('silence',
                 'How many sensors are silent now: the latest reading missing for the limit of cadences the observer '
                 'role reading it allows (`sensing:silentAfter`), as `missed` answers it at each ask, until a reading '
                 'ends it.',
                 levels=('silent',), counted=False),
        Reported('doubted',
                 'A sensor the agent doubts, as it stands at the ask: silent (`missed`), said stuck '
                 '(`sensing:stuckOn`, concluded of the percept holding now), each one or nought; and nought on both '
                 'once, for a sensor doubted at the last ask and no longer. Named by the sensor, so the series says '
                 'WHICH where `silence` says how many.',
                 levels=('silent', 'stuck'), counted=False),
    ),
    'translation': (
        Reported('translated',
                 "One use of the model: a person's message answered (`answer`) or an agent's statement rendered "
                 '(`render`), whether it ended in words, in silence, in no words or in the model failing; the requests '
                 "it made, the tokens they spent by the API's own names, and its real seconds.",
                 values=('requests', 'input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens', 'duration_s')),
    ),
}
