"""Exercise the generated PB8 clock guard, error handling and profile scope."""
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
apply = runpy.run_path(str(HERE / 'display-clock.py'))['apply']
ANCHOR = '\t\tclk_pixelpll_div = calc_div_of_pixelpll(ctx->vm.pixelclock);'


class Clock(unittest.TestCase):
    def test_scoped_patch_is_idempotent_and_rejects_unknown_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'drivers/unisoc_platform/sprd_disp/qogirn6lite/global_dpu.c'
            path.parent.mkdir(parents=True)
            path.write_text(ANCHOR)
            apply(tmp)
            first = path.read_bytes()
            apply(tmp)
            self.assertEqual(first, path.read_bytes())
            path.write_text('unrecognized layout')
            with self.assertRaises(ValueError):
                apply(tmp)
            self.assertEqual(path.read_text(), 'unrecognized layout')

    @unittest.skipUnless(shutil.which('cc'), 'C compiler required')
    def test_real_generated_fragment_preserves_other_panels_and_propagates_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'drivers/unisoc_platform/sprd_disp/qogirn6lite/global_dpu.c'
            path.parent.mkdir(parents=True)
            path.write_text(ANCHOR)
            apply(root)
            fragment = path.read_text().split(ANCHOR, 1)[1]
            (root / 'clock.c').write_text('''
#include <assert.h>
#include <string.h>
#define pr_err(...) ((void)0)
struct mode { unsigned long pixelclock; };
struct context { struct mode vm; };
struct panel { struct { const char *of_node; } info; };
struct clocks { void *clk_dpi_pixelpll; };
static int calls, fail;
static unsigned long requested;
static int of_node_name_eq(const char *a, const char *b) { return !strcmp(a,b); }
static int clk_set_rate(void *clk, unsigned long rate) {
    assert(clk == (void *)1); calls++; requested=rate; return fail;
}
static int configure(const char *name, unsigned long rate, int div) {
    struct context c={.vm={.pixelclock=rate}}, *ctx=&c;
    struct panel p={.info={.of_node=name}}, *panel=&p;
    struct clocks k={.clk_dpi_pixelpll=(void *)1}, *clk_ctx=&k;
    unsigned int clk_pixelpll_div=div;
    int ret;
''' + fragment + '''
    return 0;
}
int main(void) {
    const char *pb8="lcd_ili9488_easyquick_mipi_fhd";
    assert(configure(pb8,16000000,16)==0);
    assert(calls==1 && requested==2048000000UL);
    assert(requested>=1600000000UL && requested<=3200000000UL);
    assert(requested/16/8==16000000UL);
    calls=0;
    assert(configure("lcd_ili9488_ruiheng_mipi_hvga",16000000,16)==0);
    assert(configure(pb8,16000001,16)==0);
    assert(configure(pb8,16000000,8)==0);
    assert(calls==0);
    fail=-5;
    assert(configure(pb8,16000000,16)==-5);
    assert(calls==1);
}
''')
            subprocess.run(['cc', '-Wall', '-Werror', str(root / 'clock.c'),
                            '-o', str(root / 'clock')], check=True)
            subprocess.run([str(root / 'clock')], check=True)


if __name__ == '__main__':
    unittest.main()
