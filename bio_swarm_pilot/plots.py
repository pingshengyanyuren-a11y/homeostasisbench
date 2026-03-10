from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from .metrics import METRIC_COLUMNS
except ImportError:
    from metrics import METRIC_COLUMNS


def plot_summary_bars(aggregate_df: pd.DataFrame, output_path: Path) -> None:
    scenarios = list(dict.fromkeys(aggregate_df["scenario"].tolist()))
    systems = list(dict.fromkeys(aggregate_df["system"].tolist()))

    figure, axes = plt.subplots(2, 3, figsize=(16, 9))
    bar_width = 0.35
    x = np.arange(len(scenarios))

    for axis, metric in zip(axes.flat, METRIC_COLUMNS):
        for index, system in enumerate(systems):
            values = []
            for scenario in scenarios:
                row = aggregate_df.loc[
                    (aggregate_df["scenario"] == scenario) & (aggregate_df["system"] == system)
                ].iloc[0]
                values.append(row[f"{metric}_mean"])
            axis.bar(x + ((index - 0.5) * bar_width), values, bar_width, label=system)

        axis.set_title(metric.replace("_", " "))
        axis.set_xticks(x)
        axis.set_xticklabels(scenarios, rotation=15)
        axis.grid(axis="y", alpha=0.25)

    axes[0, 0].legend(frameon=False)
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def plot_stability_timeseries(step_df: pd.DataFrame, output_path: Path) -> None:
    scenarios = list(dict.fromkeys(step_df["scenario"].tolist()))
    figure, axes = plt.subplots(len(scenarios), 1, figsize=(14, 4 * len(scenarios)), sharex=True)
    if len(scenarios) == 1:
        axes = [axes]

    grouped = (
        step_df.groupby(["scenario", "system", "step"], as_index=False)[["pending_tasks", "error_rate_step"]]
        .mean()
        .sort_values(["scenario", "system", "step"])
    )

    for axis, scenario in zip(axes, scenarios):
        subset = grouped.loc[grouped["scenario"] == scenario]
        for system in subset["system"].unique():
            system_rows = subset.loc[subset["system"] == system]
            axis.plot(system_rows["step"], system_rows["pending_tasks"], label=f"{system} backlog")
            axis.plot(
                system_rows["step"],
                system_rows["error_rate_step"] * 20.0,
                linestyle="--",
                label=f"{system} error x20",
            )

        axis.set_title(f"{scenario} backlog / error trajectory")
        axis.set_ylabel("backlog")
        axis.grid(alpha=0.25)
        axis.legend(frameon=False, ncol=2)

    axes[-1].set_xlabel("step")
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def plot_layer_ablation(aggregate_df: pd.DataFrame, output_path: Path) -> None:
    metrics = ["stability_score", "task_completion_rate", "error_rate", "recovery_time_after_failure"]
    scenarios = list(dict.fromkeys(aggregate_df["scenario"].tolist()))
    variants = list(dict.fromkeys(aggregate_df["system"].tolist()))

    figure, axes = plt.subplots(2, 2, figsize=(15, 10))
    x = np.arange(len(variants))
    width = 0.35

    for axis, metric in zip(axes.flat, metrics):
        for index, scenario in enumerate(scenarios):
            values = []
            for variant in variants:
                row = aggregate_df.loc[
                    (aggregate_df["scenario"] == scenario) & (aggregate_df["system"] == variant)
                ].iloc[0]
                values.append(row[f"{metric}_mean"])
            axis.bar(x + ((index - 0.5) * width), values, width, label=scenario)

        axis.set_title(metric.replace("_", " "))
        axis.set_xticks(x)
        axis.set_xticklabels(variants, rotation=20)
        axis.grid(axis="y", alpha=0.25)

    axes[0, 0].legend(frameon=False)
    figure.tight_layout()
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)
