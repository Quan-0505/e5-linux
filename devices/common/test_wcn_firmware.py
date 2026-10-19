#!/usr/bin/env python3
"""Execute the generated WCN downloader with a mocked SDIO bus and firmware API.

Usage: python3 devices/common/test_wcn_firmware.py /path/to/pinned/kernel
No device access. The baseline comes from that kernel's committed source.
"""
from pathlib import Path
import os
import runpy
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
PATCH = runpy.run_path(str(HERE / 'wcn-firmware.py'))
KERNEL = Path(os.environ['E5_WCN_KERNEL']) if os.environ.get('E5_WCN_KERNEL') else None
if __name__ == '__main__' and len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
    KERNEL = Path(sys.argv.pop(1))

HARNESS = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <limits.h>
typedef uint8_t u8;
typedef uint32_t u32;
#define BIT(n) (1U << (n))
#define ARRAY_SIZE(a) (sizeof(a)/sizeof((a)[0]))
#define DIV_ROUND_UP(n,d) (((n)+(d)-1)/(d))
#define PACKET_SIZE 32768
#define SEC_IMAGE_MAGIC 0x42544844U
#define SEC_IMAGE_HDR_SIZE 512U
#define pr_info(...) ((void)0)
#define pr_err(...) ((void)0)
struct firmware { size_t size; const u8 *data; } fw;
struct sys_img_header { u32 magic_num; u8 reserved[72]; u32 img_real_size, img_signed_size; };
static struct { bool is_btwf_in_sysfs; char write_buffer[PACKET_SIZE]; } dev;
static __typeof__(dev) *marlin_dev = &dev;
static struct wcn_match_data { bool unisoc_wcn_m3lite; } match;
static struct wcn_match_data *g_match_config = &match;
static struct wcn_match_data *get_wcn_match_config(void) { return g_match_config; }
static const u8 *expected;
static size_t expected_size, written;
static void *allocation;
static int reg_ops, fail_reg, fuse, released, data_ops, fail_data, fail_alloc, partition_calls;
static u32 regs[4];
static const u32 addresses[] = { 0x4083c32c, 0x4083c024, 0x4083c050, 0x40858040 };
static const u32 masks[] = { BIT(22), BIT(11), BIT(18), BIT(0) };
static int sprdwcn_bus_reg_read(u32 addr, void *data, int len) {
 assert(len==4);
 if (++reg_ops==fail_reg) return -EIO;
 if (addr==0x40859030) { *(u32 *)data=(u32)fuse<<29; return 0; }
 for (int i=0;i<4;i++) if (addr==addresses[i]) { *(u32 *)data=regs[i]; return 0; }
 abort();
}
static int sprdwcn_bus_reg_write(u32 addr, void *data, int len) {
 assert(len==4);
 if (++reg_ops==fail_reg) return -EIO;
 for (int i=0;i<4;i++) if (addr==addresses[i]) {
  assert(*(u32 *)data==(regs[i]|masks[i])); regs[i]=*(u32 *)data; return 0;
 }
 /* No writes to eFuse data/programming registers are permitted. */
 abort();
}
static int request_firmware(const struct firmware **out, const char *name, void *device) {
 (void)device; assert(!strcmp(name,"wcnmodem.bin")); *out=&fw; return 0;
}
static void release_firmware(const struct firmware *f) { assert(f==&fw); released++; }
static void *vmalloc(size_t n) { assert(!allocation); return allocation=fail_alloc?NULL:malloc(n); }
static void vfree(void *p) { assert(p && p==allocation); free(p); allocation=NULL; }
static int marlin_download_from_partition(void) { partition_calls++; return 42; }
static unsigned int get_cp_start_addr(void) { return 0x100000; }
static int sprdwcn_bus_direct_write(unsigned int address, void *data, int length) {
 if (++data_ops==fail_data) return -EIO;
 assert(address==get_cp_start_addr()+written);
 assert(length>0 && length<=PACKET_SIZE);
 assert(written+(size_t)length<=expected_size);
 assert(!memcmp(data,expected+written,length)); written+=length; return 0;
}
/* HEADER */
/* DOWNLOADER */
static void reset(void) {
 assert(!allocation); memset(&dev,0,sizeof(dev)); match.unisoc_wcn_m3lite=true;
 reg_ops=fail_reg=fuse=released=data_ops=fail_data=fail_alloc=partition_calls=0;
 written=0; for(int i=0;i<4;i++) regs[i]=0x80;
 /* RESET_CACHE */
}
static void run(size_t size, bool lite, int efuse, size_t offset, size_t length) {
 reset(); match.unisoc_wcn_m3lite=lite; fuse=efuse;
 u8 *image=malloc(size); assert(image); memset(image,0x11,size);
 if(size==0x300000) memset(image+0x180000,0x22,0x180000);
 fw=(struct firmware){size,image}; expected=image+offset; expected_size=length;
 assert(btwifi_download_firmware()==0);
 assert(written==length && released==1 && !allocation);
 assert(data_ops==(int)DIV_ROUND_UP(length,PACKET_SIZE));
 free(image);
}
int main(void) {
 /* First case also makes the original downloader fail its payload assertion. */
 run(0x300000,true,1,0x180000,0xe73b0);
 for(int efuse=0;efuse<4;efuse++) {
  run(0x300000,true,efuse,efuse==1?0x180000:0,efuse==1?0xe73b0:0x300000);
  run(0x300000,false,efuse,0,0x300000); assert(reg_ops==0);
 }
 run(4096,true,1,0,4096); assert(reg_ops==0);
 run(0x180000,true,1,0,0x180000); assert(reg_ops==0);
 run(0x300000-1,true,1,0,0x300000-1); assert(reg_ops==0);
 run(0x300000+1,true,1,0,0x300000+1); assert(reg_ops==0);
#ifdef WCN_XPE_PACK_BYTES
 reset(); fuse=1;
 for(int i=0;i<4;i++) regs[i]|=masks[i];
 assert(wcn_read_xpe_fuse()==1 && reg_ops==5);
 for(int i=0;i<4;i++) assert(regs[i]==(0x80|masks[i]));
#endif
 reset(); g_match_config=NULL;
 u8 *image=calloc(1,0x300000+SEC_IMAGE_HDR_SIZE+16); assert(image);
 fw=(struct firmware){4096,image}; expected=image; expected_size=4096;
 assert(!btwifi_download_firmware() && written==4096 && reg_ops==0); g_match_config=&match;
 /* Signed wrapper: select inside the payload, free the owning allocation. */
 reset(); fuse=1;
 struct sys_img_header *h=(void *)image;
 h->magic_num=SEC_IMAGE_MAGIC; h->img_real_size=0x300000; h->img_signed_size=0x300000+SEC_IMAGE_HDR_SIZE+16;
 memset(image+SEC_IMAGE_HDR_SIZE,0x11,0x300000);
 memset(image+SEC_IMAGE_HDR_SIZE+0x180000,0x22,0x180000);
 fw=(struct firmware){h->img_signed_size,image}; expected=image+SEC_IMAGE_HDR_SIZE+0x180000; expected_size=0xe73b0;
 assert(!btwifi_download_firmware() && written==expected_size && !allocation && released==1);
 reset(); fuse=1; fail_data=2;
 assert(btwifi_download_firmware()==-EIO && !allocation && released==1);
 reset(); fail_alloc=1;
 assert(btwifi_download_firmware()<0 && !allocation && released==1 && data_ops==0);
 /* Every register read/write failure prevents an unverified image download. */
 for(int op=1;op<=9;op++) {
  reset(); fuse=1; fail_reg=op;
  assert(btwifi_download_firmware()==-EIO && data_ops==0 && released==1 && !allocation);
 }
 /* A failed eFuse read is not cached. A valid cached value avoids bus I/O. */
 reset(); fuse=1; fail_reg=1;
 assert(btwifi_download_firmware()==-EIO); fail_reg=0; released=0; reg_ops=0;
 expected=image+SEC_IMAGE_HDR_SIZE+0x180000; expected_size=0xe73b0;
 assert(!btwifi_download_firmware() && written==expected_size);
 reg_ops=written=released=data_ops=0;
 assert(!btwifi_download_firmware() && reg_ops==0 && written==expected_size);
 /* Malformed headers must not read beyond firmware or allocate/download. */
 for(size_t size=0;size<SEC_IMAGE_HDR_SIZE;size++) {
  reset(); fw=(struct firmware){size,image};
  assert(btwifi_download_firmware()<0 && released==1 && !allocation && data_ops==0);
 }
 reset(); fw=(struct firmware){SEC_IMAGE_HDR_SIZE+16,image}; h->img_real_size=UINT32_MAX;
 assert(btwifi_download_firmware()<0 && released==1 && !allocation && data_ops==0);
 reset(); dev.is_btwf_in_sysfs=true;
 assert(btwifi_download_firmware()==42 && partition_calls==1 && !released && !reg_ops);
 free(image); puts("PASS: XPE selection, unchanged formats, signed buffers, error cleanup and read cache");
 return 0;
}
'''


@unittest.skipUnless(KERNEL, 'pass the pinned kernel source path')
class Firmware(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        command = ['git', '-c', 'safe.directory=' + str(KERNEL), '-C', str(KERNEL),
                   'show', 'HEAD:' + PATCH['RELATIVE'].as_posix()]
        cls.baseline = subprocess.check_output(command, text=True)

    def stage(self, directory, source=None):
        path = directory / PATCH['RELATIVE']
        path.parent.mkdir(parents=True)
        path.write_text(self.baseline if source is None else source)
        return path

    def execute(self, directory, body, header='', baseline=False):
        start = body.index('static int btwifi_download_firmware(void)\n{')
        end = body.index('\nstatic int wcn_get_syscon_regmap(', start)
        code = HARNESS.replace('/* HEADER */', header).replace('/* DOWNLOADER */', body[start:end])
        code = code.replace('/* RESET_CACHE */', '' if baseline else 'wcn_xpe_fuse=-1;')
        source = directory / 'test.c'; binary = directory / 'test'
        source.write_text(code)
        subprocess.run(['cc', '-std=gnu11', '-g', '-O1', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', str(source), '-o', str(binary)], check=True)
        return subprocess.run([str(binary)], capture_output=True, text=True,
                              env=dict(os.environ, ASAN_OPTIONS='detect_leaks=1'))

    def test_generated_downloader_and_original_regression(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); path = self.stage(directory)
            old = self.execute(directory, self.baseline, baseline=True)
            self.assertNotEqual(old.returncode, 0)
            self.assertIn('Assertion', old.stderr)
            PATCH['apply'](directory)
            fixed = self.execute(directory, path.read_text(), (HERE / 'wcn-firmware.h').read_text())
            self.assertEqual(fixed.returncode, 0, fixed.stdout + fixed.stderr)

    def test_idempotent_and_unknown_downloader_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp); path = self.stage(directory)
            PATCH['apply'](directory); first = path.read_bytes()
            PATCH['apply'](directory); self.assertEqual(first, path.read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = self.baseline.replace('memcpy(buf, tx_img_ptr + len, trans_size);',
                                           'unknown_firmware_copy();')
            path = self.stage(directory, source)
            with self.assertRaises(ValueError): PATCH['apply'](directory)
            self.assertEqual(path.read_text(), source)
            self.assertFalse((path.parent / 'wcn-firmware.h').exists())

    def test_all_build_entrypoints(self):
        top = HERE.parents[1]
        for name in ('devices/e5/prepare-kernel.py', 'devices/t551m/prepare-kernel.py',
                     'devices/m8/prepare-kernel.py', 'upstream/build.sh', 'upstream/build-native.sh'):
            self.assertIn('wcn-firmware.py', (top / name).read_text(), name)
        self.assertIn('t551m/prepare-kernel.py', (top / 'devices/t512n/prepare-kernel.py').read_text())


if __name__ == '__main__':
    unittest.main()
