"""Contract tests for the checkbox uninstall + 5 gap fixes (§8, §14 B3/D1).

Covers: only-installed modules are shown/uninstalled; execution order (module
uninstallers before state_dir deletion); NyxNiri_archive_* glob cleanup (gap #1);
fisher uninstall incl. fish-absent degrade (gap #3); quickphrase.conf restore
(gap #5); greeter /var/lib removal (gap #2).
"""

import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from tests.utils import TempEnv


class TestUninstallModuleVisibility(unittest.TestCase):
    """§14 B3: only installed modules are uninstalled (all_keys reflects install)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_only_installed_module_uninstallers_run(self):
        from nyxniri.state.uninstall import uninstall_nyxniri

        fcitx_u = MagicMock()
        gtk_u = MagicMock()
        greeter_u = MagicMock()
        fisher_u = MagicMock()
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxniri.state.uninstall.copy_path"), patch("nyxniri.state.uninstall.remove_path"), \
             patch("nyxniri.state.uninstall.get_pics_dir", return_value=self._ctx.env.home / "Pictures"), \
             patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
             patch("nyxniri.modules.greeter.greeter_installed", return_value=False), \
             patch("nyxniri.modules.fcitx.fcitx_uninstall", side_effect=fcitx_u), \
             patch("nyxniri.modules.gtktheme.gtktheme_uninstall", side_effect=gtk_u), \
             patch("nyxniri.modules.greeter.greeter_uninstall", side_effect=greeter_u), \
             patch("nyxniri.modules.fisher.fisher_uninstall", side_effect=fisher_u):
            result = uninstall_nyxniri("")

        self.assertTrue(result)
        fcitx_u.assert_called_once()   # installed → uninstalled
        gtk_u.assert_not_called()
        greeter_u.assert_not_called()
        fisher_u.assert_not_called()  # fisher.fish absent → not shown → not called

    def test_greeter_uninstall_failure_propagates(self):
        from nyxniri.state.uninstall import uninstall_nyxniri

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxniri.state.uninstall.copy_path"), patch("nyxniri.state.uninstall.remove_path"), \
             patch("nyxniri.state.uninstall.get_pics_dir", return_value=self._ctx.env.home / "Pictures"), \
             patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=False), \
             patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
             patch("nyxniri.modules.greeter.greeter_installed", return_value=True), \
             patch("nyxniri.modules.greeter.greeter_uninstall", return_value=False), \
             patch("nyxniri.modules.fisher.fisher_installed", return_value=False):
            result = uninstall_nyxniri("")

        self.assertFalse(result)


class TestUninstallExecutionOrder(unittest.TestCase):
    """§14 B3: module uninstallers run BEFORE nyx_dir/state_dir deletion."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        (self.env.config_dir / "niri").mkdir(parents=True, exist_ok=True)
        (self.env.config_dir / "niri" / "config.kdl").write_text("x")

    def tearDown(self):
        self._ctx.__exit__()

    def test_fcitx_runs_before_state_dir_deleted(self):
        from nyxniri.state.uninstall import uninstall_nyxniri

        state_at_fcitx = {}

        def fcitx_side():
            # When fcitx runs, state_dir (holding its .prev) must still exist.
            state_at_fcitx["exists"] = self.env.state_dir.exists()

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxniri.state.uninstall.copy_path"), \
             patch("nyxniri.state.uninstall.get_pics_dir", return_value=self.env.home / "Pictures"), \
             patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=True), \
             patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
             patch("nyxniri.modules.greeter.greeter_installed", return_value=False), \
             patch("nyxniri.modules.fcitx.fcitx_uninstall", side_effect=fcitx_side):
            uninstall_nyxniri("")

        self.assertTrue(state_at_fcitx.get("exists"), "state_dir must outlive module uninstallers")


class TestUninstallArchiveGlob(unittest.TestCase):
    """Gap #1: NyxNiri_archive_* dirs are cleaned when 'archives' selected."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_old_archives_cleaned_new_archive_preserved(self):
        from nyxniri.state.uninstall import uninstall_nyxniri
        from nyxniri.constants import PROJECT_NAME

        old = self.env.config_dir / f"{PROJECT_NAME}_archive_20250101_000000"
        old.mkdir(parents=True)
        (old / "niri").mkdir()
        (old / "niri" / "config.kdl").write_text("old")
        (self.env.config_dir / "niri").mkdir(parents=True, exist_ok=True)
        (self.env.config_dir / "niri" / "config.kdl").write_text("current")

        with patch("sys.stdin.isatty", return_value=False), patch("builtins.print"), \
             patch("nyxniri.modules.fcitx.fcitx5_installed", return_value=False), \
             patch("nyxniri.modules.gtktheme.gtktheme_registered", return_value=False), \
             patch("nyxniri.modules.greeter.greeter_installed", return_value=False):
            uninstall_nyxniri("")  # non-TTY → all selected, configs archived

        # Old archive cleaned (gap #1), but the freshly-created config archive survives.
        self.assertFalse(old.exists(), "Pre-existing archive must be cleaned")
        new_archives = list(self.env.config_dir.glob(f"{PROJECT_NAME}_archive_*"))
        self.assertEqual(len(new_archives), 1, "Only the freshly-created archive remains")
        self.assertTrue((new_archives[0] / "niri" / "config.kdl").exists())


class TestFisherUninstall(unittest.TestCase):
    """Gap #3: fisher_uninstall removes fisher.fish + plugins, incl. fish-absent degrade (D1)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.fish_dir = self.env.config_dir / "fish"
        (self.fish_dir / "functions").mkdir(parents=True)
        (self.fish_dir / "conf.d").mkdir(parents=True)
        (self.fish_dir / "functions" / "fisher.fish").write_text("# fisher")
        (self.fish_dir / "conf.d" / "plugin.fish").write_text("# plugin")

    def tearDown(self):
        self._ctx.__exit__()

    def test_fish_absent_degrades_to_direct_rm(self):
        from nyxniri.modules.fisher import fisher_uninstall

        with patch("nyxniri.modules.fisher.shutil.which", return_value=None):
            fisher_uninstall()

        # fish absent → conf.d/ nuked, fisher.fish removed.
        self.assertFalse((self.fish_dir / "functions" / "fisher.fish").exists())
        self.assertFalse((self.fish_dir / "conf.d").exists())

    def test_fish_present_fisher_installed_calls_remove_all(self):
        from nyxniri.modules.fisher import fisher_uninstall

        calls = []

        def fake_run(cmd, *a, **k):
            calls.append(cmd)
            r = MagicMock()
            if "functions -q fisher" in " ".join(cmd):
                r.stdout = "0"  # fisher installed
                r.returncode = 0
            else:
                r.returncode = 0
            return r

        with patch("nyxniri.modules.fisher.shutil.which", return_value="/usr/bin/fish"), \
             patch("nyxniri.modules.fisher.subprocess.run", side_effect=fake_run):
            fisher_uninstall()

        # `fisher remove --all` was invoked, and the loader file removed.
        self.assertTrue(any("fisher remove --all" in " ".join(c) for c in calls))
        self.assertFalse((self.fish_dir / "functions" / "fisher.fish").exists())


