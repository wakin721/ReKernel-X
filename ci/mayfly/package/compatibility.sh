#!/system/bin/sh
# Shared by installation and boot. The kernel performs the final CRC checks.
rkx_check_compatibility() {
    RKX_ERROR=
    if [ "$(getprop ro.product.device)" != mayfly ]; then
        RKX_ERROR="Unsupported device: only mayfly"
        return 1
    fi
    rkx_release=$(uname -r)
    rkx_expected_config=$(awk -v release="$rkx_release" \
        '$1 == release && NF == 2 { print $2 }' "$MODDIR/compatible-kernels.txt")
    if [ -z "$rkx_expected_config" ]; then
        RKX_ERROR="Kernel not validated for reuse: $rkx_release"
        return 1
    fi
    # Canonical CONFIG values include disabled options, but exclude comments,
    # ordering and the generated Linux version header. Do not ignore options.
    # Stream the config: Android printf may be external and a config exceeds
    # the per-argument limit. Missing/unreadable input hashes to a rejected value.
    rkx_config_hash=$(zcat /proc/config.gz 2>/dev/null | awk '
        /^CONFIG_[A-Za-z0-9_]+=/ { print; next }
        /^# CONFIG_[A-Za-z0-9_]+ is not set$/ { print $2 "=n" }
        ' | LC_ALL=C sort -u | sha256sum)
    rkx_config_hash=${rkx_config_hash%% *}
    if [ "$rkx_config_hash" != "$rkx_expected_config" ]; then
        RKX_ERROR="Kernel configuration options changed"
        return 1
    fi
    rkx_expected_module=$(cat "$MODDIR/module.sha256") || return 1
    rkx_actual_module=$(sha256sum "$MODDIR/rekernel_x-lineage-mayfly.ko") || return 1
    rkx_actual_module=${rkx_actual_module%% *}
    if [ -z "$rkx_expected_module" ] || [ "$rkx_actual_module" != "$rkx_expected_module" ]; then
        RKX_ERROR="Module checksum mismatch"
        return 1
    fi
    return 0
}
