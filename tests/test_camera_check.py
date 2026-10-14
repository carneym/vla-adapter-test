import contextlib
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np

from so101_setup.camera_check import camera_check


class CameraCheckTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.settings = {"cameras": [
            {"name": name, "device": index, "capture_width": 640, "capture_height": 480, "fps": 30}
            for index, name in enumerate(("overhead", "wrist"))
        ]}
        config = patch("so101_setup.camera_check.load_config", return_value=self.settings)
        config.start()
        self.addCleanup(config.stop)
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def report(self):
        return json.loads(next(self.root.glob(".cache/camera-check/*/report.json")).read_text())

    def test_invalid_selection_fails_before_camera_construction(self):
        with patch("lerobot.cameras.opencv.OpenCVCamera") as factory:
            for invalid in (None, -1, True, 0):
                self.settings["cameras"][1]["device"] = invalid
                with self.subTest(device=invalid), self.assertRaises(ValueError):
                    camera_check(self.root)
            factory.assert_not_called()
        self.assertFalse((self.root / ".cache").exists())

    def test_second_camera_failure_releases_first_and_records_failure(self):
        first = Mock(is_connected=True)
        second = Mock(is_connected=False, thread=None)
        second.connect.side_effect = RuntimeError("Unsupported camera mode")
        with patch("lerobot.cameras.opencv.OpenCVCamera", side_effect=[first, second]):
            with self.assertRaisesRegex(RuntimeError, "Unsupported camera mode"):
                camera_check(self.root)
        first.disconnect.assert_called_once()
        second.disconnect.assert_not_called()
        report = self.report()
        self.assertFalse(report["capture_check_passed"])
        self.assertIn("Unsupported camera mode", report["error"])

    def test_repeated_cached_frame_does_not_count_as_a_live_stream(self):
        # A fake clock makes this test deterministic; the camera never publishes another timestamp.
        clock = [100.0]

        def advance(seconds):
            clock[0] += seconds

        cameras = [Mock(
            is_connected=True, frame_lock=threading.Lock(),
            latest_timestamp=100.0, latest_frame=np.zeros((480, 640, 3), dtype=np.uint8),
        ) for _ in range(2)]
        with (
            patch("lerobot.cameras.opencv.OpenCVCamera", side_effect=cameras),
            patch("so101_setup.camera_check.time.perf_counter", side_effect=lambda: clock[0]),
            patch("so101_setup.camera_check.time.sleep", side_effect=advance),
        ):
            report = camera_check(self.root, duration=0.1)
        self.assertTrue(report["completed"])
        self.assertFalse(report["capture_check_passed"])
        for summary in report["cameras"].values():
            self.assertEqual(summary["fresh_frames"], 1)
            self.assertEqual(summary["measured_fps"], 0)
        for camera in cameras:
            camera.disconnect.assert_called_once()


if __name__ == "__main__":
    unittest.main()
