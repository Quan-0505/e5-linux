#!/usr/bin/env python3
"""Execute imported build control flow with fake commands, without compiling firmware."""
from pathlib import Path
import os
import subprocess
import tempfile

TOP = Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    bindir = root / 'bin'
    bindir.mkdir()
    log = root / 'docker.log'
    fake = bindir / 'docker'
    fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_LOG"\n')
    fake.chmod(0o755)
    env = dict(os.environ, PATH=str(bindir) + ':' + os.environ['PATH'], TEST_LOG=str(log))
    for name in ('build-hostapd.sh', 'build-bluez.sh'):
        source = (TOP / 'openwrt' / name).read_text()
        # Architecture selection and container launch are executed verbatim.
        section = source[source.index('case "$(uname -m)"'):]
        if name == 'build-hostapd.sh':
            section = section[:section.index('\npython3 ')]
        else:
            section = section[:section.index("\nexport DEBIAN_FRONTEND")]
            section = section[:section.rindex("bash -euc '")] + 'true\n'
        for machine, platform in (('x86_64', 'linux/amd64'), ('aarch64', 'linux/arm64'), ('arm64', 'linux/arm64')):
            log.write_text('')
            script = f'''set -eu
uname() {{ echo {machine}; }}
TOP={root} OUT={root} WORK={root} VER=25.12.5 E5REV=1 stamp=test
{section}
'''
            subprocess.run(['bash', '-c', script], env=env, check=True)
            assert '--platform ' + platform in log.read_text(), (name, machine, log.read_text())
    # merge_config creates scratch files in cwd. Run the actual new command with
    # a merger that refuses a source cwd, including paths containing spaces.
    source_dir = root / 'kernel source'
    (source_dir / 'scripts/kconfig').mkdir(parents=True)
    output = root / 'object dir'
    output.mkdir()
    merger = source_dir / 'scripts/kconfig/merge_config.sh'
    merger.write_text('#!/bin/sh\n[ "$PWD" = "$O" ] || exit 71\n[ "$3" = "$O" ] || exit 72\ntouch .merge-ran\n')
    merger.chmod(0o755)
    for name in ('build.sh', 'build-native.sh'):
        source = (TOP / 'upstream' / name).read_text()
        lines = source.splitlines()
        index = next(i for i, line in enumerate(lines) if line.startswith('kernel_merge_config='))
        section = '\n'.join(lines[index:index + 2])
        subprocess.run(['bash', '-ec', section], cwd=source_dir,
                       env=dict(os.environ, O=str(output), CFG=str(root / 'config')), check=True)
        assert (output / '.merge-ran').exists()
        (output / '.merge-ran').unlink()
    # Fresh host-tool caches build tools first, then the target toolchain.
    inner = (TOP / 'openwrt/build-hostapd-inner.sh').read_text()
    section = '\n'.join(line for line in inner.splitlines() if line.startswith('ls staging_dir/'))
    assert len(section.splitlines()) == 2
    calls = root / 'calls'
    for prepared in (False, True):
        if prepared:
            for name in ('staging_dir/host/bin/openssl', 'staging_dir/toolchain-test/bin/test-gcc'):
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()
        subprocess.run(['sh', '-ec', 'make() { echo "$*" >> "$CALLS"; };\n' + section], cwd=root,
                       env=dict(os.environ, CALLS=str(calls)), check=True)
        expected = '-j4 tools/install\n-j4 toolchain/install\n'
        assert calls.read_text() == expected
    packaging = (TOP / 'openwrt/make-flash-bundle.sh').read_text()
    assert '--user "$(id -u):$(id -g)"' in packaging
    assert '[ ! -O "$P/files/e5-bootctl" ]' in packaging
print('Build architecture, fresh cache, merge cwd and helper ownership checks passed')
