from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import unittest

from examples.physio_swarm_demo import run_demo


class PhysiologicalDemoTest(unittest.TestCase):
    def test_demo_returns_structured_artifacts(self) -> None:
        result = run_demo()

        self.assertIn("artifacts", result)
        self.assertIn("final_state", result)
        self.assertIn("final_cells", result)
        self.assertGreaterEqual(len(result["artifacts"]), 3)

    def test_demo_uses_fast_lane_and_quarantine(self) -> None:
        result = run_demo()
        routes = [artifact["route"] for artifact in result["artifacts"]]
        quarantined = [cell for cell in result["final_cells"].values() if cell["quarantined"]]

        self.assertIn("fast_lane", routes)
        self.assertGreaterEqual(len(quarantined), 1)

    def test_demo_records_budget_contraction_when_pressure_rises(self) -> None:
        result = run_demo()
        budgets = [artifact["resource_budget"] for artifact in result["artifacts"]]

        self.assertLess(min(budgets), 1.0)

    def test_demo_script_runs_directly(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        completed = subprocess.run(
            [sys.executable, str(repo_root / "examples" / "physio_swarm_demo.py")],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("fast_lane", completed.stdout)


if __name__ == "__main__":
    unittest.main()
