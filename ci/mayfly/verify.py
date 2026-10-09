"""Fail closed on configuration drift or an incompatible module ABI."""
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

from elftools.elf.elffile import ELFFile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_config(path):
    values = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_'):
            key, value = line.split('=', 1)
            values[key] = value
        elif match := re.fullmatch(r'# (CONFIG_\w+) is not set', line):
            values[match[1]] = 'n'
    return values


def check_config(original, prepared):
    before, after = read_config(original), read_config(prepared)
    allowed_additions = {'CONFIG_CC_CAN_LINK': 'y', 'CONFIG_CC_CAN_LINK_STATIC': 'y',
                         'CONFIG_UAPI_HEADER_TEST': 'n'}
    changes = {k: (before.get(k), after.get(k)) for k in before.keys() | after.keys()
               if before.get(k) != after.get(k)}
    invalid = {k: v for k, v in changes.items()
               if not (v[0] is None and allowed_additions.get(k) == v[1])}
    require(not invalid, f'Unexpected configuration changes: {invalid}')
    print(json.dumps({'approved_config_additions': changes}, indent=2))


def check_profile(directory):
    profile = json.loads((directory / 'profile.json').read_text())
    for filename, key in [('kernel.config', 'config_sha256'), ('Module.symvers', 'symvers_sha256')]:
        require(sha256(directory / filename) == profile[key], f'{filename}: SHA256 mismatch')
    rows = [line.split() for line in (directory / 'Module.symvers').read_text().splitlines()]
    require(len(rows) == profile['kernel_exports'], 'Export count mismatch')
    require(len({row[1] for row in rows}) == len(rows), 'Duplicate exports')
    config = read_config(directory / 'kernel.config')
    for key in ('CONFIG_CFI_CLANG', 'CONFIG_CFI_CLANG_SHADOW', 'CONFIG_LTO_CLANG_FULL',
                'CONFIG_MODVERSIONS', 'CONFIG_STACKPROTECTOR_PER_TASK', 'CONFIG_STACKPROTECTOR_STRONG'):
        require(config.get(key) == 'y', f'Required protection missing: {key}')
    return profile


def check_module(directory, path):
    profile = check_profile(directory)
    table = {a[1]: int(a[0], 16) for line in (directory / 'Module.symvers').read_text().splitlines()
             if (a := line.split())}
    with path.open('rb') as stream:
        elf = ELFFile(stream)
        require(elf['e_machine'] == 'EM_AARCH64' and elf.elfclass == 64 and elf.little_endian,
                'Expected little-endian AArch64 ELF64')
        symbols = list(elf.get_section_by_name('.symtab').iter_symbols())
        undefined = {s.name for s in symbols if s.name and s['st_shndx'] == 'SHN_UNDEF'}
        section = elf.get_section_by_name('__versions')
        require(section is not None, 'Missing __versions')
        versions = section.data()
        require(len(versions) > 0 and len(versions) % 64 == 0, 'Invalid/empty __versions')
        crcs = {}
        for i in range(0, len(versions), 64):
            name = versions[i + 8:i + 64].split(b'\0')[0].decode()
            require(name and name not in crcs, 'Invalid/duplicate version name')
            crcs[name] = struct.unpack_from('<Q', versions, i)[0]
        require(not (undefined - crcs.keys()), f'Imports without CRC: {undefined - crcs.keys()}')
        require('module_layout' in crcs, 'Missing module_layout CRC')
        require(not (crcs.keys() - table.keys()), 'Imports absent from kernel export table')
        mismatch = [name for name, crc in crcs.items() if table[name] != crc]
        require(not mismatch, f'Kernel CRC mismatch: {mismatch}')
        require('__stack_chk_guard' not in undefined, 'Global stack canary is incompatible')
        require('__stack_chk_fail' in undefined, 'Stack protector dependency missing')
        require(any(s.name == '__cfi_check' and s['st_shndx'] != 'SHN_UNDEF' for s in symbols),
                'CFI check function missing')
        info = [s.decode() for s in elf.get_section_by_name('.modinfo').data().split(b'\0') if s]
        vermagic = next(s.removeprefix('vermagic=') for s in info if s.startswith('vermagic='))
        expected = profile['kernel_release'] + ' SMP preempt mod_unload modversions aarch64'
        require(vermagic.strip() == expected, f'Wrong vermagic: {vermagic}')
    return {'file': path.name, 'size': path.stat().st_size, 'sha256': sha256(path),
            'vermagic': vermagic, 'imports': len(undefined), 'validated_versions': len(crcs),
            'cfi_check_present': True, 'stack_chk_guard_dependency': False}


if __name__ == '__main__':
    command, *args = sys.argv[1:]
    if command == 'profile':
        check_profile(Path(args[0]))
    elif command == 'config':
        check_config(*map(Path, args))
    elif command == 'module':
        print(json.dumps(check_module(*map(Path, args)), indent=2))
    else:
        raise SystemExit('Usage: verify.py profile DIR | config ORIGINAL PREPARED | module PROFILE KO')
