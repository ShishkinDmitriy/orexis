"""The account: what an agent says of itself for a person, in the dictionary's words — what it observes,
what it is doing — published retained on its own account topic every pass it changes, and read by the
translator standing in a chat with it (knowledge/domain/account/account.md,
an-agent-gives-an-account-of-itself-and-the-model-only-reads-it).

TELEMETRY, NEVER A BELIEF. No plan branches on what the agent said of itself, so it is written nowhere in
the store; it is prose by templates, each part answering its own section (`account()`, duck-typed as
`link`, `start` and `stop` are), and this package imports no package's words, as history and metrics
import none. The role is `account:Reporter`, declared in the self graph, and the topic the agent
`account:accountsOn` is named by onboarding's rule, `agents/<id>/account`.
"""
