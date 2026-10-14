#!/usr/bin/env python3
"""Positive and negative packaging checks using the actual staged public payload."""
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
import tempfile

TOP = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('addons', TOP / 'tools/stage-network-addons.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as temp:
    tmp = Path(temp)
    root = tmp / 'root'
    for name in ['sbin/init', 'sbin/ip', 'sbin/tc', 'etc/openwrt_release']:
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('fixture\n')
    module.stage(root)
    fake = tmp / 'fixture-source/upstream/out-release'
    fake.mkdir(parents=True)
    options = ['NETKIT', 'VETH', 'BPF_SYSCALL', 'BPF_JIT', 'DEBUG_INFO_BTF', 'NET_CLS_ACT', 'NET_CLS_BPF', 'NET_SCH_INGRESS', 'NET_ACT_BPF', 'TUN']
    (fake / 'config').write_text(''.join('CONFIG_' + o + '=y\n' for o in options))
    module.TOP = tmp / 'fixture-source'
    archive = tmp / 'root.tar'
    def pack():
        with tarfile.open(archive, 'w') as tar:
            tar.add(root, arcname='.')
    pack()
    module.verify(archive)
    p = root / 'usr/bin/daed'
    real = p.read_bytes()
    p.write_bytes(real[:-1] + bytes([real[-1] ^ 1]))
    pack()
    try:
        module.verify(archive)
        raise RuntimeError('Corrupted binary incorrectly accepted')
    except AssertionError:
        pass
    p.write_bytes(real)
    (root / 'etc/daed-kdae').mkdir()
    (root / 'etc/daed-kdae/wing.db').write_text('private fixture')
    pack()
    try:
        module.verify(archive)
        raise RuntimeError('Personal state incorrectly accepted')
    except AssertionError:
        pass

    old, new = tmp / 'old', tmp / 'new'
    (old / 'etc/daed-kdae').mkdir(parents=True)
    (old / 'usr/local/owjdxb/bin').mkdir(parents=True)
    (new / 'etc/e5').mkdir(parents=True)
    (new / 'usr/local/owjdxb/bin').mkdir(parents=True)
    meta = {'nodebaby_software_files':['usr/local/owjdxb/bin/owjdxb']}
    (new / 'etc/e5/network-addons.json').write_text(json.dumps(meta))
    (old / 'usr/local/owjdxb/bin/owjdxb').write_text('old software')
    (new / 'usr/local/owjdxb/bin/owjdxb').write_text('new software')
    (old / 'usr/local/owjdxb/bin/.dmac').write_text('synthetic identity')
    # Keep the connection open with a committed WAL transaction.
    db = sqlite3.connect(old / 'etc/daed-kdae/wing.db')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE test(value TEXT)')
    db.execute("INSERT INTO test VALUES ('synthetic account')")
    db.commit()
    helper = TOP / 'openwrt/network-addons/overlay/usr/libexec/e5-network-addons-preserve'
    subprocess.run([sys.executable, str(helper), str(old), str(new)], check=True)
    with sqlite3.connect(new / 'etc/daed-kdae/wing.db') as dest:
        assert dest.execute('SELECT value FROM test').fetchone()[0] == 'synthetic account'
    assert (new / 'usr/local/owjdxb/bin/owjdxb').read_text() == 'new software'
    assert (new / 'usr/local/owjdxb/bin/.dmac').read_text() == 'synthetic identity'
    db.close()
print('Positive payload, corrupt binary rejection, privacy rejection, live WAL preservation, new software retention: PASS')
