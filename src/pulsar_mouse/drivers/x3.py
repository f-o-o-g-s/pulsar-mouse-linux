"""
Pulsar X3 on its cable (3710:3409) — protocol driver.

The X3 is a Fusion2 mouse: the same Sonix 64-byte Feature Report protocol
as the X2A and Xlite v4, on interface 3, and the mouse the 1K dongle driver
(xlite_v4_wireless.py) was confirmed on.  Plugged in by its cable it
enumerates under its own ID and answers for itself, so this is the Xlite v4
driver with the X3's ID, name and button labels, plus the Fusion2 power
category: on the cable the mouse reports its own battery and charging state
and holds the sleep timer and Low Power Mode, so the GUI can show it filling
up while it charges.  Link quality and "which mouse is on the dongle" are the
dongle's business and stay there.

This driver has no model_key.  Its dongle, 0x5402, is shared across the
Fusion2 line, so a static pairing would be wrong for anyone whose dongle
carries another model; find_sibling() instead asks the dongle which mouse
it carries and matches the answer against this driver's ID.

USB:
    VID 0x3710
    PID 0x3409
    Interface 3

Confirmed on hardware with a Pulsar X3 on its cable (2026-10).
"""

from pulsar_mouse.base import DeviceCapabilities
from pulsar_mouse.drivers.xlite_v4 import PulsarXliteV4
from pulsar_mouse.drivers.xlite_v4_wireless import Fusion2Power


class PulsarX3(Fusion2Power, PulsarXliteV4):
    """Driver for the Pulsar X3 on its cable (Sonix chipset)."""

    capabilities = DeviceCapabilities(
        name='Pulsar X3 Wired',
        vid_pid_pairs=[(0x3710, 0x3409)],
        interface_num=3,
        report_size=64,
        num_profiles=5,
        max_dpi_stages=6,
        dpi_min=100,
        dpi_max=26000,
        dpi_step=100,
        buttons={
            'left':   0x01,
            'right':  0x02,
            'wheel':  0x03,
            'thumb1': 0x04,
            'thumb2': 0x05,
            'dpi':    0x0b,
        },
        polling_rates=[125, 250, 500, 1000],
        lod_values=[1, 2],
        button_labels={
            'left': 'Left Click',
            'right': 'Right Click',
            'wheel': 'Wheel Click',
            'thumb1': 'Side Front (forward)',
            'thumb2': 'Side Back (backward)',
            'dpi': 'DPI Button',
        },
        wireless=False,
    )
