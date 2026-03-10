from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from bio_swarm_pilot import simulation


class CliTest(unittest.TestCase):
    def test_main_accepts_output_dir_and_generates_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            exit_code = simulation.main(
                [
                    "--steps",
                    "20",
                    "--replicates",
                    "1",
                    "--output-dir",
                    tmp_dir,
                    "--seed",
                    "42",
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertTrue((Path(tmp_dir) / "aggregate_summary.csv").exists())


if __name__ == "__main__":
    unittest.main()
