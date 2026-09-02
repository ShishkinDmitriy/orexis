"""One agent, one process. It is given its own id and discovers everything else.

  OREXIS_AGENT_ID=fern orexis-agent

Startup builds its own belief base and then reads it:

  0. the ratified **world files** are loaded into a store that belongs to this process alone,
     and the derivation rules are re-run over them — so what this agent can do is computed
     from the world, not told to it, and no shared service has to be up for that to happen;
  1. the **world** says what I am — what I act for, what I may poll, which market I belong
     to, what I can do, where each of those lives on the wire, and which bus to meet on;
  2. my **own beliefs** supply the parameters for each capability I composed. They are written
     once, at birth, and are mine thereafter — a restart does not touch them;
  3. the **packages** implementing those capabilities are loaded, and nothing else runs;
  4. those beliefs are **validated against the shapes of the capabilities I derived**, and I
     refuse to run if they do not hold — the check belongs where the data is.

The environment tells it which agent it is and where to keep its store. Everything else —
including the broker — is discovered, because a channel name is meaningless without the bus it
is on and every member must agree on it.

Nothing in this process can reach another agent's beliefs, and no module knows the name of
any instance. Adding a capability to an agent is a genesis edit: compose the capability in
the world, add its block of beliefs, and the module starts running at next boot.

See knowledge/decisions/capability-packages.md.
"""

from __future__ import annotations

import logging
from datetime import datetime
import signal

from rdflib import URIRef

from agent import config, genesis

from assembly import loader
from orexis_agent_deliberation.beliefs import BeliefError, Beliefs
from assembly.inject import attribute_for, opened
from orexis_agent_progression.ontology import DESIRES, DESIRE_URGENCY, STATE_GRAPH

#  The avoided-pattern wants the kernel lifts into pursuit itself (#468) — see `pursuing`.
#  The select is OPTIONAL here because the node a want points at may be the DOMAIN's — declared
#  in a package's ontology, public knowledge the desire modality does not keep after its
#  rebuild — and is then read from the belief base, whose default graph merges public knowledge.
#  `?me`, `?node` are BOUND BY SUBSTITUTION (#500) — the engine's own parameters, projected
#  so the engine can reach them — never spliced into the text.
_AVOIDED_Q = """
SELECT ?me ?want ?avoided ?select WHERE {
  ?me orexis:holds ?want .
  ?want orexis:unmetWhen ?avoided .
  OPTIONAL { ?avoided sh:select ?select }
}"""
_SELECT_Q = "SELECT ?node ?select WHERE { ?node sh:select ?select } LIMIT 1"
_IS_SHAPE_Q = "SELECT ?node WHERE { ?node a sh:NodeShape } LIMIT 1"
#  And the SHAPE-authored wants nobody speaks for (#497): a world may assert a positive want
#  whose met-test is a shape the domain package declares; the kernel compiles it and judges.
_SHAPED_Q = """
SELECT ?me ?want ?shape WHERE {
  ?me orexis:holds ?want .
  ?want orexis:metWhen ?shape .
}"""
from orexis_agent_deliberation.deliberator import KEEPING_PICKS, Deliberator
from orexis_agent_deliberation.desire import Desire, Desires
from orexis_agent_deliberation.reviser import Reviser
from orexis_agent_progression.intentions import Intentions
from orexis_agent_progression.keeper import Keeper
from .metrics import Metrics
from orexis_agent_progression.upkeep import BeliefBaseUpkeep
from orexis_agent_progression.store import bind, bindings
from orexis_agent_progression.scheduler import scheduler
from orexis_agent_reactive.loop import loop
from .validate import validate_agent
from .world import Self, World, load_self, load_world

log = logging.getLogger("agent")


