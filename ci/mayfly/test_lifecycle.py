"""Execute the actual module lifecycle with kernel registration boundaries stubbed."""
import pathlib
import re
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
STUBS = r'''
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <errno.h>
#define __init
#define __exit
#define LINE_SUCCESS 0
#define LINE_ERROR -1
#define RKX_VERSION "test"
#define module_init(fn)
#define module_exit(fn)
#define MODULE_LICENSE(s)
#define rkx_log_info(...) ((void)0)
#define rkx_log_debug(...) ((void)0)
#define rkx_log_err(...) ((void)0)
#define DEFINE_MUTEX(name) int name
#define mutex_lock(p) ((void)0)
#define mutex_unlock(p) ((void)0)
#define READ_ONCE(x) (x)
#define WRITE_ONCE(x,v) ((x)=(v))
struct kernel_param { void *arg; };
struct kernel_param_ops { int (*set)(const char *, const struct kernel_param *); int (*get)(char *, const struct kernel_param *); };
#define module_param_cb(name,ops,arg,mode)
#define MODULE_PARM_DESC(name,s)
static int net, rules, genl, binder, signal_hook, nf, kp, fail;
void rkx_init_net_uid(void) { net=1; }
void rkx_destroy_net_uid(void) { net=0; }
void rkx_init_free_async(void) { rules=1; }
void rkx_destroy_free_async(void) { rules=0; }
int rkx_register_genl(void) { if(fail==1) return -12; genl=1; return 0; }
void rkx_unregister_genl(void) { genl=0; }
int rkx_register_binder(void) { if(fail==2) return -22; binder=1; return 0; }
void rkx_unregister_binder(void) { binder=0; }
int rkx_register_signal(void) { if(fail==3) return -22; signal_hook=1; return 0; }
void rkx_unregister_signal(void) { signal_hook=0; }
int rkx_register_netfilter(void) { if(fail==4) return -22; nf=1; return 0; }
void rkx_unregister_netfilter(void) { nf=0; }
void rkx_register_binder_kp(void) { kp=1; }
void rkx_unregister_binder_kp(void) { kp=0; }
void tracepoint_synchronize_unregister(void) {}
int kstrtobool(const char *s, bool *b) { if(!strcmp(s,"1")){*b=true;return 0;} if(!strcmp(s,"0")){*b=false;return 0;} return -EINVAL; }
int param_get_bool(char *buf,const struct kernel_param *p) { return sprintf(buf,"%c",*(bool*)p->arg?'Y':'N'); }
'''


class LifecycleTests(unittest.TestCase):
    def run_case(self, body):
        source = (ROOT / 'LKM-Source/rkx.c').read_text()
        source = re.sub(r'^#include[^\n]*\n', '', source, flags=re.M)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'probe.c').write_text(STUBS + source + '\nint main(void) {\n' + body + '\n}\n')
            compile_result = subprocess.run(['cc', '-std=gnu11', '-o', str(path / 'probe'), str(path / 'probe.c')], capture_output=True, text=True)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            result = subprocess.run([str(path / 'probe')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_boot_exposes_transport_without_activating_hooks(self):
        self.run_case('''
if(start_rekernel()!=0 || !genl || !net || !rules) return 10;
if(binder || signal_hook || nf || kp) { fprintf(stderr,"Hooks activated during early init\\n"); return 11; }
exit_rekernel();
if(genl || net || rules || binder || signal_hook || nf || kp) return 12;
return 0;
''')

    def test_transport_failure_cleans_up_resources(self):
        self.run_case('''
fail=1; if(start_rekernel()==0) return 10;
if(genl || net || rules || binder || signal_hook || nf || kp) return 11;
return 0;
''')

    def test_activation_waits_for_initialized_transport(self):
        self.run_case('''
struct kernel_param p={.arg=&hooks_enabled};
if(rkx_hooks_param_set("1",&p)!=-EAGAIN) return 10;
if(binder || signal_hook || nf || kp) return 11;
return 0;
''')

    def test_hooks_activate_once_and_cannot_be_torn_down_live(self):
        self.run_case('''
struct kernel_param p={.arg=&hooks_enabled};
if(start_rekernel() || rkx_hooks_param_set("1",&p)) return 10;
if(!hooks_enabled || !binder || !signal_hook || !nf || !kp || !genl) return 11;
if(rkx_hooks_param_set("1",&p)) return 12;
if(rkx_hooks_param_set("0",&p)!=-EPERM || !hooks_enabled || !binder) return 13;
exit_rekernel();
if(genl || net || rules || binder || signal_hook || nf || kp) return 14;
return 0;
''')

    def test_failed_activation_rolls_back_hooks_but_preserves_transport(self):
        for stage in (2, 3, 4):
            with self.subTest(stage=stage):
                self.run_case('''
struct kernel_param p={.arg=&hooks_enabled};
if(start_rekernel()) return 10;
fail=STAGE;
if(rkx_hooks_param_set("1",&p)==0) return 11;
if(hooks_enabled || binder || signal_hook || nf || kp || !genl) return 12;
fail=0;
if(rkx_hooks_param_set("1",&p) || !hooks_enabled) return 13;
exit_rekernel(); return 0;
'''.replace('STAGE', str(stage)))


if __name__ == '__main__':
    unittest.main()
