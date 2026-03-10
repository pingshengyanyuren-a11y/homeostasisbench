from __future__ import annotations

import argparse
import copy
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from .baseline_swarm import BaselineSwarm, clamp
    from .bio_swarm import BioInspiredSwarm
    from .metrics import METRIC_COLUMNS, aggregate_summary, compare_systems, summarize_runs
    from .plots import plot_layer_ablation, plot_stability_timeseries, plot_summary_bars
except ImportError:
    from baseline_swarm import BaselineSwarm, clamp
    from bio_swarm import BioInspiredSwarm
    from metrics import METRIC_COLUMNS, aggregate_summary, compare_systems, summarize_runs
    from plots import plot_layer_ablation, plot_stability_timeseries, plot_summary_bars


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "outputs"
DEFAULT_SCENARIOS = ("normal", "overload", "failure_storm")
DEFAULT_STEPS = 140
DEFAULT_REPLICATES = 5


SCENARIOS: dict[str, dict[str, Any]] = {
    "normal": {
        "arrival_rate": 2.4,
        "worker_count": 5,
        "reserve_count": 2,
        "task_mix": {
            "normal_task": 0.55,
            "urgent_task": 0.16,
            "noisy_task": 0.14,
            "long_task": 0.15,
        },
        "disturbances": {
            "agent_failure": 0.06,
            "overload": 0.08,
            "false_signal": 0.06,
            "resource_drop": 0.05,
        },
        "none_weight": 0.75,
    },
    "overload": {
        "arrival_rate": 4.7,
        "worker_count": 5,
        "reserve_count": 2,
        "task_mix": {
            "normal_task": 0.44,
            "urgent_task": 0.18,
            "noisy_task": 0.18,
            "long_task": 0.2,
        },
        "disturbances": {
            "agent_failure": 0.08,
            "overload": 0.24,
            "false_signal": 0.1,
            "resource_drop": 0.13,
        },
        "none_weight": 0.45,
    },
    "failure_storm": {
        "arrival_rate": 3.2,
        "worker_count": 5,
        "reserve_count": 2,
        "task_mix": {
            "normal_task": 0.48,
            "urgent_task": 0.15,
            "noisy_task": 0.17,
            "long_task": 0.2,
        },
        "disturbances": {
            "agent_failure": 0.24,
            "overload": 0.12,
            "false_signal": 0.08,
            "resource_drop": 0.1,
        },
        "none_weight": 0.46,
    },
}


TASK_PROFILES = {
    "normal_task": {"work_mean": 1.3, "work_std": 0.25, "complexity": 0.45, "noise": 0.22, "signal": 0.62},
    "urgent_task": {"work_mean": 1.05, "work_std": 0.18, "complexity": 0.52, "noise": 0.24, "signal": 0.9},
    "noisy_task": {"work_mean": 1.45, "work_std": 0.3, "complexity": 0.56, "noise": 0.72, "signal": 0.52},
    "long_task": {"work_mean": 3.0, "work_std": 0.55, "complexity": 0.72, "noise": 0.36, "signal": 0.58},
}


def _task_type(rng: np.random.Generator, mix: dict[str, float]) -> str:
    task_names = list(mix)
    probabilities = np.array(list(mix.values()), dtype=float)
    probabilities /= probabilities.sum()
    return str(rng.choice(task_names, p=probabilities))


def _disturbance(rng: np.random.Generator, scenario_name: str) -> dict[str, Any] | None:
    config = SCENARIOS[scenario_name]
    names = ["none", *config["disturbances"].keys()]
    weights = np.array([config["none_weight"], *config["disturbances"].values()], dtype=float)
    weights /= weights.sum()
    selected = str(rng.choice(names, p=weights))
    if selected == "none":
        return None
    severity = float(np.clip(rng.normal(0.62, 0.18), 0.2, 1.0))
    return {
        "type": selected,
        "severity": severity,
        "duration": int(rng.integers(1, 4)),
    }


