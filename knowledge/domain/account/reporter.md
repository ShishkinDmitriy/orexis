---
type: Role
title: Reporter
term: http://example.org/orexis/account#Reporter
description: >-
  An agent that gives an account of itself - the role whose part is the account package's, declared
  in the self graph beside the agent's other roles, and the topic it accounts on stated in the
  society. The bus is loaded for it, since the account goes out retained on a topic.
---

# What it is

A **reporter** is an agent that gives an [account](/domain/account/account.md) of itself, declared
in its self graph as any [role](/domain/kernel/role.md) is:

```turtle
:terrace_agent a orexis:Self ;
    orexis:plays [ a sensing:Observer ; … ] , [ a speech:Speaker ] , [ a account:Reporter ] .
```

and stated in the society to account on a topic:

```turtle
:terrace_agent account:accountsOn :terrace_account .
:terrace_account a mqtt4ssn:Topic .
```

The boot loads the account package for the role and nothing else, and the MQTT transport where
the agent accounts on a topic, as it loads it for a speaker that listens on one. An agent in a chat
is a reporter where a person is to ask after it; one that merely says statements need not be.

# What it costs

A pass in which nothing a part says of itself changed publishes nothing. The terrace's agent, which
observes and wants nothing, gives a new account at each reading that moves a value, a few lines.
