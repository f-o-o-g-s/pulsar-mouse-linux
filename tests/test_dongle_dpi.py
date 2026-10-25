"""Regression tests for the 1K dongle's DPI range (xlite_v4_wireless.py): a
stage the X3 holds on its cable has to fit the dongle's stage rows, or the
GUI shows it clamped and Apply writes the clamped value back."""

import unittest

from pulsar_mouse.drivers.x3 import PulsarX3
from pulsar_mouse.drivers.xlite_v4_wireless import PulsarXliteV4Wireless


class RecordingDongle(PulsarXliteV4Wireless):
    """A 1K dongle that answers every request at once."""

    def __init__(self):
        super().__init__()
        self.sent = []

    def _transact(self, cmd):
        self.sent.append(bytes(cmd))
        rsp = bytearray(cmd)
        rsp[0] = 0x01
        return bytes(rsp)


class DongleDpiTests(unittest.TestCase):
    def test_the_dongle_covers_the_x3s_range(self):
        dongle = PulsarXliteV4Wireless.capabilities
        x3 = PulsarX3.capabilities
        self.assertGreaterEqual(dongle.dpi_max, x3.dpi_max)
        self.assertLessEqual(dongle.dpi_min, x3.dpi_min)
        self.assertEqual(x3.dpi_step % dongle.dpi_step, 0)

    def test_stages_above_26000_and_off_the_hundreds_are_written(self):
        dongle = RecordingDongle()
        dongle.set_dpi_stages([400, 800, 1600, 3200, 26010, 32000], 3, 1)
        frame = dongle.sent[-1]
        self.assertEqual(frame[1:4], bytes([0x05, 0x04, 0x21]))
        # payload from byte 7: active, count, then (stage, x lo, x hi,
        # y lo, y hi) per stage
        stage5, stage6 = frame[9 + 4 * 5:9 + 5 * 5], frame[9 + 5 * 5:9 + 6 * 5]
        self.assertEqual(stage5, bytes([5]) + (26010).to_bytes(2, 'little') * 2)
        self.assertEqual(stage6, bytes([6]) + (32000).to_bytes(2, 'little') * 2)

    def test_above_32000_is_still_refused(self):
        with self.assertRaises(ValueError):
            RecordingDongle().set_dpi_stages([32010], 1, 1)


if __name__ == '__main__':
    unittest.main()
