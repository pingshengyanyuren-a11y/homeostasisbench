from __future__ import annotations

from typing import Any

import numpy as np

try:
    from .baseline_swarm import BaselineSwarm, clamp
except ImportError:
    from baseline_swarm import BaselineSwarm, clamp


class BioInspiredSwarm(BaselineSwarm):
    def __init__(
        self,
        rng: np.random.Generator,
        scenario_name: str,
        config: dict[str, Any],
        system_name: str = "bio",
        layer_flags: dict[str, bool] | None = None,
    ) -> None:
        self.layer_flags = {
            "enable_nervous": True,
            "enable_endocrine": True,
            "enable_immune": True,
            "enable_metabolic": True,
        }
        if layer_flags:
            self.layer_flags.update(layer_flags)

        super().__init__(rng=rng, scenario_name=scenario_name, config=config, system_name=system_name)

        self.primary_worker_count = len(self.worker_ids)
        self.reserve_ids: list[str] = []
        for index in range(self.config.get("reserve_count", 2)):
            worker_id = f"reserve_{index}"
            self.reserve_ids.append(worker_id)
            self.worker_ids.append(worker_id)
            self.agents[worker_id] = self._make_agent(worker_id, "reserve_worker", reserve=True)

        self.system_state = {
            "risk_level": 0.18,
            "stress_level": 0.12,
            "resource_budget": 1.0,
            "exploration": 0.55,
            "backlog_pressure": 0.0,
            "error_pressure": 0.0,
            "failure_pressure": 0.0,
        }
        self.recovery_pool: set[str] = set()

    def _fast_lane(self, task: dict[str, Any]) -> bool:
        if not self.layer_flags["enable_nervous"]:
            return False
        if task["type"] == "urgent_task":
            return True
        return bool(task.get("flagged_urgent") and task.get("signal_confidence", 0.0) >= 0.62)

    def _review_capacity(self, effect: dict[str, Any]) -> int:
        if not self.layer_flags["enable_endocrine"]:
            return 2
        capacity = 2 + int(self.system_state["resource_budget"] > 0.85) - int(self.system_state["stress_level"] > 0.75)
        if effect["resource_drop"] > 0.25:
            capacity -= 1
        return max(capacity, 1)

    def _review_correction_probability(
        self,
        task: dict[str, Any],
        effect: dict[str, Any],
    ) -> float:
        probability = super()._review_correction_probability(task, effect)
        probability += 0.05 * self.system_state["resource_budget"]
        if self._fast_lane(task):
            probability -= 0.03
        return clamp(probability, 0.2, 0.9)

    def _enqueue_tasks(self, new_tasks: list[dict[str, Any]]) -> None:
        for task in new_tasks:
            if task.get("flagged_urgent") and not self._fast_lane(task):
                self.step_counters["demoted_false_signals"] += 1
            if self._fast_lane(task):
                self.step_counters["nervous_fast_lane_tasks"] += 1
                insertion_index = min(len(self.queue), max(0, len(self.queue) // 3))
                self.queue.insert(insertion_index, task)
            else:
                self.queue.append(task)

    def _apply_disturbance(
        self,
        disturbance: dict[str, Any] | None,
        step: int,
    ) -> dict[str, Any]:
        effect = super()._apply_disturbance(disturbance, step)
        if disturbance is None:
            return effect

        disturbance_type = disturbance["type"]
        severity = float(disturbance["severity"])

        if disturbance_type == "agent_failure" and self.layer_flags["enable_immune"]:
            effect["disturbance_pressure"] += 0.12
            effect["extra_error"] -= 0.01
        elif disturbance_type == "false_signal" and self.layer_flags["enable_nervous"]:
            effect["extra_error"] -= 0.03 * severity
        elif disturbance_type == "overload" and self.layer_flags["enable_endocrine"]:
            effect["capacity_multiplier"] *= 1.02
        elif disturbance_type == "resource_drop" and self.layer_flags["enable_endocrine"]:
            effect["capacity_multiplier"] *= 1.03

        return effect

    def _update_endocrine(self, effect: dict[str, Any]) -> None:
        if not self.layer_flags["enable_endocrine"]:
            self.system_state["risk_level"] = 0.2
            self.system_state["stress_level"] = 0.2
            self.system_state["resource_budget"] = 1.0
            self.system_state["exploration"] = 0.55
            self.system_state["backlog_pressure"] = 0.0
            self.system_state["error_pressure"] = 0.0
            self.system_state["failure_pressure"] = 0.0
            return

        recent_error = float(np.mean(self.recent_error_rates)) if self.recent_error_rates else 0.0
        recent_completion = float(np.mean(self.recent_completions)) if self.recent_completions else 0.0
        recent_backlog = float(np.mean(self.recent_backlog)) if self.recent_backlog else 0.0
        queue_pressure = len(self.queue) / max(len(self.worker_ids) * 2.0, 1.0)
        backlog_pressure = clamp(max(queue_pressure - 0.55, 0.0), 0.0, 1.0)
        backlog_pressure = max(
            backlog_pressure,
            clamp(recent_backlog / max(self.config["arrival_rate"] * 3.2, 1.0) - 0.45, 0.0, 1.0),
        )
        completion_pressure = clamp(
            1.0 - (recent_completion / max(self.config["arrival_rate"], 1.0)),
            0.0,
            1.0,
        )
        error_pressure = clamp((recent_error - 0.03) / 0.12, 0.0, 1.0)
        failure_pressure = clamp(
            (effect["failure_count"] * 0.42)
            + (effect["disturbance_pressure"] * 0.28)
            + (effect["resource_drop"] * 0.2),
            0.0,
            1.0,
        )
        low_error_overload = recent_error < 0.04 and error_pressure < 0.15 and failure_pressure < 0.4

        stress_target = (
            0.12
            + (backlog_pressure * 0.16)
            + (completion_pressure * 0.12)
            + (error_pressure * 0.34)
            + (failure_pressure * 0.26)
        )
        risk_target = (
            0.1
            + (error_pressure * 0.45)
            + (failure_pressure * 0.3)
            + (completion_pressure * 0.08)
        )
        if low_error_overload:
            stress_target -= 0.07
            risk_target -= 0.05

        stress = (
            (self.system_state["stress_level"] * 0.35)
            + (clamp(stress_target, 0.0, 1.0) * 0.65)
        )
        risk = (
            (self.system_state["risk_level"] * 0.35)
            + (clamp(risk_target, 0.0, 1.0) * 0.65)
        )

        if low_error_overload:
            resource_budget = 1.0 + (backlog_pressure * 0.1) - (effect["resource_drop"] * 0.1)
        else:
            resource_budget = (
                1.02
                + (backlog_pressure * 0.04)
                - (error_pressure * 0.22)
                - (failure_pressure * 0.16)
                - (effect["resource_drop"] * 0.25)
            )
            resource_budget -= max(stress - 0.72, 0.0) * 0.18

        if recent_backlog < self.config["arrival_rate"]:
            resource_budget += 0.04

        exploration = 0.58 - (risk * 0.35) - (error_pressure * 0.15) - (failure_pressure * 0.08)

        self.system_state["stress_level"] = clamp(stress, 0.0, 1.0)
        self.system_state["risk_level"] = clamp(risk, 0.0, 1.0)
        self.system_state["resource_budget"] = clamp(resource_budget, 0.45, 1.15)
        self.system_state["exploration"] = clamp(exploration, 0.05, 0.65)
        self.system_state["backlog_pressure"] = backlog_pressure
        self.system_state["error_pressure"] = error_pressure
        self.system_state["failure_pressure"] = failure_pressure

    def _restore_recovering_agents(self, step: int) -> None:
        for worker_id in self.worker_ids:
            agent = self.agents[worker_id]
            quarantine_until = max(agent["failed_until"], agent["isolated_until"])
            if step < quarantine_until:
                agent["recovering"] = True
                agent["health"] = clamp(agent["health"] + 0.03, 0.35, 1.0)
                agent["reliability"] = clamp(agent["reliability"] + 0.02, 0.3, 0.99)
                agent["energy"] = clamp(agent["energy"] + 0.08, 0.0, 1.0)
                self.recovery_pool.add(worker_id)
                continue
            if worker_id in self.recovery_pool:
                health_threshold = 0.68 if self.scenario_name == "failure_storm" else 0.72
                reliability_threshold = 0.62 if self.scenario_name == "failure_storm" else 0.66
                energy_threshold = 0.45 if self.scenario_name == "failure_storm" else 0.5
                if (
                    agent["health"] >= health_threshold
                    and agent["reliability"] >= reliability_threshold
                    and agent["energy"] >= energy_threshold
                ):
                    agent["active"] = True
                    agent["recovering"] = False
                    agent["rest_until"] = min(agent["rest_until"], step)
                    self.recovery_pool.discard(worker_id)

    def _activate_reserves(self, step: int) -> None:
        if not self.layer_flags["enable_immune"]:
            return
        active_primary = [
            worker_id
            for worker_id in self.worker_ids[: self.primary_worker_count]
            if self._worker_ready(worker_id, step)
        ]
        missing_capacity = self.primary_worker_count - len(active_primary)
        if missing_capacity <= 0 and self.system_state["stress_level"] < 0.68:
            return
        if missing_capacity <= 0:
            missing_capacity = 1

        for reserve_id in self.reserve_ids:
            reserve = self.agents[reserve_id]
            if reserve["active"]:
                continue
            reserve["active"] = True
            reserve["failed_until"] = 0
            reserve["isolated_until"] = 0
            reserve["rest_until"] = step
            reserve["recovering"] = False
            reserve["energy"] = clamp(reserve["energy"] + 0.25, 0.0, 0.95)
            reserve["health"] = clamp(reserve["health"] + 0.08, 0.6, 1.0)
            reserve["reliability"] = clamp(reserve["reliability"] + 0.04, 0.6, 0.95)
            self.step_counters["reserve_activations"] += 1
            missing_capacity -= 1
            if missing_capacity <= 0:
                break

    def _apply_local_reflex(self, step: int) -> None:
        if not self.layer_flags["enable_nervous"]:
            return
        for worker_id, task in list(self.in_progress.items()):
            worker = self.agents[worker_id]
            progress_ratio = 1.0 - max(task["remaining_work"], 0.0) / max(task["initial_work"], 0.1)
            overload_hit = worker["context_load"] > 0.88 or worker["latency"] > 4.8
            if overload_hit and progress_ratio < 0.45:
                self.in_progress.pop(worker_id, None)
                self.queue.insert(0, task)
                worker["rest_until"] = step + 1
                worker["context_load"] *= 0.45
                worker["latency"] *= 0.72
                self.step_counters["reflex_actions"] += 1

    def _schedule_metabolic_rests(self, step: int) -> None:
        urgent_pressure = any(self._fast_lane(task) for task in self.queue[: max(len(self.queue), 3)])
        for worker_id in self.worker_ids:
            worker = self.agents[worker_id]
            if not worker["active"] or worker_id in self.in_progress:
                continue
            if worker["energy"] < 0.22 and not urgent_pressure and self.layer_flags["enable_metabolic"]:
                worker["rest_until"] = max(worker["rest_until"], step + 1)
                self.step_counters["metabolic_rests"] += 1

    def _pre_step(self, step: int, effect: dict[str, Any]) -> None:
        self._update_endocrine(effect)
        self._restore_recovering_agents(step)
        self._apply_local_reflex(step)
        self._activate_reserves(step)
        self._schedule_metabolic_rests(step)

    def _task_priority_key(self, task: dict[str, Any], step: int) -> tuple[float, int]:
        del step
        if self._fast_lane(task):
            return (0.0, task["arrival_step"])
        stress = self.system_state["stress_level"]
        risk = self.system_state["risk_level"]
        priority = {
            "normal_task": 1.0,
            "long_task": 1.45 if stress < 0.65 else 1.6,
            "noisy_task": 1.85 if stress > 0.75 and risk > 0.35 else 1.35,
            "urgent_task": 0.4,
        }[task["type"]]
        priority += task["attempts"] * 0.1
        return (priority, task["arrival_step"])

    def _worker_score(self, worker_id: str) -> float:
        agent = self.agents[worker_id]
        return (
            (agent["reliability"] * 0.45)
            + (agent["health"] * 0.2)
            + (agent["energy"] * 0.25)
            - (agent["context_load"] * 0.18)
            - (agent["latency"] * 0.04)
        )

    def _assign_tasks(self, step: int, effect: dict[str, Any]) -> None:
        available = [worker_id for worker_id in self._available_workers(step) if worker_id not in self.in_progress]
        if not available or not self.queue:
            return

        self.queue.sort(key=lambda task: self._task_priority_key(task, step))
        available.sort(key=self._worker_score, reverse=True)
        total_available = len(available)

        if self.layer_flags["enable_endocrine"]:
            fast_lane_workers = [worker_id for worker_id in available if self.queue and self._fast_lane(self.queue[0])]
            parallel_factor = (
                0.82
                + (self.system_state["resource_budget"] * 0.22)
                - (self.system_state["risk_level"] * 0.14)
                - (max(self.system_state["stress_level"] - 0.82, 0.0) * 0.28)
            )
            parallel_floor = max(2, int(np.ceil(self.primary_worker_count * 0.6)))
            parallel_cap = int(round(len(available) * clamp(parallel_factor, 0.45, 1.0)))
            parallel_cap = max(parallel_floor, parallel_cap)
            available = available[: max(parallel_cap, 1)]
            for worker_id in fast_lane_workers:
                if worker_id not in available:
                    available.append(worker_id)
            self.step_counters["endocrine_throttle_ratio"] = max(
                0.0,
                1.0 - (len(available) / max(total_available, 1)),
            )

        for worker_id in available:
            if not self.queue:
                break
            self.in_progress[worker_id] = self.queue.pop(0)

    def _progress_multiplier(
        self,
        worker: dict[str, Any],
        task: dict[str, Any],
        effect: dict[str, Any],
    ) -> float:
        throughput = effect["capacity_multiplier"] * worker["health"]
        throughput *= 0.6 + (worker["energy"] * 0.55)
        throughput *= 0.92 + (worker["reliability"] * 0.1)
        throughput *= self.system_state["resource_budget"]
        throughput *= 1.04

        if task["type"] == "long_task":
            throughput *= 0.9
        elif task["type"] == "noisy_task" and self.system_state["stress_level"] > 0.6:
            throughput *= 0.85
        if self._fast_lane(task):
            throughput *= 1.25
        if worker["energy"] < 0.35:
            throughput *= 0.65

        return clamp(throughput, 0.18, 1.7)

    def _error_probability(
        self,
        worker: dict[str, Any],
        task: dict[str, Any],
        effect: dict[str, Any],
    ) -> float:
        queue_pressure = len(self.queue) / max(len(self.worker_ids) * 2.5, 1.0)
        error_probability = self._task_base_error(task)
        error_probability += effect["extra_error"] * 0.85
        error_probability += max(worker["context_load"] - 0.78, 0.0) * 0.12
        error_probability += (1.0 - worker["reliability"]) * 0.18
        error_probability += queue_pressure * 0.03
        error_probability -= self.system_state["resource_budget"] * 0.05
        error_probability += self.system_state["risk_level"] * 0.03
        if self._fast_lane(task):
            error_probability -= 0.03
        if worker["energy"] < 0.35:
            error_probability += 0.15
        return clamp(error_probability, 0.01, 0.8)

    def _post_process_worker(
        self,
        worker_id: str,
        task: dict[str, Any],
        progress: float,
        step: int,
        effect: dict[str, Any],
        stats: dict[str, Any],
    ) -> None:
        del task, step, effect, stats
        worker = self.agents[worker_id]
        worker["energy"] = clamp(worker["energy"] - (0.05 + (0.05 * progress)), 0.0, 1.0)
        worker["fatigue"] = clamp(worker["fatigue"] + 0.04, 0.0, 1.0)

    def _handle_success(
        self,
        worker_id: str,
        task: dict[str, Any],
        step: int,
        stats: dict[str, Any],
        latency: float,
    ) -> None:
        super()._handle_success(worker_id, task, step, stats, latency)
        worker = self.agents[worker_id]
        worker["energy"] = clamp(worker["energy"] + 0.02, 0.0, 1.0)
        worker["reliability"] = clamp(worker["reliability"] + 0.004, 0.3, 0.99)

    def _handle_error(
        self,
        worker_id: str,
        task: dict[str, Any],
        step: int,
        effect: dict[str, Any],
        stats: dict[str, Any],
        latency: float,
    ) -> None:
        super()._handle_error(worker_id, task, step, effect, stats, latency)
        worker = self.agents[worker_id]
        worker["energy"] = clamp(worker["energy"] - 0.05, 0.0, 1.0)

        if not self.layer_flags["enable_immune"]:
            return

        isolate = worker["consecutive_errors"] >= 2 or worker["reliability"] <= 0.58
        if isolate:
            worker["isolated_until"] = step + 2
            worker["active"] = False
            worker["recovering"] = True
            self.recovery_pool.add(worker_id)
            self.step_counters["immune_actions"] += 1
            if worker_id in self.in_progress:
                pending_task = self.in_progress.pop(worker_id)
                self.queue.insert(0, pending_task)

    def _on_idle_worker(self, worker_id: str, step: int) -> None:
        worker = self.agents[worker_id]
        if worker["recovering"]:
            previous_energy = worker["energy"]
            worker["energy"] = clamp(worker["energy"] + 0.1, 0.0, 1.0)
            worker["health"] = clamp(worker["health"] + 0.03, 0.35, 1.0)
            worker["reliability"] = clamp(worker["reliability"] + 0.02, 0.3, 0.99)
            self.step_counters["metabolic_recovery_gain"] += worker["energy"] - previous_energy
            return

        previous_energy = worker["energy"]
        super()._on_idle_worker(worker_id, step)
        worker["energy"] = clamp(worker["energy"] + (0.12 if self.layer_flags["enable_metabolic"] else 0.05), 0.0, 1.0)
        worker["fatigue"] = clamp(worker["fatigue"] - 0.05, 0.0, 1.0)
        self.step_counters["metabolic_recovery_gain"] += worker["energy"] - previous_energy

    def _post_step(
        self,
        step: int,
        effect: dict[str, Any],
        disturbance: dict[str, Any] | None,
        stats: dict[str, Any],
    ) -> None:
        del step, disturbance, stats
        if not self.layer_flags["enable_immune"]:
            return

        for reserve_id in self.reserve_ids:
            reserve = self.agents[reserve_id]
            deactivation_floor = 0.2 if self.scenario_name == "failure_storm" else 0.32
            if reserve["active"] and reserve_id not in self.in_progress and reserve["energy"] < deactivation_floor:
                reserve["active"] = False
                reserve["recovering"] = True
                self.recovery_pool.add(reserve_id)

        self.step_counters["immune_replacement_ratio"] = self.step_counters["reserve_activations"] / max(
            effect["failure_count"] + self.step_counters["immune_actions"],
            1,
        )

    def _build_step_record(
        self,
        step: int,
        disturbance: dict[str, Any] | None,
        stats: dict[str, Any],
        effect: dict[str, Any],
    ) -> dict[str, Any]:
        record = super()._build_step_record(step, disturbance, stats, effect)
        record["stress_level"] = self.system_state["stress_level"]
        record["risk_level"] = self.system_state["risk_level"]
        record["resource_budget"] = self.system_state["resource_budget"]
        record["isolated_agents"] = sum(
            1
            for worker_id in self.worker_ids
            if step < self.agents[worker_id]["isolated_until"]
        )
        record["recovery_pool"] = len(self.recovery_pool)
        return record
