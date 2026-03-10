from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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


if __name__ == "__main__":
    unittest.main()
