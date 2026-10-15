SKIPUNZIP=0
MODDIR="$MODPATH"
. "$MODDIR/compatibility.sh"
rkx_check_compatibility || abort "$RKX_ERROR"
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
set_perm "$MODPATH/service.sh" 0 0 0755
ui_print "Validated compatible mayfly kernel: $(uname -r)"
ui_print "ReKernel-X staged diagnostic: native CFI and CRC checks retained"
ui_print "Unlock within 10 minutes after reboot to activate hooks."
ui_print "Netlink starts early; hooks wait for healthy SystemUI and Keyguard."
