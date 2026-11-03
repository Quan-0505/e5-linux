#!/usr/bin/env python3
"""Guard E5 mainline config against unmet scheduler and wrong-SoC options."""
from pathlib import Path
import runpy
import unittest

TOP = Path(__file__).resolve().parents[2]
CONFIG = TOP / 'upstream/e5-mainline.config'
CHECKER = TOP / 'upstream/check-container-support.py'


def settings(path):
    result = {}
    for line in path.read_text().splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=', 1)
            result[key] = value
    return result


class E5MainlineConfig(unittest.TestCase):
    def test_utilization_clamping_stays_off_without_schedutil(self):
        config = settings(CONFIG)
        self.assertEqual(config.get('CONFIG_UCLAMP_TASK'), 'n')
        self.assertEqual(config.get('CONFIG_UCLAMP_TASK_GROUP'), 'n')
        self.assertNotEqual(config.get('CONFIG_CPU_FREQ_GOV_SCHEDUTIL'), 'y')

    def test_ums9620_interrupt_module_is_not_an_e5_requirement(self):
        config = settings(CONFIG)
        modules = runpy.run_path(str(CHECKER))['MODULES']
        self.assertNotIn('CONFIG_UMS9620_LPINTC', config)
        self.assertNotIn('UMS9620_LPINTC', modules)


if __name__ == '__main__':
    unittest.main()
