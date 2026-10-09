#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
PROFILE="$ROOT/profiles/lineage-mayfly"
WORK=${BUILD_ROOT:-"$ROOT/.build-mayfly"}
mkdir -p "$WORK" "$ROOT/dist"
WORK=$(cd "$WORK" && pwd)
CACHE=${DOWNLOAD_CACHE:-"$WORK/downloads"}
mkdir -p "$CACHE"
readarray -t settings < <(python3 - "$PROFILE/profile.json" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
for key in ('kernel_repository', 'kernel_commit', 'kernel_release',
            'clang_repository_commit', 'clang_revision', 'module_version'):
    print(p[key])
PY
)
KERNEL_REPO=${settings[0]}
KERNEL_COMMIT=${settings[1]}
RELEASE=${settings[2]}
CLANG_COMMIT=${settings[3]}
CLANG_REV=${settings[4]}
VERSION=${settings[5]}
python3 "$ROOT/ci/mayfly/verify.py" profile "$PROFILE"

download() {
    local url=$1 target=$2
    if [ ! -s "$target" ]; then
        curl --fail --location --retry 3 --retry-all-errors --connect-timeout 30 \
            --max-time 1800 "$url" --output "$target.partial"
        mv "$target.partial" "$target"
    fi
    tar -tzf "$target" > /dev/null
}
download "https://codeload.github.com/$KERNEL_REPO/tar.gz/$KERNEL_COMMIT" "$CACHE/kernel-$KERNEL_COMMIT.tar.gz"
download "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/$CLANG_COMMIT/clang-$CLANG_REV.tar.gz" "$CACHE/clang-$CLANG_COMMIT.tar.gz"

# A fresh tree prevents stale objects or unrelated modules affecting the result.
RUN=$(mktemp -d "$WORK/run.XXXXXXXX")
KERNEL="$RUN/kernel"
OUT="$RUN/out"
CLANG="$RUN/clang"
mkdir -p "$KERNEL" "$OUT" "$CLANG"
tar -xzf "$CACHE/kernel-$KERNEL_COMMIT.tar.gz" --strip-components=1 -C "$KERNEL"
tar -xzf "$CACHE/clang-$CLANG_COMMIT.tar.gz" -C "$CLANG"
export PATH="$CLANG/bin:$PATH"
clang-21 --version | tee "$ROOT/dist/compiler.txt"
grep -F 'Android (14054515,' "$ROOT/dist/compiler.txt"
grep -F 'based on r563880c' "$ROOT/dist/compiler.txt"
export KBUILD_BUILD_USER=builder KBUILD_BUILD_HOST=github-actions
export KBUILD_BUILD_TIMESTAMP='Fri Sep 25 00:00:00 UTC 2026'
export KBUILD_BUILD_VERSION=1
printf '%s\n' "-g${KERNEL_COMMIT:0:12}" > "$KERNEL/.scmversion"
cp -R "$ROOT/LKM-Source" "$KERNEL/drivers/rekernel_x"
cp "$PROFILE/kernel.config" "$OUT/.config"
ARGS=(-C "$KERNEL" O="$OUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
      LLVM=1 LLVM_IAS=1 CC=clang-21 HOSTCC=gcc HOSTCXX=g++ HOSTLD=ld HOSTAR=ar)
make "${ARGS[@]}" olddefconfig
"$KERNEL/scripts/diffconfig" "$PROFILE/kernel.config" "$OUT/.config" | tee "$ROOT/dist/config-diff.txt"
python3 "$ROOT/ci/mayfly/verify.py" config "$PROFILE/kernel.config" "$OUT/.config"
make "${ARGS[@]}" -j"${JOBS:-2}" modules_prepare
test "$(cat "$OUT/include/config/kernel.release")" = "$RELEASE"
cp "$PROFILE/Module.symvers" "$OUT/Module.symvers"
make "${ARGS[@]}" -j"${JOBS:-2}" M="$KERNEL/drivers/rekernel_x" RKX_VERSION="$VERSION" modules
MODULE="$ROOT/dist/rekernel_x-lineage-mayfly.ko"
cp "$KERNEL/drivers/rekernel_x/rekernel_x.ko" "$MODULE"
# Only debug information is stripped; keep __versions, CFI and stack protection.
llvm-strip --strip-debug "$MODULE"
python3 "$ROOT/ci/mayfly/verify.py" module "$PROFILE" "$MODULE" > "$ROOT/dist/validation.json"
cat "$ROOT/dist/validation.json"
python3 "$ROOT/ci/mayfly/package.py"
