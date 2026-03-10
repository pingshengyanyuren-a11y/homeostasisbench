# bio_swarm_pilot

This directory contains the working benchmark implementation behind the repository-level `HomeostasisBench` pitch.

## Core Files

- `simulation.py`: scenario generation, experiment runner, CLI entrypoint
- `baseline_swarm.py`: manager / worker / reviewer baseline
- `bio_swarm.py`: bio-inspired controller with nervous, endocrine, immune, and metabolic logic
- `metrics.py`: aggregation and comparison metrics
- `plots.py`: summary, stability, and layer-ablation figures

## Run

From the repository root:

```powershell
python -m bio_swarm_pilot --steps 140 --replicates 5 --seed 42
```

From this directory directly:

```powershell
python .\simulation.py
```

## Test

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -v
```

## Outputs

Generated artifacts are written to `bio_swarm_pilot/outputs/` by default:

- step metrics CSVs
- scenario summaries
- aggregate summary
- comparison figures
- experiment report
- hypothesis markdown when the acceptance gates pass

For the public-facing overview, use the repository root [README.md](../README.md).
