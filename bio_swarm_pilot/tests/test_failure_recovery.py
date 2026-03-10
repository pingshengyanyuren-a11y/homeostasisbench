from pathlib import Path
import sys
import unittest

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


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
        worker["health"] = 0.70
        worker["reliability"] = 0.64
        worker["energy"] = 0.48

        swarm.recovery_pool.add("worker_0")
        swarm._restore_recovering_agents(step=3)

        self.assertTrue(swarm.agents["worker_0"]["active"])


if __name__ == "__main__":
    unittest.main()
