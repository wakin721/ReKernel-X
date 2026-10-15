/*
 * Copyright (c) 2026 myflavor <admin@myflv.cn>. All rights reserved.
 * Based on Re-Kernel project by nep_timeline@outlook.com.
 * Transport starts early; hooks are activated after Android UI readiness.
 */
#include "rkx_log.h"
#include "rkx.h"
#include <linux/printk.h>
#include <linux/module.h>
#include <linux/init.h>
#include <linux/tracepoint.h>
#include <linux/mutex.h>
#include <linux/kstrtox.h>

static DEFINE_MUTEX(rkx_lifecycle_lock);
static bool hooks_enabled;
static bool rkx_initialized;

static void rkx_stop_hooks(void)
{
	rkx_unregister_binder_kp();
	rkx_unregister_netfilter();
	rkx_unregister_signal();
	rkx_unregister_binder();
	tracepoint_synchronize_unregister();
}

static int rkx_hooks_param_set(const char *value, const struct kernel_param *param)
{
	bool enable;
	int rc = kstrtobool(value, &enable);

	if (rc)
		return rc;
	mutex_lock(&rkx_lifecycle_lock);
	if (!enable) {
		rc = hooks_enabled ? -EPERM : 0;
		goto out;
	}
	if (!rkx_initialized) {
		rc = -EAGAIN;
		goto out;
	}
	if (hooks_enabled)
		goto out;

	rkx_log_info("stage=hooks activating\n");
	rc = rkx_register_binder();
	if (rc)
		goto rollback;
	rc = rkx_register_signal();
	if (rc)
		goto rollback;
	rc = rkx_register_netfilter();
	if (rc)
		goto rollback;
	rkx_register_binder_kp();
	WRITE_ONCE(hooks_enabled, true);
	rkx_log_info("stage=hooks active\n");
	goto out;
rollback:
	rkx_stop_hooks();
	rkx_log_err("stage=hooks failed rc=%d; transport retained\n", rc);
out:
	mutex_unlock(&rkx_lifecycle_lock);
	return rc;
}

static const struct kernel_param_ops rkx_hooks_ops = {
	.set = rkx_hooks_param_set,
	.get = param_get_bool,
};
module_param_cb(hooks_enabled, &rkx_hooks_ops, &hooks_enabled, 0600);
MODULE_PARM_DESC(hooks_enabled, "One-way hook activation after Android UI readiness; default off");

static int __init start_rekernel(void)
{
	int rc;

	rkx_log_info("Version %s | stage=transport starting\n", RKX_VERSION);
	rkx_init_net_uid();
	rkx_init_free_async();
	rc = rkx_register_genl();
	if (rc) {
		rkx_destroy_free_async();
		rkx_destroy_net_uid();
		return rc;
	}
	mutex_lock(&rkx_lifecycle_lock);
	rkx_initialized = true;
	mutex_unlock(&rkx_lifecycle_lock);
	rkx_log_info("stage=transport ready; hooks disabled\n");
	return 0;
}

static void __exit exit_rekernel(void)
{
	mutex_lock(&rkx_lifecycle_lock);
	rkx_initialized = false;
	rkx_stop_hooks();
	WRITE_ONCE(hooks_enabled, false);
	rkx_unregister_genl();
	rkx_destroy_free_async();
	rkx_destroy_net_uid();
	mutex_unlock(&rkx_lifecycle_lock);
}

module_init(start_rekernel);
module_exit(exit_rekernel);
MODULE_LICENSE("GPL");
