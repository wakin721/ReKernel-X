"""Exercise the Android service policy; replace only device/sysfs/time boundaries."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class StagedServiceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = pathlib.Path(temporary.name)
        self.module = self.directory / 'module'
        shutil.copytree(ROOT / 'ci/mayfly/package', self.module)
        (self.module / '.boot-pending').touch()
        (self.directory / 'clock').write_text('0')
        self.unlocked = True
        self.services_ready = True
        self.keyguard_dead = False
        self.fallback = False
        self.activate_status = 0
        self.fail_after_activation = False
        self.pid_switch_at = -1
        self.user_override = None
        self.service_pid = None
        self.focus_prefix = 'mCurrentFocus=Window'
        self.fail_after_time = -1

    def run_service(self):
        clock = self.directory / 'clock'
        active = self.directory / 'active'
        services = ('  * ServiceRecord{x u0 com.android.systemui/.SystemUIService c:android}\n'
                    '    app=ProcessRecord{x 123:com.android.systemui/u0a1}\n'
                    '  * ServiceRecord{x u0 com.android.systemui/.keyguard.KeyguardService c:android}\n'
                    '    app=ProcessRecord{x 123:com.android.systemui/u0a1}\n') if self.services_ready else ''
        if self.keyguard_dead:
            services += '  * ConnectionRecord{x u0 CR DEAD com.android.systemui/.keyguard.KeyguardService:x}\n'
        user = '  Started users state: [0=RUNNING_UNLOCKED]' if self.unlocked else '  Started users state: [0=RUNNING_LOCKED]'
        user = self.user_override or user
        focus = self.focus_prefix + ('{x com.android.settings/.FallbackHome}' if self.fallback else '{x com.android.launcher3/.Launcher}')
        services_pid = '$(pidof com.android.systemui)' if self.service_pid is None else str(self.service_pid)
        wrappers = f'''
getprop() {{ printf '1\\n'; }}
pidof() {{ n=$(command cat '{clock}'); if [ {self.pid_switch_at} -ge 0 ] && [ "$n" -ge {self.pid_switch_at} ]; then echo 456; else echo 123; fi; }}
dumpsys() {{
    if [ '{int(self.fail_after_activation)}' = 1 ] && [ -e '{active}' ]; then return 1; fi
    n=$(command cat '{clock}')
    if [ {self.fail_after_time} -ge 0 ] && [ "$n" -ge {self.fail_after_time} ]; then return 1; fi
    case "$1 $2" in
      user*) printf '%s\\n' '{user}' ;;
      'activity services') service_pid={services_pid}; printf '%s' '{services}' | sed "s/ 123:/ $service_pid:/g" ;;
      'activity activities') printf '%s\\n' '{focus}' ;;
    esac
}}
timeout() {{ shift; "$@"; }}
cut() {{ if [ "$3" = /proc/uptime ]; then command cat '{clock}'; else command cut "$@"; fi; }}
sleep() {{ n=$(command cat '{clock}'); echo $((n + $1)) > '{clock}'; }}
tee() {{
    [ "$1" = /sys/module/rekernel_x/parameters/hooks_enabled ] || return 99
    command cat > '{active}'
    command cat '{clock}' > '{self.directory / "activation-time"}'
    return {self.activate_status}
}}
cat() {{
    if [ "$1" = /sys/module/rekernel_x/parameters/hooks_enabled ]; then
      [ -e '{active}' ] && echo Y || echo N
    else command cat "$@"; fi
}}
sync() {{ :; }}
. "$0"
'''
        return subprocess.run(['bash', '-c', wrappers, str(self.module / 'service.sh')], capture_output=True, text=True, timeout=15)

    def test_healthy_ui_activates_hooks_and_completes_observation(self):
        result = self.run_service()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.directory / 'active').exists())
        self.assertFalse((self.module / '.boot-pending').exists())
        self.assertFalse((self.module / 'disable').exists())

    def test_locked_user_cannot_clear_guard_or_activate_hooks(self):
        self.unlocked = False
        self.run_service()
        self.assertFalse((self.directory / 'active').exists())
        self.assertTrue((self.module / 'disable').exists())
        self.assertTrue((self.module / '.boot-pending').exists())

    def test_dead_keyguard_is_not_treated_as_successful_boot(self):
        self.keyguard_dead = True
        self.run_service()
        self.assertFalse((self.directory / 'active').exists())
        self.assertTrue((self.module / 'disable').exists())

    def test_fallback_home_prevents_activation(self):
        self.fallback = True
        self.run_service()
        self.assertFalse((self.directory / 'active').exists())
        self.assertTrue((self.module / 'disable').exists())

    def test_missing_services_prevent_activation(self):
        self.services_ready = False
        self.run_service()
        self.assertFalse((self.directory / 'active').exists())

    def test_activation_failure_disables_next_boot(self):
        self.activate_status = 1
        self.run_service()
        self.assertTrue((self.module / 'disable').exists())
        self.assertTrue((self.module / '.boot-pending').exists())

    def test_ui_failure_after_activation_retains_failed_boot_marker(self):
        self.fail_after_activation = True
        self.run_service()
        self.assertTrue((self.directory / 'active').exists())
        self.assertTrue((self.module / 'disable').exists())
        self.assertTrue((self.module / '.boot-pending').exists())

    def test_pid_change_restarts_readiness_stability_window(self):
        self.pid_switch_at = 4
        result = self.run_service()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(int((self.directory / 'activation-time').read_text()), 14)
        self.assertIn('systemui_pid=456', (self.module / 'load.log').read_text())

    def test_other_unlocked_user_does_not_unlock_user_zero(self):
        self.user_override = 'Started users state: [0=RUNNING_LOCKED, 10=RUNNING_UNLOCKED]'
        self.run_service()
        self.assertFalse((self.directory / 'active').exists())

    def test_stale_systemui_services_do_not_authorize_new_pid(self):
        self.service_pid = 999
        self.run_service()
        self.assertFalse((self.directory / 'active').exists())

    def test_resumed_activity_fallback_format_prevents_activation(self):
        self.focus_prefix = 'ResumedActivity: ActivityRecord'
        self.fallback = True
        self.run_service()
        self.assertFalse((self.directory / 'active').exists())

    def test_failure_during_final_sleep_does_not_clear_guard(self):
        self.fail_after_time = 70
        self.run_service()
        self.assertTrue((self.module / '.boot-pending').exists())
        self.assertTrue((self.module / 'disable').exists())


if __name__ == '__main__':
    unittest.main()
