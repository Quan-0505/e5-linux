"""Allow shared mode selection without importing another board's LTE bands."""
from pathlib import Path
import runpy
import tempfile
import unittest

validate = runpy.run_path(str(Path(__file__).with_name('stage.py')))['validate_radio_defaults']


class RadioDefaults(unittest.TestCase):
    def test_shared_modes_preserve_user_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'unisoc_modem'
            for value in ('default', '134', '152'):
                with self.subTest(value=value):
                    text = "config core 'main'\n option auto_work_mode '"+value+"'\n option auto_work_mode_default '134'\n"
                    config.write_text(text)
                    validate(config)
                    self.assertEqual(config.read_text(), text)

    def test_older_config_without_selector_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'unisoc_modem'
            config.write_text("config core 'main'\n")
            validate(config)

    def test_donor_band_allowlist_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)/'unisoc_modem'
            config.write_text("config core 'main'\n option auto_work_mode 'default'\n option lte_supported_bands '1,3,5'\n")
            with self.assertRaisesRegex(ValueError, 'Donor radio defaults'):
                validate(config)


if __name__ == '__main__':
    unittest.main()
