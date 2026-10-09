#!/system/bin/sh
MODDIR=${0%/*}
LOG="$MODDIR/load.log"
if [ -e "$MODDIR/.boot-pending" ]; then
    echo "Previous boot did not pass the stability window; module disabled." > "$LOG"
    touch "$MODDIR/disable"
    rm -f "$MODDIR/.boot-pending"
    sync
    exit 1
fi
if [ "$(uname -r)" != "5.10.260-gki-gef362912d37b" ]; then
    echo "Kernel release changed; module disabled." > "$LOG"
    touch "$MODDIR/disable"
    sync
    exit 1
fi
config_hash=$(zcat /proc/config.gz 2>/dev/null | sha256sum | cut -d ' ' -f 1)
if [ "$config_hash" != "0eae19ac5cf26d9314ab4de5eae1e7e4419f43e12c1042e3b6f90a75e0dec4e5" ]; then
    echo "Kernel configuration changed; module disabled." > "$LOG"
    touch "$MODDIR/disable"
    sync
    exit 1
fi
if [ -d /sys/module/rekernel_x ]; then
    echo "ReKernel-X is already loaded; no duplicate load attempted." > "$LOG"
    exit 0
fi
touch "$MODDIR/.boot-pending" || exit 1
sync
insmod "$MODDIR/rekernel_x-lineage-mayfly.ko" > "$LOG" 2>&1
result=$?
echo "insmod_exit=$result" >> "$LOG"
if [ "$result" -ne 0 ]; then
    touch "$MODDIR/disable"
    rm -f "$MODDIR/.boot-pending"
fi
sync
exit "$result"
