# mayfly 5.10.269 compatibility review

Reference: LineageOS `23.2-20261009-NIGHTLY-mayfly`, kernel
`5.10.269-gki-g490755fcc6cc`, official source commit
`490755fcc6ccddb2fe73e66d3d76af0eda226372` in
[LineageOS/android_kernel_xiaomi_sm8450](https://github.com/LineageOS/android_kernel_xiaomi_sm8450).

This profile reuses the original 60,744-byte module compiled for 5.10.260.
No module source, vermagic, CFI or `__versions` bytes were modified.

## Evidence

- The decompressed `/proc/config.gz` differs from the 5.10.260 profile only in
  the generated version comment. All CONFIG assignments are identical.
- Compiler remains Android Clang r563880c, build 14054515.
- 14,609 export CRCs were extracted read-only from the active boot_b kernel,
  using vmlinux-to-elf 1.3.6 and the same PREL32 export/direct CRC method as
  the original profile. Raw boot images and device logs are not included.
- All 66 versions imported by the reused module, including `module_layout`,
  match this kernel. All 101 core-kernel CRC imports of the loaded
  `coresight-tmc.ko` independently match; its other 33 imports are module exports.
- These files have identical Git blob hashes at the old and new source commits:
  `drivers/android/binder.c`, `binder_alloc.c`, `binder_internal.h`,
  `binder_alloc.h`, `include/trace/hooks/binder.h` and `include/trace/hooks/signal.h`.
- `include/linux/sched.h` added five fields under `CONFIG_KCOV`; this option is
  disabled in both real configurations, so those additions do not affect the
  active task_struct layout.
- The new kernel's `same_magic()` ignores the release token when the module has
  CRC versions, then checks the other vermagic flags. Normal insmod still checks
  the imported CRCs before module initialization. No force flags are used.

`profile.json` pins the config and complete export-table hashes. Packaging
validates every recorded CRC and checks the canonical CONFIG fingerprint before
generating the same compatibility list consumed at installation and boot.

Future 5.10 patches are not automatically assumed compatible. Internal Binder
interfaces are outside a universal stable ABI guarantee, even when exported
CRCs match; review the actual source/config and test runtime behavior before
adding another kernel to this profile set.
