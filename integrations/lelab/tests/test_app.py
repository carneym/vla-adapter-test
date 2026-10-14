"""Run with the LeLab runtime; no serial ports or physical cameras are opened."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from so101_setup.config import JOINTS, configure, import_calibration, initialize, load_config
from so101_setup.lelab_app import configure_paths, prepare, reuse_motor_calibration


class LeLabIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name).resolve()
        (cls.root / "configs").mkdir()
        (cls.root / "configs/hardware.example.json").write_bytes((REPO / "configs/hardware.example.json").read_bytes())
        initialize(cls.root, "macbook")
        configure(cls.root, leader_port="/dev/test-leader", follower_port="/dev/test-follower",
                  overhead_camera=0, wrist_camera=1)
        for role in ("leader", "follower"):
            source = cls.root / f"{role}.json"
            source.write_text(json.dumps({name: {"id": i, "drive_mode": 0, "homing_offset": 0,
                                                "range_min": 100, "range_max": 3900}
                                          for i, name in enumerate(JOINTS, 1)}))
            import_calibration(cls.root, role, source)
        cls.profile = prepare(cls.root)
        cls.hardware = load_config(cls.root)

    def request(self, **overrides):
        from lelab.record import RecordingRequest

        values = {k: self.profile[k] for k in ("leader_port", "follower_port", "leader_config", "follower_config")}
        values.update(dataset_repo_id="local/test", single_task="Raise your arm.",
                      num_episodes=2, episode_time_s=15, reset_time_s=30,
                      cameras={c["name"]: c for c in self.profile["cameras"]})
        values.update(overrides)
        return RecordingRequest(**values)

    def test_generated_configs_preserve_working_settings(self):
        from lelab import record, teleoperate

        cfg = record.create_record_config(self.request())
        self.assertEqual(cfg.robot.max_relative_target, 5.0)
        self.assertFalse(cfg.robot.disable_torque_on_disconnect)
        self.assertTrue(cfg.robot.use_degrees and cfg.teleop.use_degrees)
        self.assertEqual(cfg.robot.calibration_dir, self.root / "calibration/follower")
        self.assertEqual(cfg.teleop.calibration_dir, self.root / "calibration/leader")
        self.assertEqual({c.warmup_s for c in cfg.robot.cameras.values()}, {5})
        self.assertEqual(cfg.dataset.rgb_encoder.vcodec, "h264")
        self.assertEqual(cfg.dataset.encoder_threads, 2)
        self.assertEqual(cfg.dataset.encoder_queue_maxsize, 30)
        self.assertEqual(cfg.dataset.root, self.root / "data/lelab/local/test")
        self.assertFalse(cfg.dataset.push_to_hub)
        self.assertEqual(cfg.dataset.reset_time_s, 30)
        teleop_cfg = teleoperate.SO101FollowerConfig(port=self.profile["follower_port"], id="follower")
        self.assertEqual(teleop_cfg.max_relative_target, 5.0)
        self.assertFalse(teleop_cfg.disable_torque_on_disconnect)
        with self.assertRaisesRegex(ValueError, "profile"):
            record.create_record_config(self.request(follower_port=self.profile["leader_port"]))

    def test_existing_calibration_and_gui_camera_changes_are_preserved(self):
        from lelab.utils import config as paths

        before = {p: p.read_bytes() for p in (self.root / "calibration").rglob("*.json")}
        edited = [dict(c, rotation=180) for c in self.profile["cameras"]]
        paths.save_robot_record("SO101", {"cameras": edited})
        configure_paths(self.root, self.hardware)
        self.assertEqual(paths.get_robot_record("SO101")["cameras"], edited)
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        paths.save_robot_record("SO101", {"cameras": self.profile["cameras"]})

    def test_calibration_verification_does_not_write_motor_registers(self):
        bus = MagicMock()
        saved = {"motor": "calibration"}
        bus.read_calibration.return_value = saved.copy()
        reuse_motor_calibration(bus)
        bus.write_calibration(saved)
        self.assertEqual(bus.calibration, saved)
        bus.write.assert_not_called()
        bus.read_calibration.return_value = {"motor": "different"}
        with self.assertRaisesRegex(ValueError, "differs"):
            bus.write_calibration(saved)
        bus.write.assert_not_called()

    def test_device_factories_use_settings_without_connecting(self):
        from lelab import record, teleoperate
        from lerobot.robots import make_robot_from_config
        from lerobot.teleoperators import make_teleoperator_from_config

        cfg = record.create_record_config(self.request())
        with patch("serial.Serial.open", side_effect=AssertionError("Must not open serial")):
            follower = make_robot_from_config(cfg.robot)
            leader = make_teleoperator_from_config(cfg.teleop)
            ui_follower = teleoperate.SO101Follower(cfg.robot)
        self.assertFalse(follower.is_connected)
        self.assertFalse(leader.is_connected)
        self.assertEqual(ui_follower.config.max_relative_target, 5.0)
        self.assertEqual(follower.bus.write_calibration.__name__, "verify")
        self.assertEqual(leader.bus.write_calibration.__name__, "verify")

    def test_record_reset_redo_loop_saves_real_dataset_with_fake_hardware(self):
        import av
        import numpy as np
        from lelab import record

        cfg = record.create_record_config(self.request(dataset_repo_id="local/loop-test"))
        robot = MagicMock(name="fake follower")
        robot.name = "so101_follower"
        robot.cameras = {name: MagicMock() for name in ("overhead", "wrist")}
        robot.action_features = {f"{name}.pos": float for name in JOINTS}
        robot.observation_features = {**robot.action_features, "overhead": (480, 640, 3), "wrist": (480, 640, 3)}
        leader = MagicMock(name="fake leader")
        events = {"stop_recording": False, "exit_early": False, "rerecord_episode": False}
        phases = []

        def fake_loop(**kwargs):
            dataset = kwargs.get("dataset")
            phases.append("record" if dataset is not None else "reset")
            if dataset is None:
                self.assertEqual(kwargs["control_time_s"], 30)
                return
            for _ in range(6):
                dataset.add_frame({"observation.state": np.zeros(6, dtype=np.float32),
                                   "action": np.zeros(6, dtype=np.float32),
                                   "observation.images.overhead": np.zeros((480, 640, 3), dtype=np.uint8),
                                   "observation.images.wrist": np.zeros((480, 640, 3), dtype=np.uint8),
                                   "task": "Raise your arm."})
            if phases.count("record") == 1:
                record.handle_rerecord_episode()
            else:
                record.handle_exit_early()

        with (patch("lerobot.robots.make_robot_from_config", return_value=robot),
              patch("lerobot.teleoperators.make_teleoperator_from_config", return_value=leader),
              patch("lerobot.scripts.lerobot_record.record_loop", side_effect=fake_loop),
              patch.object(record, "recording_active", True),
              patch.object(record, "recording_events", events)):
            dataset = record.record_with_web_events(cfg, events)
        self.assertEqual(phases, ["reset", "record", "reset", "record", "reset", "record"])
        self.assertEqual(dataset.num_episodes, 2)
        self.assertEqual(dataset.num_frames, 12)
        for device in (robot, leader):
            device.bus.connect.assert_called_once()
            device.disconnect.assert_called_once()
        videos = list(cfg.dataset.root.rglob("*.mp4"))
        self.assertEqual(len(videos), 2)
        for path in videos:
            with av.open(str(path)) as video:
                self.assertEqual(sum(1 for _ in video.decode(video=0)), 12)


if __name__ == "__main__":
    unittest.main()
