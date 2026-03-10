from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


METRIC_COLUMNS = [
    "task_completion_rate",
    "avg_latency",
    "error_rate",
    "recovery_time_after_failure",
    "resource_efficiency",
    "stability_score",
]


def _weighted_latency(group: pd.DataFrame) -> float:
    completed = group["completed_tasks"].sum()
    if completed <= 0:
        return float("nan")
    weighted_latency = (group["avg_latency_step"].fillna(0.0) * group["completed_tasks"]).sum()
    return float(weighted_latency / completed)


def _recovery_time(group: pd.DataFrame) -> float:
    failure_steps = group.loc[group["disturbance_type"] == "agent_failure", "step"].tolist()
    if not failure_steps:
        return 0.0

    indexed = group.set_index("step")
    max_step = int(group["step"].max())
    windows: list[float] = []

    for failure_step in failure_steps:
        pre_window = group.loc[group["step"] < failure_step].tail(5)
        baseline_backlog = float(pre_window["pending_tasks"].mean()) if not pre_window.empty else float(
            indexed.loc[failure_step, "pending_tasks"]
        )
        baseline_error = float(pre_window["error_rate_step"].mean()) if not pre_window.empty else 0.0
        baseline_active = float(pre_window["active_workers"].mean()) if not pre_window.empty else float(
            indexed.loc[failure_step, "active_workers"]
        )
        target_backlog = max(2.0, baseline_backlog * 1.05)
        target_error = min(0.12, baseline_error + 0.03)
        target_active = max(1.0, baseline_active * 0.9)

        recovered = False
        for step in range(failure_step + 1, min(max_step, failure_step + 10) + 1):
            row = indexed.loc[step]
            if (
                row["pending_tasks"] <= target_backlog
                and row["error_rate_step"] <= target_error
                and row["active_workers"] >= target_active
            ):
                windows.append(float(step - failure_step))
                recovered = True
                break
        if not recovered:
            windows.append(10.0)

    return float(np.mean(windows))


def _stability_score(group: pd.DataFrame) -> float:
    completion_ratio = group["completed_tasks"] / group["arrived_tasks"].clip(lower=1)
    latency = group["avg_latency_step"].fillna(group["avg_latency_step"].mean()).fillna(0.0)
    components = (
        (group["pending_tasks"].std(ddof=0) / 10.0)
        + (group["error_rate_step"].std(ddof=0) * 3.5)
        + (completion_ratio.std(ddof=0) * 4.0)
        + (latency.std(ddof=0) / 5.0)
    )
    return float(100.0 / (1.0 + components))


def summarize_runs(step_df: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    group_keys = ["scenario", "system", "seed"] if "seed" in step_df.columns else ["scenario", "system"]

    for keys, group in step_df.groupby(group_keys, sort=False):
        if isinstance(keys, tuple):
            if len(group_keys) == 3:
                scenario, system, seed = keys
            else:
                scenario, system = keys
                seed = -1
        else:
            scenario = str(keys)
            system = str(group["system"].iloc[0])
            seed = -1

        total_arrived = int(group["arrived_tasks"].sum())
        total_completed = int(group["completed_tasks"].sum())
        total_errors = int(group["failed_tasks"].sum())
        total_resource = float(group["resource_used_step"].sum())

        rows.append(
            {
                "scenario": scenario,
                "system": system,
                "seed": seed,
                "task_completion_rate": total_completed / max(total_arrived, 1),
                "avg_latency": _weighted_latency(group),
                "error_rate": total_errors / max(total_completed + total_errors, 1),
                "recovery_time_after_failure": _recovery_time(group),
                "resource_efficiency": total_completed / max(total_resource, 1e-6),
                "stability_score": _stability_score(group),
                "total_arrived": total_arrived,
                "total_completed": total_completed,
                "total_errors": total_errors,
                "total_resource_used": total_resource,
                "mean_reflex_actions": float(group["reflex_actions"].mean()),
                "mean_immune_actions": float(group["immune_actions"].mean()),
                "mean_reserve_activations": float(group["reserve_activations"].mean()),
                "mean_metabolic_rests": float(group["metabolic_rests"].mean()),
                "mean_demoted_false_signals": float(group["demoted_false_signals"].mean()),
                "mean_nervous_fast_lane_share": float(group["nervous_fast_lane_share"].mean()),
                "mean_endocrine_throttle_ratio": float(group["endocrine_throttle_ratio"].mean()),
                "mean_immune_replacement_ratio": float(group["immune_replacement_ratio"].mean()),
                "mean_metabolic_recovery_gain": float(group["metabolic_recovery_gain"].mean()),
            }
        )

    return pd.DataFrame(rows)


def aggregate_summary(summary_df: pd.DataFrame) -> pd.DataFrame:
    aggregation_map = {column: ["mean", "std"] for column in METRIC_COLUMNS}
    aggregation_map.update(
        {
            "mean_reflex_actions": ["mean"],
            "mean_immune_actions": ["mean"],
            "mean_reserve_activations": ["mean"],
            "mean_metabolic_rests": ["mean"],
            "mean_demoted_false_signals": ["mean"],
            "mean_nervous_fast_lane_share": ["mean"],
            "mean_endocrine_throttle_ratio": ["mean"],
            "mean_immune_replacement_ratio": ["mean"],
            "mean_metabolic_recovery_gain": ["mean"],
        }
    )
    aggregated = summary_df.groupby(["scenario", "system"], as_index=False).agg(aggregation_map)
    flattened_columns = ["scenario", "system"]
    for column, stat in aggregated.columns.tolist()[2:]:
        flattened_columns.append(f"{column}_{stat}")
    aggregated.columns = flattened_columns
    return aggregated


def compare_systems(
    aggregate_df: pd.DataFrame,
    scenario_names: Iterable[str],
    baseline_system: str = "baseline",
    bio_system: str = "bio",
) -> pd.DataFrame:
    subset = aggregate_df.loc[aggregate_df["scenario"].isin(list(scenario_names))].copy()
    pivoted_frames = []
    for metric in METRIC_COLUMNS:
        pivot = subset.pivot(index="scenario", columns="system", values=f"{metric}_mean").reset_index()
        pivot["metric"] = metric
        pivot["delta_bio_minus_baseline"] = pivot[bio_system] - pivot[baseline_system]
        pivoted_frames.append(pivot)
    return pd.concat(pivoted_frames, ignore_index=True)
