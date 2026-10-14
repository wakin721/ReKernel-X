"""Run the real Android loader scripts with only device/insmod operations stubbed."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'ci/mayfly/package'


class LoadingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.module = self.directory / 'module'
        shutil.copytree(PACKAGE, self.module)
        prebuilt = ROOT / 'prebuilt/mayfly/rekernel_x-lineage-mayfly.ko'
        shutil.copyfile(prebuilt, self.module / prebuilt.name)
        self.config = self.directory / 'kernel.config'
        self.config.write_bytes((ROOT / 'profiles/lineage-mayfly/kernel.config').read_bytes())
        self.release = '5.10.269-gki-g490755fcc6cc'
        self.device = 'mayfly'
        self.insmod_status = 0
        self.external_printf = False

    def run_script(self, name):
        # All file writes, checksums and control flow remain real. These stubs
        # replace Android properties, procfs and actual kernel code execution.
        wrappers = f'''
uname() {{ printf '%s\\n' '{self.release}'; }}
getprop() {{ [ "$1" = ro.product.device ] && printf '%s\\n' '{self.device}'; }}
zcat() {{ cat '{self.config}'; }}
sync() {{ :; }}
insmod() {{ [ "$1" = '{self.module}/rekernel_x-lineage-mayfly.ko' ] || return 98;
    touch '{self.directory}/load-attempt'; return {self.insmod_status}; }}
abort() {{ printf '%s\\n' "$*"; exit 1; }}
ui_print() {{ printf '%s\\n' "$*"; }}
set_perm() {{ :; }}
set_perm_recursive() {{ :; }}
MODPATH='{self.module}'
. "$0"
'''
        if self.external_printf:
            wrappers = 'printf() { /usr/bin/printf "$@"; }\n' + wrappers
        return subprocess.run(['bash', '-c', wrappers, str(self.module / name)],
                              capture_output=True, text=True)

    def test_verified_update_loads_existing_module(self):
        result = self.run_script('post-fs-data.sh')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.directory / 'load-attempt').exists())
        self.assertFalse((self.module / 'disable').exists())
        self.assertTrue((self.module / '.boot-pending').exists())

    def test_large_config_does_not_become_one_command_argument(self):
        self.external_printf = True
        result = self.run_script('post-fs-data.sh')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.directory / 'load-attempt').exists())

    def test_install_accepts_only_comment_change(self):
        self.config.write_text(self.config.read_text().replace('5.10.260 Kernel', '5.10.269 Kernel'))
        result = self.run_script('customize.sh')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_original_kernel_remains_supported(self):
        self.release = '5.10.260-gki-gef362912d37b'
        self.assertEqual(self.run_script('post-fs-data.sh').returncode, 0)

    def test_los24_loads_only_its_reviewed_configuration(self):
        self.release = '5.10.269-gki-geff4b40407a1'
        self.config.write_bytes((ROOT / 'profiles/lineage-mayfly-5.10.269-los24/kernel.config').read_bytes())
        result = self.run_script('post-fs-data.sh')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.directory / 'load-attempt').exists())

    def test_los24_rejects_configuration_from_previous_kernel(self):
        self.release = '5.10.269-gki-geff4b40407a1'
        self.assertNotEqual(self.run_script('post-fs-data.sh').returncode, 0)
        self.assertFalse((self.directory / 'load-attempt').exists())

    def test_unknown_patch_is_not_assumed_compatible(self):
        self.release = '5.10.270-gki-gunknown'
        self.assertNotEqual(self.run_script('post-fs-data.sh').returncode, 0)
        self.assertFalse((self.directory / 'load-attempt').exists())
        self.assertTrue((self.module / 'disable').exists())

    def test_changed_cfi_option_never_loads(self):
        self.config.write_text(self.config.read_text().replace('CONFIG_CFI_CLANG=y', '# CONFIG_CFI_CLANG is not set'))
        self.assertNotEqual(self.run_script('post-fs-data.sh').returncode, 0)
        self.assertFalse((self.directory / 'load-attempt').exists())

    def test_modified_module_never_loads(self):
        self.release = '5.10.260-gki-gef362912d37b'
        (self.module / 'rekernel_x-lineage-mayfly.ko').write_bytes(b'corrupted')
        self.assertNotEqual(self.run_script('post-fs-data.sh').returncode, 0)
        self.assertFalse((self.directory / 'load-attempt').exists())

    def test_wrong_device_never_loads(self):
        self.release = '5.10.260-gki-gef362912d37b'
        self.device = 'other'
        self.assertNotEqual(self.run_script('post-fs-data.sh').returncode, 0)
        self.assertFalse((self.directory / 'load-attempt').exists())

    def test_kernel_rejection_disables_module(self):
        self.insmod_status = 1
        self.assertNotEqual(self.run_script('post-fs-data.sh').returncode, 0)
        self.assertTrue((self.directory / 'load-attempt').exists())
        self.assertTrue((self.module / 'disable').exists())
        self.assertFalse((self.module / '.boot-pending').exists())

    def test_previous_failed_boot_disables_before_loading(self):
        (self.module / '.boot-pending').touch()
        self.assertNotEqual(self.run_script('post-fs-data.sh').returncode, 0)
        self.assertFalse((self.directory / 'load-attempt').exists())
        self.assertTrue((self.module / 'disable').exists())
        self.assertFalse((self.module / '.boot-pending').exists())


if __name__ == '__main__':
    unittest.main()