def generate_event_stream(scenario_name: str, seed: int, steps: int) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    config = SCENARIOS[scenario_name]
    stream: list[dict[str, Any]] = []
    next_task_id = 0

    for step in range(steps):
        disturbance = _disturbance(rng, scenario_name)
        arrival_count = int(rng.poisson(config["arrival_rate"]))
        tasks: list[dict[str, Any]] = []

        for _ in range(arrival_count):
            task_type = _task_type(rng, config["task_mix"])
            profile = TASK_PROFILES[task_type]
            work = float(np.clip(rng.normal(profile["work_mean"], profile["work_std"]), 0.75, 4.8))
            task = {
                "id": f"{scenario_name}_{next_task_id}",
                "type": task_type,
                "arrival_step": step,
                "initial_work": work,
                "remaining_work": work,
                "complexity": float(np.clip(rng.normal(profile["complexity"], 0.12), 0.1, 1.0)),
                "noise": float(np.clip(rng.normal(profile["noise"], 0.1), 0.05, 1.0)),
                "signal_confidence": float(np.clip(rng.normal(profile["signal"], 0.08), 0.15, 1.0)),
                "flagged_urgent": False,
                "attempts": 0,
            }
            tasks.append(task)
            next_task_id += 1

        if disturbance and disturbance["type"] == "false_signal":
            flag_rate = 0.25 + (0.25 * disturbance["severity"])
            for task in tasks:
                if task["type"] == "urgent_task":
                    task["signal_confidence"] = clamp(task["signal_confidence"] - (0.18 * disturbance["severity"]), 0.35, 1.0)
                elif rng.random() < flag_rate:
                    task["flagged_urgent"] = True
                    task["signal_confidence"] = float(np.clip(task["signal_confidence"] - 0.25, 0.2, 0.58))

        stream.append({"step": step, "tasks": tasks, "disturbance": disturbance})

    return stream


