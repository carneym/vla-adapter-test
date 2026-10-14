"""Parse the generated command through LeRobot without connecting any devices."""

import importlib.util
import shlex
import unittest

import test_setup
from so101_setup.commands import teleop_command
from so101_setup.config import configure, import_calibration, load_config


@unittest.skipUnless(importlib.util.find_spec("lerobot"), "Run in the installed project environment")
class LeRobotIntegrationTests(unittest.TestCase):
    def test_generated_command_is_accepted_by_pinned_lerobot(self):
        import draccus
        from lerobot.scripts.lerobot_teleoperate import TeleoperateConfig

        fixture = test_setup.SetupTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        configure(fixture.root, leader_port="/dev/test-leader", follower_port="/dev/test-follower", overhead_camera=0, wrist_camera=1)
        for role in ("leader", "follower"):
            import_calibration(fixture.root, role, fixture.source)
        args = shlex.split(teleop_command(fixture.root, load_config(fixture.root)))[4:]
        config = draccus.parse(config_class=TeleoperateConfig, args=args)
        self.assertEqual(set(config.robot.cameras), {"overhead", "wrist"})
        self.assertEqual(config.fps, 30)
        self.assertEqual(config.robot.max_relative_target, 5.0)
        self.assertFalse(config.robot.disable_torque_on_disconnect)
        self.assertEqual(config.robot.calibration_dir, fixture.root / "calibration/follower")
        self.assertEqual(config.teleop.calibration_dir, fixture.root / "calibration/leader")
        self.assertEqual(config.robot.port, "/dev/test-follower")
        self.assertEqual(config.teleop.port, "/dev/test-leader")
        self.assertTrue(config.robot.use_degrees and config.teleop.use_degrees)
