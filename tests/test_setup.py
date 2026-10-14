import json
import shlex
import shutil
import tempfile
import unittest
from pathlib import Path

from so101_setup.commands import teleop_command
from so101_setup.config import (
    JOINTS, configure, import_calibration, initialize, load_config, validate_calibration,
)

REPO = Path(__file__).resolve().parents[1]


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="so101 test ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "configs").mkdir()
        shutil.copyfile(REPO / "configs/hardware.example.json", self.root / "configs/hardware.example.json")
        initialize(self.root, "macbook")
        self.data = {
            name: {"id": index, "drive_mode": 0, "homing_offset": 0, "range_min": 100, "range_max": 3900}
            for index, name in enumerate(JOINTS, 1)
        }
        self.source = self.root / "existing.json"
        self.source.write_text(json.dumps(self.data))

    def test_init_preserves_existing_machine_configuration(self):
        configure(self.root, leader_port="/dev/leader")
        before = (self.root / "configs/hardware.local.json").read_bytes()
        _, created = initialize(self.root, "mac-mini")
        self.assertFalse(created)
        self.assertEqual(before, (self.root / "configs/hardware.local.json").read_bytes())
        self.assertEqual(load_config(self.root)["control_host"]["memory_gb"], 8)

    def test_import_preserves_source_and_uses_portable_paths(self):
        original = self.source.read_bytes()
        result = import_calibration(self.root, "leader", self.source)
        self.assertEqual(result.read_bytes(), original)
        self.assertEqual(self.source.read_bytes(), original)
        arm = load_config(self.root)["leader"]
        self.assertEqual(arm["id"], "existing")
        self.assertEqual(arm["calibration_path"], "calibration/leader/existing.json")
        import_calibration(self.root, "leader", self.source)  # idempotent

    def test_import_refuses_overwrite_and_path_traversal(self):
        destination = import_calibration(self.root, "leader", self.source)
        original = destination.read_bytes()
        self.data["gripper"]["homing_offset"] = 10
        self.source.write_text(json.dumps(self.data))
        with self.assertRaisesRegex(ValueError, "overwrite"):
            import_calibration(self.root, "leader", self.source)
        self.assertEqual(destination.read_bytes(), original)
        with self.assertRaises(ValueError):
            import_calibration(self.root, "leader", self.source, "../bad")

    def test_rejects_incomplete_calibration_before_writing(self):
        del self.data["gripper"]
        self.source.write_text(json.dumps(self.data))
        with self.assertRaises(ValueError):
            import_calibration(self.root, "leader", self.source)
        self.assertFalse((self.root / "calibration").exists())

    def test_rejects_invalid_motor_mapping_and_ranges(self):
        self.data["gripper"]["id"] = 1
        with self.assertRaises(ValueError):
            validate_calibration(self.data)
        self.data["gripper"]["id"] = 6
        self.data["gripper"]["range_max"] = 100
        with self.assertRaises(ValueError):
            validate_calibration(self.data)

    def test_bad_configuration_does_not_replace_saved_settings(self):
        before = (self.root / "configs/hardware.local.json").read_bytes()
        with self.assertRaises(ValueError):
            configure(self.root, leader_port="/dev/same", follower_port="/dev/same")
        with self.assertRaises(ValueError):
            configure(self.root, leader_port="/dev/cu.usbmodemTEST", follower_port="/dev/tty.usbmodemTEST")
        with self.assertRaises(ValueError):
            configure(self.root, overhead_camera=0, wrist_camera=0)
        self.assertEqual(before, (self.root / "configs/hardware.local.json").read_bytes())

    def test_command_requires_calibration_and_keeps_shell_arguments_intact(self):
        configure(self.root, leader_port="/dev/leader", follower_port="/dev/follower", overhead_camera=0, wrist_camera=1)
        with self.assertRaisesRegex(ValueError, "calibration"):
            teleop_command(self.root, load_config(self.root))
        for role in ("leader", "follower"):
            import_calibration(self.root, role, self.source)
        args = shlex.split(teleop_command(self.root, load_config(self.root)))
        self.assertIn(f"--robot.calibration_dir={self.root}/calibration/follower", args)
        self.assertIn("--robot.type=so101_follower", args)
        self.assertIn("--teleop.type=so101_leader", args)
        cameras = json.loads(next(arg.split("=", 1)[1] for arg in args if arg.startswith("--robot.cameras=")))
        self.assertEqual(cameras["wrist"]["index_or_path"], 1)
        self.assertIn("--robot.use_degrees=true", args)
        self.assertIn("--teleop.use_degrees=true", args)

    def test_moving_checkout_keeps_calibration_paths_usable(self):
        configure(self.root, leader_port="/dev/leader", follower_port="/dev/follower")
        for role in ("leader", "follower"):
            import_calibration(self.root, role, self.source)
        target = self.root / "different machine"
        shutil.copytree(self.root / "configs", target / "configs")
        shutil.copytree(self.root / "calibration", target / "calibration")
        command = teleop_command(target, load_config(target), without_cameras=True)
        self.assertIn(str(target / "calibration/follower"), command)

    def test_teleop_settings_reject_invalid_limits_and_preserve_explicit_values(self):
        configure(self.root, leader_port="/dev/leader", follower_port="/dev/follower")
        for role in ("leader", "follower"):
            import_calibration(self.root, role, self.source)
        config = load_config(self.root)
        for invalid in (None, True, 0, -1, float("nan"), float("inf"), "5"):
            config["follower"]["max_relative_target"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                teleop_command(self.root, config, without_cameras=True)
        config["follower"].update(max_relative_target=3.0, disable_torque_on_disconnect=True)
        args = shlex.split(teleop_command(self.root, config, without_cameras=True))
        self.assertIn("--robot.max_relative_target=3.0", args)
        self.assertIn("--robot.disable_torque_on_disconnect=true", args)
        config["follower"]["disable_torque_on_disconnect"] = "false"
        with self.assertRaises(ValueError):
            teleop_command(self.root, config, without_cameras=True)

    def test_older_machine_config_gets_observed_teleop_defaults(self):
        configure(self.root, leader_port="/dev/leader", follower_port="/dev/follower")
        for role in ("leader", "follower"):
            import_calibration(self.root, role, self.source)
        config = load_config(self.root)
        config["follower"].pop("max_relative_target")
        config["follower"].pop("disable_torque_on_disconnect")
        args = shlex.split(teleop_command(self.root, config, without_cameras=True))
        self.assertIn("--robot.max_relative_target=5.0", args)
        self.assertIn("--robot.disable_torque_on_disconnect=false", args)


if __name__ == "__main__":
    unittest.main()
