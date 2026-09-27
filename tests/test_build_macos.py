"""Privremeno zauzet macOS resurs: ograničen ponovni pokušaj, bez skrivanja drugih grešaka."""

import contextlib
import io
import subprocess
import unittest
from pathlib import Path
from unittest import mock

from tools import build_macos


class DmgRetryTest(unittest.TestCase):
    def setUp(self):
        self.root = Path("test-stage")
        self.run = self.enterContext(mock.patch.object(build_macos, "run"))
        self.sleep = self.enterContext(mock.patch.object(build_macos.time, "sleep"))
        self.output = self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.success = subprocess.CompletedProcess(["hdiutil"], 0, "created: test.dmg\n", "")

    def failure(self, message):
        return subprocess.CalledProcessError(1, ["hdiutil"], stderr=message)

    def test_success_does_not_retry(self):
        self.run.return_value = self.success
        build_macos.create_dmg(self.root)
        self.run.assert_called_once()
        self.sleep.assert_not_called()
        command = self.run.call_args.args[0]
        self.assertEqual(command[:2], ["hdiutil", "create"])
        self.assertEqual(command[command.index("-srcfolder") + 1], str(self.root))
        self.assertEqual(command[-1], str(build_macos.DMG))
        self.assertIn("-ov", command)
        self.assertEqual(self.run.call_args.kwargs["env"]["LC_ALL"], "C")
        self.assertIn("created: test.dmg", self.output.getvalue())

    def test_busy_then_success_retries_and_preserves_diagnostics(self):
        busy = self.failure("hdiutil: create failed - Resource busy\n")
        self.run.side_effect = [busy, self.success]
        build_macos.create_dmg(self.root)
        self.assertEqual(self.run.call_count, 2)
        self.sleep.assert_called_once_with(2)
        self.assertIn(busy.stderr, self.output.getvalue())
        self.assertIn("created: test.dmg", self.output.getvalue())

    def test_busy_stops_after_three_attempts(self):
        busy = self.failure("hdiutil: create failed - Resource busy\n")
        self.run.side_effect = busy
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            build_macos.create_dmg(self.root)
        self.assertIs(caught.exception, busy)
        self.assertEqual(self.run.call_count, 3)
        self.assertEqual(self.sleep.call_args_list, [mock.call(2), mock.call(4)])

    def test_other_error_fails_immediately(self):
        failed = self.failure("hdiutil: create failed - No space left on device\n")
        self.run.side_effect = failed
        with self.assertRaises(subprocess.CalledProcessError) as caught:
            build_macos.create_dmg(self.root)
        self.assertIs(caught.exception, failed)
        self.run.assert_called_once()
        self.sleep.assert_not_called()
        self.assertIn(failed.stderr, self.output.getvalue())

    def test_missing_tool_fails_immediately(self):
        self.run.side_effect = FileNotFoundError("hdiutil")
        with self.assertRaises(FileNotFoundError):
            build_macos.create_dmg(self.root)
        self.run.assert_called_once()
        self.sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
