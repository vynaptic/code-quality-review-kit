"""Behavioral regressions for naming candidates, Git scope and advisory evidence."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "repo/.agents/skills/code-quality-review/scripts/scan_names.py"
SPEC = importlib.util.spec_from_file_location("scan_names", SCRIPT)
scanner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scanner
SPEC.loader.exec_module(scanner)


class NamingRulesTests(unittest.TestCase):
    def scan(self, source, path="Invoice.java"):
        lines = [(path, number, line, True) for number, line in enumerate(source.splitlines(), 1)]
        return scanner.scan(lines, scanner.load_rules(), include_tests=False)

    def test_command_query_and_use_case_types_are_valid_exceptions(self):
        for name in ("CreateInvoiceCommand", "GetInvoiceQuery", "CreateInvoiceUseCase"):
            with self.subTest(name=name):
                self.assertEqual(self.scan("public class " + name + " {}"), [])

    def test_verb_named_type_without_an_allowed_suffix_is_a_candidate(self):
        findings = self.scan("public class CreateInvoice {}")
        self.assertEqual([(f.identifier, f.rule, f.confidence) for f in findings],
                         [("CreateInvoice", "NAME-T5", "medium")])

    def test_methods_retain_real_contract_violations_and_valid_predicates(self):
        findings = self.scan("public class Invoice {\n"
                             "  public void getTotal() {}\n"
                             "  public boolean isPaid() { return true; }\n"
                             "  public void sendReminder(boolean urgent) {}\n}")
        self.assertEqual([(f.line, f.identifier, f.rule, f.confidence) for f in findings],
                         [(2, "getTotal", "NAME-M2", "high"),
                          (4, "sendReminder", "NAME-M5", "high")])

    def test_diff_parser_preserves_line_numbers_and_does_not_scan_context(self):
        patch = ("diff --git a/Invoice.java b/Invoice.java\n--- a/Invoice.java\n+++ b/Invoice.java\n"
                 "@@ -8,2 +8,2 @@\n public class OldHelper {}\n-public class Invoice {}\n"
                 "+public class NewHelper {}\n")
        findings = scanner.scan(scanner.iter_diff(patch), scanner.load_rules(), False)
        self.assertEqual([(f.file, f.line, f.identifier) for f in findings],
                         [("Invoice.java", 9, "NewHelper")])

    def test_test_and_generated_paths_remain_excluded(self):
        for path in ("src/test/java/InvoiceHelper.java", "target/InvoiceHelper.java"):
            with self.subTest(path=path):
                self.assertEqual(self.scan("public class InvoiceHelper {}", path), [])


@unittest.skipUnless(shutil.which("git"), "Git is required for integration tests")
class GitScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="cqr-naming-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_TERMINAL_PROMPT="0", PYTHONDONTWRITEBYTECODE="1")
        self.git("init", "-q")
        self.git("symbolic-ref", "HEAD", "refs/heads/main")
        self.git("config", "user.name", "Naming tests")
        self.git("config", "user.email", "naming@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.quotepath", "true")
        self.write("Invoice.java", "public class Invoice {}\n")
        self.commit()

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.root, env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def write(self, path, content):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def commit(self):
        self.git("add", "--all")
        self.git("commit", "-q", "-m", "test baseline")

    def cli(self, *args, cwd=None, input=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args, "--format", "json"],
                              cwd=cwd or self.root, env=self.env, input=input,
                              capture_output=True, text=True)

    def assert_error(self, result):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("error:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_invalid_base_is_an_error_instead_of_a_clean_scan(self):
        self.write("Invoice.java", "public class InvoiceHelper {}\n")
        result = self.cli("--base", "missing-ref", "--fail-on", "high")
        self.assert_error(result)
        self.assertIn("missing-ref", result.stderr)

    def test_git_diff_failure_is_reported_for_branch_and_staged_modes(self):
        self.write("Invoice.java", "public class InvoiceHelper {}\n")
        self.git("add", "Invoice.java")
        self.git("config", "diff.algorithm", "not-an-algorithm")
        for args in (("--base", "main"), ("--staged",)):
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assert_error(result)
                self.assertIn("algorithm", result.stderr)

    def test_invalid_evidence_ref_is_an_error_in_explicit_mode(self):
        self.assert_error(self.cli("--files", "Invoice.java", "--repo-ref", "missing-ref"))

    def test_empty_explicit_refs_are_errors_instead_of_defaults(self):
        for args in (("--base", ""), ("--files", "Invoice.java", "--repo-ref", "")):
            with self.subTest(args=args):
                self.assert_error(self.cli(*args))

    def test_valid_empty_diff_passes_branch_and_staged_modes(self):
        for args in (("--base", "main"), ("--staged",), ()):
            with self.subTest(args=args):
                result = self.cli(*args, "--fail-on", "low")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)["findings"], [])

    def test_unstaged_and_staged_scopes_are_distinct(self):
        self.write("Invoice.java", "public class InvoiceHelper {}\n")
        unstaged = self.cli("--staged", "--fail-on", "high")
        self.assertEqual(unstaged.returncode, 0, unstaged.stderr)
        self.assertEqual(json.loads(unstaged.stdout)["findings"], [])
        self.git("add", "Invoice.java")
        self.write("Invoice.java", "public class Invoice {}\n")
        staged = self.cli("--staged", "--fail-on", "high")
        self.assertEqual(staged.returncode, 1, staged.stderr)
        self.assertEqual(json.loads(staged.stdout)["findings"][0]["identifier"], "InvoiceHelper")

    def test_quoted_unicode_and_newline_paths_are_scanned_in_all_input_modes(self):
        paths = ("café/Invoice.java", 'quote"dir/Invoice.java', "line\nbreak/Invoice.java",
                 "tab\tdir/Invoice.java", "back\\slash/Invoice.java", "space dir/Invoice.java")
        for path in paths:
            self.write(path, "public class Invoice {}\n")
        self.commit()
        for path in paths:
            self.write(path, "public class InvoiceHelper {}\n")
        self.git("add", "--all")
        patch = self.git("diff", "--cached")
        self.write("change.patch", patch)
        for args in (("--base", "HEAD"), ("--staged",), ("--diff-file", "change.patch"),
                     ("--files", *paths)):
            with self.subTest(args=args):
                result = self.cli(*args, "--fail-on", "high")
                self.assertEqual(result.returncode, 1, result.stderr)
                findings = json.loads(result.stdout)["findings"]
                self.assertEqual({f["file"] for f in findings}, set(paths))
                self.assertTrue(all(f["identifier"] == "InvoiceHelper" and f["line"] == 1
                                    for f in findings))

    def test_untracked_paths_use_nul_separators(self):
        paths = ("café/Invoice.java", 'quote"dir/Invoice.java', "line\nbreak/Invoice.java")
        for path in paths:
            self.write(path, "public class InvoiceHelper {}\n")
        result = self.cli("--base", "main", "--fail-on", "high")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual({f["file"] for f in json.loads(result.stdout)["findings"]}, set(paths))
        excluded = self.cli("--base", "main", "--no-untracked", "--fail-on", "high")
        self.assertEqual(excluded.returncode, 0, excluded.stderr)
        self.assertEqual(json.loads(excluded.stdout)["findings"], [])

    def test_missing_explicit_file_is_an_error(self):
        self.assert_error(self.cli("--files", "missing.java"))

    def test_explicit_files_and_stdin_diff_work_outside_git(self):
        with tempfile.TemporaryDirectory(prefix="cqr-naming-files-") as outside:
            path = Path(outside) / "Invoice.java"
            path.write_text("public class InvoiceHelper {}\n", encoding="utf-8")
            explicit = self.cli("--files", str(path), "--fail-on", "high", cwd=outside)
            patch = "--- /dev/null\n+++ b/Invoice.java\n@@ -0,0 +1 @@\n+public class InvoiceHelper {}\n"
            from_stdin = self.cli("--diff-file", "-", "--fail-on", "high", cwd=outside, input=patch)
            for result in (explicit, from_stdin):
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(json.loads(result.stdout)["findings"][0]["identifier"], "InvoiceHelper")

    def test_commented_and_quoted_type_examples_do_not_establish_evidence(self):
        self.write("Invoice.java", "// class InvoiceHelper {}\n// class PaymentHelper {}\n"
                                  "// class AccountHelper {}\npublic class Invoice {\n"
                                  '  String example = "class AnotherHelper {}";\n}\n')
        self.commit()
        self.write("RefundHelper.java", "public class RefundHelper {}\n")
        result = self.cli("--base", "HEAD", "--fail-on", "high")
        self.assertEqual(result.returncode, 1, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["repo_conventions"], {})
        self.assertEqual(payload["findings"][0]["confidence"], "high")

    def test_counts_are_advisory_across_modules_verbs_and_interfaces(self):
        for name in ("Invoice", "Payment", "Account"):
            self.write("legacy/" + name + ".java", "public class " + name + "Helper {\n"
                       "  public void process" + name + "() {}\n}\n"
                       "interface I" + name + " {}\n")
        self.commit()
        self.write("current/Refund.java", "public class RefundHelper {\n"
                   "  public void processRefund() {}\n}\ninterface IRefund {}\n")
        result = self.cli("--base", "HEAD", "--fail-on", "high")
        ignored = self.cli("--base", "HEAD", "--ignore-repo-conventions", "--fail-on", "high")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(ignored.returncode, 1, ignored.stderr)
        evidence = json.loads(result.stdout)
        without = json.loads(ignored.stdout)
        self.assertEqual(evidence["repo_conventions"], {"suffix:Helper": 3, "verb:process": 3, "iprefix": 3})
        self.assertEqual(without["repo_conventions"], {})
        expected = [("RefundHelper", "NAME-T2", "high"), ("processRefund", "NAME-M3", "medium"),
                    ("IRefund", "NAME-T3", "medium")]
        for payload in (evidence, without):
            self.assertEqual([(f["identifier"], f["rule"], f["confidence"]) for f in payload["findings"]], expected)

    def test_advisory_counts_handle_colons_newlines_and_unicode_in_paths(self):
        for path in ("café/Invoice.java", "with:colon/Payment.java", "line\nbreak/Account.java"):
            self.write(path, "public class ExistingHelper {}\n")
        self.commit()
        result = self.cli("--base", "HEAD")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["repo_conventions"], {"suffix:Helper": 3})


if __name__ == "__main__":
    unittest.main()
