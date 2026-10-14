"""Validate and package a pinned module without invoking a compiler."""
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile
from verify import check_module, check_profile, read_config, require, sha256

REVIEWABLE_TOOLCHAIN_OPTIONS = {
    'CONFIG_AS_VERSION', 'CONFIG_CC_VERSION_TEXT', 'CONFIG_CLANG_VERSION', 'CONFIG_LLD_VERSION',
}


def check_config_review(base, profile, reviewed):
    require(reviewed.keys() <= REVIEWABLE_TOOLCHAIN_OPTIONS,
            'Only toolchain metadata may differ; functional configuration changes require a new module review')
    changes = {key: {'base': base.get(key), 'profile': profile.get(key)}
               for key in base.keys() | profile.keys() if base.get(key) != profile.get(key)}
    require(changes == reviewed,
            f'Exact configuration review missing or stale: actual={changes}, reviewed={reviewed}')


def config_fingerprint(path):
    values = read_config(path)
    # Sort complete assignments like LC_ALL=C sort, rather than just key names.
    normalized = ''.join(line + '\n' for line in sorted(f'{k}={v}' for k, v in values.items()))
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def check_compatible_profiles(root, module):
    manifest = json.loads((root / 'profiles/mayfly-compatibility.json').read_text())
    validation = check_module(root / manifest['base_profile'], module)
    base_config = read_config(root / manifest['base_profile'] / 'kernel.config')
    reviews = manifest.get('reviewed_config_changes', {})
    require(reviews.keys() <= set(manifest['compatible_profiles']), 'Configuration review references an unknown profile')
    with module.open('rb') as stream:
        data = ELFFile(stream).get_section_by_name('__versions').data()
    versions = {data[i+8:i+64].split(b'\0')[0].decode(): struct.unpack_from('<Q', data, i)[0]
                for i in range(0, len(data), 64)}
    kernels = []
    for relative in manifest['compatible_profiles']:
        directory = root / relative
        profile = check_profile(directory)
        reviewed = reviews.get(relative, {})
        check_config_review(base_config, read_config(directory / 'kernel.config'), reviewed)
        table = {a[1]: int(a[0], 16) for line in (directory / 'Module.symvers').read_text().splitlines()
                 if (a := line.split())}
        mismatches = [name for name, crc in versions.items() if table.get(name) != crc]
        require(not mismatches, f'{profile["kernel_release"]}: CRC mismatch: {mismatches}')
        fingerprint = config_fingerprint(directory / 'kernel.config')
        kernels.append({'kernel_release': profile['kernel_release'], 'profile': relative,
                        'config_fingerprint': fingerprint, 'validated_versions': len(versions),
                        'kernel_commit': profile['kernel_commit'], 'lineage_build': profile['lineage_build'],
                        'kernel_clang_revision': profile['clang_revision'],
                        'reviewed_config_changes': reviewed})
    require(len({k['kernel_release'] for k in kernels}) == len(kernels), 'Duplicate compatible kernels')
    expected = ''.join(f'{k["kernel_release"]} {k["config_fingerprint"]}\n' for k in kernels)
    require((root / 'ci/mayfly/package/compatible-kernels.txt').read_text() == expected,
            'Loader compatibility list disagrees with validated profiles')
    return validation, kernels


def main():
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((root / 'profiles/mayfly-compatibility.json').read_text())
    module = root / manifest['prebuilt']
    require(sha256(module) == manifest['prebuilt_sha256'], 'Pinned module checksum mismatch')
    source_tree = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD:LKM-Source'], text=True).strip()
    require(source_tree == manifest['lkm_source_tree'], 'Module source changed: prebuilt must be revalidated/rebuilt')
    changed_source = subprocess.check_output(['git', '-C', str(root), 'diff', 'HEAD', '--', 'LKM-Source'])
    require(not changed_source, 'Uncommitted module source changes cannot use the pinned prebuilt')
    validation, kernels = check_compatible_profiles(root, module)
    report = {'module_reused_without_compilation': True, 'validation': validation, 'compatible_kernels': kernels}
    print(json.dumps(report, indent=2))
    if '--verify-only' in sys.argv[1:]:
        return
    dist = root / 'dist'
    dist.mkdir(exist_ok=True)
    shutil.copyfile(module, dist / module.name)
    (dist / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    (dist / 'compiler.txt').write_text((root / 'prebuilt/mayfly/compiler.txt').read_text())
    (dist / 'config-diff.txt').write_text('No compilation: reuse of the original validated binary.\n')
    subprocess.run([sys.executable, str(root / 'ci/mayfly/package.py')], check=True)


if __name__ == '__main__':
    main()