def _family_q(family: str) -> str:
    """Which capability terms belong to a family. Asked of the T-Box, so a module can look
    for "whoever perceives" without knowing that polling and listening are the two ways.

    Two branches, and the second is not the tidy-up it looks like. A caller may name a family
    (`sensing:SensingCapability`, whose members are `sensing:Subscribing` and `sensing:Listening`) or it may
    name a capability that is its own family of one — `agent.provider(ACTUATION)` does exactly
    that, and there is no term anywhere declared `a actuation:Actuation`. That used to work by accident:
    the branch said `rdfs:subClassOf*`, and a zero-length path matches reflexively, so the family
    returned itself. Stating it is the same answer without depending on a property path's
    reflexivity to carry a case nobody had written down.

    The subclass walk itself is gone. `orexis/inference.py` asserts what the vocabulary entails
    before anything reads it, so a capability under a sub-family already carries the parent's
    type here.
    """
    return f"""
SELECT ?capability WHERE {{
  {{ GRAPH ?g {{ ?capability a <{family}> }} }}
  UNION
  {{ BIND(<{family}> AS ?capability) }}
}}"""


#  WHAT EVERY AGENT HAS, as classes, so `orexis-validate` can check a package's `@requires`
#  without constructing anything. Registered from the live objects below; this is the same
#  seven, said statically.
KERNEL_SERVICES = (Beliefs, Desires, Intentions, Keeper, Deliberator, Metrics)


