from __future__ import annotations

import unittest

from physio_swarm.kernel import (
    EndocrineController,
    ImmuneMonitor,
    MetabolicController,
    NervousRouter,
    PhysioSwarmKernel,
)
from physio_swarm.protocol import CellState, HomeostasisState, TaskSignal


class PhysiologicalKernelTest(unittest.TestCase):
    def test_endocrine_controller_contracts_when_overloaded(self) -> None:
        state = HomeostasisState()
        controller = EndocrineController()

        updated = controller.update(
            state=state,
            queue_pressure=0.92,
            error_pressure=0.35,
            resource_pressure=0.4,
        )

        self.assertGreater(updated.stress_level, state.stress_level)
        self.assertLess(updated.resource_budget, state.resource_budget)
        self.assertLess(updated.exploration_level, state.exploration_level)

    def test_metabolic_controller_downgrades_fatigued_cells(self) -> None:
        controller = MetabolicController()
        cell = CellState(cell_id="cortex-1", organ="cortex", energy=0.16, load=0.87)

        adjusted = controller.apply(cell)

        self.assertLess(adjusted.energy, 0.16)
        self.assertGreaterEqual(adjusted.load, 0.87)
        self.assertTrue(adjusted.needs_recovery())

    def test_nervous_router_prefers_reflex_for_simple_urgent_signals(self) -> None:
        router = NervousRouter()
        cells = {
            "reflex-1": CellState(cell_id="reflex-1", organ="reflex_arc"),
            "cortex-1": CellState(cell_id="cortex-1", organ="cortex"),
        }
        task = TaskSignal(
            task_id="urgent-1",
            objective="stop recursion",
            urgency=0.95,
            noise=0.1,
            complexity=0.2,
        )

        routed = router.select_cell(task=task, cells=cells)

        self.assertEqual(routed.cell_id, "reflex-1")

    def test_immune_monitor_quarantines_cells_after_repeated_faults(self) -> None:
        immune = ImmuneMonitor()
        cell = CellState(cell_id="analyst-1", organ="cortex", reliability=0.55, health=0.7)

        marked = immune.observe_failure(cell)
        marked = immune.observe_failure(marked)

        self.assertTrue(marked.quarantined)
        self.assertGreaterEqual(marked.recent_failures, 2)

    def test_kernel_routes_and_records_artifacts(self) -> None:
        kernel = PhysioSwarmKernel(
            endocrine=EndocrineController(),
            metabolic=MetabolicController(),
            router=NervousRouter(),
            immune=ImmuneMonitor(),
        )
        cells = {
            "reflex-1": CellState(cell_id="reflex-1", organ="reflex_arc"),
            "cortex-1": CellState(cell_id="cortex-1", organ="cortex"),
        }
        task = TaskSignal(
            task_id="urgent-2",
            objective="reroute overloaded queue",
            urgency=0.93,
            noise=0.12,
            complexity=0.25,
        )

        artifact, next_state, next_cells = kernel.route_and_execute(
            state=HomeostasisState(),
            cells=cells,
            task=task,
            queue_pressure=0.84,
            error_pressure=0.18,
            resource_pressure=0.22,
        )

        self.assertEqual(artifact.route, "fast_lane")
        self.assertEqual(artifact.status, "executed")
        self.assertIn("reflex", artifact.notes[0])
        self.assertLess(next_state.resource_budget, 1.0)
        self.assertIn("reflex-1", next_cells)


if __name__ == "__main__":
    unittest.main()
