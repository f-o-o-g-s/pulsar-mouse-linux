"""Regression tests for the Fusion2 family's active profile (x2a.py, #24)."""

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from pulsar_mouse import cli
from pulsar_mouse.drivers.x2a import PulsarX2A
from pulsar_mouse.drivers.x3 import PulsarX3
from pulsar_mouse.drivers.xlite_v4_wireless import PulsarXliteV4Wireless


def recording(cls, active=1):
    """`cls` with a transport that records every command and answers it at
    once, with `active` in the profile byte of a read's reply."""

    class Recording(cls):
        def __init__(self):
            super().__init__()
            self.sent = []

        def _set_report(self, data):
            self.sent.append(bytes(data))

        def _get_report(self):
            rsp = bytearray(self.sent[-1])
            rsp[0] = 0x01
            if rsp[2] & 0x80:
                rsp[6] = active
            return bytes(rsp)

    return Recording()


class ActiveProfileTests(unittest.TestCase):
    def test_switch_puts_the_profile_in_byte_6_and_nothing_after(self):
        mouse = recording(PulsarX3)
        mouse.set_active_profile(6)
        self.assertEqual(len(mouse.sent), 1)
        cmd = mouse.sent[0]
        self.assertEqual(cmd[1:4], bytes([0x02, 0x06, 0x01]))
        self.assertEqual(cmd[6], 6)
        self.assertEqual(cmd[7:62], bytes(55))

    def test_read_asks_through_profile_0_and_takes_byte_6(self):
        mouse = recording(PulsarX3, active=4)
        self.assertEqual(mouse.get_active_profile(), 4)
        cmd = mouse.sent[0]
        self.assertEqual(cmd[1:4], bytes([0x02, 0x86, 0x01]))
        self.assertEqual(cmd[6], 0)

    def test_profile_count_comes_from_the_model(self):
        for cls, count in ((PulsarX3, 6), (PulsarX2A, 5)):
            mouse = recording(cls)
            mouse.set_active_profile(count)
            for bad in (0, count + 1):
                with self.assertRaises(ValueError):
                    mouse.set_active_profile(bad)
            self.assertEqual(len(mouse.sent), 1)


class StatusJsonTests(unittest.TestCase):
    def status_with_mouse_on(self, active):
        """--status-json through a stub 1K dongle (five profiles) whose
        mouse says it is on profile `active`."""
        class Dongle(PulsarXliteV4Wireless):
            def open(self):
                pass

            def close(self):
                pass

            def _set_report(self, data):
                self.last = bytes(data)

            def _get_report(self):
                rsp = bytearray(self.last)
                rsp[0] = 0x01
                if rsp[1:3] == bytes([0x02, 0x86]):
                    rsp[6] = active
                return bytes(rsp)

        out = io.StringIO()
        with patch.object(sys, 'argv', ['pulsar-mouse', '--status-json']), \
                patch('pulsar_mouse.cli.find_device', return_value=Dongle()), \
                redirect_stdout(out):
            cli.main()
        return json.loads(out.getvalue())

    def test_active_profile_is_reported(self):
        self.assertEqual(self.status_with_mouse_on(3)['active_profile'], 3)

    def test_profile_the_connection_cant_address_is_left_out(self):
        # An X3 left on profile 6 and then used through the dongle: handing
        # back 6 would make the caller's next --profile 6 fail.
        status = self.status_with_mouse_on(6)
        self.assertEqual(status['num_profiles'], 5)
        self.assertIsNone(status['active_profile'])


if __name__ == '__main__':
    unittest.main()
