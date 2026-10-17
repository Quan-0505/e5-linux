#!/usr/bin/env python3
"""Exercise a real WAL writer snapshot and verify resumed processes/new code."""
from pathlib import Path
import os,sqlite3,subprocess,sys,tarfile,tempfile

TOP=Path(__file__).resolve().parents[2]
helper=TOP/'openwrt/network-addons/overlay/usr/libexec/e5-network-addons-snapshot'
with tempfile.TemporaryDirectory() as temp:
    root=Path(temp);old=root/'old';data=old/'etc/daed'
    data.mkdir(parents=True)
    app=old/'usr/local/owjdxb/bin';app.mkdir(parents=True)
    (app/'owjdxb').write_text('old binary must not overwrite new image')
    (app/'.dmac').write_text('synthetic local identity')
    writer=subprocess.Popen([sys.executable,'-u','-c',
        'import sqlite3,time,sys; c=sqlite3.connect(sys.argv[1]); c.execute("PRAGMA journal_mode=WAL"); c.execute("CREATE TABLE test(value INTEGER)"); c.execute("INSERT INTO test VALUES (42)"); c.commit(); print("ready",flush=True); time.sleep(120)',str(data/'wing.db')],stdout=subprocess.PIPE,text=True)
    try:
        assert writer.stdout.readline().strip()=='ready'
        bindir=root/'bin';bindir.mkdir()
        fake=bindir/'pidof';fake.write_text('#!/bin/sh\n[ "$1" != daed ] || echo '+str(writer.pid)+'\n');fake.chmod(0o755)
        exclude=root/'exclude';exclude.write_text('usr/local/owjdxb/bin/owjdxb\n')
        archive=root/'settings.tar'
        env={**os.environ,'PATH':str(bindir)+os.pathsep+os.environ['PATH']}
        subprocess.run(['sh',str(helper),str(old),str(archive),str(exclude),'etc/daed','usr/local/owjdxb'],check=True,env=env)
        assert '\nState:\tT' not in Path('/proc/'+str(writer.pid)+'/status').read_text(), 'Writer left suspended'
        target=root/'restored';target.mkdir()
        with tarfile.open(archive) as tar:
            assert 'usr/local/owjdxb/bin/owjdxb' not in tar.getnames()
            tar.extractall(target,filter='data')
        with sqlite3.connect(target/'etc/daed/wing.db') as db:
            assert db.execute('SELECT value FROM test').fetchone()[0]==42
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        assert (target/'usr/local/owjdxb/bin/.dmac').read_text()=='synthetic local identity'
        # Force archive failure and prove the EXIT trap still resumes the writer.
        result=subprocess.run(['sh',str(helper),str(old),str(root/'missing/out.tar'),str(exclude),'etc/daed'],env=env,capture_output=True)
        assert result.returncode!=0
        assert '\nState:\tT' not in Path('/proc/'+str(writer.pid)+'/status').read_text(), 'Failed snapshot left writer suspended'
    finally:
        writer.terminate();writer.wait(timeout=10)
print('Internal update state: live WAL + identity preserved, old binary excluded, all exit paths resume writers: PASS')
