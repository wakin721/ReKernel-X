# Pinned, reusable ReKernel-X module

`rekernel_x-lineage-mayfly.ko` is the original locally compiled and device-tested
module, not a new build for the later kernel:

- SHA256: `db926c6e0ffddf31d310ae2343c329f1b82346fc78420cf323565f2be9ecf0b2`
- Size: 60,744 bytes, debug information stripped only.
- ReKernel-X source: upstream 1.6 commit
  `afb5e6bc62c6b9702c823009566a58b2e53b7797`; complete source is in `LKM-Source`.
- LKM-Source Git tree: `082f6e2e17faf302a518bc697661d799b483eedc`.
- Kernel/config/toolchain: `profiles/lineage-mayfly`, compiled with
  `ci/mayfly/build.sh`'s equivalent make options. The original local build used
  ARM64 host gcc helpers and the official x86_64 Clang through QEMU; the target
  module was AArch64. Compiler identification is in `compiler.txt`.
- GPL license is the repository's `LICENSE`.

This binary passed original reboot, NoActive connection and interactive device
testing. The repository's CI build produced an otherwise identical ELF with a
different GNU build-id. The reuse workflow deliberately preserves this original
binary and validates it against each recorded compatible kernel.

The fixed binary and hashes remain accessible after Actions artifacts expire.
If LKM-Source changes, reuse fails until the binary/source provenance is updated.
