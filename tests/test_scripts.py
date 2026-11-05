import contextlib
import io
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import generate_skills  # noqa: E402
import sync_workspace_deps  # noqa: E402
import update_skills  # noqa: E402


class SkillToolkitsTest(unittest.TestCase):
    def test_skill_toolkits_is_a_tuple(self):
        # A bare string iterates per-character in `for toolkit in toolkits`.
        self.assertIsInstance(generate_skills.SKILL_TOOLKITS, tuple)
        self.assertTrue(generate_skills.SKILL_TOOLKITS)


class SelectedToolkitsTest(unittest.TestCase):
    def test_default_when_env_unset(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(generate_skills._selected_toolkits(), generate_skills.SKILL_TOOLKITS)

    def test_env_override_parsed(self):
        with patch.dict("os.environ", {"DLTHUB_SKILL_TOOLKITS": "init, rest-api-pipeline ,, transformations"}):
            self.assertEqual(
                generate_skills._selected_toolkits(),
                ("init", "rest-api-pipeline", "transformations"),
            )


class PinFullRefTest(unittest.TestCase):
    def test_rewrites_full_ref_line(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write('WORKBENCH_REF_SHORT = "old1234"\nWORKBENCH_REF = "old1234old1234"\n')
            script = Path(fh.name)
        self.addCleanup(script.unlink)
        new_full = "a" * 40
        with patch.object(generate_skills, "SCRIPT_PATH", script), contextlib.redirect_stdout(io.StringIO()):
            generate_skills._pin_full_ref(new_full)
        content = script.read_text(encoding="utf-8")
        self.assertIn(f'WORKBENCH_REF = "{new_full}"', content)
        self.assertIn('WORKBENCH_REF_SHORT = "old1234"', content)  # short line untouched


class CopyToolkitSkillsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.skills_dir = self.root / "out"
        self.skills_dir.mkdir()
        self.workbench = self.root / "wb"

    def tearDown(self):
        self._tmp.cleanup()

    def _make(self, toolkit, skill):
        d = self.workbench / "workbench" / toolkit / "skills" / skill
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text(f"# {skill}\n", encoding="utf-8")

    def test_copies_selected_toolkit_skills(self):
        self._make("init", "router")
        self._make("rest-api-pipeline", "find-source")
        with patch.object(generate_skills, "SKILLS_DIR", self.skills_dir):
            collected = generate_skills._copy_toolkit_skills(self.workbench, ("init", "rest-api-pipeline"))
        self.assertEqual(set(collected), {"router", "find-source"})
        self.assertTrue((self.skills_dir / "router" / "SKILL.md").exists())

    def test_duplicate_skill_name_raises(self):
        self._make("init", "dup")
        self._make("rest-api-pipeline", "dup")
        with patch.object(generate_skills, "SKILLS_DIR", self.skills_dir):
            with self.assertRaises(SystemExit):
                generate_skills._copy_toolkit_skills(self.workbench, ("init", "rest-api-pipeline"))

    def test_missing_toolkit_raises(self):
        with patch.object(generate_skills, "SKILLS_DIR", self.skills_dir):
            with self.assertRaises(SystemExit):
                generate_skills._copy_toolkit_skills(self.workbench, ("nope",))


class ResolveShortTest(unittest.TestCase):
    def test_full_sha_truncated_to_seven(self):
        self.assertEqual(update_skills._resolve_short("0123456789abcdef0123"), "0123456")

    def test_short_sha_passthrough(self):
        self.assertEqual(update_skills._resolve_short("abc1234"), "abc1234")


class WriteShortTest(unittest.TestCase):
    def test_rewrites_short_ref_line(self):
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
            fh.write('WORKBENCH_REF_SHORT = "old1234"\nWORKBENCH_REF = "old1234old1234"\n')
            script = Path(fh.name)
        self.addCleanup(script.unlink)
        with patch.object(update_skills, "GENERATE_SCRIPT", script):
            update_skills._write_short("new5678")
        content = script.read_text(encoding="utf-8")
        self.assertIn('WORKBENCH_REF_SHORT = "new5678"', content)
        self.assertIn('WORKBENCH_REF = "old1234old1234"', content)  # full line untouched


class ScaffoldDltVersionTest(unittest.TestCase):
    def _lock(self, body):
        path = Path(self._tmp.name) / "uv.lock"
        path.write_text(body, encoding="utf-8")
        return path

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

    def test_reads_dlt_version(self):
        lock = self._lock('[[package]]\nname = "dlt"\nversion = "1.30.0"\n')
        self.assertEqual(sync_workspace_deps.scaffold_dlt_version(lock), "1.30.0")

    def test_raises_when_dlt_absent(self):
        lock = self._lock('[[package]]\nname = "duckdb"\nversion = "1.5.5"\n')
        with self.assertRaises(sync_workspace_deps.SyncError):
            sync_workspace_deps.scaffold_dlt_version(lock)


class ProbeSourceTest(unittest.TestCase):
    """PROBE_SOURCE runs inside the throwaway env; exercise it against a fake dlt module here."""

    def _run_probe(self, **attrs):
        module = types.ModuleType(sync_workspace_deps.WORKSPACE_DEPS_MODULE)
        for name, value in attrs.items():
            setattr(module, name, value)
        out = io.StringIO()
        with patch.dict(sys.modules, {sync_workspace_deps.WORKSPACE_DEPS_MODULE: module}):
            with contextlib.redirect_stdout(out):
                exec(sync_workspace_deps.PROBE_SOURCE, {"__name__": "__probe__"})  # noqa: S102
        return sync_workspace_deps.parse_workspace_deps(out.getvalue())

    def test_calls_workspace_deps_function(self):
        # dlt >= 1.32.0: the list is computed, so the function result is the source of truth
        deps = self._run_probe(workspace_deps=lambda: ["duckdb>=0.9,<2", "s3fs>=2022.4.0"])
        self.assertEqual(deps, ["duckdb>=0.9,<2", "s3fs>=2022.4.0"])

    def test_falls_back_to_legacy_constant(self):
        # dlt < 1.32.0 exposes a module-level list instead
        deps = self._run_probe(WORKSPACE_DEPS=("duckdb>=0.9",))
        self.assertEqual(deps, ["duckdb>=0.9"])

    def test_function_wins_over_constant(self):
        deps = self._run_probe(workspace_deps=lambda: ["new>=1"], WORKSPACE_DEPS=["old>=1"])
        self.assertEqual(deps, ["new>=1"])

    def test_missing_both_raises(self):
        with self.assertRaises(AttributeError):
            self._run_probe()


class ParseWorkspaceDepsTest(unittest.TestCase):
    def test_reads_last_json_line(self):
        # dlt may log to stdout before the probe prints; only the last line is the payload
        stdout = 'some dlt notice\n["duckdb>=0.9", "s3fs>=2022.4.0"]\n'
        self.assertEqual(sync_workspace_deps.parse_workspace_deps(stdout), ["duckdb>=0.9", "s3fs>=2022.4.0"])

    def test_empty_output_raises(self):
        with self.assertRaises(sync_workspace_deps.SyncError):
            sync_workspace_deps.parse_workspace_deps("\n  \n")

    def test_non_json_raises(self):
        with self.assertRaises(sync_workspace_deps.SyncError):
            sync_workspace_deps.parse_workspace_deps("Traceback (most recent call last)")

    def test_non_list_of_strings_raises(self):
        for payload in ['{"a": 1}', '["ok", 2]', '"duckdb"']:
            with self.subTest(payload=payload), self.assertRaises(sync_workspace_deps.SyncError):
                sync_workspace_deps.parse_workspace_deps(payload)


class FetchWorkspaceDepsTest(unittest.TestCase):
    def _completed(self, returncode=0, stdout="", stderr=""):
        return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)

    def test_runs_probe_against_locked_version(self):
        with (
            patch.object(sync_workspace_deps.shutil, "which", return_value="/usr/bin/uv"),
            patch.object(sync_workspace_deps.subprocess, "run") as run,
        ):
            run.return_value = self._completed(stdout='["duckdb>=0.9,<2"]\n')
            self.assertEqual(sync_workspace_deps.fetch_workspace_deps("1.32.0"), ["duckdb>=0.9,<2"])
        command = run.call_args.args[0]
        self.assertEqual(command[0], "/usr/bin/uv")
        self.assertIn("--isolated", command)
        self.assertIn("--no-project", command)
        self.assertEqual(command[command.index("--with") + 1], "dlt==1.32.0")
        self.assertEqual(command[-1], sync_workspace_deps.PROBE_SOURCE)

    def test_probe_failure_reports_stderr(self):
        with (
            patch.object(sync_workspace_deps.shutil, "which", return_value="/usr/bin/uv"),
            patch.object(sync_workspace_deps.subprocess, "run") as run,
        ):
            run.return_value = self._completed(returncode=1, stderr="error: No solution found for dlt==9.9.9\n")
            with self.assertRaises(sync_workspace_deps.SyncError) as ctx:
                sync_workspace_deps.fetch_workspace_deps("9.9.9")
        self.assertIn("No solution found", str(ctx.exception))

    def test_missing_uv_raises(self):
        with patch.object(sync_workspace_deps.shutil, "which", return_value=None):
            with self.assertRaises(sync_workspace_deps.SyncError):
                sync_workspace_deps.fetch_workspace_deps("1.32.0")

    def test_timeout_raises(self):
        with (
            patch.object(sync_workspace_deps.shutil, "which", return_value="/usr/bin/uv"),
            patch.object(sync_workspace_deps.subprocess, "run", side_effect=subprocess.TimeoutExpired("uv", 1)),
        ):
            with self.assertRaises(sync_workspace_deps.SyncError):
                sync_workspace_deps.fetch_workspace_deps("1.32.0")


class MergeSpecsTest(unittest.TestCase):
    def test_concatenates_when_disjoint(self):
        merged = sync_workspace_deps.merge_specs(("dlt[hub]>=1.27.2,<2",), ["duckdb>=0.9"])
        self.assertEqual(merged, ["dlt[hub]>=1.27.2,<2", "duckdb>=0.9"])

    def test_raises_when_upstream_claims_a_base_spec(self):
        with self.assertRaises(sync_workspace_deps.SyncError):
            sync_workspace_deps.merge_specs(("dlthub>=0.27.0,<1",), ["dlthub>=0.30", "duckdb>=0.9"])

    def test_overlap_detected_across_naming_styles(self):
        with self.assertRaises(sync_workspace_deps.SyncError):
            sync_workspace_deps.merge_specs(("dlthub_client>=0.27.7,<1",), ["dlthub-client>=0.28.1"])

    def test_extras_do_not_hide_overlap(self):
        with self.assertRaises(sync_workspace_deps.SyncError):
            sync_workspace_deps.merge_specs(("dlt[hub]>=1.27.2,<2",), ["dlt>=1.30"])


class PackageNameTest(unittest.TestCase):
    def test_normalizes(self):
        for spec, expected in [
            ("dlt[hub]>=1.27.2,<2", "dlt"),
            ("dlthub_client>=0.27.7,<1", "dlthub-client"),
            ("mowidgets>=0.2.1 ; python_version >= '3.11'", "mowidgets"),
            ("Ibis.Framework>=12", "ibis-framework"),
        ]:
            self.assertEqual(sync_workspace_deps.package_name(spec), expected)


class WriteDependenciesTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.pyproject = Path(self._tmp.name) / "pyproject.toml"
        self.pyproject.write_text(
            '[project]\nname = "dlthub-workspace"\ndependencies = [\n    "old>=1",\n]\n\n[tool.other]\nkeep = true\n',
            encoding="utf-8",
        )

    def test_replaces_block_and_preserves_rest(self):
        sync_workspace_deps.write_dependencies(["dlt[hub]>=1.27.2,<2", "duckdb>=0.9"], self.pyproject)
        text = self.pyproject.read_text(encoding="utf-8")
        self.assertIn('    "dlt[hub]>=1.27.2,<2",\n', text)
        self.assertNotIn("old>=1", text)
        self.assertIn("[tool.other]\nkeep = true\n", text)
        self.assertIn('name = "dlthub-workspace"', text)

    def test_round_trips_through_read(self):
        specs = ["dlt[hub]>=1.27.2,<2", "duckdb>=0.9", "mowidgets>=0.2.1 ; python_version >= '3.11'"]
        sync_workspace_deps.write_dependencies(specs, self.pyproject)
        self.assertEqual(sync_workspace_deps.read_dependencies(self.pyproject), specs)

    def test_bracketed_spec_does_not_truncate_the_array(self):
        self.pyproject.write_text(
            '[project]\ndependencies = [\n    "dlt[hub]>=1.27.2,<2",\n    "duckdb>=0.9",\n]\n\n[tool.other]\nkeep = true\n',
            encoding="utf-8",
        )
        sync_workspace_deps.write_dependencies(["dlt[hub]>=1.27.2,<2", "s3fs>=2022.4.0"], self.pyproject)
        text = self.pyproject.read_text(encoding="utf-8")
        self.assertEqual(
            sync_workspace_deps.read_dependencies(self.pyproject),
            ["dlt[hub]>=1.27.2,<2", "s3fs>=2022.4.0"],
        )
        self.assertIn("[tool.other]\nkeep = true\n", text)
        self.assertNotIn("duckdb", text)

    def test_missing_block_raises(self):
        self.pyproject.write_text('[project]\nname = "x"\n', encoding="utf-8")
        with self.assertRaises(sync_workspace_deps.SyncError):
            sync_workspace_deps.write_dependencies(["duckdb>=0.9"], self.pyproject)


class BaseSpecsTest(unittest.TestCase):
    def test_base_specs_lead_the_bundled_scaffold(self):
        current = sync_workspace_deps.read_dependencies()
        self.assertEqual(current[: len(sync_workspace_deps.BASE_SPECS)], list(sync_workspace_deps.BASE_SPECS))


if __name__ == "__main__":
    unittest.main()
