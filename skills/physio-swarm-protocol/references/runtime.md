# Runtime Reference

## Python Runtime Mapping

The bundled runtime lives in:

- `physio_swarm/protocol.py`
- `physio_swarm/kernel.py`
- `examples/physio_swarm_demo.py`

## What Each File Does

`physio_swarm/protocol.py`

- defines `HomeostasisState`
- defines `TaskSignal`
- defines `CellState`
- defines `ExecutionArtifact`

`physio_swarm/kernel.py`

- defines `EndocrineController`
- defines `MetabolicController`
- defines `NervousRouter`
- defines `ImmuneMonitor`
- defines `PhysioSwarmKernel`

`examples/physio_swarm_demo.py`

- builds a tiny organism with reflex and cortex cells
- runs a small task stream
- returns structured artifacts
- demonstrates fast lane, budget contraction, and quarantine

## Expected Usage

Use this runtime as a starter kernel, not as a finished production system.

When extending it:

- keep global state explicit
- keep cell state explicit
- keep routing decisions inspectable
- keep immune actions visible in artifacts
