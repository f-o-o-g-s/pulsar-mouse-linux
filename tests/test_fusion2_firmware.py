"""Regression tests for the Fusion2 family's firmware version (x2a.py)."""

import unittest

from pulsar_mouse.drivers.x2a import PulsarX2A
from pulsar_mouse.drivers.x3 import PulsarX3
from pulsar_mouse.drivers.xlite_v4_wireless import PulsarXliteV4Wireless


def answering(cls, version: bytes):
    """`cls` with a transport that answers every command with `version` at
    bytes [6:10], the way a real reply echoes the request around its data."""

    class Answering(cls):
        def __init__(self):
            super().__init__()
            self.sent = []

        def _set_report(self, data):
            self.sent.append(bytes(data))

        def _get_report(self):
            rsp = bytearray(self.sent[-1])
            rsp[0] = 0x01
            rsp[6:10] = version
            return bytes(rsp)

    return Answering()


class FirmwareVersionTests(unittest.TestCase):
    def test_x3_reads_as_its_bcd_device(self):
        mouse = answering(PulsarX3, bytes.fromhex('16100000'))
        self.assertEqual(mouse.get_firmware_version(), '00.00.10.16')
        self.assertEqual(mouse.sent[0][1:4], bytes([0x01, 0x87, 0x04]))
        self.assertEqual(mouse.sent[0][6], 0x00)

    def test_x2a_reads_as_its_bcd_device(self):
        mouse = answering(PulsarX2A, bytes.fromhex('00000800'))
        self.assertEqual(mouse.get_firmware_version(), '00.08.00.00')

    def test_dongle_asks_the_mouse(self):
        mouse = answering(PulsarXliteV4Wireless, bytes.fromhex('16100000'))
        self.assertEqual(mouse.get_firmware_version(), '00.00.10.16')

    def test_dongle_with_the_mouse_asleep_raises(self):
        # The 1K dongle answers 05 to every poll while its mouse sleeps.
        class Asleep(PulsarXliteV4Wireless):
            _REPLY_TIMEOUT = 0
            _REPLY_POLL = 0

            def _set_report(self, data):
                self.last = bytes(data)

            def _get_report(self):
                return bytes([0x05]) + self.last[1:]

        with self.assertRaises(IOError):
            Asleep().get_firmware_version()


if __name__ == '__main__':
    unittest.main()
