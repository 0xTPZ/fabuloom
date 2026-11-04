from __future__ import annotations

import subprocess
import sys
import unittest

from fabuloom_core.cinematic import CinematicCompatibility
from fabuloom_core.engine import EngineService
from fabuloom_core.process_identity import process_identity, process_is_alive


class ProcessIdentityTests(unittest.TestCase):
    def test_query_is_non_destructive_and_identity_aware(self) -> None:
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
        identity = None
        try:
            identity = process_identity(process.pid)
            self.assertIsNotNone(identity)
            self.assertTrue(process_is_alive(process.pid, identity))
            self.assertIsNone(process.poll(), "querying process state must not terminate the process")

            wrong_identity = dict(identity or {})
            if "creation_time_100ns" in wrong_identity:
                wrong_identity["creation_time_100ns"] = int(wrong_identity["creation_time_100ns"]) + 1
            elif "start_time_ticks" in wrong_identity:
                wrong_identity["start_time_ticks"] = int(wrong_identity["start_time_ticks"]) + 1
            else:
                wrong_identity["image_name"] = "definitely-not-the-running-image"
            self.assertFalse(process_is_alive(process.pid, wrong_identity))
            self.assertIsNone(process.poll(), "identity mismatch must not terminate the process")
            self.assertTrue(CinematicCompatibility._pid_alive(process.pid, identity))
            self.assertTrue(EngineService._pid_alive(process.pid, identity))
            self.assertFalse(CinematicCompatibility.stop_runner_pid(process.pid, wrong_identity))
            self.assertIsNone(process.poll(), "a mismatched explicit cancellation must not terminate the process")
        finally:
            process.terminate()
            process.wait(timeout=5)
        self.assertFalse(process_is_alive(process.pid, identity))


if __name__ == "__main__":
    unittest.main()
