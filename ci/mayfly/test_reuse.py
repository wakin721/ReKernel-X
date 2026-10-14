import subprocess
import sys
import unittest
import json
import hashlib
import shutil
import tempfile
from elftools.elf.elffile import ELFFile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
from reuse import check_compatible_profiles


class ReuseTests(unittest.TestCase):
    def reviewed_copy(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        shutil.copytree(ROOT / 'profiles', root / 'profiles')
        package = root / 'ci/mayfly/package'
        package.mkdir(parents=True)
        shutil.copyfile(ROOT / 'ci/mayfly/package/compatible-kernels.txt', package / 'compatible-kernels.txt')
        return root

    def repin_config(self, root, old, new):
        profile = root / 'profiles/lineage-mayfly-5.10.269-los24'
        config = profile / 'kernel.config'
        config.write_text(config.read_text().replace(old, new))
        metadata = json.loads((profile / 'profile.json').read_text())
        metadata['config_sha256'] = hashlib.sha256(config.read_bytes()).hexdigest()
        (profile / 'profile.json').write_text(json.dumps(metadata))

    def test_los24_profile_reuses_original_binary_after_explicit_review(self):
        validation, kernels = check_compatible_profiles(ROOT, ROOT / 'prebuilt/mayfly/rekernel_x-lineage-mayfly.ko')
        self.assertEqual(validation['validated_versions'], 66)
        current = next(k for k in kernels if k['kernel_release'] == '5.10.269-gki-geff4b40407a1')
        self.assertEqual(current['config_fingerprint'], '1a949c95bec22addd96dea0e636487e7c728547545cf578706730ce1b549e6b0')

    def test_unreviewed_toolchain_change_rejected_even_when_profile_hash_is_updated(self):
        root = self.reviewed_copy()
        self.repin_config(root, 'CONFIG_CLANG_VERSION=220002', 'CONFIG_CLANG_VERSION=220003')
        with self.assertRaisesRegex(ValueError, 'configuration review'):
            check_compatible_profiles(root, ROOT / 'prebuilt/mayfly/rekernel_x-lineage-mayfly.ko')

    def test_functional_option_cannot_be_whitelisted_as_toolchain_metadata(self):
        root = self.reviewed_copy()
        self.repin_config(root, '# CONFIG_KCOV is not set', 'CONFIG_KCOV=y')
        manifest_path = root / 'profiles/mayfly-compatibility.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['reviewed_config_changes']['profiles/lineage-mayfly-5.10.269-los24']['CONFIG_KCOV'] = {'base': 'n', 'profile': 'y'}
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'toolchain metadata'):
            check_compatible_profiles(root, ROOT / 'prebuilt/mayfly/rekernel_x-lineage-mayfly.ko')

    def test_los24_crc_change_rejected_even_when_symvers_hash_is_updated(self):
        root = self.reviewed_copy()
        directory = root / 'profiles/lineage-mayfly-5.10.269-los24'
        symvers = directory / 'Module.symvers'
        rows = symvers.read_text().splitlines(keepends=True)
        for index, row in enumerate(rows):
            fields = row.split('\t')
            if fields[1] == 'module_layout':
                fields[0] = '0x00000001'
                rows[index] = '\t'.join(fields)
                break
        symvers.write_text(''.join(rows))
        metadata = json.loads((directory / 'profile.json').read_text())
        metadata['symvers_sha256'] = hashlib.sha256(symvers.read_bytes()).hexdigest()
        (directory / 'profile.json').write_text(json.dumps(metadata))
        with self.assertRaisesRegex(ValueError, 'CRC mismatch'):
            check_compatible_profiles(root, ROOT / 'prebuilt/mayfly/rekernel_x-lineage-mayfly.ko')

    def test_rebuilt_module_records_current_source_revision(self):
        prepared = subprocess.run([sys.executable, str(ROOT / 'ci/mayfly/reuse.py')], capture_output=True, text=True)
        self.assertEqual(prepared.returncode, 0, prepared.stdout + prepared.stderr)
        module = ROOT / 'dist/rekernel_x-lineage-mayfly.ko'
        original = module.read_bytes()
        self.addCleanup(module.write_bytes, original)
        with module.open('rb') as stream:
            section = ELFFile(stream).get_section_by_name('.note.gnu.build-id')
            offset = section['sh_offset'] + section['sh_size'] - 1
        rebuilt = bytearray(original)
        rebuilt[offset] ^= 1
        module.write_bytes(rebuilt)
        packaged = subprocess.run([sys.executable, str(ROOT / 'ci/mayfly/package.py')], capture_output=True, text=True)
        self.assertEqual(packaged.returncode, 0, packaged.stdout + packaged.stderr)
        metadata = json.loads((ROOT / 'dist/build-info.json').read_text())
        current = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        self.assertFalse(metadata['module_reused_without_compilation'])
        self.assertEqual(metadata['module_source_commit'], current)

    def test_existing_binary_validates_all_kernel_profiles_without_building(self):
        result = subprocess.run([sys.executable, str(ROOT / 'ci/mayfly/reuse.py'), '--verify-only'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('5.10.260-gki-gef362912d37b', result.stdout)
        self.assertIn('5.10.269-gki-g490755fcc6cc', result.stdout)
        self.assertIn('5.10.269-gki-geff4b40407a1', result.stdout)
        self.assertIn('"validated_versions": 66', result.stdout)


if __name__ == '__main__':
    unittest.main()
