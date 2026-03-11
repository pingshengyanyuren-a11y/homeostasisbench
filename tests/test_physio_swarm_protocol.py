from __future__ import annotations

import unittest

from physio_swarm.protocol import CellState, HomeostasisState, TaskSignal


class PhysiologicalProtocolTest(unittest.TestCase):
    def test_homeostasis_defaults_start_in_balanced_state(self) -> None:
        state = HomeostasisState()

        self.assertAlmostEqual(state.stress_level, 0.2)
        self.assertAlmostEqual(state.risk_level, 0.2)
        self.assertAlmostEqual(state.resource_budget, 1.0)
        self.assertAlmostEqual(state.energy_budget, 1.0)
        self.assertAlmostEqual(state.exploration_level, 0.45)
        self.assertAlmostEqual(state.toxicity_level, 0.0)

    def test_task_signal_classifies_fast_lane_candidates(self) -> None:
        fast_lane_task = TaskSignal(
            task_id="urgent-reflex",
            objective="stabilize queue",
            urgency=0.95,
            noise=0.1,
            complexity=0.2,
        )
        deliberative_task = TaskSignal(
            task_id="deep-analysis",
            objective="analyze paper",
            urgency=0.5,
            noise=0.4,
            complexity=0.85,
        )

        self.assertTrue(fast_lane_task.qualifies_for_fast_lane())
        self.assertFalse(deliberative_task.qualifies_for_fast_lane())

    def test_cell_state_exposes_fatigue_and_quarantine_flags(self) -> None:
        cell = CellState(
            cell_id="cortex-1",
            organ="cortex",
            energy=0.18,
            load=0.88,
            reliability=0.42,
            health=0.51,
            quarantined=True,
        )

        self.assertTrue(cell.is_fatigued)
        self.assertTrue(cell.quarantined)
        self.assertTrue(cell.needs_recovery())


if __name__ == "__main__":
    unittest.main()
