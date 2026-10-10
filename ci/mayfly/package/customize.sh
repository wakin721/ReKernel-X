SKIPUNZIP=0
MODDIR="$MODPATH"
. "$MODDIR/compatibility.sh"
rkx_check_compatibility || abort "$RKX_ERROR"
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
set_perm "$MODPATH/service.sh" 0 0 0755
ui_print "Validated compatible mayfly kernel: $(uname -r)"
ui_print "ReKernel-X 1.6: native CFI and symbol version checks retained"
ui_print "Reboot to load. Verified compatible updates reuse this module."
