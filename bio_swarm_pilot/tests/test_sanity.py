from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class PilotSanityTest(unittest.TestCase):
    def test_run_experiment_generates_core_outputs(self) -> None:
        from simulation import run_experiment

        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            summary = run_experiment(
                seed=7,
                scenario_name="normal",
                steps=20,
                output_dir=output_dir,
            )

            self.assertIn("baseline", summary)
            self.assertIn("bio", summary)
            self.assertTrue((output_dir / "scenario_normal_step_metrics.csv").exists())
            self.assertTrue((output_dir / "scenario_normal_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
