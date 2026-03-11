# Protocol Reference

## Design Intent

This skill is for systems where the primary abstraction is organism control, not social hierarchy.

The minimum useful physiological mapping is:

- endocrine: global slow variables
- metabolic: resource and fatigue accounting
- nervous: reflex and fast-lane routing
- immune: anomaly containment

## Minimal State Model

Global state:

- `stress_level`
- `risk_level`
- `resource_budget`
- `energy_budget`
- `exploration_level`
- `toxicity_level`

Cell state:

- `cell_id`
- `organ`
- `energy`
- `load`
- `reliability`
- `health`
- `quarantined`
- `recent_failures`

Task signal:

- `task_id`
- `objective`
- `urgency`
- `noise`
- `complexity`

## Protocol Questions

For any proposed architecture, answer these in order:

1. What are the organism-wide state variables?
2. What causes endocrine contraction or relaxation?
3. What qualifies for nervous fast-lane routing?
4. What metabolic events reduce agent capability?
5. What immune evidence causes quarantine?
6. What artifacts prove the system stayed coherent?
