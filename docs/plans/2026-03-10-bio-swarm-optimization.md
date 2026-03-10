# Bio Swarm Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the current `bio_swarm_pilot` so the bio-inspired system keeps its latency/error advantages while fixing the weakest point: the endocrine controller currently suppresses throughput too aggressively and does not consistently improve failure recovery.

**Architecture:** Keep the existing four-layer structure, but separate optimization into three concrete loops: better endocrine control policy, stronger immune/recovery behavior under failure storms, and tighter instrumentation/regression tests so layer-level claims remain grounded in generated metrics. The work should preserve the existing simulation API and output artifact layout.

**Tech Stack:** Python 3, `unittest`, `numpy`, `pandas`, `matplotlib`

---

### Task 1: Lock In The Current Failure With Regression Tests

**Files:**
- Create: `bio_swarm_pilot/tests/test_optimization_regression.py`
- Modify: `bio_swarm_pilot/tests/test_sanity.py`
- Test: `bio_swarm_pilot/tests/test_optimization_regression.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
import tempfile
import unittest

from simulation import run_all


class OptimizationRegressionTest(unittest.TestCase):
    def test_bio_beats_baseline_on_overload_latency_and_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = run_all(output_dir=Path(tmp_dir), steps=90, replicates=3, base_seed=42)
            summary = result["aggregate_summary"]
            overload = summary.loc[summary["scenario"] == "overload"].set_index("system")
            self.assertLess(
                overload.loc["bio", "avg_latency_mean"],
                overload.loc["baseline", "avg_latency_mean"],
            )
            self.assertLess(
                overload.loc["bio", "error_rate_mean"],
                overload.loc["baseline", "error_rate_mean"],
            )

    def test_full_bio_should_outperform_no_endocrine_on_stability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            result = run_all(output_dir=Path(tmp_dir), steps=90, replicates=3, base_seed=42)
            ablation = result["ablation_summary"]
            overload = ablation.loc[ablation["scenario"] == "overload"].set_index("system")
            self.assertGreater(
                overload.loc["full_bio", "stability_score_mean"],
                overload.loc["no_endocrine", "stability_score_mean"],
            )
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -p "test_optimization_regression.py" -v
```

Expected: first assertion passes, second assertion fails because the current endocrine layer is weaker than the ablated version.

**Step 3: Write minimal implementation scaffolding**

```python
# no implementation change yet; this task exists to freeze the current gap
```

**Step 4: Run test to verify it still fails for the right reason**

Run:

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -p "test_optimization_regression.py" -v
```

Expected: still FAIL, and the failure message should point specifically at `full_bio` underperforming `no_endocrine`.

**Step 5: Commit**

```bash
git add bio_swarm_pilot/tests/test_optimization_regression.py bio_swarm_pilot/tests/test_sanity.py
git commit -m "test: add optimization regression coverage for bio swarm"
```

### Task 2: Rework Endocrine Control Into A Soft Adaptive Governor

**Files:**
- Modify: `bio_swarm_pilot/bio_swarm.py`
- Test: `bio_swarm_pilot/tests/test_optimization_regression.py`
- Test: `bio_swarm_pilot/tests/test_endocrine_control.py`

**Step 1: Write the failing test**

```python
import unittest
import numpy as np

from bio_swarm import BioInspiredSwarm
from simulation import SCENARIOS


