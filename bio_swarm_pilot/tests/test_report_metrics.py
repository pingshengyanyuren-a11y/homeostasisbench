from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from simulation import run_all


class ReportMetricsTest(unittest.TestCase):
    def test_report_contains_acceptance_gates_and_layer_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            run_all(output_dir=Path(tmp_dir), steps=60, replicates=2, base_seed=42)
            report = (Path(tmp_dir) / "experiment_report.md").read_text(encoding="utf-8")

            self.assertIn("## Acceptance Gates", report)
            self.assertIn("endocrine_throttle_ratio", report)
            self.assertIn("immune_replacement_ratio", report)
            self.assertIn("metabolic_recovery_gain", report)
            self.assertIn("nervous_fast_lane_share", report)


if __name__ == "__main__":
    unittest.main()
