"""Exercise the installer against real destination files; no user files are touched."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


KIT = Path(__file__).resolve().parents[1]
INSTALLER = KIT / "scripts/install.py"
ASSET = Path(".agents/skills/code-quality-review/SKILL.md")
GUIDANCE = ("AGENTS.md", "CLAUDE.md", "REVIEW.md")
MARKER = b"<!-- code-quality-review-kit:start -->"


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="review-kit-install-")
        self.addCleanup(self.scratch.cleanup)
        self.target = Path(self.scratch.name) / "project with spaces"

    def run_installer(self):
        return subprocess.run(
            [sys.executable, str(INSTALLER), str(self.target)],
            cwd=self.scratch.name, capture_output=True, text=True,
        )

    def write(self, relative, content):
        path = self.target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def snapshot(self):
        return {
            p.relative_to(self.target): (p.read_bytes(), p.stat().st_mtime_ns)
            for p in self.target.rglob("*") if p.is_file() and not p.is_symlink()
        }

    def test_fresh_install_copies_assets_and_all_tool_entrypoints(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        for relative in (
            ASSET, Path(".claude/skills/code-quality-review/SKILL.md"),
            Path(".factory/skills/review-guidelines/SKILL.md"),
            Path(".agents/skills/code-quality-review/scripts/scan_names.py"),
        ):
            self.assertEqual((self.target / relative).read_bytes(), (KIT / "repo" / relative).read_bytes())
        for name in GUIDANCE:
            self.assertIn(MARKER, (self.target / name).read_bytes())

    def test_existing_guidance_and_overrides_are_preserved(self):
        original = b"# Team rules\r\nKeep this exact text.\r\n"
        for name in GUIDANCE:
            self.write(name, original)
        override = self.write(".agents/review-overrides.md", b"- Keep project policy.\n")
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in GUIDANCE:
            self.assertTrue((self.target / name).read_bytes().startswith(original))
        self.assertEqual(override.read_bytes(), b"- Keep project policy.\n")

    def test_repeat_install_leaves_files_untouched(self):
        first = self.run_installer()
        self.assertEqual(first.returncode, 0, first.stderr)
        guidance = self.target / "AGENTS.md"
        guidance.write_bytes(guidance.read_bytes() + b"\nMy additional policy.\n")
        before = self.snapshot()
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(guidance.read_bytes().count(MARKER), 1)

    def test_conflicting_asset_stops_before_any_writes(self):
        self.write(ASSET, b"My customized skill.\n")
        self.write("AGENTS.md", b"Original policy.\n")
        before = self.snapshot()
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(str(ASSET), result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.target / ".claude").exists())

    def test_file_in_place_of_directory_stops_before_any_writes(self):
        self.write(".factory", b"Existing file.\n")
        before = self.snapshot()
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".factory", result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.target / ".agents").exists())

    def test_symlinked_asset_directory_does_not_modify_its_target(self):
        external = Path(self.scratch.name) / "shared skills"
        external.mkdir()
        (external / "keep.txt").write_text("untouched", encoding="utf-8")
        self.target.mkdir()
        (self.target / ".agents").symlink_to(external, target_is_directory=True)
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".agents", result.stderr)
        self.assertEqual(list(external.iterdir()), [external / "keep.txt"])
        self.assertFalse((self.target / "AGENTS.md").exists())

    def test_missing_package_source_fails_without_claiming_installation(self):
        standalone = Path(self.scratch.name) / "standalone/scripts/install.py"
        standalone.parent.mkdir(parents=True)
        shutil.copyfile(INSTALLER, standalone)
        result = subprocess.run(
            [sys.executable, str(standalone), str(self.target)],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("repo", result.stderr)
        self.assertFalse(self.target.exists())

    def test_malformed_markers_reject_install_without_changes(self):
        end = b"<!-- code-quality-review-kit:end -->"
        for index, content in enumerate((MARKER, end + MARKER, (MARKER + end) * 2)):
            with self.subTest(content=content):
                self.target = Path(self.scratch.name) / str(index)
                self.write("AGENTS.md", content)
                before = self.snapshot()
                result = self.run_installer()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("AGENTS.md", result.stderr)
                self.assertEqual(self.snapshot(), before)

    def test_file_symlinks_are_rejected_even_when_broken(self):
        external = Path(self.scratch.name) / "shared-policy.md"
        external.write_bytes(b"External policy.\n")
        for relative, referent in (("AGENTS.md", external), (str(ASSET), external.with_name("missing.md"))):
            with self.subTest(relative=relative):
                self.target = Path(self.scratch.name) / relative.replace("/", "_")
                link = self.target / relative
                link.parent.mkdir(parents=True)
                link.symlink_to(referent)
                result = self.run_installer()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(relative, result.stderr)
                self.assertTrue(link.is_symlink())
                self.assertEqual(external.read_bytes(), b"External policy.\n")
                self.assertFalse((self.target / "REVIEW.md").exists())


if __name__ == "__main__":
    unittest.main()
