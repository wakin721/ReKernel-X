# Pinned staged-initialization diagnostic module

This binary was rebuilt once for the staged-init diagnostic on 2026-10-15.
It is not the original 60,744-byte module.

- SHA256: `7d6b35f7d95d32cdb67d64913b8bfc99f1b8d96a34711b7f91bad43cb024a9e0`
- Size: 64,144 bytes; only debug information stripped.
- Module source commit: `fb00b4a91d42a584a634046a0f59d67e068a77bc`.
- LKM-Source Git tree: `4fb99a9d31ae8b6f0299adc874dff9c269002b30`.
- Based on upstream ReKernel-X 1.6 commit `afb5e6bc62c6b9702c823009566a58b2e53b7797`.
- Kernel/config/toolchain: `profiles/lineage-mayfly`, original Android Clang
  r563880c build14054515; compile arguments match `ci/mayfly/build.sh`.
- Native CFI, stack protection, vermagic, and all 68 version entries retained.
  All entries statically match each of the three recorded kernel profiles.
- GPL license: repository LICENSE. Full source is packaged with the module.

The changed lifecycle exposes Netlink at init but keeps hooks off by default.
A root-only, one-way sysfs parameter enables hooks after Android readiness.
Host lifecycle and real shell policy tests do not prove phone boot stability.
**Device test on 2026-10-15 failed to resolve the boot problem.** Netlink-only
early initialization (`hooks_enabled=N`, never activated) still coincided with
12 process start timeouts and dead Keyguard/FallbackHome. This is not a stable
fix. The result narrows investigation toward the early client/injection path,
and does not identify a particular kernel hook or establish an ABI/CFI failure.
An authorized NoActive-injection-off control was confounded by an earlier
Lineage charging HAL wait (`ChargingControlController -> waitForDeclaredService`)
and a 65-second system_server Watchdog. NoActive's original enabled state was
restored and ReKernel-X autoload disabled. Do not attribute the failure to
NoActive or LSPosed from that inconclusive control.

The previous binary SHA256 was
`db926c6e0ffddf31d310ae2343c329f1b82346fc78420cf323565f2be9ecf0b2`.
It remains in Git history at `92a79ed`, but was associated with early-boot
SystemUI startup timeouts; do not automatically restore early loading.

The reuse workflow packages this pinned diagnostic without recompiling it.
Future source changes require rebuilding and updating this provenance again.
