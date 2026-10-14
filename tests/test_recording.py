import contextlib
import io
import sys
import unittest
from unittest.mock import patch

import test_setup
from so101_setup.config import configure, import_calibration, load_config
from so101_setup.recording import record_test


class RecordingLaunchTests(unittest.TestCase):
    def setUp(self):
        fixture = test_setup.SetupTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.root = fixture.root
        configure(self.root, leader_port="/dev/leader", follower_port="/dev/follower", overhead_camera=0, wrist_camera=1)
        for role in ("leader", "follower"):
            import_calibration(self.root, role, fixture.source)
        self.config = load_config(self.root)

    def test_countdown_finishes_before_foreground_launch_and_preserves_arguments(self):
        events = []
        with (
            contextlib.redirect_stdout(io.StringIO()),
            patch("so101_setup.recording.time.sleep", side_effect=lambda _: events.append("wait")),
            patch("so101_setup.recording.os.execv", side_effect=lambda *_: events.append("launch")) as execute,
        ):
            record_test(self.root, self.config, setup_seconds=15)
        self.assertEqual(events, ["wait"] * 15 + ["launch"])
        executable, args = execute.call_args.args
        self.assertEqual(executable, sys.executable)
        self.assertEqual(args[:3], [sys.executable, "-m", "lerobot.scripts.lerobot_record"])
        self.assertIn("--robot.max_relative_target=5.0", args)
        self.assertIn("--dataset.push_to_hub=false", args)
        self.assertIn("--dataset.episode_time_s=15", args)
        self.assertIn(f"--robot.calibration_dir={self.root}/calibration/follower", args)
        self.assertFalse((self.root / "data").exists())  # LeRobot must create the new root itself.

    def test_cancel_during_setup_never_launches(self):
        output = io.StringIO()
        with (contextlib.redirect_stdout(output),
              patch("so101_setup.recording.time.sleep", side_effect=KeyboardInterrupt),
              patch("so101_setup.recording.os.execv") as execute):
            record_test(self.root, self.config)
        execute.assert_not_called()
        self.assertIn("No devices were opened", output.getvalue())
        self.assertFalse((self.root / "data").exists())

    def test_dry_run_never_waits_or_launches_and_retries_have_fresh_names(self):
        destinations = []
        with patch("so101_setup.recording.time.sleep") as sleep, patch("so101_setup.recording.os.execv") as execute:
            for _ in range(2):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    record_test(self.root, self.config, dry_run=True)
                destinations.append(output.getvalue().splitlines()[0])
        self.assertNotEqual(*destinations)
        sleep.assert_not_called()
        execute.assert_not_called()
        self.assertFalse((self.root / "data").exists())

    def test_invalid_setup_or_hardware_settings_block_launch(self):
        with patch("so101_setup.recording.os.execv") as execute:
            with self.assertRaises(ValueError):
                record_test(self.root, self.config, setup_seconds=-1)
            self.config["follower"]["port"] = None
            with self.assertRaises(ValueError):
                record_test(self.root, self.config)
        execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
