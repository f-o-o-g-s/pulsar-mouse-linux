"""
pulsar-mouse-linux — Configuration tool for Pulsar gaming mice.

Provides a plugin architecture where each mouse model has its own
protocol driver, while sharing the CLI and GTK4 GUI framework.
"""

__version__ = '0.1.12'

from pulsar_mouse.base import PulsarDevice, DeviceCapabilities

import usb.core
from pulsar_mouse.drivers import discover_all


def scan_devices() -> list[PulsarDevice]:
    """Scan USB for any known Pulsar mouse, return instantiated (unopened) drivers."""
    found = []
    for name, cls in discover_all().items():
        caps = cls.capabilities
        for vid, pid in caps.vid_pid_pairs:
            dev = usb.core.find(idVendor=vid, idProduct=pid)
            if dev is not None:
                found.append(cls())
                break
    # A mouse plugged in by cable usually still has its dongle attached, and
    # the dongle then has nothing to relay to — commands sent through it
    # time out.  Put anything declared wireless after everything else so the
    # cable wins.  Stable sort: drivers that don't declare keep their order.
    found.sort(key=lambda d: d.capabilities.wireless is True)
    return found


def device_present(device: PulsarDevice) -> bool:
    """Is the mouse this driver speaks to still on the bus?

    Cheap enough to call on a timer: it asks libusb for a descriptor and
    claims nothing, so it does not disturb the device the way opening it
    would.
    """
    return any(usb.core.find(idVendor=vid, idProduct=pid) is not None
               for vid, pid in device.capabilities.vid_pid_pairs)


def _carried_mouse(dongle: PulsarDevice) -> tuple[int, int] | None:
    """The cabled (vid, pid) of the mouse a shared dongle is paired with.

    None when the dongle cannot say.  Opens the dongle for the one read and
    closes it again, so the caller must not be holding it open; the GUI
    takes its USB lock around find_sibling() for that reason.
    """
    try:
        dongle.open()
    except Exception:
        return None
    try:
        ids = dongle.get_connected_mouse()
        return (ids['vid'], ids['pid'])
    except Exception:
        return None
    finally:
        try:
            dongle.close()
        except Exception:
            pass


def find_sibling(device: PulsarDevice) -> PulsarDevice | None:
    """The same mouse on its other connection, if that one is plugged in.

    A mouse reached by cable and by dongle is two drivers with two PIDs and
    often different capabilities.  This is what lets the app follow a mouse
    across a swap — plug the cable in to charge, unplug it later — instead of
    reporting the connection it started on as missing.

    Two ways to know that two drivers are one mouse.  A dongle sold with one
    model is paired to its cabled driver by capabilities.model_key.  A dongle
    Pulsar ships across a line has no fixed partner, so it is asked instead:
    get_connected_mouse() returns the cabled VID:PID of the mouse it is
    paired with, and the cabled driver claiming that ID is the sibling.  The
    same question serves a cabled mouse: a dongle on the bus that names this
    mouse is its other half.  Nothing is inferred from names or from a dongle
    merely being present.

    None when the driver has no declared or discoverable sibling, or the
    sibling isn't plugged in.  Never returns a different model: following a
    swap onto somebody's other Pulsar mouse would be worse than not following
    it.
    """
    mine = set(device.capabilities.vid_pid_pairs)
    others = [c for c in scan_devices()
              if not mine & set(c.capabilities.vid_pid_pairs)]

    key = device.capabilities.model_key
    if key:
        for candidate in others:
            if candidate.capabilities.model_key == key:
                return candidate
        return None

    if hasattr(device, 'get_connected_mouse'):
        # Ask the dongle only when there is a cabled mouse to match the
        # answer against; this runs on every battery poll.
        cabled = [c for c in others if c.capabilities.wireless is not True]
        if not cabled:
            return None
        carried = _carried_mouse(device)
        for candidate in cabled:
            if carried in candidate.capabilities.vid_pid_pairs:
                return candidate
        return None

    for candidate in others:
        if (hasattr(candidate, 'get_connected_mouse')
                and _carried_mouse(candidate) in mine):
            return candidate
    return None


def find_device(name: str | None = None) -> PulsarDevice:
    """Find a single Pulsar mouse device.

    If *name* is given, only that driver is tried.  Otherwise, scan for
    all known devices and return the first one found.
    Raises RuntimeError if no device is found.
    """
    if name is not None:
        drivers = discover_all()
        cls = drivers.get(name)
        if cls is None:
            avail = ', '.join(sorted(drivers))
            raise RuntimeError(
                f"Unknown device '{name}'. Available: {avail}")
        device = cls()
        return device

    devices = scan_devices()
    if not devices:
        all_drivers = discover_all()
        names = ', '.join(d.capabilities.name for d in all_drivers.values())
        raise RuntimeError(
            f"No supported Pulsar mouse found. Supported: {names}")
    return devices[0]
