"""Exercise the profiler CLI against real, disposable Git repositories."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "repo/.agents/skills/code-quality-review/scripts/scan_conventions.py"
BASE_SOURCE = """package com.acme.billing;
import org.slf4j.Logger;
public class InvoiceService {
    public String fetchInvoice() { return "invoice"; }
}
"""


class ConventionSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT="0")
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", os.devnull)
        self.write("pom.xml", "<project><java.version>17</java.version></project>")
        self.write("src/InvoiceService.java", BASE_SOURCE)
        self.write("application.properties", "spring.jpa.open-in-view=false")
        self.write(".editorconfig", "root = true")
        self.git("add", ".")
        self.git("commit", "-qm", "baseline")
        self.commit = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, env=self.env, check=True,
                              capture_output=True, text=True).stdout

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")

    def run_profile(self, *args, root=None):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root or self.root),
                               "--format", "json", *args], env=self.env, capture_output=True, text=True)

    def profile(self, *args, root=None):
        result = self.run_profile(*args, root=root)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_commit_ignores_staged_unstaged_untracked_and_deleted_inputs(self):
        self.write("pom.xml", "<project><java.version>21</java.version></project>")
        self.write("src/InvoiceService.java", BASE_SOURCE.replace("org.slf4j", "java.util.logging"))
        self.git("add", ".")
        self.write("application.properties", "spring.jpa.open-in-view=true")
        self.write("src/Untracked.java", "public class Untracked {}")
        (self.root / ".editorconfig").unlink()
        result = self.profile("--ref", self.commit)
        self.assertEqual(result["java_baseline"], {"Java 17": 1})
        self.assertEqual(result["log_facades"], {"SLF4J": 1})
        self.assertEqual(result["app_config"], {"spring.jpa.open-in-view": "false", "open-in-view": "false"})
        self.assertEqual(result["configs"]["editorconfig"], [".editorconfig"])
        self.assertEqual(result["main_files"], 1)
        self.assertEqual(result["meta"]["commit"], self.commit)
        self.assertEqual(result["meta"]["ref"], self.commit)
        self.assertEqual(result["meta"]["snapshot"], "commit")

    def test_current_tree_default_reads_local_edits(self):
        self.write("pom.xml", "<project><java.version>21</java.version></project>")
        result = self.profile()
        self.assertEqual(result["java_baseline"], {"Java 21": 1})
        self.assertEqual(result["meta"]["snapshot"], "current-tree")
        self.assertIsNone(result["meta"]["commit"])

    def test_current_tree_git_error_does_not_silently_walk(self):
        (self.root / ".git/index").write_bytes(b"broken index")
        result = self.run_profile()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("git ls-files failed", result.stderr)

    def test_ref_is_the_supplied_commit_not_its_merge_base(self):
        self.write("pom.xml", "<project><java.version>21</java.version></project>")
        self.git("add", ".")
        self.git("commit", "-qm", "future baseline")
        future = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "--detach", self.commit)
        result = self.profile("--ref", future)
        self.assertEqual(result["java_baseline"], {"Java 21": 1})
        self.assertEqual(result["meta"]["commit"], future)

    def test_deleted_unicode_module_is_scoped_to_the_requested_commit(self):
        module = "services/facturación 東京"
        self.write(module + "/src/Résumé.java", BASE_SOURCE.replace("billing", "module"))
        self.write(module + "/pom.xml", "<project><java.version>17</java.version></project>")
        self.git("add", ".")
        self.git("commit", "-qm", "module")
        shutil.rmtree(self.root / "services")
        result = self.profile("--ref", "HEAD", root=self.root / module)
        self.assertEqual(result["main_files"], 1)
        self.assertEqual(result["build_files"], ["pom.xml"])
        self.assertEqual(result["packages_main"], {"com.acme.module": 1})

    def test_invalid_ref_fails_without_a_partial_profile(self):
        for ref in ("does-not-exist", "--help"):
            with self.subTest(ref=ref):
                result = self.run_profile("--ref=" + ref)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("error:", result.stderr)

    def test_empty_ref_is_rejected_instead_of_using_head(self):
        result = self.run_profile("--ref", "")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("--ref must not be empty", result.stderr)

    def test_snapshot_outside_git_or_missing_module_fails(self):
        with tempfile.TemporaryDirectory() as outside:
            for root in (Path(outside), self.root / "missing"):
                with self.subTest(root=root):
                    result = self.run_profile("--ref", "HEAD", root=root)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, "")

    def test_unreadable_git_blob_fails_without_a_partial_profile(self):
        oid = self.git("rev-parse", "HEAD:src/InvoiceService.java").strip()
        (self.root / ".git/objects" / oid[:2] / oid[2:]).unlink()
        result = self.run_profile("--ref", "HEAD")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("error:", result.stderr)

    def test_sample_limit_reports_omissions_and_keeps_later_build_metadata(self):
        for i in range(6):
            self.write("src/Extra%d.java" % i, BASE_SOURCE)
        self.write("zz/pom.xml", "<project><java.version>21</java.version></project>")
        self.git("add", ".")
        self.git("commit", "-qm", "more files")
        result = self.profile("--ref", "HEAD", "--max-files", "1")
        self.assertEqual(result["files_scanned"], 1)
        self.assertEqual(result["files_skipped"], 6)
        self.assertTrue(result["meta"]["sample_incomplete"])
        self.assertIn("zz/pom.xml", result["build_files"])


if __name__ == "__main__":
    unittest.main()
