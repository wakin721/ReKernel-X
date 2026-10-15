"""Package only the module that passed the pinned profile's ABI checks."""
import json
import subprocess
import zipfile
from pathlib import Path

from verify import check_module, sha256
from reuse import check_compatible_profiles

root = Path(__file__).resolve().parents[2]
profile_dir = root / 'profiles/lineage-mayfly'
profile = json.loads((profile_dir / 'profile.json').read_text())
dist = root / 'dist'
module = dist / 'rekernel_x-lineage-mayfly.ko'
validation, compatible_kernels = check_compatible_profiles(root, module)
manifest = json.loads((root / 'profiles/mayfly-compatibility.json').read_text())
module_reused = sha256(module) == manifest['prebuilt_sha256']
commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
dirty = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip()
metadata = dict(profile, source_commit=commit, source_worktree_dirty=bool(dirty),
                validation=validation, compatible_kernels=compatible_kernels,
                module_reused_without_compilation=module_reused,
                module_source_commit=manifest['module_source_commit'] if module_reused else commit,
                runtime_test='Staged diagnostic: device boot and NoActive verification required.',
                hook_activation_policy='Early Netlink only; user0 unlocked and UI stable 10s, then activate hooks and observe UI 60s; wait deadline 600s.')
metadata['compiler'] = (dist / 'compiler.txt').read_text()
metadata['config_diff'] = (dist / 'config-diff.txt').read_text()
metadata_text = json.dumps(metadata, ensure_ascii=False, indent=2) + '\n'
(dist / 'build-info.json').write_text(metadata_text, encoding='utf-8')
files = {}


def add_tree(directory, prefix):
    for path in sorted(directory.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            files[prefix + path.relative_to(directory).as_posix()] = path.read_bytes()


add_tree(root / 'ci/mayfly/package', '')
add_tree(root / 'template/META-INF', 'META-INF/')
add_tree(root / 'LKM-Source', 'source/LKM-Source/')
add_tree(root / 'ci/mayfly', 'source/ci/mayfly/')
add_tree(root / 'profiles', 'source/profiles/')
files['LICENSE'] = (root / 'LICENSE').read_bytes()
files['source/README.md'] = (root / 'README.md').read_bytes()
files['build-info.json'] = metadata_text.encode('utf-8')
files[module.name] = module.read_bytes()
files['module.sha256'] = (sha256(module) + '\n').encode('ascii')
filename = 'ReKernel-X-1.6-LineageOS-mayfly-staged-diagnostic.zip'
with zipfile.ZipFile(dist / filename, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, content in sorted(files.items()):
        entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
        entry.create_system = 3
        executable = name.endswith('.sh') or name.endswith('/update-binary')
        entry.external_attr = (0o100755 if executable else 0o100644) << 16
        entry.compress_type = zipfile.ZIP_DEFLATED
        archive.writestr(entry, content)
with (dist / 'SHA256SUMS').open('w', newline='\n') as stream:
    for name in (filename, module.name, 'build-info.json', 'validation.json'):
        stream.write(f'{sha256(dist / name)}  {name}\n')
print(f'Created {dist / filename}')
