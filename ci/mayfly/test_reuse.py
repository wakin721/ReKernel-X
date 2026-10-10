import subprocess
import sys
import unittest
import json
from elftools.elf.elffile import ELFFile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class ReuseTests(unittest.TestCase):
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

    def test_existing_binary_validates_both_kernel_profiles_without_building(self):
        result = subprocess.run([sys.executable, str(ROOT / 'ci/mayfly/reuse.py'), '--verify-only'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('5.10.260-gki-gef362912d37b', result.stdout)
        self.assertIn('5.10.269-gki-g490755fcc6cc', result.stdout)
        self.assertIn('"validated_versions": 66', result.stdout)


if __name__ == '__main__':
    unittest.main()
