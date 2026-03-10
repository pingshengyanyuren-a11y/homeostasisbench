# Contributing

Thanks for considering a contribution to HomeostasisBench.

## Good Contribution Targets

The project is most valuable when contributions improve comparison quality rather than only adding more story. High-signal contributions include:

- stronger non-biological baselines
- new disturbance regimes
- controller adapters with clear benchmark deltas
- better metrics, plots, and reproducibility tooling
- documentation that makes external reproduction easier

## Development Workflow

1. Install the project in editable mode.
2. Make your change.
3. Run the test suite.
4. Re-run the benchmark if behavior changed.
5. Include the resulting evidence in your pull request.

```powershell
pip install -e .
python -m unittest discover -s .\bio_swarm_pilot\tests -v
python -m bio_swarm_pilot --steps 140 --replicates 5 --seed 42 --output-dir bio_swarm_pilot/outputs
```

## Contribution Rules

- Keep the benchmark reproducible. New randomness must remain seed-controlled.
- Do not replace evidence with intuition. If a controller is better, show it in the exported metrics.
- If you add a new controller, compare it against at least one existing baseline.
- Keep dependencies light unless the new dependency clearly expands the benchmark surface.
- Prefer small, reviewable pull requests over large rewrites.

## Pull Request Notes

Include:

- what changed
- why it matters
- whether metrics changed
- which tests and commands you ran
- which output files are relevant

If your change affects benchmark behavior, attach or summarize:

- `aggregate_summary.csv`
- `experiment_report.md`
- any new or updated figure
