---
name: physio-swarm-protocol
description: Use when designing, critiquing, or implementing a multi-agent system as a physiological organism instead of a human bureaucracy. Applies to swarm protocols with endocrine global state, nervous fast lanes, immune quarantine, metabolic budget control, reflex routing, and cell-like agent state. Also use when translating a role-based agent system into a biologically inspired control architecture.
---

# Physio Swarm Protocol

Treat the system as an organism, not as a company org chart.

## Core Rule

Do not begin by assigning social roles like CEO, PM, worker, or reviewer.
Begin with organism-level control layers:

- `endocrine`: slow global state and prompt/budget modulation
- `metabolic`: energy, fatigue, context budget, and recovery
- `nervous`: fast-lane routing and local reflex
- `immune`: anomaly detection, quarantine, and replacement

## Workflow

1. Define the organism-wide state variables before defining any agent roles.
2. Define the cell state schema for each agent.
3. Define what signals move globally versus locally.
4. Route urgent low-noise work through nervous fast lanes.
5. Let endocrine state modulate budgets, exploration, and caution system-wide.
6. Use immune logic to quarantine unreliable cells and recover them outside the main path.
7. Record execution as structured artifacts, not only conversational transcripts.

## Use The Bundled Runtime

When a user asks for a runnable prototype, start from:

- `physio_swarm/protocol.py`
- `physio_swarm/kernel.py`
- `examples/physio_swarm_demo.py`

Read these references as needed:

- `references/protocol.md` for the conceptual protocol
- `references/runtime.md` for the Python runtime mapping

## Output Standard

Prefer outputs that expose:

- homeostasis state
- cell state
- signal route
- immune events
- metabolic contractions
- execution artifacts

Avoid outputs that only rename classic role-based agents with biological vocabulary.
