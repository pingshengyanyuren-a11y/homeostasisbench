from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from physio_swarm.kernel import (
    EndocrineController,
    ImmuneMonitor,
    MetabolicController,
    NervousRouter,
    PhysioSwarmKernel,
)
from physio_swarm.protocol import CellState, ExecutionArtifact, HomeostasisState, TaskSignal


def _artifact_record(artifact: ExecutionArtifact, state: HomeostasisState) -> dict[str, Any]:
    return {
        "task_id": artifact.task_id,
        "cell_id": artifact.cell_id,
        "route": artifact.route,
        "status": artifact.status,
        "notes": list(artifact.notes),
        "resource_budget": state.resource_budget,
        "stress_level": state.stress_level,
    }


def run_demo() -> dict[str, Any]:
    endocrine = EndocrineController()
    metabolic = MetabolicController()
    router = NervousRouter()
    immune = ImmuneMonitor()
    kernel = PhysioSwarmKernel(
        endocrine=endocrine,
        metabolic=metabolic,
        router=router,
        immune=immune,
    )

    state = HomeostasisState()
    cells = {
        "reflex-1": CellState(cell_id="reflex-1", organ="reflex_arc", energy=0.9),
        "cortex-1": CellState(cell_id="cortex-1", organ="cortex", energy=0.86),
        "cortex-noisy": CellState(
            cell_id="cortex-noisy",
            organ="cortex",
            energy=0.61,
            reliability=0.48,
            health=0.69,
        ),
    }

    artifacts: list[dict[str, Any]] = []

    task_stream = [
        (
            TaskSignal(
                task_id="urgent-reroute",
                objective="protect overloaded queue",
                urgency=0.96,
                noise=0.08,
                complexity=0.22,
            ),
            0.9,
            0.12,
            0.18,
        ),
        (
            TaskSignal(
                task_id="deep-synthesis",
                objective="synthesize evidence",
                urgency=0.58,
                noise=0.28,
                complexity=0.82,
            ),
            0.72,
            0.18,
            0.31,
        ),
    ]

    for task, queue_pressure, error_pressure, resource_pressure in task_stream:
        artifact, state, cells = kernel.route_and_execute(
            state=state,
            cells=cells,
            task=task,
            queue_pressure=queue_pressure,
            error_pressure=error_pressure,
            resource_pressure=resource_pressure,
        )
        artifacts.append(_artifact_record(artifact, state))

    compromised = immune.observe_failure(cells["cortex-noisy"])
    compromised = immune.observe_failure(compromised)
    cells["cortex-noisy"] = compromised
    immune_artifact = ExecutionArtifact(
        task_id="immune-sweep",
        cell_id="cortex-noisy",
        route="immune_response",
        status="quarantined",
        notes=["immune monitor quarantined noisy cortex cell"],
    )
    artifacts.append(_artifact_record(immune_artifact, state))

    return {
        "artifacts": artifacts,
        "final_state": asdict(state),
        "final_cells": {cell_id: asdict(cell) for cell_id, cell in cells.items()},
    }


if __name__ == "__main__":
    demo = run_demo()
    for artifact in demo["artifacts"]:
        print(artifact)
    print("final_state", demo["final_state"])