class Agent:
    """A single agent: its identity, its beliefs, its modules, and one connection."""

    def __init__(self, agent_id: str, st=None):
        self.id = agent_id
        st_given = st
        # Genesis builds my store from the ratified files; the belief MODALITY owns it from
        # here, and this class never learns what kind it is — that is the separation of
        # concerns a-store-is-a-modality rules. Nothing else can reach it either: the
        # isolation is structural, one process, one volume.
        st = st or genesis.open_belief_base(
            genesis.current_world(), agent_id, config.env("OREXIS_STORE"))
        self.world: World = load_world(st.query)
        self.me: Self = load_self(st.query, agent_id)
        self.beliefs = Beliefs(st, agent_id)
        # The desire modality, rebuilt from the beliefs it is deduced from. Each modality
        # decides its own store and its own writability — this one exposes no writer — and
        # the agent holds the modalities, never the stores, by the sovereign's ruling.
        self.desires = Desires(self.beliefs)
        # The intention modality: the ledger's own store, in its own room of the volume — a
        # commitment survives a restart, so it persists where the imaginarium never does. A
        # pathless mind (every test agent) has no rooms and the ledger stays beside the
        # beliefs, exactly as pre-split volumes kept it; the surface is the boundary.
        self.intentions = Intentions(config.env("OREXIS_STORE") if st_given is None else None,
                                     self.beliefs)

        # Built before the modules, because Observations counts into it and a module builds one
        # of those. Counting only — nothing is reported until run() starts it.
        self.metrics = Metrics(self)
        #  The belief-revision seam: a change is marked here and the pass runs on a thread of
        #  the mind's own, never on the one that noticed (#392).
        self.reviser = Reviser(self)

        #  What this agent offers, by term — the kernel's own, filled below, and a package's
        #  resolved on first ask (an-injected-service-is-reached-by-term).
        self._services: dict = {}
        #  What has to be shut when this agent does, newest first. A provider that YIELDS its
        #  service cleans up after the yield; an ordinary one leaves nothing to do.
        self._closing: list = []


        # exactly the modules this agent composed — no more, no less, and since #216 the
        # IMPORTS follow the grants too: a capability names its owning package by namespace,
        # so nothing this agent was not granted is ever imported into this process.
        registry = loader.registry_for(self.me.capabilities)
        #  THE PACKAGES THIS AGENT LOADS (#455): the grants' owners plus every package a
        #  REQUIRED injection pulls, needs after needs. `offers` and `service` below answer
        #  from this set and the kernel's own table, so a soft annotation (`X | None`) injects
        #  what is already there and never causes a load — a provider elsewhere in the tree is
        #  present in the checkout, not in this build.
        self._packages = loader.packages_for(self.me.capabilities)
        self.modules = [
            registry[c](self) for c in sorted(self.me.capabilities) if c in registry
        ]
        unknown = [c for c in sorted(self.me.capabilities) if c not in registry]
        if unknown:
            log.warning("no package implements %s — the world expects more than this build has",
                        ", ".join(unknown))

        # Check myself before acting. A shape applies only to capabilities I actually derived,
        # so this asks exactly the right questions — and refusing to start is the enforcement.
        # It is not self-report: the consequence is not running, not a claim to be fine.
        validate_agent(self.beliefs, agent_id, self.me.uri, self.me.capabilities,
                       desires=self.desires)

        # Keeping my own house. Not a capability and never optional: every agent's belief base
        # bloats whatever else it can do, so this holds a clock no capability owns — an agent
        # given no room to review itself must still compact. Nothing here starts a thread.
        self.upkeep = BeliefBaseUpkeep(self)


        # And noticing I am cut off (#53) — kernel for the same reason, on a clock of its own
        # because paho's network thread is one of the things it watches. Nothing starts here.

        # The WHETHER. Unconditional, like the modalities above and for the same reason: a mind
        # is not plug-in-able. It was a capability granted by a stake and a lever, which made
        # having one conditional on the world having said so — while `Desires` and `Intentions`
        # were already built for every agent three lines up. That split could not be defended
        # once it was written down in one place.
        #
        # An agent with no stake and no lever gets a deliberator that answers None to
        # everything and reports nothing, which is the honest shape of "there is nothing here
        # to decide" — see `Deliberator.series`.
        #
        # It joins `self.modules` as well as being held by name, because everything the choir
        # does — start, stop, series, the hooks — iterates that list, and a kernel member that
        # needed its own line in each loop would be the same module list maintained twice.
        # `provider()` still cannot return it: it matches on `CAPABILITY`, which is `""` here,
        # because the deliberator is not something a world grants.
        self.deliberator = Deliberator(self)

        # And the KEEPER, for the same reason and with a sharper version of it: the intention
        # STORE three dozen lines above was already built for every agent, while the thing that
        # writes it was a grant. A modality nobody may write is not a modality.
        self.keeper = Keeper(self)
        #  ITS PATIENCE, handed down: the keeper is progression's and reads no belief, so the
        #  container reads the pick through the desire modality and assigns it. An agent that
        #  states none — `world/sensing`'s stakeless one, every minimal fixture — is handed
        #  nothing, and the keeper raises `NoPatience` only if something asks it to commit.
        try:
            self.keeper.beliefs = self.desires.read(KEEPING_PICKS)
        except BeliefError:
            pass

        #  THE LEDGER OF DEBTS IS NOT HERE, and the reason is the one sensing already
        #  demonstrates: a package may write a graph the kernel declares. The kernel owns the
        #  obligation MODALITY — the class, the graph, its classification, and the branches
        #  that rank a debt against a want — and market owns incurring one, which is the only
        #  half that was ever a market's. See knowledge/domain/obligation.md.
        self.modules += [self.deliberator, self.keeper]
        #  WHAT THE KERNEL OFFERS, keyed by the CLASS of each — the thing a package imports
        #  anyway to type its own code, so there is no parallel naming system to keep in step.
        #  Named in `KERNEL_SERVICES` rather than listed inline, so a gate can know what the
        #  kernel offers WITHOUT building an agent (an-injected-service-is-reached-by-term).
        for value in (self.beliefs, self.desires, self.intentions,
                      self.keeper, self.deliberator, self.metrics):
            self.offering(type(value), value)


    # --- how one capability reaches another, without knowing its name ---

    def service(self, key):
        """Whatever offers this service — the kernel's own, or a package's. One or none.

        The fan-in door, beside `ask` (everyone's opinion) and `provider` (whoever implements an
        ability). Resolved on first ask and remembered: a package's offer is a function in its
        manifest, and it runs once, here, rather than when the manifest was read
        (an-injected-service-is-reached-by-term).
        """
        if key in self._services:
            return self._services[key]
        offer = loader.offers().get(key)
        if offer is None:
            raise KeyError(
                f"nothing offers {attribute_for(key)} — no package this agent composed "
                "provides it, and the kernel does not. A service nobody offers is a "
                "dependency nobody declared."
            )
        package, build = offer
        if package not in self._packages:
            raise KeyError(
                f"{attribute_for(key)} is offered by {package.import_name}, which is not "
                "among the packages this agent loads — nothing it composed requires it. A "
                "required annotation is what pulls a provider in (#455); a soft one takes "
                "only what is already there."
            )
        service, close = opened(build, self)
        self._services[key] = service
        if close is not None:
            self._closing.append(close)
        return service

    def offers(self, key) -> bool:
        """Is this service on the table FOR THIS AGENT? Asked without building it — which is
        what lets an optional dependency be resolved to None rather than to a handle that
        would raise. Scoped to the packages this agent loads (#455): a provider outside them
        is a package no need of this agent pulls, so a soft annotation naming it stays None
        and the package stays unloaded."""
        if key in self._services:
            return True
        offer = loader.offers().get(key)
        return offer is not None and offer[0] in self._packages

    def offering(self, key, value) -> None:
        """The kernel putting one of its own on the table, under its class."""
        self._services[key] = value

    def provider(self, family: str):
        """Whichever of MY modules provides a capability of this family, or None.

        The family is a T-Box term, so the caller asks for "something that perceives" rather
        than for `SubscribingModule`. That is the whole point: no capability package imports
        another's Python, so any of them can be removed without breaking the rest. None is a
        normal answer — an agent that composed neither is simply an agent that cannot.
        """
        return next(iter(self.providers(family)), None)

    def providers(self, family: str) -> list:
        """ALL of my modules that provide a capability of this family, in module order.

        `provider` above is the ordinary door and answers with one, because most families have
        one member per agent and a caller wanting "whoever can pour" means whoever that is.
        The plural exists for the family where an agent legitimately holds TWO — sensing splits
        by who holds the clock, and `world/loner`'s gardener subscribes to a probe AND listens
        to a float switch, so it composes both modules and each owns its own sensors.

        Asking the singular there is a silent wrong answer rather than an error: `provider`
        returns whichever comes first, and a nudge sent to the listening module is a nudge sent
        to a method whose whole body is a docstring saying listening cannot. The gardener
        adopted a look at its probe, called that method, and nothing left the process — the
        intention then stood until patience outwaited it, for ever, with every module behaving
        exactly as written. Which is why this is a list and not a better tie-break: there is no
        right one to pick, and the question was never singular.
        """
        members = {r["capability"] for r in bindings(self.beliefs.query(_family_q(family)))}
        return [m for m in self.modules if m.CAPABILITY in members]

    def pursuing(self, now: datetime | None = None) -> list[Desire]:
        """Everything this agent is pursuing, hottest first, whoever sourced it.

        Assembled from the modules that hold wants rather than asked of one, because since the
        ledger became its own capability no single module can see them all: desire contributes
        stakes, owing contributes debts, and an agent may compose either without the other. The
        ranking is what makes the two comparable — urgency is unit-free on both sides, so a
        litre owed and a pot drying finally rank against each other.
        """
        #  ONE WANT, ONE NODE. Two modules may hold the same want — the gardener composes two
        #  sensing modules and each reads every region the agent holds — and a want is its
        #  node, so the second sighting is the same want and not a second one.
        seen: dict[str, Desire] = {}
        for wants in self.ask(DESIRES, now):
            for desire in wants:
                seen.setdefault(desire.uri, desire)
        #  THE WANTS NO MODULE SPEAKS FOR (#468): a world may ratify a desire DIRECTLY — the
        #  asserted block — and wanting is the kernel's, so the kernel is who lifts such a
        #  want into pursuit rather than a capability minted to re-say it. Scoped to the
        #  avoided-pattern wants, whose judging is one select on the store's own engine;
        #  binary, because between entered and held there is nothing to be nearer to. A
        #  pattern that fails to run reads as unmet — the loud direction.
        for row in bindings(self.desires.query_union(_AVOIDED_Q, {"me": self.me.uri})):
            if row["want"] in seen:
                continue
            #  THE DESIRE OWNS THE TERM AND THE PACKAGE OWNS THE MEASURE: a world may write
            #  the pattern inline beside its asserted want, or point at a node the domain
            #  package declares. The first rides in the modality; the second is public
            #  knowledge and is asked of the belief base — one text, either road.
            select = row.get("select")
            if not select:
                found = bindings(self.beliefs.query(_SELECT_Q, {"node": row["avoided"]}))
                select = found[0]["select"] if found else None
            try:
                if select:
                    text = bind(select, this=self.me.uri, state=STATE_GRAPH)
                    entered = bool(bindings(self.beliefs.query(text)))
                elif bindings(self.beliefs.query(_IS_SHAPE_Q, {"node": row["avoided"]})):
                    #  THE AVOIDED STATE AS A SHAPE (#499): compiled to its conformance
                    #  select — rows where the state has been entered — and run over the
                    #  same view a compiled positive want is.
                    text = self._unmet_select(row["want"], row["avoided"], entered=True)
                    entered = bool(bindings(self.beliefs.query_over(
                        text, *self.beliefs.public_graphs(),
                        *self.beliefs.recorded_graphs())))
                else:
                    log.error("%s: %s points at an avoided state that is neither a select "
                              "nor a shape", self.id, row["want"])
                    continue
            except Exception as exc:
                log.error("%s: avoided-state pattern failed to run: %s", self.id, exc)
                entered = True
            seen[row["want"]] = Desire(uri=row["want"],
                                       urgency=1.0 if entered else 0.0,
                                       state="unmet" if entered else "met")
        #  A SHAPE WANT NO MODULE SPEAKS FOR (#497): the courier's and hanoi's, authored
        #  positive and universal, pointing at a shape the package declares. Compiled once
        #  per want into the select whose rows are its violations — computed, never stored —
        #  and run on the store's own engine over the same view the judge would be handed.
        #  Binary, like the pattern wants above: met is no row.
        for row in bindings(self.desires.query_union(_SHAPED_Q, {"me": self.me.uri})):
            if row["want"] in seen:
                continue
            try:
                text = self._unmet_select(row["want"], row["shape"])
                violated = bool(bindings(self.beliefs.query_over(
                    text, *self.beliefs.public_graphs(), *self.beliefs.recorded_graphs())))
            except Exception as exc:
                log.error("%s: could not judge %s by its shape: %s", self.id, row["want"], exc)
                violated = True
            seen[row["want"]] = Desire(uri=row["want"],
                                       urgency=1.0 if violated else 0.0,
                                       state="unmet" if violated else "met")
        return sorted(seen.values(), key=lambda g: -g.urgency)

    def _unmet_select(self, want: str, shape: str, entered: bool = False) -> str:
        """The compiled select of an asserted want's shape, once per process: an asserted
        want never changes while the agent runs, and compiling is a carve and a string. Read
        from public knowledge, where a package's shape lives — and the asserted block is
        public too. `entered` picks the conformance select, for a shape under `unmetWhen`."""
        from orexis_agent_deliberation.conformance import graph_from
        from orexis_agent_progression.violation import entered_select, unmet_select

        cache = self.__dict__.setdefault("_compiled_wants", {})
        if (want, entered) not in cache:
            public = graph_from(self.beliefs, *self.beliefs.public_graphs())
            compile = entered_select if entered else unmet_select
            cache[(want, entered)] = compile(public.cbd(URIRef(shape)), URIRef(shape))
        return cache[(want, entered)]

    def ask(self, point: str, *args, **kwargs) -> list:
        """Every module's answer to one question, in module order, None left out.

        THE CHOIR, generically, and BY TERM: `point` is an `assembly:Extension` some ontology declares —
        the kernel's for the BDI-shaped questions, a package's for its own — and a module
        answers it by the method it decorated with that term (a-hook-is-a-term). What the
        kernel owns is the mechanism: whoever answers is asked, an error in one voice is
        logged and does not silence the rest, and the caller merges the answers by its own
        rule. Sensing asks its verdicts on a reading this way and says what they mean.
        """
        self._declared(point)
        answers = []
        for module in self.modules:
            fn = module.answer(point)
            if fn is None:
                continue
            try:
                answer = fn(*args, **kwargs)
            except Exception as exc:
                log.error("%s: %s could not answer %s: %s", self.id, module.name, _short(point), exc)
                continue
            if answer is not None:
                answers.append(answer)
        return answers

    @staticmethod
    def _declared(point: str) -> None:
        """An extension point is a TERM some ontology declares (a-hook-is-a-term); a string nobody
        declared would be answered by silence, which is the failure this refuses."""
        if point not in loader.extensions():
            raise ValueError(f"{point} is not an extension point any ontology declares — a question nobody "
                             "owns would be answered by nobody, silently")

    def tell(self, point: str, *args, **kwargs) -> None:
        """Every module that listens for one event is told, and a failure in one is logged."""
        self._declared(point)
        for module in self.modules:
            fn = module.answer(point)
            if fn is None:
                continue
            try:
                fn(*args, **kwargs)
            except Exception as exc:
                log.error("%s: %s failed on %s: %s", self.id, module.name, _short(point), exc)

    def desire_urgency(self, desire, query, state: str,
                       value: float | None = None) -> float | None:
        """How urgent one desire is in one world — the sharpest answer any module gives.

        The choir again, and deliberately the same resolution as `urgency` above: the kernel
        iterates its modules and never names a family, a capability that owns the question
        answers, and None means nobody here knows how to measure this want — which every
        ranking caller turns into 1.0, because not knowing how bad is maximal. The kernel
        holds no measure of its own (a-desire-states-its-own-measure): this method is the
        whole of its involvement.
        """
        answers = self.ask(DESIRE_URGENCY, desire, query, state, value)
        return max(answers) if answers else None

    # --- the shared connection; modules route by the topics they asked for ---

    #  `publish`, `_on_connect`, `_on_disconnect` and `_on_message` WERE HERE — the kernel's
    #  mailbox: a client, a dispatch loop handing every message to every module, a session to
    #  watch. None of it is BDI. How an agent reaches its society is a capability the fact of
    #  a bus grants (`packages/orexis-transport-mqtt/module.py`), reached through the choir:
    #  `Module.publish` tells `send`, the transport asks `subscriptions` and `handle`
    #  (the-kernel-has-no-mailbox).

    def run(self) -> None:
        # Who I am on the bus. The broker refuses anonymous connections, and the ACL it holds
        # grants this principal exactly the topics the world wires me to — so a missing
        # credential is a deployment fault worth naming here rather than a bare "Not
        # authorized" from the broker. Set at run() and not at construction: it is needed to
        # connect, and nothing that merely builds an agent should require it.
        signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM})

        #  The link opens with whatever credential and door its transport reads off the
        #  environment — the kernel hands over its three callbacks and nothing else.
        # After the mask, so the timer thread inherits it and this thread stays the one that
        # wakes on a signal. Its thread is a daemon, so it cannot hold the process open either.
        # Upkeep runs for everyone, on its own clock, and is NOT a capability: nothing about
        # reclaiming your own disk could be done differently. Started here rather than at
        # construction so that building an agent starts no threads and a test can hold one
        # without it acting. Reporting used to start here too and is a module now — mandatory,
        # granted to every agent, and started below with the rest.
        self.reviser.start()
        self.upkeep.start()
        # The watchdog last, after the connect above has had its chance: its disconnection
        # clock started at construction, so an agent that never gets its CONNACK is already
        # being timed. When it resigns it sends SIGTERM to this process — blocked, pending,
        # and received by the sigwait below exactly as `podman stop`'s would be, so a
        # resignation IS a clean shutdown and the container's restart policy is the recovery.
        for module in self.modules:
            module.start()
        log.info("%s up — world v%s, running %s", self.id, self.world.version,
                 ", ".join(m.name for m in self.modules) or "nothing")

        try:
            signal.sigwait({signal.SIGINT, signal.SIGTERM})
        except KeyboardInterrupt:
            pass
        finally:
            log.info("%s shutting down", self.id)
            for module in self.modules:
                module.stop()
            self.upkeep.stop()
            self.reviser.stop()
            #  Services last and in reverse, so one that leans on another is closed before the
            #  thing it leans on. A failure in one is logged and does not strand the others: a
            #  shutdown that stops half way is worse than a noisy one.
            for close in reversed(self._closing):
                try:
                    close()
                except Exception as exc:
                    log.error("%s: a service would not close: %s", self.id, exc)
            #  THE THREE THREADS, last (#452): the scheduler stops keeping time, then the loop
            #  finishes the item in hand and exits. The reviser above was the third. An agent
            #  is a process, so the process's clock and loop are this agent's to stop.
            scheduler().stop()
            loop().stop()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s"
    )
    agent_id = config.env("OREXIS_AGENT_ID")
    if not agent_id:
        raise SystemExit(
            "OREXIS_AGENT_ID is required — an agent process is one agent, and its id is the "
            "only thing it is told. Try: OREXIS_AGENT_ID=fern orexis-agent"
        )
    Agent(agent_id).run()


if __name__ == "__main__":
    main()


def _short(iri: str) -> str:
    return iri.rsplit("#", 1)[-1]
