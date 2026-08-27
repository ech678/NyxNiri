"""Behavior contracts for CLI: exit code propagation, --force path, update hooks.

Safety: all tests run inside TempEnv. CLI main() calls acquire_lock, init_logger,
ensure_nyxniri_symlink — these are patched to avoid touching real system state.
"""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

from tests.utils import TempEnv


class TestGreeterExitCode(unittest.TestCase):
    """greeter install/uninstall exit code must propagate."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_greeter_install_failure_propagates_exit_1(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "greeter", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.greeter.greeter_install", return_value=False):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 1)

    def test_greeter_install_success_propagates_exit_0(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "greeter", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.greeter.greeter_install", return_value=True):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 0)


class TestFcitxExitCode(unittest.TestCase):
    """fcitx install/uninstall exit code must propagate."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_fcitx_uninstall_failure_propagates_exit_1(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "fcitx", "uninstall"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.fcitx.fcitx_uninstall", return_value=False):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 1)


class TestGtkExitCode(unittest.TestCase):
    """gtk install/uninstall exit code must propagate."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_gtk_install_failure_propagates_exit_1(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "gtk", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.gtktheme.gtktheme_install", return_value=False):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 1)

    def test_gtk_install_success_propagates_exit_0(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "gtk", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.gtktheme.gtktheme_install", return_value=True):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 0)


class TestFisherExitCode(unittest.TestCase):
    """fisher install/uninstall exit code must propagate."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_fisher_install_failure_propagates_exit_1(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "fisher", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.fisher.fisher_install", return_value=False):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 1)

    def test_fisher_install_success_propagates_exit_0(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "fisher", "install"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.modules.fisher.fisher_install", return_value=True):
                            with self.assertRaises(SystemExit) as ctx:
                                main()
                            self.assertEqual(ctx.exception.code, 0)


class TestUpdateForcePath(unittest.TestCase):
    """update --force must deploy wallpapers + greeter, not just configs + fcitx."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_force_deploys_wallpapers_and_greeter(self):
        from nyxniri.cli import offer_overwrite_upgrade

        with patch("nyxniri.cli.deploy_selected_configs", return_value=[]):
            with patch("nyxniri.cli.deploy_wallpapers") as mock_wp:
                with patch("nyxniri.cli.fcitx_enabled", return_value=True):
                    with patch("nyxniri.cli.fcitx_install"):
                        with patch("nyxniri.cli.greeter_install") as mock_greeter:
                            with patch("nyxniri.cli.render_completion_screen"):
                                offer_overwrite_upgrade("--force")

        mock_wp.assert_called_once_with(do_download=True)
        mock_greeter.assert_called_once()

    def test_force_returns_false_when_greeter_fails(self):
        from nyxniri.cli import offer_overwrite_upgrade

        with patch("nyxniri.cli.deploy_selected_configs", return_value=[]), \
             patch("nyxniri.cli.deploy_wallpapers"), \
             patch("nyxniri.cli.fcitx_enabled", return_value=False), \
             patch("nyxniri.cli.greeter_install", return_value=False), \
             patch("nyxniri.cli.render_completion_screen") as render:
            result = offer_overwrite_upgrade("--force")

        self.assertFalse(result)
        render.assert_not_called()


class TestGreeterWorkflowFailure(unittest.TestCase):
    """Install and interactive update must not report a failed greeter as complete."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    @staticmethod
    def _greeter_only_selection():
        return {
            "configs": [], "wallpapers": False, "fcitx": False,
            "greeter": True, "backup": False,
        }

    def test_install_returns_false_when_greeter_fails(self):
        from nyxniri.cli import install_configs_workflow

        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.cli.run_master_component_menu", return_value=self._greeter_only_selection()), \
             patch("nyxniri.cli._phase_preflight_check"), \
             patch("nyxniri.cli.deploy_wallpapers"), \
             patch("nyxniri.cli.greeter_install", return_value=False), \
             patch("nyxniri.cli.render_completion_screen") as render, \
             patch("builtins.print"):
            result = install_configs_workflow("config")

        self.assertFalse(result)
        render.assert_not_called()

    def test_interactive_update_returns_false_when_greeter_fails(self):
        from nyxniri.cli import offer_overwrite_upgrade

        with patch("sys.stdin.isatty", return_value=True), \
             patch("nyxniri.cli.Menu") as menu, \
             patch("nyxniri.cli.run_master_component_menu", return_value=self._greeter_only_selection()), \
             patch("nyxniri.cli.greeter_install", return_value=False), \
             patch("nyxniri.cli.render_completion_screen") as render, \
             patch("builtins.print"):
            menu.return_value.run.return_value = 0
            result = offer_overwrite_upgrade()

        self.assertFalse(result)
        render.assert_not_called()


class TestUpdateChecksNewDeps(unittest.TestCase):
    """update command should call check_new_deps_post_update after deploy."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_update_calls_check_new_deps(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "update"]):
            with patch("nyxniri.cli.acquire_lock"):
                with patch("nyxniri.cli.init_logger"):
                    with patch("nyxniri.cli.ensure_nyxniri_symlink"):
                        with patch("nyxniri.cli.safe_git_pull", return_value=True):
                            with patch("nyxniri.cli.offer_overwrite_upgrade", return_value=True):
                                with patch("nyxniri.cli.check_new_deps_post_update") as mock_check:
                                    with patch("builtins.print"):
                                        with self.assertRaises(SystemExit):
                                            main()

        mock_check.assert_called_once()

    def test_update_does_not_report_completion_after_greeter_failure(self):
        from nyxniri.cli import main

        with patch("sys.argv", ["nyxniri", "update", "--force"]), \
             patch("nyxniri.cli.acquire_lock"), \
             patch("nyxniri.cli.init_logger"), \
             patch("nyxniri.cli.ensure_nyxniri_symlink"), \
             patch("nyxniri.cli.safe_git_pull", return_value=True), \
             patch("nyxniri.cli.offer_overwrite_upgrade", return_value=False), \
             patch("nyxniri.cli.check_new_deps_post_update") as check, \
             patch("builtins.print"):
            with self.assertRaises(SystemExit) as ctx:
                main()

        self.assertEqual(ctx.exception.code, 1)
        check.assert_not_called()


class TestCheckNewDepsPostUpdate(unittest.TestCase):
    """check_new_deps_post_update should detect and offer to install missing deps."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_no_missing_deps_no_action(self):
        from nyxniri.cli import check_new_deps_post_update

        with patch("nyxniri.cli.get_missing_deps", return_value=[]):
            with patch("nyxniri.cli.install_selected_deps") as mock_install:
                check_new_deps_post_update()

        mock_install.assert_not_called()

    def test_missing_deps_non_interactive_auto_installs(self):
        from nyxniri.cli import check_new_deps_post_update

        with patch("nyxniri.cli.get_missing_deps", return_value=["some-pkg"]):
            with patch("sys.stdin.isatty", return_value=False):
                with patch("nyxniri.cli.install_selected_deps") as mock_install:
                    with patch("builtins.print"):
                        check_new_deps_post_update()

        mock_install.assert_called_once_with(["some-pkg"])


if __name__ == "__main__":
    unittest.main()
