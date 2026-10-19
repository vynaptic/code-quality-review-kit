"""The sample command must detect missing expected scanner candidates."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


KIT = Path(__file__).resolve().parents[1]


class JavaSampleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(KIT / "repo", self.root / "repo", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(KIT / "examples/java-sample", self.root / "examples/java-sample",
                        ignore=shutil.ignore_patterns("target"))

    def run_sample(self, env=None):
        return subprocess.run(["bash", str(self.root / "examples/java-sample/try.sh")],
                              env=env, capture_output=True, text=True)

    def external_git_config(self):
        hooks = self.root / "external-hooks"
        hooks.mkdir()
        hook = hooks / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 86\n")
        hook.chmod(0o755)
        config = self.root / "external.gitconfig"
        for key, value in (("commit.gpgsign", "true"),
                           ("gpg.program", str(self.root / "unavailable-gpg")),
                           ("core.hooksPath", str(hooks))):
            subprocess.run(["git", "config", "--file", str(config), key, value], check=True)
        return dict(os.environ, GIT_CONFIG_GLOBAL=str(config), GIT_CONFIG_SYSTEM=str(config),
                    GIT_CONFIG_NOSYSTEM="0")

    def test_sample_checks_violations_and_accepted_baseline_names(self):
        result = self.run_sample()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Scanner assertions passed", result.stdout)

    def test_sample_fails_if_expected_vague_verbs_disappear(self):
        for path in (self.root / "examples/java-sample/change").rglob("*.java"):
            path.write_text(path.read_text().replace("processRefund", "issueRefund"))
        result = self.run_sample()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Missing expected scanner candidates", result.stderr)

    def test_sample_ignores_external_signing_and_failing_hooks(self):
        result = self.run_sample(env=self.external_git_config())
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Scanner assertions passed", result.stdout)

    def test_profiler_fixtures_ignore_external_signing_and_failing_hooks(self):
        result = subprocess.run([sys.executable, str(KIT / "tests/test_scan_conventions.py")],
                                env=self.external_git_config(), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
