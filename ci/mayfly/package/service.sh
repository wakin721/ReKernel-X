#!/system/bin/sh
MODDIR=${0%/*}
[ -e "$MODDIR/.boot-pending" ] || exit 0
attempt=0
while [ "$(getprop sys.boot_completed)" != "1" ]; do
    attempt=$((attempt + 1))
    [ "$attempt" -ge 180 ] && exit 1
    sleep 1
done
sleep 60
if [ -d /sys/module/rekernel_x ]; then
    rm -f "$MODDIR/.boot-pending"
    echo "Boot completed and 60-second observation window passed." >> "$MODDIR/load.log"
    sync
fi
