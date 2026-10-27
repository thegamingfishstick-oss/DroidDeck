import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "linuxfs/overlay/usr/local/bin/droiddeck-lavapipe-setup"


class LavapipeSetupTest(unittest.TestCase):
    def run_setup(self, uid, manifest=False, pacman="exit 1"):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            icd = root / "icd.d"
            icd.mkdir()
            if manifest:
                (icd / "lvp_icd.aarch64.json").write_text("{}")
            bin_dir = root / "bin"
            bin_dir.mkdir()
            for name, body in {"id": "echo %d" % uid, "pacman": pacman, "pacman-key": "exit 0"}.items():
                (bin_dir / name).write_text("#!/bin/sh\n%s\n" % body)
                (bin_dir / name).chmod(0o755)
            script = root / "setup"
            script.write_text(SCRIPT.read_text().replace("ICD=/usr/share/vulkan/icd.d", "ICD=%s" % icd)
                              .replace("WORK=/var/cache/droiddeck-lavapipe", "WORK=%s/work" % root)
                              .replace("/etc/pacman.d/gnupg/pubring.gpg", str(root / "pubring.gpg"))
                              .replace("    /etc/pacman.conf >", "    %s >" % (root / "pacman.conf")))
            (root / "pacman.conf").write_text("[options]\n[core]\nInclude = /etc/pacman.d/mirrorlist\n")
            (root / "pubring.gpg").write_text("")
            env = dict(os.environ, PATH="%s:%s" % (bin_dir, os.environ["PATH"]))
            result = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=30)
            return result.returncode, result.stdout

    def test_needs_root(self):
        code, out = self.run_setup(1000)
        self.assertEqual(code, 1)
        self.assertIn("== FAIL needs root", out)

    def test_an_installed_lavapipe_is_left_alone(self):
        code, out = self.run_setup(0, manifest=True)
        self.assertEqual(code, 0)
        self.assertIn("== DONE already installed", out)
        self.assertNotIn("Reading the package lists", out)

    def test_an_unreachable_mirror_fails_cleanly(self):
        code, out = self.run_setup(0)
        self.assertEqual(code, 1)
        self.assertIn("== FAIL could not reach the Arch Linux ARM mirrors", out)


if __name__ == "__main__":
    unittest.main()