class EndocrineControlTest(unittest.TestCase):
    def test_endocrine_does_not_cut_parallelism_when_errors_are_low(self) -> None:
        swarm = BioInspiredSwarm(
            rng=np.random.default_rng(1),
            scenario_name="overload",
            config=SCENARIOS["overload"],
        )
        swarm.queue = [{"type": "normal_task", "arrival_step": 0, "attempts": 0}] * 12
        swarm.recent_error_rates.extend([0.01] * 6)
        swarm.recent_completions.extend([5.0] * 6)
        swarm.recent_backlog.extend([10.0] * 6)
        swarm._update_endocrine(
            {
                "capacity_multiplier": 1.0,
                "extra_error": 0.0,
                "disturbance_pressure": 0.1,
                "resource_drop": 0.0,
                "failure_count": 0,
            }
        )
        self.assertGreaterEqual(swarm.system_state["resource_budget"], 0.85)
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -p "test_endocrine_control.py" -v
```

Expected: FAIL because the current controller shrinks `resource_budget` too early.

**Step 3: Write minimal implementation**

Implement in `bio_swarm.py`:

```python
# Replace the current scalar update with a softer policy:
# 1. Separate backlog pressure from error pressure
# 2. Only hard-throttle when both stress and observed error are high
# 3. Add hysteresis so the system relaxes faster after transient overload
# 4. Exempt urgent fast-lane work from the concurrency clamp
```

Concrete code direction:

- Add `backlog_pressure`, `error_pressure`, `failure_pressure` as separate terms.
- Compute `resource_budget` from a piecewise rule instead of a single linear expression.
- In `_assign_tasks`, use a floor like `max(primary_workers * 0.6, 2)` before any throttle applies.
- Keep `urgent_task` and validated fast-lane tasks outside the endocrine throttle cap.

**Step 4: Run tests to verify they pass**

Run:

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -p "test_endocrine_control.py" -v
python -m unittest discover -s .\bio_swarm_pilot\tests -p "test_optimization_regression.py" -v
```

Expected:
- `test_endocrine_does_not_cut_parallelism_when_errors_are_low` PASS
- The `full_bio_should_outperform_no_endocrine_on_stability` regression moves from FAIL to PASS

**Step 5: Commit**

```bash
git add bio_swarm_pilot/bio_swarm.py bio_swarm_pilot/tests/test_endocrine_control.py bio_swarm_pilot/tests/test_optimization_regression.py
git commit -m "feat: retune endocrine controller for adaptive concurrency"
```

### Task 3: Improve Failure-Storm Recovery With Faster Immune Recycling

**Files:**
- Modify: `bio_swarm_pilot/bio_swarm.py`
- Test: `bio_swarm_pilot/tests/test_failure_recovery.py`
- Test: `bio_swarm_pilot/tests/test_optimization_regression.py`

**Step 1: Write the failing test**

```python
import unittest
import numpy as np

from bio_swarm import BioInspiredSwarm
from simulation import SCENARIOS


class FailureRecoveryTest(unittest.TestCase):
    def test_isolated_worker_can_return_after_short_recovery(self) -> None:
        swarm = BioInspiredSwarm(
            rng=np.random.default_rng(2),
            scenario_name="failure_storm",
            config=SCENARIOS["failure_storm"],
        )
        worker = swarm.agents["worker_0"]
        worker["active"] = False
        worker["recovering"] = True
        worker["isolated_until"] = 2
        worker["health"] = 0.78
        worker["reliability"] = 0.72
        worker["energy"] = 0.62

        swarm.recovery_pool.add("worker_0")
        swarm._restore_recovering_agents(step=3)

        self.assertTrue(swarm.agents["worker_0"]["active"])
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -p "test_failure_recovery.py" -v
```

Expected: FAIL if the current thresholds or reserve-release behavior delay return too long.

**Step 3: Write minimal implementation**

Implement in `bio_swarm.py`:

```python
# Improve recovery by:
# 1. Distinguishing quarantine from rehabilitation
# 2. Returning agents earlier when energy and reliability have recovered
# 3. Keeping reserve agents warm during clustered failures instead of toggling them off too aggressively
```

Concrete code direction:

- Split `isolated_until` and `recovering` semantics so a worker can become schedulable immediately after quarantine if metrics are above threshold.
- Lower reserve deactivation sensitivity under `failure_storm`.
- Add a short “cooldown preference” in `_assign_tasks` so newly recovered agents receive normal tasks first.

**Step 4: Run tests and scenario verification**

Run:

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -p "test_failure_recovery.py" -v
python .\bio_swarm_pilot\simulation.py
```

Expected:
- `test_isolated_worker_can_return_after_short_recovery` PASS
- In `outputs/aggregate_summary.csv`, `failure_storm` bio `recovery_time_after_failure_mean` should be lower than baseline and lower than the current starting point (~`8.10`)

**Step 5: Commit**

```bash
git add bio_swarm_pilot/bio_swarm.py bio_swarm_pilot/tests/test_failure_recovery.py bio_swarm_pilot/outputs
git commit -m "feat: speed up immune recovery under clustered failures"
```

### Task 4: Add Layer-Specific Instrumentation And Acceptance Gates

**Files:**
- Modify: `bio_swarm_pilot/simulation.py`
- Modify: `bio_swarm_pilot/metrics.py`
- Modify: `bio_swarm_pilot/README.md`
- Test: `bio_swarm_pilot/tests/test_report_metrics.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
import tempfile
import unittest

