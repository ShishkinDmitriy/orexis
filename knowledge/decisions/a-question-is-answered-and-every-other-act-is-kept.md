---
type: Decision
title: A question is answered and every other act is kept, FIPA names the acts, and no engine runs a protocol
status: superseded-in-part
superseded-by: a-person-states-what-the-chat-allows-in-the-worlds-words
timestamp: 2026-11-01T12:00:00Z
description: >-
  The sovereign's question of 2026-11-01, whether the society should have FIPA's communicative acts and
  interaction protocols, since a sayable and the askable proposed beside it are FIPA's PROPOSE and
  QUERY-REF and an auction could be held between people. Decided - one distinction is mechanised, the
  one a reader branches on. A question, an askable, is answered from the asked agent's store by a select
  that agent's own package ships and writes nothing; every other act is a statement, kept, and believed
  by the extraction. The askable is speech's, speech:Askable, beside the sayable; sensing and execution
  ship one each in its words.
  The acts are named as FIPA names them, in an alignment kept in this record, and the market's round is
  read against Contract Net. Refused - a performative term on every statement kind, which nothing would
  read; FIPA's semantics, which reason about the sender's mind; an envelope beside the content; and a
  protocol engine, which would dictate the next act.
---

> **Superseded in part** by [the-model-queries-what-its-chat-may-read](/decisions/the-model-queries-what-its-chat-may-read.md).
> What does not hold any more is the ONE CALL: the model converses, calling as many askables as a question
> needs, and loads and queries what its chat may read, and nothing says none fits.
>
> **And superseded in part again** by [a-person-states-what-the-chat-allows-in-the-worlds-words](/decisions/a-person-states-what-the-chat-allows-in-the-worlds-words.md).
> The askable and the sayable are retired: a question is the model's query, and a statement is triples in
> the words the chat allows, held to their domain and range. What stands is the distinction itself - a
> question writes nothing and every other act is kept - and the FIPA alignment, with the refusals of a
> performative term, FIPA's semantics, an envelope and a protocol engine.

# The question

A person's words now meet two kinds of tool at the model: a sayable, the
shape of a statement they may make, which the model fills and the agent keeps; and the askable, a
question they may ask, which the agent answers from its store and which replaces the account's dumped
sections ([an-agent-translates-for-itself](/decisions/an-agent-translates-for-itself.md)). The sovereign
saw FIPA in that: an act per message — `inform`, `query-ref`, `propose`, `request` — and protocols built
of acts, Contract Net and the auctions, in which someone offers to us or asks us. Should the society
have them? And since an auction is statements, could it be held between people as well as agents?

Three records were waiting for this. The 0.1.0 survey said that the day the conversation grows message
types, FIPA's performatives are checked before any word is invented
([there-is-no-bdi-ontology](/decisions/0.1.0/there-is-no-bdi-ontology.md)); the settlement record left
FIPA's interaction protocols "the most promising thing left unread"
([settlement-speaks-rea](/decisions/settlement-speaks-rea.md)); and #394, closed once a peer's word had
a shape, left open "whether the shape is FIPA-flavoured or the performatives this society actually
uses. The vocabulary should follow the acts we have."

# What is true of the acts we have

What a message does to its receiver is decided **by the receiver's rules over its content**, never by a
tag. A peer's document is a statement, `speech:StatementGraph`, which no reader of the mind is handed; a
domain's [extraction](/domain/speech/extraction.md) makes the belief, and the receiver's desires read
that belief ([a-peers-word-is-testimony-and-a-rule-makes-it-a-belief](/decisions/a-peers-word-is-testimony-and-a-rule-makes-it-a-belief.md)).
A call is a want arriving to the host not because it is marked a request but because the host's desire
— no unanswered calls — is unmet by the belief the call's extraction made. No reader in the mind
branches on what kind of act a message was, and none should: FIPA's semantics define an act by its
feasibility precondition and rational effect over the sender's beliefs and intentions, and this society
holds beliefs about other agents first-order — what they said, never what they believe
([model-it-only-if-a-plan-would-branch-on-it](/decisions/model-it-only-if-a-plan-would-branch-on-it.md)).

One reader does branch, at one place: the person's edge. Words that fill a sayable are kept as a
statement; words that call an askable are answered and leave nothing behind. That is the one difference
between acts that changes what the code does.

# What was decided

**A question is answered, and every other act is kept.** The askable is the one act mechanised apart:
`speech:Askable`, a `sh:NodeShape` whose `sh:property` entries are what the asker may fill — declared as
a sayable's fields are, so translation offers both as tools the same way — whose `speech:reads` names
the kinds of graph it is handed and whose `speech:select` is the text the asked agent runs, each filled
field bound into it by `store.bind`. The asker never writes the text and never sees it; it picks a
question the asked agent's own package declares, as it picks a sayable. Nothing is written. Every other
act — telling, proposing, requesting, refusing — is a statement, kept whole and believed by the
extraction, whichever it is.

**The askable is speech's, beside the sayable.** Both are an act a person may make, and speech owns
what is said. Sensing ships one, the latest reading of each sensor, and execution one, the intentions
standing, each in an `askables.ttl` beside its ontology — the one document of either that speaks
speech's words, since a question about what sensing observes can only be asked in sensing's. An agent
that speaks with nobody holds no speech vocabulary and passes the document over, as every agent passes
over a package's requirements; translation finds the rest in the store by kind. The kernel was weighed
first, since sensing and execution may otherwise not speak speech's words, and refused by the sovereign:
the askable is an act of speech, and a kernel word for it would be a second home for speech's
vocabulary. The `account.rq` files, found by their file
name, go, and so does the account as a word: `/account` becomes `/status`, the rows of every askable that
takes no field, answered for nothing.

