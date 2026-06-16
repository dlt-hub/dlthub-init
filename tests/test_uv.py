import unittest
from pathlib import Path
from unittest.mock import patch

import dlthub_init.uv as uv


class IsolatedProjectEnvTest(unittest.TestCase):
    def test_strips_venv_hints_keeps_others(self):
        fake = {"VIRTUAL_ENV": "/a", "CONDA_PREFIX": "/b", "PYTHONPATH": "/c", "PATH": "/usr/bin"}
        with patch.dict("os.environ", fake, clear=True):
            env = uv._isolated_project_env()
        self.assertNotIn("VIRTUAL_ENV", env)
        self.assertNotIn("CONDA_PREFIX", env)
        self.assertNotIn("PYTHONPATH", env)
        self.assertEqual(env["PATH"], "/usr/bin")


class CommonUvPathsTest(unittest.TestCase):
    def test_returns_local_and_cargo_bin(self):
        paths = uv._common_uv_paths()
        names = {p.name for p in paths}
        self.assertTrue(names <= {"uv", "uv.exe"})
        self.assertTrue(any(".local" in p.parts for p in paths))
        self.assertTrue(any(".cargo" in p.parts for p in paths))


class FindUvTest(unittest.TestCase):
    def test_returns_path_when_on_path(self):
        with patch("dlthub_init.uv.shutil.which", return_value="/usr/local/bin/uv"):
            self.assertEqual(uv.find_uv(), "/usr/local/bin/uv")

    def test_falls_back_to_common_paths(self):
        with (
            patch("dlthub_init.uv.shutil.which", return_value=None),
            patch("dlthub_init.uv._common_uv_paths", return_value=()),
        ):
            self.assertIsNone(uv.find_uv())

    def test_finds_in_common_path_when_present(self):
        fake = Path("/tmp/does-not-matter/uv")
        with (
            patch("dlthub_init.uv.shutil.which", return_value=None),
            patch("dlthub_init.uv._common_uv_paths", return_value=(fake,)),
            patch.object(Path, "exists", return_value=True),
        ):
            self.assertEqual(uv.find_uv(), str(fake))


if __name__ == "__main__":
    unittest.main()