class TestQuickphraseRestore(unittest.TestCase):
    """Gap #5: fcitx_uninstall restores prior quickphrase.conf hotkeys."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env
        self.qp = self.env.config_dir / "fcitx5" / "conf" / "quickphrase.conf"
        self.qp.parent.mkdir(parents=True)
        # Prior user setting (before NyxNiri touched it).
        self.qp.write_text("[Hotkey]\nTriggerKey=Super+space\n", encoding="utf-8")

    def tearDown(self):
        self._ctx.__exit__()

    def test_uninstall_restores_prior_quickphrase(self):
        from nyxniri.modules.fcitx import fcitx_configure_quickphrase, fcitx_uninstall

        # NyxNiri install overrides the hotkey (and backs up the prior state).
        fcitx_configure_quickphrase()
        self.assertIn("Super+semicolon", self.qp.read_text())

        with patch("nyxniri.modules.fcitx.fcitx_restart"):
            fcitx_uninstall()

        # Prior hotkey restored, .prev state file consumed.
        content = self.qp.read_text()
        self.assertIn("Super+space", content)
        self.assertNotIn("Super+semicolon", content)
        self.assertFalse((self.env.state_dir / "fcitx-nyxmellow-quickphrase.prev").exists())

    def test_uninstall_deletes_quickphrase_if_never_existed(self):
        from nyxniri.modules.fcitx import fcitx_configure_quickphrase, fcitx_uninstall

        # No prior quickphrase.conf → install creates it, uninstall deletes it.
        self.qp.unlink()
        fcitx_configure_quickphrase()
        self.assertTrue(self.qp.exists())
        with patch("nyxniri.modules.fcitx.fcitx_restart"):
            fcitx_uninstall()
        self.assertFalse(self.qp.exists(), "quickphrase.conf must be deleted if it never existed")


class TestGreeterStateDirRemoval(unittest.TestCase):
    """Gap #2: greeter_uninstall removes /var/lib/noctalia-greeter."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_var_lib_state_dir_removed(self):
        from nyxniri.modules.greeter import greeter_uninstall

        config = self._ctx.env.home / "greetd" / "config.toml"
        polkit = self._ctx.env.home / "polkit.rules"
        state_dir = self._ctx.env.home / "state-dir"
        dm_state = self._ctx.env.home / "display-manager"
        calls = []
        def fake_run(command, **kwargs):
            calls.append(command)
            result = MagicMock()
            result.returncode = 1 if command == ["systemctl", "is-enabled", "greetd"] else 0
            result.stdout = ""
            return result

        with patch("nyxniri.modules.greeter.GREETER_ETC_CFG", config), \
             patch("nyxniri.modules.greeter.GREETER_POLKIT_RULE", polkit), \
             patch("nyxniri.modules.greeter.GREETER_STATE_DIR", state_dir), \
             patch("nyxniri.modules.greeter.GREETER_DM_STATE", dm_state), \
             patch("nyxniri.modules.greeter.shutil.which", return_value="/usr/bin/systemctl"), \
             patch("nyxniri.modules.greeter.subprocess.run", side_effect=fake_run):
            greeter_uninstall()

        # A `sudo rm -rf <state_dir>` command was issued.
        self.assertTrue(
            any("rm" in c and "-rf" in c and str(state_dir) in " ".join(c) for c in calls),
            f"Expected sudo rm -rf {state_dir}, got: {calls}",
        )


class TestFisherInstallDetect(unittest.TestCase):
    """fisher module: install early-returns when fish absent; detection by loader file."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.env = self._ctx.env

    def tearDown(self):
        self._ctx.__exit__()

    def test_installed_detects_loader_file(self):
        from nyxniri.modules.fisher import fisher_installed
        fish_dir = self.env.config_dir / "fish" / "functions"
        fish_dir.mkdir(parents=True)
        (fish_dir / "fisher.fish").write_text("# fisher")
        self.assertTrue(fisher_installed())

    def test_install_noop_when_fish_absent(self):
        from nyxniri.modules.fisher import fisher_install
        with patch("nyxniri.modules.fisher.shutil.which", return_value=None), patch("builtins.print"):
            self.assertFalse(fisher_install())


if __name__ == "__main__":
    unittest.main()
