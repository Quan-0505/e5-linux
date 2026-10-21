"""Run the shared DWC3 host/sink C regressions against the 41S ABI."""
from pathlib import Path
import runpy
import unittest

HostSink = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'common/test_dwc3_host_sink.py'))['HostSink']

if __name__ == '__main__':
    unittest.main()
