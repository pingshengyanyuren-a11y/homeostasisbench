from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = REPO_ROOT / "skills" / "physio-swarm-protocol" / "SKILL.md"


class PhysiologicalSkillTest(unittest.TestCase):
    def test_skill_file_exists(self) -> None:
        self.assertTrue(SKILL_PATH.exists())

    def test_skill_mentions_core_organs_and_runtime(self) -> None:
        content = SKILL_PATH.read_text(encoding="utf-8")

        self.assertIn("endocrine", content)
        self.assertIn("metabolic", content)
        self.assertIn("nervous", content)
        self.assertIn("immune", content)
        self.assertIn("examples/physio_swarm_demo.py", content)
        self.assertIn("physio_swarm/kernel.py", content)


if __name__ == "__main__":
    unittest.main()
