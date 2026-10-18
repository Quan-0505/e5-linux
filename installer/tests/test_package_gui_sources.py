import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from package_gui import source_digest_bytes


class PackageGuiSources(unittest.TestCase):
    def test_text_source_fingerprint_is_line_ending_independent(self):
        lf = b"first line\nsecond line\n"
        crlf = lf.replace(b"\n", b"\r\n")
        expected = hashlib.sha256(lf).hexdigest()
        self.assertEqual(source_digest_bytes(lf), expected)
        self.assertEqual(source_digest_bytes(crlf), expected)


if __name__ == "__main__":
    unittest.main()
