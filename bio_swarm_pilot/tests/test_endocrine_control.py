from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from bio_swarm import BioInspiredSwarm
from simulation import SCENARIOS


class EndocrineControlTest(unittest.TestCase):
    def test_endocrine_does_not_cut_parallelism_when_errors_are_low(self) -> None:
        swarm = BioInspiredSwarm(
            rng=np.random.default_rng(1),
            scenario_name="overload",
            config=SCENARIOS["overload"],
        )
        swarm.queue = [
            {
                "type": "normal_task",
                "arrival_step": 0,
                "attempts": 0,
                "remaining_work": 1.0,
                "initial_work": 1.0,
                "noise": 0.2,
                "complexity": 0.4,
            }
            for _ in range(12)
        ]
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

        self.assertGreaterEqual(swarm.system_state["resource_budget"], 1.0)


if __name__ == "__main__":
    unittest.main()
