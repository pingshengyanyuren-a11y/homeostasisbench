# GitHub Launch Playbook

## Recommended Public Positioning

Lead with the benchmark, not with the metaphor.

- Recommended public name: `HomeostasisBench`
- Repository description: `A benchmark for stress-testing multi-agent systems under overload, failures, false signals, and resource collapse.`
- Elevator pitch: `Not another agent framework. A benchmark and reference controller for multi-agent resilience.`

This framing is stronger because it invites comparison. People are more likely to star, fork, or run a benchmark against their own controller than to adopt another speculative framework.

## Recommended GitHub Metadata

Suggested topics:

- `multi-agent-systems`
- `ai-agents`
- `swarm-intelligence`
- `benchmark`
- `fault-tolerance`
- `resilience`
- `distributed-systems`
- `simulation`
- `python`
- `agent-evals`

Suggested social preview:

- one clean 1280x640 image
- left side: title + one-line benchmark pitch
- right side: a compact baseline-vs-bio plot
- avoid tiny tables and dense text

## Launch Sequence

### Phase 1: Make the repo star-worthy

- keep the root README short, visual, and benchmark-first
- pin the best result figure near the top
- keep install and run commands copy-pasteable
- ship a first release tag with the generated result artifacts

### Phase 2: Make the repo discussable

- post one short demo clip or GIF where baseline collapses and bio remains stable
- publish one simple challenge: `bring your own controller and beat the stress-suite`
- open Discussions or Issues with starter prompts for alternative baselines

### Phase 3: Make the repo reusable

- add a controller adapter interface
- add at least two strong non-biological baselines
- make result cards standardized so external submissions are easy to compare

## What Will Actually Drive Attention

- a sharp one-sentence hook
- a visible win on stress scenarios
- credible ablation instead of pure storytelling
- easy reproducibility
- a clear invitation for others to plug in their own controller

## What Will Kill Momentum

- over-selling the biological metaphor without stronger baselines
- letting the README read like a lab notebook
- hiding the exact commands needed to reproduce the figures
- shipping only a toy baseline and calling the problem solved

## Immediate Next Wins

- add one stronger queueing/scheduling baseline
- add a benchmark result card in the release notes
- create a social preview image from the existing plots
- prepare a `v0.1.0` release with a short discussion thread
