SKIPUNZIP=0
[ "$(getprop ro.product.device)" = "mayfly" ] || abort "Unsupported device: only mayfly"
[ "$(uname -r)" = "5.10.260-gki-gef362912d37b" ] || abort "Kernel release mismatch"
[ -r /proc/config.gz ] || abort "Cannot verify kernel configuration"
config_hash=$(zcat /proc/config.gz | sha256sum | cut -d ' ' -f 1)
[ "$config_hash" = "0eae19ac5cf26d9314ab4de5eae1e7e4419f43e12c1042e3b6f90a75e0dec4e5" ] || abort "Kernel configuration mismatch"
set_perm_recursive "$MODPATH" 0 0 0755 0644
set_perm "$MODPATH/post-fs-data.sh" 0 0 0755
set_perm "$MODPATH/service.sh" 0 0 0755
ui_print "Matched LineageOS mayfly kernel and configuration"
ui_print "ReKernel-X 1.6: native CFI and symbol version checks retained"
ui_print "Reboot to load. Kernel changes require a new matching build."
