import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from elftools.elf.elffile import ELFFile

p = argparse.ArgumentParser()
p.add_argument('elf')
p.add_argument('config')
p.add_argument('output')
args = p.parse_args()
config = Path(args.config).read_text(encoding='utf-8-sig')
assert 'CONFIG_HAVE_ARCH_PREL32_RELOCATIONS=y' in config
relative_crc = 'CONFIG_MODULE_REL_CRCS=y' in config
with open(args.elf, 'rb') as f:
    elf = ELFFile(f)
    syms = {s.name: s['st_value'] for s in elf.get_section_by_name('.symtab').iter_symbols()}
    kernel = elf.get_section_by_name('.kernel')
    data, base = kernel.data(), kernel['sh_addr']

def read(addr, n):
    off = addr - base
    assert 0 <= off <= len(data) - n, hex(addr)
    return data[off:off+n]

def string(addr):
    off = addr - base
    assert 0 <= off < len(data), hex(addr)
    end = data.index(b'\0', off)
    return data[off:end].decode()

banner = string(syms['linux_banner'])
assert '5.10.260-gki-gef362912d37b' in banner, banner
rows = []
counts = {}
for suffix, export in [('', 'EXPORT_SYMBOL'), ('_gpl', 'EXPORT_SYMBOL_GPL'),
                       ('_gpl_future', 'EXPORT_SYMBOL_GPL_FUTURE'),
                       ('_unused', 'EXPORT_UNUSED_SYMBOL'),
                       ('_unused_gpl', 'EXPORT_UNUSED_SYMBOL_GPL')]:
    start = syms['__start___ksymtab' + suffix]
    stop = syms['__stop___ksymtab' + suffix]
    crc_start = syms['__start___kcrctab' + suffix]
    crc_stop = syms['__stop___kcrctab' + suffix]
    assert (stop-start) % 12 == 0
    count = (stop-start) // 12
    assert crc_stop-crc_start == count*4
    names = []
    for i in range(count):
        entry = start + i*12
        value_rel, name_rel, ns_rel = struct.unpack('<iii', read(entry, 12))
        name_addr = entry + 4 + name_rel
        name = string(name_addr)
        namespace = string(entry + 8 + ns_rel)
        assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name), name
        assert not namespace or re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', namespace), namespace
        assert syms.get('__kstrtab_' + name, name_addr) == name_addr
        assert syms.get('__ksymtab_' + name, entry) == entry
        crc_addr = crc_start + i*4
        if relative_crc:
            crc_addr += struct.unpack('<i', read(crc_addr, 4))[0]
        crc = struct.unpack('<I', read(crc_addr, 4))[0]
        assert crc != 0, name
        rows.append(f'0x{crc:08x}\t{name}\tvmlinux\t{export}\t{namespace}\n')
        names.append(name)
    assert names == sorted(names), suffix
    counts[export] = count
assert len(rows) == len({r.split('\t')[1] for r in rows})
Path(args.output).write_text(''.join(rows))
print(json.dumps({'banner': banner.strip(), 'base': hex(base), 'relative_crc': relative_crc,
                  'counts': counts, 'total': len(rows),
                  'symvers_sha256': hashlib.sha256(''.join(rows).encode()).hexdigest()}, indent=2))
