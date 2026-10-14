# LineageOS 24 mayfly compatibility review

Reference: `24.0-20261012-NIGHTLY-mayfly` (Android 17), kernel
`5.10.269-gki-geff4b40407a1`, source commit
[`eff4b40407a1b6f1b1ab84554cbb540bcb495175`](https://github.com/LineageOS/android_kernel_xiaomi_sm8450/tree/eff4b40407a1b6f1b1ab84554cbb540bcb495175).

The pinned 60,744-byte ReKernel-X module is unchanged. It was compiled with
Clang r563880c for 5.10.260; this kernel uses Clang r596125, version 22.0.2,
build 15071444. These are separate module and kernel toolchains.

## Evidence and limits

- Read-only extraction from the active boot_a image finds 14,609 exports.
  The complete Module.symvers is byte-for-byte identical to the reviewed
  `5.10.269-gki-g490755fcc6cc` profile. All 66 old module CRCs match.
- Independent cross-check against this system's `coresight-tmc.ko` matches
  all 101 core-kernel CRC imports; the other 33 are exports from other modules.
- Git blob hashes are identical at these two kernel commits for Binder C
  files and headers, Binder/signal trace hooks, `include/linux/sched.h`,
  `include/linux/sched/signal.h`, and `kernel/module.c`.
- Only four CONFIG assignments changed: `CONFIG_AS_VERSION`,
  `CONFIG_CC_VERSION_TEXT`, `CONFIG_CLANG_VERSION`, and `CONFIG_LLD_VERSION`.
  Exact before/after values are recorded in `mayfly-compatibility.json`.
  No functional, CFI, stack-protector or MODVERSIONS option changed.
- Every kernel keeps its own full canonical configuration fingerprint.
  Toolchain values are not ignored at installation or boot. Packaging accepts
  only explicitly reviewed values, and cannot whitelist functional changes.
- CRC/source agreement does not alone prove cross-toolchain CFI runtime
  compatibility. CI does static validation; device verification is separate.
  Keep normal insmod, native CFI/CRC checks, and failed-boot protection.

This review permits bounded testing of the original binary. It does not imply
that arbitrary LineageOS 24 releases or future Clang versions are compatible.
Raw boot images and private device logs are excluded from the repository.