from simulation import run_all


class ReportMetricsTest(unittest.TestCase):
    def test_report_contains_endocrine_penalty_signal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_all(output_dir=Path(tmp_dir), steps=60, replicates=2, base_seed=42)
            report = (Path(tmp_dir) / "experiment_report.md").read_text(encoding="utf-8")
            self.assertIn("endocrine", report.lower())
```

**Step 2: Run test to verify it fails**

Run:

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -p "test_report_metrics.py" -v
```

Expected: FAIL if the report omits the new control-specific instrumentation or acceptance language.

**Step 3: Write minimal implementation**

Implement in `metrics.py` and `simulation.py`:

```python
# Add explicit derived metrics for:
# - endocrine_throttle_ratio
# - immune_replacement_ratio
# - metabolic_recovery_gain
# - nervous_fast_lane_share
```

Concrete code direction:

- Record per-step throttle intensity in `bio_swarm.py` and aggregate it in `metrics.py`.
- Add acceptance summary in the markdown report:
  - endocrine must not underperform its ablation on overload/failure_storm
  - bio must keep latency and error advantages
  - failure recovery must beat baseline in `failure_storm`
- Update `README.md` to define the new diagnostics.

**Step 4: Run verification**

Run:

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -p "test_report_metrics.py" -v
python -m unittest discover -s .\bio_swarm_pilot\tests -v
python .\bio_swarm_pilot\simulation.py
```

Expected:
- All tests PASS
- Report and CSVs include the new instrumentation
- Acceptance gates are explicit in the report, not inferred manually

**Step 5: Commit**

```bash
git add bio_swarm_pilot/simulation.py bio_swarm_pilot/metrics.py bio_swarm_pilot/README.md bio_swarm_pilot/tests/test_report_metrics.py bio_swarm_pilot/outputs
git commit -m "feat: add layer diagnostics and acceptance gates"
```

### Task 5: Final Verification And Closeout

**Files:**
- Verify: `bio_swarm_pilot/outputs/aggregate_summary.csv`
- Verify: `bio_swarm_pilot/outputs/layer_ablation_summary.csv`
- Verify: `bio_swarm_pilot/outputs/experiment_report.md`
- Verify: `bio_swarm_pilot/bio-inspired-agent-swarm-prototype-hypothesis.md`

**Step 1: Re-run the full experiment**

Run:

```powershell
python .\bio_swarm_pilot\simulation.py
```

Expected: exit code `0` and all output artifacts regenerated.

**Step 2: Verify the target outcomes**

Run:

```powershell
Import-Csv .\bio_swarm_pilot\outputs\aggregate_summary.csv | Format-Table -Auto
Import-Csv .\bio_swarm_pilot\outputs\layer_ablation_summary.csv | Format-Table -Auto
```

Expected acceptance:
- `bio` latency and error remain better than `baseline` in all three scenarios
- `bio` completion stays above `baseline` in `normal` and `failure_storm`, and at least does not regress materially in `overload`
- `bio` recovery in `failure_storm` becomes better than `baseline`
- `full_bio` no longer loses to `no_endocrine` on the stress scenarios

**Step 3: Verify the narrative matches the data**

Run:

```powershell
Get-Content .\bio_swarm_pilot\outputs\experiment_report.md
Get-Content .\bio_swarm_pilot\bio-inspired-agent-swarm-prototype-hypothesis.md
```

Expected: report explicitly acknowledges any remaining weak layer; hypothesis markdown stays aligned with the latest ablation results.

**Step 4: Run the entire test suite**

Run:

```powershell
python -m unittest discover -s .\bio_swarm_pilot\tests -v
```

Expected: PASS with no failures.

**Step 5: Commit**

```bash
git add bio_swarm_pilot
git commit -m "feat: optimize bio swarm control and recovery loops"
```
