# Physiological Swarm Skill Framework Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a reusable physiological multi-agent framework plus a Codex skill that teaches and applies the protocol instead of only simulating it.

**Architecture:** Create a lightweight Python framework centered on system-wide homeostasis, fast nervous routing, immune quarantine, and explicit cell state. Wrap that framework in a skill folder that teaches the institutional protocol, references the runtime, and ships a runnable demo showing endocrine/metabolic control over a small swarm.

**Tech Stack:** Python 3.11, standard library, `unittest`, markdown skill files, no heavyweight frameworks.

---

### Task 1: Create the framework skeleton and protocol tests

**Files:**
- Create: `physio_swarm/__init__.py`
- Create: `physio_swarm/protocol.py`
- Create: `tests/test_physio_swarm_protocol.py`

**Step 1: Write the failing test**

Create protocol tests for:
- `HomeostasisState` default values
- `TaskSignal` priority classification
- `CellState` fatigue and quarantine flags

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_physio_swarm_protocol -v`
Expected: FAIL because `physio_swarm.protocol` does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- `HomeostasisState`
- `TaskSignal`
- `CellState`
- `ExecutionArtifact`

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_physio_swarm_protocol -v`
Expected: PASS

**Step 5: Commit**

```bash
git add physio_swarm/__init__.py physio_swarm/protocol.py tests/test_physio_swarm_protocol.py
git commit -m "feat: add physiological swarm protocol primitives"
```

### Task 2: Implement endocrine, metabolic, nervous, and immune kernel behavior

**Files:**
- Create: `physio_swarm/kernel.py`
- Create: `tests/test_physio_swarm_kernel.py`

**Step 1: Write the failing test**

Create kernel tests for:
- endocrine state contraction under overload
- metabolic downgrade when cell energy drops
- nervous fast-lane routing for urgent low-noise tasks
- immune quarantine after repeated faults

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_physio_swarm_kernel -v`
Expected: FAIL because `PhysioSwarmKernel` and related controllers do not exist yet.

**Step 3: Write minimal implementation**

Implement:
- `EndocrineController`
- `MetabolicController`
- `NervousRouter`
- `ImmuneMonitor`
- `PhysioSwarmKernel.route_and_execute()`

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_physio_swarm_kernel -v`
Expected: PASS

**Step 5: Commit**

```bash
git add physio_swarm/kernel.py tests/test_physio_swarm_kernel.py
git commit -m "feat: add physiological swarm control kernel"
```

### Task 3: Add demo workflow and runtime example

**Files:**
- Create: `examples/physio_swarm_demo.py`
- Create: `tests/test_physio_swarm_demo.py`

**Step 1: Write the failing test**

Create a demo test that runs a short workflow and asserts:
- at least one urgent task uses the fast lane
- overloaded cells receive budget contraction
- immune monitor can quarantine a noisy cell
- the demo returns an artifact trail instead of only printing text

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_physio_swarm_demo -v`
Expected: FAIL because the demo module does not exist yet.

**Step 3: Write minimal implementation**

Implement a small script exposing `run_demo()` that:
- builds a few cell definitions
- injects disturbance and urgent tasks
- runs the kernel
- returns structured artifacts

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_physio_swarm_demo -v`
Expected: PASS

**Step 5: Commit**

```bash
git add examples/physio_swarm_demo.py tests/test_physio_swarm_demo.py
git commit -m "feat: add physiological swarm demo workflow"
```

### Task 4: Package the system as a skill

**Files:**
- Create: `skills/physio-swarm-protocol/SKILL.md`
- Create: `skills/physio-swarm-protocol/references/protocol.md`
- Create: `skills/physio-swarm-protocol/references/runtime.md`
- Modify: `README.md`

**Step 1: Write the failing test**

Create a test that asserts:
- the skill file exists
- it mentions endocrine, metabolic, nervous, immune
- it points to the bundled runtime/example

**Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_physio_swarm_skill -v`
Expected: FAIL because the skill folder does not exist yet.

**Step 3: Write minimal implementation**

Implement the skill with:
- concise trigger metadata
- protocol guidance
- runtime references
- demo entrypoint

Update `README.md` to point to the new framework and skill.

**Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_physio_swarm_skill -v`
Expected: PASS

**Step 5: Commit**

```bash
git add skills/physio-swarm-protocol README.md tests/test_physio_swarm_skill.py
git commit -m "feat: add physiological swarm skill package"
```

### Task 5: Full verification

**Files:**
- Verify: `tests/test_physio_swarm_protocol.py`
- Verify: `tests/test_physio_swarm_kernel.py`
- Verify: `tests/test_physio_swarm_demo.py`
- Verify: `tests/test_physio_swarm_skill.py`
- Verify: `bio_swarm_pilot/tests/*.py`

**Step 1: Run targeted framework tests**

Run: `python -m unittest tests.test_physio_swarm_protocol tests.test_physio_swarm_kernel tests.test_physio_swarm_demo tests.test_physio_swarm_skill -v`
Expected: PASS

**Step 2: Run full repository tests**

Run: `python -m unittest discover -s . -p "test*.py" -v`
Expected: PASS

**Step 3: Run demo**

Run: `python examples/physio_swarm_demo.py`
Expected: prints a structured artifact trail showing routing, homeostasis shifts, and quarantine.

**Step 4: Commit**

```bash
git add README.md
git commit -m "test: verify physiological swarm framework and skill"
```
