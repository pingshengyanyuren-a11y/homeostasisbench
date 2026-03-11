from __future__ import annotations

from dataclasses import replace

from .protocol import CellState, ExecutionArtifact, HomeostasisState, TaskSignal


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(value, upper))


class EndocrineController:
    def update(
        self,
        state: HomeostasisState,
        queue_pressure: float,
        error_pressure: float,
        resource_pressure: float,
    ) -> HomeostasisState:
        stress = _clamp(state.stress_level + (queue_pressure * 0.18) + (error_pressure * 0.08))
        risk = _clamp(state.risk_level + (error_pressure * 0.2) + (resource_pressure * 0.06))
        resource_budget = _clamp(state.resource_budget - (queue_pressure * 0.12) - (resource_pressure * 0.1))
        exploration = _clamp(state.exploration_level - (stress * 0.18) - (risk * 0.1))
        toxicity = _clamp(state.toxicity_level + (error_pressure * 0.12))
        energy_budget = _clamp(state.energy_budget - (queue_pressure * 0.04))
        return HomeostasisState(
            stress_level=stress,
            risk_level=risk,
            resource_budget=resource_budget,
            energy_budget=energy_budget,
            exploration_level=exploration,
            toxicity_level=toxicity,
        )


class MetabolicController:
    def apply(self, cell: CellState) -> CellState:
        energy_cost = 0.06 + (cell.load * 0.05)
        next_energy = _clamp(cell.energy - energy_cost)
        next_load = _clamp(cell.load + 0.03)
        next_health = _clamp(cell.health - (0.04 if cell.is_fatigued else 0.01))
        return replace(cell, energy=next_energy, load=next_load, health=next_health)


class NervousRouter:
    def select_cell(self, task: TaskSignal, cells: dict[str, CellState]) -> CellState:
        eligible = [cell for cell in cells.values() if not cell.quarantined]
        if task.qualifies_for_fast_lane():
            reflex_cells = [cell for cell in eligible if cell.organ == "reflex_arc"]
            if reflex_cells:
                return reflex_cells[0]
        cortex_cells = [cell for cell in eligible if cell.organ == "cortex"]
        if cortex_cells:
            return cortex_cells[0]
        return eligible[0]


class ImmuneMonitor:
    def observe_failure(self, cell: CellState) -> CellState:
        failures = cell.recent_failures + 1
        reliability = _clamp(cell.reliability - 0.12)
        quarantined = failures >= 2 or reliability <= 0.35 or cell.health <= 0.45
        return replace(cell, recent_failures=failures, reliability=reliability, quarantined=quarantined)

    def observe_success(self, cell: CellState) -> CellState:
        failures = max(0, cell.recent_failures - 1)
        reliability = _clamp(cell.reliability + 0.03)
        return replace(cell, recent_failures=failures, reliability=reliability)


class PhysioSwarmKernel:
    def __init__(
        self,
        endocrine: EndocrineController,
        metabolic: MetabolicController,
        router: NervousRouter,
        immune: ImmuneMonitor,
    ) -> None:
        self.endocrine = endocrine
        self.metabolic = metabolic
        self.router = router
        self.immune = immune

    def route_and_execute(
        self,
        state: HomeostasisState,
        cells: dict[str, CellState],
        task: TaskSignal,
        queue_pressure: float,
        error_pressure: float,
        resource_pressure: float,
    ) -> tuple[ExecutionArtifact, HomeostasisState, dict[str, CellState]]:
        next_state = self.endocrine.update(
            state=state,
            queue_pressure=queue_pressure,
            error_pressure=error_pressure,
            resource_pressure=resource_pressure,
        )
        selected = self.router.select_cell(task=task, cells=cells)
        adjusted = self.metabolic.apply(selected)
        adjusted = self.immune.observe_success(adjusted)

        next_cells = dict(cells)
        next_cells[adjusted.cell_id] = adjusted

        route = "fast_lane" if task.qualifies_for_fast_lane() and selected.organ == "reflex_arc" else "deliberative"
        artifact = ExecutionArtifact(
            task_id=task.task_id,
            cell_id=adjusted.cell_id,
            route=route,
            status="executed",
            notes=[f"{selected.organ} handled {task.objective}"],
        )
        return artifact, next_state, next_cells
