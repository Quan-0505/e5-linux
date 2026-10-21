"""Keep the 41S Type-C ABI while sharing the UMS9620 DWC3 host/sink path."""
from pathlib import Path
import runpy


def apply(kernel):
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'common/dwc3-host-sink.py'))['apply'](
        kernel, api_prefix='yh41s', api_header='yh41s-host-sink.h')


if __name__ == '__main__':
    import sys
    apply(sys.argv[1])
