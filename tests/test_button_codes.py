"""Regression tests for the mouse-button action codes (hid.py, #24)."""

import unittest

from pulsar_mouse.drivers.feinmann8k import PulsarFeinmann8K
from pulsar_mouse.drivers.nordic import _NORDIC_MOUSE_TO_SONIX, _SONIX_MOUSE_TO_NORDIC
from pulsar_mouse.drivers.x2_crazylight import PulsarX2CrazyLight
from pulsar_mouse.drivers.x3 import PulsarX3
from pulsar_mouse.hid import BTN_TYPE_MOUSE, describe_button, parse_button_function


class MouseActionCodeTests(unittest.TestCase):
    def test_back_and_forward_are_hid_buttons_4_and_5(self):
        self.assertEqual(parse_button_function('backward'), (BTN_TYPE_MOUSE, 0x04, 0x00))
        self.assertEqual(parse_button_function('forward'), (BTN_TYPE_MOUSE, 0x05, 0x00))
        self.assertEqual(describe_button(BTN_TYPE_MOUSE, 0x04, 0x00), 'backward')
        self.assertEqual(describe_button(BTN_TYPE_MOUSE, 0x05, 0x00), 'forward')

    def test_nordic_bitmasks_keep_their_meaning(self):
        # The Nordic bitmask is the HID button as a bit: 0x08 is button 4,
        # 0x10 button 5.  Both directions of the translation have to agree
        # with hid.py's names.
        for bit, name in ((0x08, 'backward'), (0x10, 'forward')):
            self.assertEqual(
                describe_button(BTN_TYPE_MOUSE, _NORDIC_MOUSE_TO_SONIX[bit], 0), name)
            self.assertEqual(
                _SONIX_MOUSE_TO_NORDIC[parse_button_function(name)[1]], bit)


def imported_buttons(cls, data):
    """What import_profile() writes to the buttons of `cls` for `data`."""
    calls = []

    class Recording(cls):
        def set_button(self, btn_id, btn_type, a1, a2, profile):
            calls.append((btn_id, btn_type, a1, a2))

    warnings = Recording().import_profile(1, data)
    return calls, warnings


class OldProfileFileTests(unittest.TestCase):
    OLD = {'format': 'pulsar-mouse-profile', 'version': 1,
           'buttons': {'thumb1': 'forward', 'thumb2': 'backward'}}

    def test_old_file_restores_what_it_saved(self):
        # Saved before the fix, a factory-default X3 reads as thumb1
        # 'forward' (code 4, back) and thumb2 'backward' (code 5, forward).
        calls, warnings = imported_buttons(PulsarX3, self.OLD)
        self.assertEqual(warnings, [])
        self.assertEqual(calls, [(0x04, BTN_TYPE_MOUSE, 0x04, 0x00),
                                 (0x05, BTN_TYPE_MOUSE, 0x05, 0x00)])

    def test_new_file_is_taken_as_written(self):
        calls, _ = imported_buttons(PulsarX3, dict(self.OLD, version=2))
        self.assertEqual(calls, [(0x04, BTN_TYPE_MOUSE, 0x05, 0x00),
                                 (0x05, BTN_TYPE_MOUSE, 0x04, 0x00)])

    def test_exports_say_version_2(self):
        # No transport behind it: every read fails and is skipped, which
        # leaves the header.
        self.assertEqual(PulsarX3().export_profile(1)['version'], 2)

    def test_only_drivers_that_pass_codes_through_swap(self):
        self.assertTrue(PulsarX3._V1_EXPORTS_SWAP_BACK_FORWARD)
        self.assertTrue(PulsarFeinmann8K._V1_EXPORTS_SWAP_BACK_FORWARD)
        self.assertFalse(PulsarX2CrazyLight._V1_EXPORTS_SWAP_BACK_FORWARD)


if __name__ == '__main__':
    unittest.main()
