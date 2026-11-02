#!/usr/bin/env python3
"""Exercise clean baseline, policy idempotence and provenance rejection in Git fixtures."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

TOP = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('prepare_kernel', TOP / 'tools/prepare-release-kernel.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def git(directory, *args):
    return subprocess.check_output(['git', '-C', str(directory),
        '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args], text=True).strip()


class Preparation(unittest.TestCase):
    def fixture(self, root, idempotent=True):
        top = root / 'source'; top.mkdir()
        kernel = root / 'kernel'; kernel.mkdir()
        for path in (top, kernel):
            git(path, 'init', '-q')
        (kernel / 'config').write_text('BASE\n')
        git(kernel, 'add', '.'); git(kernel, 'commit', '-qm', 'base')
        baseline = git(kernel, 'rev-parse', 'HEAD')
        (top / 'upstream').mkdir()
        shutil.copyfile(TOP / 'upstream/check-kernel-source.py', top / 'upstream/check-kernel-source.py')
        (top / 'upstream/kernel-source.json').write_text(json.dumps({'minimum_revision': baseline}))
        (top / 'policy.py').write_text(
            'from pathlib import Path\nimport sys\np=Path(sys.argv[1])/"config"\ns=p.read_text()\n' +
            ('if "POLICY" not in s:p.write_text(s+"POLICY\\n")\n' if idempotent else 'p.write_text(s+"POLICY\\n")\n'))
        git(top, 'add', '.'); git(top, 'commit', '-qm', 'source')
        return top, kernel

    def test_prepared_tree_is_clean_and_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            top, kernel = self.fixture(Path(folder))
            with patch.object(policy, 'TOP', top), patch.object(policy, 'POLICIES', ('policy.py',)):
                policy.prepare(kernel)
                self.assertEqual(git(kernel, 'status', '--porcelain'), '')
                policy.verify(kernel)
                (top / 'policy.py').write_text('changed policy\n')
                with self.assertRaisesRegex(ValueError, 'input changed'):
                    policy.verify(kernel)

    def test_dirty_baseline_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            top, kernel = self.fixture(Path(folder))
            (kernel / 'config').write_text('unexpected\n')
            with patch.object(policy, 'TOP', top), patch.object(policy, 'POLICIES', ('policy.py',)):
                with self.assertRaisesRegex(ValueError, 'uncommitted'):
                    policy.prepare(kernel)

    def test_nonidempotent_policy_rejected_before_commit(self):
        with tempfile.TemporaryDirectory() as folder:
            top, kernel = self.fixture(Path(folder), idempotent=False)
            baseline = git(kernel, 'rev-parse', 'HEAD')
            with patch.object(policy, 'TOP', top), patch.object(policy, 'POLICIES', ('policy.py',)):
                with self.assertRaisesRegex(ValueError, 'not idempotent'):
                    policy.prepare(kernel)
            self.assertEqual(git(kernel, 'rev-parse', 'HEAD'), baseline)


if __name__ == '__main__':
    unittest.main()
