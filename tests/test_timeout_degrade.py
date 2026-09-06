"""Behavior contracts for timeout degradation (timed_run + call sites).

v3.0.3 shipped `timeout=` on external commands but only network.py caught
TimeoutExpired — every other site turned a hang into a crash (real-world:
fisher install stalled on weak network, whole deploy died mid-flow). These
tests pin the degrade semantics: external commands are polish, never
load-bearing; a timeout must skip the step and move on.
"""

import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from io import StringIO
from subprocess import CompletedProcess
from unittest.mock import call, patch

from tests.utils import TempEnv


def _cp(returncode=0, stdout=""):
    return CompletedProcess(args=[], returncode=returncode, stdout=stdout)


class TestTimedRun(unittest.TestCase):

    def test_timeout_degrades_to_none(self):
        from nyxniri.core import timed_run

        with patch("nyxniri.core.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["x"], timeout=5)):
            self.assertIsNone(timed_run(["x"], 5, check=False))

    def test_passes_through_args_and_result(self):
        from nyxniri.core import timed_run

        with patch("nyxniri.core.subprocess.run", return_value=_cp(0)) as m:
            r = timed_run(["x"], 7, check=False, capture_output=True)
        m.assert_called_once_with(["x"], timeout=7, check=False, capture_output=True)
        self.assertEqual(r.returncode, 0)


class TestPostInstallHooksIndependence(unittest.TestCase):
    """A timed-out hook (theme-sync) must not abort the remaining hooks (fisher)."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_sync_timeout_does_not_block_fisher(self):
        from nyxniri.deploy.deploy import _phase_post_install_services

        sync_script = self._ctx.env.config_dir / "noctalia" / "theme-sync.sh"
        sync_script.parent.mkdir(parents=True, exist_ok=True)
        sync_script.touch()

        with patch("nyxniri.deploy.deploy.timed_run", side_effect=[None, None]), \
             patch("nyxniri.deploy.deploy.shutil.which", return_value=True), \
             patch("nyxniri.modules.fisher.fisher_install") as mock_fisher, \
             patch("builtins.print"):
            _phase_post_install_services()

        mock_fisher.assert_called_once()


class TestUserPostDeployHooks(unittest.TestCase):

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        self.hooks_dir = self._ctx.env.nyx_dir / "hooks"

    def tearDown(self):
        self._ctx.__exit__()

    def test_missing_or_empty_directory_is_silent(self):
        from nyxniri.deploy.deploy import run_user_hooks

        with patch("nyxniri.deploy.deploy.timed_run") as run, patch("builtins.print") as output:
            self.assertEqual(run_user_hooks(), [])
            self.hooks_dir.mkdir(parents=True)
            self.assertEqual(run_user_hooks(), [])

        run.assert_not_called()
        output.assert_not_called()

    def test_runs_scripts_in_filename_order_with_bash_argv(self):
        from nyxniri.deploy.deploy import USER_HOOK_TIMEOUT, run_user_hooks

        self.hooks_dir.mkdir(parents=True)
        first = self.hooks_dir / "10-first.sh"
        second = self.hooks_dir / "20-second.sh"
        second.touch()
        first.touch()
        (self.hooks_dir / "ignored.txt").touch()
        (self.hooks_dir / "directory.sh").mkdir()

        with patch("nyxniri.deploy.deploy.timed_run", return_value=_cp(0)) as run:
            self.assertEqual(run_user_hooks(), [])

        self.assertEqual(run.call_args_list, [
            call(["bash", str(first)], USER_HOOK_TIMEOUT, check=False),
            call(["bash", str(second)], USER_HOOK_TIMEOUT, check=False),
        ])

    def test_timeout_and_failure_are_reported_without_stopping_later_hooks(self):
        from nyxniri.deploy.deploy import run_user_hooks

        self.hooks_dir.mkdir(parents=True)
        first = self.hooks_dir / "10-timeout.sh"
        second = self.hooks_dir / "20-failure.sh"
        third = self.hooks_dir / "30-later.sh"
        for hook in (first, second, third):
            hook.touch()

        with patch("nyxniri.deploy.deploy.timed_run", side_effect=[None, _cp(7), _cp(0)]) as run, \
             patch("nyxniri.deploy.deploy.log_msg") as log, \
             patch("builtins.print") as output:
            returned = run_user_hooks()

        self.assertEqual(run.call_args_list, [
            call(["bash", str(first)], 30, check=False),
            call(["bash", str(second)], 30, check=False),
            call(["bash", str(third)], 30, check=False),
        ])
        diagnostics = "\n".join(str(entry.args[0]) for entry in output.call_args_list)
        self.assertIn(first.name, diagnostics)
        self.assertIn(second.name, diagnostics)
        self.assertIn("30", diagnostics)
        self.assertIn("7", diagnostics)
        self.assertNotIn(third.name, diagnostics)
        self.assertTrue(all(entry.kwargs == {"file": sys.stderr} for entry in output.call_args_list))
        self.assertEqual(returned, [
            output.call_args_list[0].args[0],
            output.call_args_list[1].args[0],
        ])
        log.assert_has_calls([
            call("WARN", f"User deploy hook {first.name} timed out after 30s"),
            call("WARN", f"User deploy hook {second.name} exited with 7"),
        ])

    def test_builtin_post_install_does_not_run_user_hooks(self):
        from nyxniri.deploy.deploy import _phase_post_install_services

        with patch("nyxniri.deploy.deploy.shutil.which", side_effect=lambda name: name == "fish"), \
             patch("nyxniri.modules.fisher.fisher_install") as fisher, \
             patch("nyxniri.deploy.deploy.run_user_hooks") as hooks:
            _phase_post_install_services()

        fisher.assert_called_once()
        hooks.assert_not_called()

    def test_completion_keeps_hook_diagnostics_after_clear_screen(self):
        from nyxniri.deploy.deploy import render_completion_screen

        output = StringIO()
        diagnostic = "User deploy hook 10-timeout.sh timed out after 30s; continuing"
        with patch("sys.stdin.isatty", return_value=False), \
             patch("nyxniri.deploy.deploy.show_logo"), \
             redirect_stdout(output):
            render_completion_screen(chosen_items=[], hook_diagnostics=[diagnostic])

        final_frame = output.getvalue().rsplit("\033[H\033[J", 1)[-1]
        self.assertIn("10-timeout.sh", final_frame)
        self.assertIn("30s", final_frame)

    def test_test_deploy_never_runs_user_hooks(self):
        from nyxniri.deploy.deploy import test_deploy

        with patch("nyxniri.deploy.deploy._phase_atomic_deployment", return_value=[]), \
             patch("nyxniri.deploy.deploy._phase_render_templates"), \
             patch("nyxniri.deploy.deploy._phase_hardware_patches"), \
             patch("nyxniri.deploy.deploy.deploy_wallpapers"), \
             patch("nyxniri.deploy.deploy.render_completion_screen"), \
             patch("nyxniri.deploy.deploy.run_user_hooks") as hooks:
            self.assertTrue(test_deploy())

        hooks.assert_not_called()


class TestDepsTimeout(unittest.TestCase):

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_pacman_timeout_degrades_to_empty_set(self):
        import nyxniri.deps as deps_mod

        deps_mod._PACMAN_INSTALLED_CACHE = None
        try:
            with patch("nyxniri.deps.timed_run", return_value=None):
                self.assertEqual(deps_mod._get_pacman_installed(), set())
        finally:
            deps_mod._PACMAN_INSTALLED_CACHE = None

    def test_fc_list_timeout_degrades_to_empty(self):
        import nyxniri.deps as deps_mod

        deps_mod._FC_LIST_CACHE = None
        try:
            with patch("nyxniri.deps.timed_run", return_value=None):
                self.assertEqual(deps_mod._get_fc_list(), "")
        finally:
            deps_mod._FC_LIST_CACHE = None

    def test_gi_probe_timeout_reports_missing(self):
        import nyxniri.deps as deps_mod

        with patch("nyxniri.deps.timed_run", return_value=None):
            self.assertFalse(deps_mod.is_dep_installed("python-gobject"))


class TestDoctorTimeout(unittest.TestCase):
    """One stalled probe must not kill the whole diagnosis."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_check_timeout_does_not_abort_run_doctor(self):
        from nyxniri.doctor import run_doctor

        def boom(env):
            raise subprocess.TimeoutExpired(cmd="probe", timeout=1)

        with patch("nyxniri.doctor.DOCTOR_SECTIONS", [("doctor_sec_x", [boom])]), \
             patch("builtins.print"):
            self.assertTrue(run_doctor())


class TestGitTimeout(unittest.TestCase):
    """safe_git_pull must return False (not crash) when the reset step stalls."""

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()
        # TempEnv defaults repo_dir to the real repo root — redirect into the
        # temp HOME so we never mkdir inside the actual repository tree.
        self._ctx.env.repo_dir = self._ctx.home / "repo"
        (self._ctx.env.repo_dir / ".git").mkdir(parents=True)

    def tearDown(self):
        self._ctx.__exit__()

    def test_reset_timeout_returns_false(self):
        from nyxniri.network import safe_git_pull

        fake_env = type("E", (), {"run_mode": "cache"})()
        with patch("nyxniri.network.get_env", return_value=fake_env), \
             patch("nyxniri.network.shutil.which", return_value=True), \
             patch("nyxniri.network.subprocess.run", return_value=_cp(0, "")), \
             patch("nyxniri.network._run_git_transfer", side_effect=[_cp(1), _cp(0)]), \
             patch("nyxniri.network.timed_run", return_value=None):
            self.assertIs(safe_git_pull(self._ctx.env.repo_dir), False)


class TestGtkThemeTimeout(unittest.TestCase):

    def setUp(self):
        self._ctx = TempEnv()
        self._ctx.__enter__()

    def tearDown(self):
        self._ctx.__exit__()

    def test_render_timeout_degrades_to_pending(self):
        from nyxniri.modules.gtktheme import gtktheme_trigger_render

        with patch("nyxniri.modules.gtktheme.noctalia_available", return_value=True), \
             patch("nyxniri.modules.gtktheme.timed_run", return_value=None), \
             patch("builtins.print"):
            gtktheme_trigger_render()


if __name__ == "__main__":
    unittest.main()