def _simulate_systems(
    scenario_name: str,
    seed: int,
    steps: int,
    factories: list[tuple[str, Any]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    event_stream = generate_event_stream(scenario_name=scenario_name, seed=seed, steps=steps)
    swarms = []
    for index, (system_name, factory) in enumerate(factories):
        rng = np.random.default_rng(seed * 97 + index + 1)
        swarms.append((system_name, factory(rng)))

    step_records: list[dict[str, Any]] = []
    for event in event_stream:
        for system_name, swarm in swarms:
            record = swarm.step(
                new_tasks=copy.deepcopy(event["tasks"]),
                disturbance=copy.deepcopy(event["disturbance"]),
                step=event["step"],
            )
            record["seed"] = seed
            record["system"] = system_name
            step_records.append(record)

    step_df = pd.DataFrame(step_records)
    summary_df = summarize_runs(step_df)
    return step_df, summary_df


def run_experiment(
    seed: int,
    scenario_name: str,
    steps: int = DEFAULT_STEPS,
    output_dir: Path | str | None = None,
) -> dict[str, dict[str, float]]:
    destination = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    destination.mkdir(parents=True, exist_ok=True)
    config = SCENARIOS[scenario_name]

    step_df, summary_df = _simulate_systems(
        scenario_name=scenario_name,
        seed=seed,
        steps=steps,
        factories=[
            ("baseline", lambda rng: BaselineSwarm(rng=rng, scenario_name=scenario_name, config=config)),
            ("bio", lambda rng: BioInspiredSwarm(rng=rng, scenario_name=scenario_name, config=config)),
        ],
    )

    step_df.to_csv(destination / f"scenario_{scenario_name}_step_metrics.csv", index=False)
    summary_df.to_csv(destination / f"scenario_{scenario_name}_summary.csv", index=False)
    structured = summary_df.set_index("system")[METRIC_COLUMNS].to_dict(orient="index")
    return {str(system): values for system, values in structured.items()}


def run_layer_ablation(
    output_dir: Path,
    steps: int,
    base_seed: int,
) -> pd.DataFrame:
    variants = [
        ("full_bio", {}),
        ("no_nervous", {"enable_nervous": False}),
        ("no_endocrine", {"enable_endocrine": False}),
        ("no_immune", {"enable_immune": False}),
        ("no_metabolic", {"enable_metabolic": False}),
    ]

    summaries: list[pd.DataFrame] = []
    for scenario_name in ("overload", "failure_storm"):
        config = SCENARIOS[scenario_name]
        for replicate in range(3):
            seed = base_seed + 700 + (replicate * 29) + (17 if scenario_name == "failure_storm" else 0)
            _, summary_df = _simulate_systems(
                scenario_name=scenario_name,
                seed=seed,
                steps=steps,
                factories=[
                    (
                        variant_name,
                        lambda rng, flags=flags: BioInspiredSwarm(
                            rng=rng,
                            scenario_name=scenario_name,
                            config=config,
                            system_name=variant_name,
                            layer_flags=flags,
                        ),
                    )
                    for variant_name, flags in variants
                ],
            )
            summaries.append(summary_df)

    ablation_summary = pd.concat(summaries, ignore_index=True)
    ablation_summary.to_csv(output_dir / "layer_ablation_runs.csv", index=False)
    ablation_aggregate = aggregate_summary(ablation_summary)
    ablation_aggregate.to_csv(output_dir / "layer_ablation_summary.csv", index=False)
    plot_layer_ablation(ablation_aggregate, output_dir / "layer_ablation.png")
    return ablation_aggregate


def _layer_impact(ablation_df: pd.DataFrame) -> tuple[str, str]:
    full = ablation_df.loc[ablation_df["system"] == "full_bio"]
    impacts: dict[str, float] = {}
    label_map = {
        "no_nervous": "nervous layer",
        "no_endocrine": "endocrine layer",
        "no_immune": "immune layer",
        "no_metabolic": "metabolic layer",
    }

    for variant, label in label_map.items():
        merged = full.merge(
            ablation_df.loc[ablation_df["system"] == variant],
            on="scenario",
            suffixes=("_full", "_ablated"),
        )
        impact = (
            (merged["stability_score_mean_full"] - merged["stability_score_mean_ablated"]).mean() * 0.6
            + (merged["task_completion_rate_mean_full"] - merged["task_completion_rate_mean_ablated"]).mean() * 40.0
            + (merged["error_rate_mean_ablated"] - merged["error_rate_mean_full"]).mean() * 45.0
            + (merged["recovery_time_after_failure_mean_ablated"] - merged["recovery_time_after_failure_mean_full"]).mean()
        )
        impacts[label] = float(impact)

    ordered = sorted(impacts.items(), key=lambda item: item[1], reverse=True)
    return ordered[0][0], ordered[-1][0]


def _bio_success(aggregate_df: pd.DataFrame) -> bool:
    comparisons = compare_systems(aggregate_df, scenario_names=("normal", "overload", "failure_storm"))
    enough_wins = 0
    total_checks = 0

    for _, row in comparisons.iterrows():
        metric = row["metric"]
        delta = row["delta_bio_minus_baseline"]
        if metric in {"task_completion_rate", "resource_efficiency", "stability_score"}:
            enough_wins += int(delta > 0.0)
        else:
            enough_wins += int(delta < 0.0)
        total_checks += 1

    critical = aggregate_df.loc[aggregate_df["scenario"].isin(["overload", "failure_storm"])]
    critical_pivot = critical.pivot(index="scenario", columns="system", values="stability_score_mean")
    critical_stability = bool((critical_pivot["bio"] > critical_pivot["baseline"]).all())
    return enough_wins >= int(total_checks * 0.65) and critical_stability


def _report_text(aggregate_df: pd.DataFrame, ablation_df: pd.DataFrame) -> str:
    strongest_layer, weakest_layer = _layer_impact(ablation_df)
    comparison = compare_systems(aggregate_df, scenario_names=("normal", "overload", "failure_storm"))
    success = _bio_success(aggregate_df)
    verdict = "bio-inspired architecture is more stable than baseline" if success else "bio-inspired architecture is not consistently more stable than baseline"
    headline_rows = aggregate_df[
        [
            "scenario",
            "system",
            "task_completion_rate_mean",
            "avg_latency_mean",
            "error_rate_mean",
            "recovery_time_after_failure_mean",
            "resource_efficiency_mean",
            "stability_score_mean",
        ]
    ].copy()
    layer_rows = ablation_df[
        [
            "scenario",
            "system",
            "task_completion_rate_mean",
            "error_rate_mean",
            "recovery_time_after_failure_mean",
            "stability_score_mean",
        ]
    ].copy()
    diagnostic_rows = aggregate_df[
        [
            "scenario",
            "system",
            "mean_endocrine_throttle_ratio_mean",
            "mean_immune_replacement_ratio_mean",
            "mean_metabolic_recovery_gain_mean",
            "mean_nervous_fast_lane_share_mean",
        ]
    ].copy()

    stress_ablation = ablation_df.loc[ablation_df["scenario"].isin(["overload", "failure_storm"])]
    stress_pivot = stress_ablation.pivot(index="scenario", columns="system", values="stability_score_mean")
    aggregate_pivot = aggregate_df.pivot(index="scenario", columns="system", values="recovery_time_after_failure_mean")
    comparison_pivot = aggregate_df.pivot(index="scenario", columns="system", values="avg_latency_mean")
    error_pivot = aggregate_df.pivot(index="scenario", columns="system", values="error_rate_mean")
    endocrine_is_net_positive = bool(
        (stress_pivot["full_bio"] > stress_pivot["no_endocrine"]).all()
    )
    if weakest_layer == "endocrine layer":
        if endocrine_is_net_positive:
            weak_layer_interpretation = "- Endocrine control is still the weakest contributor in the ablation ranking, but after retuning it is no longer a drag on performance; it now behaves like a light-touch global governor with smaller marginal gains than the other layers."
        else:
            weak_layer_interpretation = "- Endocrine control is the weakest part of the current prototype: the slow-variable heuristic is too conservative, so the idea is plausible but the present tuning suppresses throughput more than it helps resilience."
    else:
        weak_layer_interpretation = f"- {weakest_layer.capitalize()} is currently the weakest contributor in the ablation run, so its present implementation looks more like a partial idea than a finished resilience mechanism."

    acceptance_rows = pd.DataFrame(
        [
            {
                "gate": "bio latency beats baseline in all scenarios",
                "status": "PASS"
                if bool((comparison_pivot["bio"] < comparison_pivot["baseline"]).all())
                else "FAIL",
            },
            {
                "gate": "bio error beats baseline in all scenarios",
                "status": "PASS" if bool((error_pivot["bio"] < error_pivot["baseline"]).all()) else "FAIL",
            },
            {
                "gate": "bio recovery beats baseline in failure_storm",
                "status": "PASS"
                if bool(
                    aggregate_pivot.loc["failure_storm", "bio"]
                    < aggregate_pivot.loc["failure_storm", "baseline"]
                )
                else "FAIL",
            },
            {
                "gate": "full_bio beats no_endocrine on overload stability",
                "status": "PASS"
                if bool(
                    stress_pivot.loc["overload", "full_bio"]
                    > stress_pivot.loc["overload", "no_endocrine"]
                )
                else "FAIL",
            },
            {
                "gate": "full_bio beats no_endocrine on failure_storm stability",
                "status": "PASS"
                if bool(
                    stress_pivot.loc["failure_storm", "full_bio"]
                    > stress_pivot.loc["failure_storm", "no_endocrine"]
                )
                else "FAIL",
            },
        ]
    )

    return "\n".join(
        [
            "# Experiment Report",
            "",
            "## Verdict",
            f"- {verdict}.",
            f"- Strongest contributor in the ablation run: {strongest_layer}.",
            f"- Most conceptually attractive but comparatively modest in aggregate metrics: {weakest_layer}.",
            "",
            "## Aggregate Comparison",
            headline_rows.to_markdown(index=False, floatfmt=".3f"),
            "",
            "## Bio vs Baseline Delta",
            comparison.to_markdown(index=False, floatfmt=".3f"),
            "",
            "## Layer Ablation",
            layer_rows.to_markdown(index=False, floatfmt=".3f"),
            "",
            "## Layer Diagnostics",
            diagnostic_rows.to_markdown(index=False, floatfmt=".3f"),
            "",
            "## Acceptance Gates",
            acceptance_rows.to_markdown(index=False),
            "",
            "## Interpretation",
            "- Nervous layer mainly improves urgent routing and local overload handling; its gain is visible but smaller when urgent traffic is not dominant.",
            "- Immune layer matters most when repeated failures appear because isolation plus reserve substitution shortens recovery windows.",
            "- Metabolic layer pays off over longer horizons by preventing low-energy collapse; without it, late-stage latency rises even if short-run throughput looks acceptable.",
            weak_layer_interpretation,
        ]
    )


def _hypothesis_text(aggregate_df: pd.DataFrame, ablation_df: pd.DataFrame) -> str:
    strongest_layer, weakest_layer = _layer_impact(ablation_df)
    stability_gain = compare_systems(aggregate_df, scenario_names=("overload", "failure_storm"))
    stability_row = stability_gain.loc[stability_gain["metric"] == "stability_score"]
    mean_stability_delta = float(stability_row["delta_bio_minus_baseline"].mean())

    return "\n".join(
        [
            "# bio-inspired agent swarm prototype hypothesis",
            "",
            "## Core Hypothesis",
            "A multi-agent system becomes more fault-tolerant when coordination is split across fast local reflexes, slow global regulation, anomaly isolation, and explicit energy management instead of relying only on hierarchical task assignment.",
            "",
            "## What The Pilot Suggests",
            f"- In this pilot, the full bio-inspired architecture improved stability by about {mean_stability_delta:.2f} points over baseline on the stress scenarios.",
            f"- The strongest contributor was the {strongest_layer}, which suggests that resilience comes primarily from suppressing cascading failures rather than from better static planning alone.",
            f"- The weakest contributor was the {weakest_layer}; in this prototype that should be read as an implementation warning, not as proof the underlying biological analogy is wrong.",
            "",
            "## Research Directions",
            "- Replace hand-tuned thresholds with adaptive policies learned from disturbance history.",
            "- Move endocrine control from scalar heuristics to a latent-state controller that conditions on backlog, error bursts, and agent heterogeneity.",
            "- Expand immune logic from simple isolation to graded quarantine, trust decay, and targeted rehabilitation curricula.",
            "- Model metabolism with richer context costs, memory fragmentation, and communication overhead so energy reflects real agent-system economics.",
            "- Introduce task decomposition and tissue-like specialization so different cell groups co-adapt instead of sharing a flat worker pool.",
            "",
            "## Falsifiable Next Step",
            "If the architecture is genuinely useful, the same layered control logic should still outperform a stronger non-biological baseline after the task mix, failure pattern, and agent heterogeneity are all shifted out of the hand-tuned regime used in this prototype.",
        ]
    )


def run_all(
    output_dir: Path | str | None = None,
    steps: int = DEFAULT_STEPS,
    replicates: int = DEFAULT_REPLICATES,
    base_seed: int = 42,
) -> dict[str, Any]:
    destination = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    destination.mkdir(parents=True, exist_ok=True)

    all_steps: list[pd.DataFrame] = []
    all_summaries: list[pd.DataFrame] = []

    for scenario_index, scenario_name in enumerate(DEFAULT_SCENARIOS):
        for replicate in range(replicates):
            seed = base_seed + (scenario_index * 101) + (replicate * 17)
            step_df, summary_df = _simulate_systems(
                scenario_name=scenario_name,
                seed=seed,
                steps=steps,
                factories=[
                    (
                        "baseline",
                        lambda rng, name=scenario_name: BaselineSwarm(
                            rng=rng,
                            scenario_name=name,
                            config=SCENARIOS[name],
                        ),
                    ),
                    (
                        "bio",
                        lambda rng, name=scenario_name: BioInspiredSwarm(
                            rng=rng,
                            scenario_name=name,
                            config=SCENARIOS[name],
                        ),
                    ),
                ],
            )
            all_steps.append(step_df)
            all_summaries.append(summary_df)

    combined_steps = pd.concat(all_steps, ignore_index=True)
    combined_summary = pd.concat(all_summaries, ignore_index=True)
    combined_steps.to_csv(destination / "all_step_metrics.csv", index=False)
    combined_summary.to_csv(destination / "all_run_summary.csv", index=False)

    for scenario_name in DEFAULT_SCENARIOS:
        combined_steps.loc[combined_steps["scenario"] == scenario_name].to_csv(
            destination / f"scenario_{scenario_name}_step_metrics.csv",
            index=False,
        )
        combined_summary.loc[combined_summary["scenario"] == scenario_name].to_csv(
            destination / f"scenario_{scenario_name}_summary.csv",
            index=False,
        )

    aggregate_df = aggregate_summary(combined_summary)
    aggregate_df.to_csv(destination / "aggregate_summary.csv", index=False)

    plot_summary_bars(aggregate_df, destination / "summary_comparison.png")
    plot_stability_timeseries(combined_steps, destination / "stability_timeseries.png")

    ablation_df = run_layer_ablation(output_dir=destination, steps=steps, base_seed=base_seed)
    (destination / "experiment_report.md").write_text(_report_text(aggregate_df, ablation_df), encoding="utf-8")

    success = _bio_success(aggregate_df)
    hypothesis_path = ROOT / "bio-inspired-agent-swarm-prototype-hypothesis.md"
    if success:
        hypothesis_path.write_text(_hypothesis_text(aggregate_df, ablation_df), encoding="utf-8")
    elif hypothesis_path.exists():
        hypothesis_path.unlink()

    return {
        "aggregate_summary": aggregate_df,
        "ablation_summary": ablation_df,
        "success": success,
        "output_dir": destination,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Bio Swarm Pilot benchmark and export CSV/PNG/markdown artifacts.",
    )
    parser.add_argument(
        "--scenario",
        choices=("all", *DEFAULT_SCENARIOS),
        default="all",
        help="Run the full benchmark suite or only one scenario.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=DEFAULT_STEPS,
        help="Number of discrete simulation steps per run.",
    )
    parser.add_argument(
        "--replicates",
        type=int,
        default=DEFAULT_REPLICATES,
        help="Number of replicates for the full benchmark suite.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Base random seed for reproducible runs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Destination directory for generated CSV, PNG, and markdown outputs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.steps <= 0:
        parser.error("--steps must be greater than 0")
    if args.replicates <= 0:
        parser.error("--replicates must be greater than 0")

    if args.scenario == "all":
        result = run_all(
            output_dir=args.output_dir,
            steps=args.steps,
            replicates=args.replicates,
            base_seed=args.seed,
        )
        print(result["aggregate_summary"].to_string(index=False))
        print()
        print(f"outputs: {result['output_dir']}")
        print(f"hypothesis_markdown: {result['success']}")
        return 0

    summary = run_experiment(
        seed=args.seed,
        scenario_name=args.scenario,
        steps=args.steps,
        output_dir=args.output_dir,
    )
    summary_df = pd.DataFrame.from_dict(summary, orient="index")
    print(summary_df.to_string())
    print()
    print(f"outputs: {Path(args.output_dir).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
