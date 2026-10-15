#!/system/bin/sh
MODDIR=${0%/*}
LOG="$MODDIR/load.log"
[ -e "$MODDIR/.boot-pending" ] || exit 0

rkx_fail() {
    echo "$*; disabled for next boot; failed-boot marker retained." >> "$LOG"
    touch "$MODDIR/disable"
    sync
    exit 1
}

rkx_uptime() {
    cut -d. -f1 /proc/uptime
}

rkx_ui_ready() {
    [ "$(getprop sys.boot_completed)" = 1 ] || return 1
    rkx_ui_pid=$(pidof com.android.systemui) || return 1
    [ -n "$rkx_ui_pid" ] || return 1
    rkx_users=$(timeout 5 dumpsys user) || return 1
    printf '%s\n' "$rkx_users" | awk '
        /Started users state:/ {
            gsub(/[][]|,/, " ")
            for (i=1; i<=NF; i++) if ($i == "0=RUNNING_UNLOCKED") unlocked=1
        }
        END { exit !unlocked }
        ' || return 1
    rkx_services=$(timeout 5 dumpsys activity services com.android.systemui) || return 1
    printf '%s\n' "$rkx_services" | awk -v pid="$rkx_ui_pid" '
        /^[ \t]*\* ServiceRecord/ {
            systemui = ($0 ~ /com.android.systemui\/\.SystemUIService /)
            keyguard = ($0 ~ /com.android.systemui\/\.keyguard.KeyguardService /)
        }
        /app=ProcessRecord/ {
            if (index($0, " " pid ":com.android.systemui/")) {
                if (systemui) s=1
                if (keyguard) k=1
            }
        }
        /CR.*DEAD.*com.android.systemui\/\.keyguard.KeyguardService/ { dead=1 }
        END { exit !(s && k && !dead) }
        ' || return 1
    rkx_activities=$(timeout 5 dumpsys activity activities) || return 1
    if printf '%s\n' "$rkx_activities" | grep -qE '(mCurrentFocus|mFocusedApp|[Tt]opResumedActivity|[Rr]esumedActivity)[=:].*FallbackHome'; then
        return 1
    fi
    return 0
}

echo "stage=waiting-ui uptime=$(rkx_uptime); unlock within 600 seconds to enable hooks." >> "$LOG"
rkx_deadline=$(($(rkx_uptime) + 600))
rkx_ready_since=
rkx_stable_pid=
while :; do
    [ ! -e "$MODDIR/disable" ] || rkx_fail "Module disabled while waiting"
    rkx_now=$(rkx_uptime)
    [ "$rkx_now" -lt "$rkx_deadline" ] || rkx_fail "UI readiness timeout; hooks remain off"
    if rkx_ui_ready; then
        if [ "$rkx_stable_pid" != "$rkx_ui_pid" ] || [ -z "$rkx_ready_since" ]; then
            rkx_ready_since=$rkx_now
            rkx_stable_pid=$rkx_ui_pid
        elif [ $((rkx_now - rkx_ready_since)) -ge 10 ]; then
            break
        fi
    else
        rkx_ready_since=
        rkx_stable_pid=
    fi
    sleep 2
done

echo "stage=hooks activating uptime=$(rkx_uptime) systemui_pid=$rkx_stable_pid" >> "$LOG"
echo 1 | tee /sys/module/rekernel_x/parameters/hooks_enabled >/dev/null || rkx_fail "Hook activation failed"
[ "$(cat /sys/module/rekernel_x/parameters/hooks_enabled)" = Y ] || rkx_fail "Hook activation not confirmed"
echo "stage=hooks active uptime=$(rkx_uptime); observing UI for 60 seconds." >> "$LOG"
rkx_observe_until=$(($(rkx_uptime) + 60))
while [ "$(rkx_uptime)" -lt "$rkx_observe_until" ]; do
    rkx_ui_ready || rkx_fail "UI health lost after hook activation"
    [ "$rkx_ui_pid" = "$rkx_stable_pid" ] || rkx_fail "SystemUI restarted after hook activation"
    [ ! -e "$MODDIR/disable" ] || rkx_fail "Module disabled during observation"
    sleep 2
done
rkx_ui_ready || rkx_fail "UI health lost at end of observation"
[ "$rkx_ui_pid" = "$rkx_stable_pid" ] || rkx_fail "SystemUI changed at end of observation"
[ ! -e "$MODDIR/disable" ] || rkx_fail "Module disabled at end of observation"
rm -f "$MODDIR/.boot-pending"
echo "stage=healthy uptime=$(rkx_uptime); UI and 60-second hook observation passed." >> "$LOG"
sync
