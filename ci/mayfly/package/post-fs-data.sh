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
. "$MODDIR/compatibility.sh"
if ! rkx_check_compatibility; then
    echo "${RKX_ERROR:-Compatibility verification failed}; module disabled." > "$LOG"
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
echo "Validated kernel: $(uname -r); reusing module with native CRC checks." > "$LOG"
insmod "$MODDIR/rekernel_x-lineage-mayfly.ko" >> "$LOG" 2>&1
result=$?
echo "insmod_exit=$result" >> "$LOG"
if [ "$result" -eq 0 ]; then
    echo "stage=transport ready; hooks stay off until UI readiness is verified." >> "$LOG"
fi
if [ "$result" -ne 0 ]; then
    touch "$MODDIR/disable"
    rm -f "$MODDIR/.boot-pending"
fi
sync
exit "$result"