**One model call offers every act a person may make.** A person's words go to the model once, with
every sayable and every askable the world and the agent's packages declare as tools; the model calls
the one the words make, or says none fits. The two calls #1043 made — sayables first, the account after
— become one. In a group the rule of [an-agent-translates-for-itself](/decisions/an-agent-translates-for-itself.md)
stands: unaddressed, an agent is offered its askables alone and answers only where one speaks to the
question.

**The acts are named as FIPA names them, here.** The alignment is prose, as the settlement record's is,
because no reader branches on any of it:

| act we have | said by → to | FIPA |
|---|---|---|
| a call for a round, `market:Call` | bidder → host | `request` |
| a round opened, `market:Round` | host → bidders | `cfp` |
| a bid, `market:Bid` | bidder → host | `propose` |
| a claim issued at a clearing, `market:Claim` | host → winner | `accept-proposal` |
| a round said again once cleared | host → bidders | `inform` |
| a claim presented, `market:Presentation` | holder → host | `request` |
| a claim said again once discharged | host → holder | `inform` (FIPA's inform-done) |
| a commitment, a reveal, `draw:` | each → peer | `inform` |
| a question, `coordination:Question` | asker → peer | `query-ref` |
| an answer, `coordination:Answer` | peer → asker | `inform` |
| a viewing offered, a viewing requested, an application refused | realtor ↔ seeker | `propose`, `request`, `reject-proposal` |
| an askable | person → agent | `query-ref` |

Seven of FIPA's twenty-two acts, and the ones not in it — `agree`, `refuse`, `failure`, `cancel`,
`subscribe` — are acts nobody here performs yet. A new statement kind is named against this table
before a word is invented for it.

**The market's round is Contract Net, sealed and multi-award.** Read against FIPA's protocols: a
bidder's call precedes it; the host's open round is the call for proposals; each bid is a proposal, said
to the host alone; the clearing accepts every winning bid pay-as-bid, a claim each; and a loser learns
it lost from the cleared round, said to every bidder, rather than from a `reject-proposal` of its own.
It is none of FIPA's auctions — English and Dutch are open and iterated, and a round's bids are sealed. The presentation and the serving after it are a request protocol of their own.

**A protocol is what the actions allow, and no engine runs one.** Contract Net's order — no proposal
before the call, no acceptance of a proposal not made — is what the market's preconditions already
hold: a bid needs an open round, a clearing a round whose window has closed, a serving a claim
presented. Each side plans its part for its own desires, and the conversation is what their plans
make ([auction](/domain/market/auction.md)). A protocol is a name for that pattern, written where the
domain's actions are.

**An auction may be held between people, because a statement does not say who typed it.** A host
cannot tell a bid a peer's step said from one a person filled in a chat: both arrive as the same
statement, `speech:saidBy` naming who said it. A market that ships its bid as a sayable takes people's
bids beside its agents'. Nothing in the mechanism changes; what a world must decide is in the seams.

# What was refused

- **A performative term on every statement kind** — `market:BidGraph` beneath a `speech:Propose`, a
  `speech:act` on each shape. It is the obvious reading of FIPA and the one 0.1.0 anticipated, and it was
  refused because nothing would read it: what a bid does is what the host's extraction and desires make
  of it, and a term nobody reads is annotation. The trigger for revisiting is the first reader that
  branches on an act rather than its content — a generic handling of `failure` across domains, say.
- **FIPA's semantics.** An act defined by what the sender believes and intends asks the receiver to
  model the sender's mind, which this society refuses everywhere: a peer is believed to have said, never
  to believe.
- **An envelope beside the content** — FIPA ACL's `conversation-id`, `in-reply-to`, `reply-by`. What an
  act is about is in its content: an answer names its question, a bid its round, a presentation its
  claim; and when it must arrive by is the period the world gives it — a round's window, a question's
  patience. A second place to say either would be a second place to be wrong.
- **A protocol engine** — a conversation state machine that knows Contract Net and steps the agents
  through it. It would dictate the next act from outside the agents' desires, which is the move
  [control-the-derivative-not-the-value](/decisions/control-the-derivative-not-the-value.md) refuses: a
  host serves a claim because it desires no presented claim unserved, not because a protocol is at that
  step.

# What it amends

- [an-agent-translates-for-itself](/decisions/an-agent-translates-for-itself.md): the account is
  askables, of speech's kind and found in the store; the model is offered sayables and askables in
  one call.
- [settlement-speaks-rea](/decisions/settlement-speaks-rea.md): FIPA's interaction protocols are read,
  and the round is Contract Net, sealed and multi-award.
- [the-agent-stack-is-a-second-axis](/decisions/the-agent-stack-is-a-second-axis.md): the speech-act path
  has its vocabulary, the statement for every act and the askable for a question.

# Seams left open

- **People in a round.** The market's windows are seconds, and a person answers in minutes, so a world
  holding a round with people states windows a person can meet; who a person is is still the carrier's
  word and unsigned, a weaker thing when the bid is money; and a draw's commit and reveal is no ceremony
  a person performs by hand. Each is a world's to decide, and none needs a mechanism.
- **A peer's question over an askable.** An agent could ask a peer's askables over the bus as a person
  asks in a chat. Nothing does: coordination's question is answered by coordination's own text, over the
  constraint the two share, and an askable is an account for a person, not a peer.
- **The sayable stays speech's.** Only domains declare sayables, and a domain may speak speech's words,
  so the sayable was not lowered beside the askable; the day a package beneath speech ships one, it is.

# What it emits

The askable, built on #1043: `speech:Askable`, `speech:reads` and `speech:select` in speech's ontology; sensing's
and execution's askables in documents of their own in place of the two `account.rq`; the account module
asking the store; one model call offering both kinds; `/status`; and the translation pages and AGENTS
lines that say so.
