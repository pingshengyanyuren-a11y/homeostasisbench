from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


class BaselineSwarm:
    def __init__(
        self,
        rng: np.random.Generator,
        scenario_name: str,
        config: dict[str, Any],
        system_name: str = "baseline",
    ) -> None:
        self.rng = rng
        self.scenario_name = scenario_name
        self.config = config
        self.system_name = system_name

        self.queue: list[dict[str, Any]] = []
        self.in_progress: dict[str, dict[str, Any]] = {}
        self.worker_ids: list[str] = []
        self.agents: dict[str, dict[str, Any]] = {}
        self.manager_pointer = 0

        self.total_arrived = 0
        self.total_completed = 0
        self.total_errors = 0
        self.total_resource_used = 0.0

        self.recent_error_rates: deque[float] = deque(maxlen=8)
        self.recent_completions: deque[float] = deque(maxlen=8)
        self.recent_backlog: deque[float] = deque(maxlen=8)

        self.step_counters = {
            "reflex_actions": 0,
            "immune_actions": 0,
            "reserve_activations": 0,
            "metabolic_rests": 0,
            "demoted_false_signals": 0,
            "nervous_fast_lane_tasks": 0,
            "endocrine_throttle_ratio": 0.0,
            "immune_replacement_ratio": 0.0,
            "metabolic_recovery_gain": 0.0,
        }

        self._build_agents()

    def _build_agents(self) -> None:
        self.manager_id = "manager_0"
        self.reviewer_id = "reviewer_0"
        self.agents[self.manager_id] = self._make_agent(self.manager_id, "manager")
        self.agents[self.reviewer_id] = self._make_agent(self.reviewer_id, "reviewer")

        for index in range(self.config.get("worker_count", 5)):
            worker_id = f"worker_{index}"
            self.worker_ids.append(worker_id)
            self.agents[worker_id] = self._make_agent(worker_id, "worker")

    def _make_agent(
        self,
        agent_id: str,
        role: str,
        reserve: bool = False,
    ) -> dict[str, Any]:
        reliability = float(self.rng.uniform(0.84, 0.95))
        if reserve:
            reliability = float(self.rng.uniform(0.78, 0.88))
        return {
            "id": agent_id,
            "role": role,
            "health": float(self.rng.uniform(0.9, 1.0)),
            "energy": 1.0,
            "reliability": reliability,
            "context_load": 0.0,
            "latency": 1.0,
            "fatigue": 0.0,
            "failed_until": 0,
            "isolated_until": 0,
            "rest_until": 0,
            "active": not reserve,
            "reserve": reserve,
            "recovering": False,
            "consecutive_errors": 0,
        }

    def _task_base_error(self, task: dict[str, Any]) -> float:
        base_error = {
            "normal_task": 0.05,
            "urgent_task": 0.07,
            "noisy_task": 0.14,
            "long_task": 0.08,
        }[task["type"]]
        return clamp(
            base_error + (task["noise"] * 0.06) + (task["complexity"] * 0.03),
            0.01,
            0.6,
        )

    def _review_capacity(self, effect: dict[str, Any]) -> int:
        del effect
        return 2

    def _review_correction_probability(
        self,
        task: dict[str, Any],
        effect: dict[str, Any],
    ) -> float:
        reviewer = self.agents[self.reviewer_id]
        probability = 0.45 + (reviewer["reliability"] * 0.22)
        if task["type"] == "urgent_task":
            probability -= 0.05
        probability -= effect["extra_error"] * 0.15
        return clamp(probability, 0.15, 0.85)

    def _worker_ready(self, worker_id: str, step: int) -> bool:
        agent = self.agents[worker_id]
        return bool(
            agent["active"]
            and step >= agent["failed_until"]
            and step >= agent["isolated_until"]
            and step >= agent["rest_until"]
        )

    def _available_workers(self, step: int) -> list[str]:
        return [worker_id for worker_id in self.worker_ids if self._worker_ready(worker_id, step)]

    def _recover_agents(self, step: int) -> None:
        del step
        for worker_id in self.worker_ids:
            agent = self.agents[worker_id]
            if worker_id not in self.in_progress:
                agent["context_load"] *= 0.55
                agent["latency"] = max(0.8, agent["latency"] * 0.9)
                agent["health"] = clamp(agent["health"] + 0.01, 0.45, 1.0)
                agent["fatigue"] = clamp(agent["fatigue"] - 0.02, 0.0, 1.0)

    def _enqueue_tasks(self, new_tasks: list[dict[str, Any]]) -> None:
        self.queue.extend(new_tasks)

    def _apply_disturbance(
        self,
        disturbance: dict[str, Any] | None,
        step: int,
    ) -> dict[str, Any]:
        effect = {
            "capacity_multiplier": 1.0,
            "extra_error": 0.0,
            "disturbance_pressure": 0.0,
            "resource_drop": 0.0,
            "failure_count": 0,
        }
        if disturbance is None:
            return effect

        disturbance_type = disturbance["type"]
        severity = float(disturbance["severity"])

        if disturbance_type == "agent_failure":
            candidates = [worker_id for worker_id in self.worker_ids if self._worker_ready(worker_id, step)]
            if candidates:
                failed_worker = candidates[int(self.rng.integers(0, len(candidates)))]
                agent = self.agents[failed_worker]
                agent["failed_until"] = step + int(disturbance.get("duration", 2)) + 1
                agent["health"] = clamp(agent["health"] - (0.12 * severity), 0.35, 1.0)
                agent["reliability"] = clamp(agent["reliability"] - (0.09 * severity), 0.3, 0.99)
                if failed_worker in self.in_progress:
                    task = self.in_progress.pop(failed_worker)
                    task["attempts"] += 1
                    self.queue.insert(0, task)
                effect["failure_count"] = 1
                effect["extra_error"] += 0.03
                effect["disturbance_pressure"] += 0.25 + (0.25 * severity)
        elif disturbance_type == "overload":
            effect["capacity_multiplier"] *= 1.0 - (0.18 + (0.22 * severity))
            effect["extra_error"] += 0.08 + (0.06 * severity)
            effect["disturbance_pressure"] += 0.3 + (0.3 * severity)
        elif disturbance_type == "false_signal":
            effect["extra_error"] += 0.06 + (0.05 * severity)
            effect["disturbance_pressure"] += 0.1 + (0.15 * severity)
        elif disturbance_type == "resource_drop":
            effect["capacity_multiplier"] *= 1.0 - (0.16 + (0.22 * severity))
            effect["extra_error"] += 0.03 + (0.03 * severity)
            effect["resource_drop"] = 0.2 + (0.4 * severity)
            effect["disturbance_pressure"] += 0.22 + (0.2 * severity)

        return effect

    def _pre_step(self, step: int, effect: dict[str, Any]) -> None:
        del step, effect

    def _task_priority_key(self, task: dict[str, Any], step: int) -> tuple[float, int]:
        del step
        return (task["arrival_step"], task["attempts"])

    def _assign_tasks(self, step: int, effect: dict[str, Any]) -> None:
        del effect
        available = [worker_id for worker_id in self._available_workers(step) if worker_id not in self.in_progress]
        if not available or not self.queue:
            return

        self.queue.sort(key=lambda task: self._task_priority_key(task, step))
        ordered_workers = self.worker_ids[self.manager_pointer :] + self.worker_ids[: self.manager_pointer]
        assigned_count = 0

        for worker_id in ordered_workers:
            if worker_id not in available or not self.queue:
                continue
            self.in_progress[worker_id] = self.queue.pop(0)
            assigned_count += 1

        self.manager_pointer = (self.manager_pointer + assigned_count) % len(self.worker_ids)

    def _progress_multiplier(
        self,
        worker: dict[str, Any],
        task: dict[str, Any],
        effect: dict[str, Any],
    ) -> float:
        throughput = effect["capacity_multiplier"] * worker["health"]
        if task["type"] == "long_task":
            throughput *= 0.82
        elif task["type"] == "noisy_task":
            throughput *= 0.92
        elif task["type"] == "urgent_task":
            throughput *= 1.05
        return clamp(throughput, 0.2, 1.45)

    def _error_probability(
        self,
        worker: dict[str, Any],
        task: dict[str, Any],
        effect: dict[str, Any],
    ) -> float:
        queue_pressure = len(self.queue) / max(len(self.worker_ids) * 2.4, 1.0)
        error_probability = self._task_base_error(task)
        error_probability += effect["extra_error"]
        error_probability += max(worker["context_load"] - 0.65, 0.0) * 0.15
        error_probability += (1.0 - worker["reliability"]) * 0.25
        error_probability += queue_pressure * 0.05
        if task.get("flagged_urgent"):
            error_probability += 0.02
        return clamp(error_probability, 0.01, 0.9)

    def _update_worker_progress_state(
        self,
        worker: dict[str, Any],
        task: dict[str, Any],
        step: int,
    ) -> None:
        queue_pressure = len(self.queue) / max(len(self.worker_ids) * 2.0, 1.0)
        progress_ratio = 1.0 - max(task["remaining_work"], 0.0) / max(task["initial_work"], 0.1)
        worker["context_load"] = clamp(0.35 + queue_pressure + (1.0 - progress_ratio) * 0.4, 0.0, 1.5)
        worker["latency"] = (worker["latency"] * 0.55) + ((step - task["arrival_step"] + 1) * 0.45)
        worker["fatigue"] = clamp(worker["fatigue"] + 0.03, 0.0, 1.0)

    def _handle_success(
        self,
        worker_id: str,
        task: dict[str, Any],
        step: int,
        stats: dict[str, Any],
        latency: float,
    ) -> None:
        del task, step
        worker = self.agents[worker_id]
        worker["consecutive_errors"] = 0
        worker["reliability"] = clamp(worker["reliability"] + 0.01, 0.3, 0.99)
        worker["health"] = clamp(worker["health"] + 0.004, 0.35, 1.0)
        stats["completed"] += 1
        stats["latencies"].append(latency)

    def _handle_error(
        self,
        worker_id: str,
        task: dict[str, Any],
        step: int,
        effect: dict[str, Any],
        stats: dict[str, Any],
        latency: float,
    ) -> None:
        worker = self.agents[worker_id]
        worker["consecutive_errors"] += 1
        worker["reliability"] = clamp(worker["reliability"] - 0.04, 0.3, 0.99)
        worker["health"] = clamp(worker["health"] - 0.01, 0.35, 1.0)

        if stats["review_used"] < self._review_capacity(effect):
            stats["review_used"] += 1
            stats["resource_used"] += 0.35
            correction_probability = self._review_correction_probability(task, effect)
            if self.rng.random() < correction_probability:
                stats["corrected_by_review"] += 1
                self._handle_success(worker_id, task, step, stats, latency + 0.5)
                return

        if task["attempts"] < 1:
            task["attempts"] += 1
            task["remaining_work"] = max(0.85, task["initial_work"] * 0.65)
            self.queue.append(task)
            return

        stats["errors"] += 1

    def _pre_process_worker(
        self,
        worker_id: str,
        task: dict[str, Any],
        step: int,
        effect: dict[str, Any],
        stats: dict[str, Any],
    ) -> None:
        del worker_id, task, step, effect, stats

    def _post_process_worker(
        self,
        worker_id: str,
        task: dict[str, Any],
        progress: float,
        step: int,
        effect: dict[str, Any],
        stats: dict[str, Any],
    ) -> None:
        del worker_id, task, progress, step, effect, stats

    def _on_idle_worker(self, worker_id: str, step: int) -> None:
        del step
        agent = self.agents[worker_id]
        if not agent["active"]:
            return
        agent["context_load"] *= 0.5
        agent["latency"] = max(0.8, agent["latency"] * 0.88)
        agent["health"] = clamp(agent["health"] + 0.012, 0.35, 1.0)
        agent["fatigue"] = clamp(agent["fatigue"] - 0.03, 0.0, 1.0)

    def _post_step(
        self,
        step: int,
        effect: dict[str, Any],
        disturbance: dict[str, Any] | None,
        stats: dict[str, Any],
    ) -> None:
        del step, effect, disturbance, stats

    def _process_worker(
        self,
        worker_id: str,
        step: int,
        effect: dict[str, Any],
        stats: dict[str, Any],
    ) -> None:
        if not self._worker_ready(worker_id, step):
            return
        task = self.in_progress.get(worker_id)
        if task is None:
            return

        worker = self.agents[worker_id]
        self._pre_process_worker(worker_id, task, step, effect, stats)
        progress = self._progress_multiplier(worker, task, effect)
        task["remaining_work"] -= progress
        stats["resource_used"] += progress
        self._update_worker_progress_state(worker, task, step)
        self._post_process_worker(worker_id, task, progress, step, effect, stats)

        if task["remaining_work"] > 0:
            return

        self.in_progress.pop(worker_id, None)
        latency = float(step - task["arrival_step"] + 1)
        error_probability = self._error_probability(worker, task, effect)
        if self.rng.random() < error_probability:
            self._handle_error(worker_id, task, step, effect, stats, latency)
            return
        self._handle_success(worker_id, task, step, stats, latency)

    def _build_step_record(
        self,
        step: int,
        disturbance: dict[str, Any] | None,
        stats: dict[str, Any],
        effect: dict[str, Any],
    ) -> dict[str, Any]:
        worker_states = [self.agents[worker_id] for worker_id in self.worker_ids if self.agents[worker_id]["active"]]
        mean_health = float(np.mean([agent["health"] for agent in worker_states])) if worker_states else 0.0
        mean_energy = float(np.mean([agent["energy"] for agent in worker_states])) if worker_states else 0.0
        mean_reliability = (
            float(np.mean([agent["reliability"] for agent in worker_states])) if worker_states else 0.0
        )
        pending_tasks = len(self.queue) + len(self.in_progress)
        error_denominator = max(stats["completed"] + stats["errors"], 1)
        average_latency = float(np.mean(stats["latencies"])) if stats["latencies"] else np.nan

        self.total_completed += stats["completed"]
        self.total_errors += stats["errors"]
        self.total_resource_used += stats["resource_used"]

        self.recent_error_rates.append(stats["errors"] / error_denominator)
        self.recent_completions.append(float(stats["completed"]))
        self.recent_backlog.append(float(pending_tasks))

        return {
            "scenario": self.scenario_name,
            "system": self.system_name,
            "step": step,
            "arrived_tasks": stats["arrived"],
            "completed_tasks": stats["completed"],
            "failed_tasks": stats["errors"],
            "pending_tasks": pending_tasks,
            "avg_latency_step": average_latency,
            "error_rate_step": stats["errors"] / error_denominator,
            "resource_used_step": stats["resource_used"],
            "active_workers": len(self._available_workers(step)),
            "mean_health": mean_health,
            "mean_energy": mean_energy,
            "mean_reliability": mean_reliability,
            "stress_level": 0.0,
            "risk_level": 0.0,
            "resource_budget": 1.0 - effect["resource_drop"],
            "isolated_agents": 0,
            "recovery_pool": 0,
            "reflex_actions": self.step_counters["reflex_actions"],
            "immune_actions": self.step_counters["immune_actions"],
            "reserve_activations": self.step_counters["reserve_activations"],
            "metabolic_rests": self.step_counters["metabolic_rests"],
            "demoted_false_signals": self.step_counters["demoted_false_signals"],
            "nervous_fast_lane_share": self.step_counters["nervous_fast_lane_tasks"] / max(stats["arrived"], 1),
            "endocrine_throttle_ratio": self.step_counters["endocrine_throttle_ratio"],
            "immune_replacement_ratio": self.step_counters["immune_replacement_ratio"],
            "metabolic_recovery_gain": self.step_counters["metabolic_recovery_gain"],
            "corrected_by_review": stats["corrected_by_review"],
            "disturbance_type": disturbance["type"] if disturbance else "none",
            "disturbance_severity": disturbance["severity"] if disturbance else 0.0,
            "cumulative_arrived": self.total_arrived,
            "cumulative_completed": self.total_completed,
            "cumulative_failed": self.total_errors,
            "cumulative_resource": self.total_resource_used,
        }

    def step(
        self,
        new_tasks: list[dict[str, Any]],
        disturbance: dict[str, Any] | None,
        step: int,
    ) -> dict[str, Any]:
        self.step_counters = {key: 0 for key in self.step_counters}
        self.total_arrived += len(new_tasks)
        self._recover_agents(step)
        self._enqueue_tasks(new_tasks)
        effect = self._apply_disturbance(disturbance, step)
        self._pre_step(step, effect)
        self._assign_tasks(step, effect)

        stats = {
            "arrived": len(new_tasks),
            "completed": 0,
            "errors": 0,
            "resource_used": 0.0,
            "latencies": [],
            "review_used": 0,
            "corrected_by_review": 0,
        }

        for worker_id in list(self.in_progress):
            self._process_worker(worker_id, step, effect, stats)

        for worker_id in self.worker_ids:
            if worker_id not in self.in_progress:
                self._on_idle_worker(worker_id, step)

        self._post_step(step, effect, disturbance, stats)
        return self._build_step_record(step, disturbance, stats, effect)
