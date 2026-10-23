"""Regression tests for the mouse-button action codes (hid.py, #24)."""

import unittest

from pulsar_mouse.drivers.nordic import _NORDIC_MOUSE_TO_SONIX, _SONIX_MOUSE_TO_NORDIC
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


if __name__ == '__main__':
    unittest.main()
