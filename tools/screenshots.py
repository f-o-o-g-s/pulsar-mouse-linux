#!/usr/bin/env python3
"""Regenerate the README screenshots from a real mouse.

The point of these images is that every number in them was read off
hardware, so this drives the actual GUI with a mouse connected rather than
mocking anything.  It runs the window in a throwaway X server by default, so
nothing appears on your screen and nothing steals your pointer — the app
does not need a compositor, a panel, or a logged-in desktop session.

    tools/screenshots.py --out screenshots      # all of them
    tools/screenshots.py --list                 # what it can take
    tools/screenshots.py --only 02-performance 06-power
    tools/screenshots.py --live                 # on your real display instead

Needs: Xvfb, xdotool and ImageMagick (`import`), plus the GUI's own
dependencies.  On Debian/Ubuntu:

    sudo apt install xvfb xdotool imagemagick

Which shots you get depends on the mouse: the Power page only exists on a
wireless one, the colour picker only on a mouse with per-stage LEDs.  The
script says what it skipped and why.

It keeps your desktop out of the pictures - no session variables, a
throwaway config directory, a fixed title bar - so the set looks the same
whoever takes it, and it refuses to photograph a sleeping mouse.

09-tray.png cannot be taken this way — a tray icon needs a desktop with a
status-icon host, and there isn't one here.  Take that one by hand on your
own desktop; see docs/screenshots.md.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

# Every shot: the file name, what to do to get there, and how big the
# window should be.  Heights are generous — a page that doesn't fill its
# window just leaves grey at the bottom, while one that overflows loses
# content off the edge, and these are read at a glance in a README table.
# Width is fixed so the README's two-column table lines up; height is
# measured from the page itself, because a tall window around a short page
# is mostly empty grey.
WIDTH = 640
MIN_HEIGHT, MAX_HEIGHT = 520, 1560

SHOTS = [
    ('01-home',          'page:home'),
    # The Performance page is the long one: DPI stages, LED, and every
    # global setting the mouse has.
    ('02-performance',   'page:performance'),
    ('03-color-picker',  'dialog:color'),
    ('04-customize',     'page:customize'),
    ('05-remap-button',  'dialog:remap'),
    ('06-power',         'page:power'),
    ('07-tools',         'page:tools'),
    ('08-input-test',    'dialog:test'),
]

SCREEN = '1800x1700x24'      # must comfortably exceed the largest window

# What the photographer's session would otherwise put in the pictures: the
# GUI grows a Hyprland section and branches on Plasma and GNOME, and GTK
# takes its theme, font and icon set from the desktop around it.
DESKTOP_VARS = ('HYPRLAND_INSTANCE_SIGNATURE', 'XDG_CURRENT_DESKTOP',
                'XDG_SESSION_DESKTOP', 'DESKTOP_SESSION', 'KDE_FULL_SESSION',
                'GNOME_DESKTOP_SESSION_ID', 'GTK_THEME', 'GTK_RC_FILES',
                'GTK2_RC_FILES', 'WAYLAND_DISPLAY')

# Window controls, as GNOME lays them out.  Without this the set comes out
# with whatever buttons the photographer's window manager asks for - three
# on a bare GTK default, one on GNOME - which is a visible difference in
# every single shot.
DECORATION_LAYOUT = ':close'


def need(binary):
    if shutil.which(binary) is None:
        sys.exit(f'{binary} not found — see this script\'s docstring for '
                 f'what to install')


def window_id(title, timeout=8.0):
    """The X11 id of the window called `title`, once it exists."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        out = subprocess.run(['xdotool', 'search', '--name', title],
                             capture_output=True, text=True).stdout.split()
        if out:
            return out[-1]       # the most recently mapped match
        time.sleep(0.2)
    return None


def capture(title, path):
    wid = window_id(title)
    if wid is None:
        return f'no window titled {title!r} appeared'
    # -window on the id rather than the root: with no window manager
    # running the window sits at 0,0 at exactly its requested size, but
    # capturing it by id means a stray dialog can't end up in the frame.
    r = subprocess.run(['import', '-window', wid, path],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(path):
        return f'import failed: {r.stderr.strip()}'
    return None


def scrub_desktop(keep_wayland):
    """Take the photographer's desktop out of the frame.

    The same mouse on two desktops otherwise gives two different sets:
    @f-o-o-g-s's first run for #18 came back in his own theme and font with
    a "Hyprland Mouse Settings" group sitting in the middle of Performance.

    Returns a throwaway XDG_CONFIG_HOME for the caller to delete.  GTK reads
    settings.ini and dconf from there, so pointing it at an empty directory
    is what gets the default theme rather than yours.
    """
    for var in DESKTOP_VARS:
        if var == 'WAYLAND_DISPLAY' and keep_wayland:
            continue        # --live on a Wayland session needs it to connect
        os.environ.pop(var, None)
    config_home = tempfile.mkdtemp(prefix='pulsar-screenshots-config-')
    os.environ['XDG_CONFIG_HOME'] = config_home
    return config_home


def asleep(device):
    """Why this mouse can't be photographed right now, or None.

    A sleeping wireless mouse doesn't stop answering - that is the trap.
    The dongle replies on its behalf with invented values: 125 Hz, every DPI
    stage at its minimum, no battery.  Every shot still comes out, still
    prints `ok`, and the whole set is fiction.  @f-o-o-g-s lost a run to
    this in #18 with a mouse that sleeps after 30 seconds and a run that
    takes about 40.

    The battery is the honest reading: the dongle answers 0xFF when it has
    no mouse to ask, and the driver raises on that.  A mouse on its cable
    never sleeps, and a wired-only driver has no get_power() to ask.
    """
    if not hasattr(device, 'get_power'):
        return None
    # find_device() hands back a closed device, and the window opens and
    # closes it around each of its own reads, so this has to as well.
    # Without it get_power() raises on every wireless mouse, awake or not.
    try:
        device.open()
        try:
            device.get_power()
        finally:
            device.close()
    except Exception as e:
        return f'{type(e).__name__}: {e}'
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--out', default='screenshots', metavar='DIR')
    ap.add_argument('--only', nargs='+', metavar='NAME',
                    help='take just these (see --list)')
    ap.add_argument('--live', action='store_true',
                    help='use the current display instead of a private '
                         'X server (your windows will flash past)')
    ap.add_argument('--theme', choices=['dark', 'light'], default='dark',
                    help='the README set is dark (default: dark)')
    ap.add_argument('--ignore-sleep', action='store_true',
                    help="take them anyway when the battery can't be read "
                         '(see --help on a sleeping mouse)')
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()

    if args.list:
        for name, how in SHOTS:
            print(f'{name:18s} {how}')
        print('09-tray           taken by hand — see docs/screenshots.md')
        return 0

    wanted = [s for s in SHOTS if not args.only or s[0] in args.only]
    if args.only:
        unknown = set(args.only) - {s[0] for s in SHOTS}
        if unknown:
            sys.exit(f'unknown shot(s): {", ".join(sorted(unknown))}')

    need('xdotool')
    need('import')

    config_home = scrub_desktop(keep_wayland=args.live)

    xvfb = None
    if not args.live:
        need('Xvfb')
        # A display number nothing else is using, so a stale lock from an
        # earlier crashed run doesn't take this one down with it.
        for num in range(90, 100):
            if not os.path.exists(f'/tmp/.X{num}-lock'):
                break
        else:
            sys.exit('no free display number between :90 and :99')
        xvfb = subprocess.Popen(['Xvfb', f':{num}', '-screen', '0', SCREEN],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        os.environ['DISPLAY'] = f':{num}'
        os.environ['GDK_BACKEND'] = 'x11'
        time.sleep(1.0)
        if xvfb.poll() is not None:
            sys.exit(f'Xvfb exited immediately on :{num}')

    try:
        return run(args, wanted)
    finally:
        if xvfb is not None:
            xvfb.terminate()
        shutil.rmtree(config_home, ignore_errors=True)


def run(args, wanted):
    # Imported here, after DISPLAY is set: GTK picks its backend when the
    # module loads, so importing earlier binds it to the wrong display.
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('Adw', '1')
    from gi.repository import Gtk, Adw, GLib, Gio
    from pulsar_mouse import find_device
    import pulsar_mouse.gui as gui

    os.makedirs(args.out, exist_ok=True)
    results = []

    device = find_device()
    if device is None:
        sys.exit('no supported mouse found — these screenshots are of real '
                 'readings, so one has to be plugged in (and reachable: see '
                 'the udev rules in udev/)')

    napping = asleep(device)
    if napping and not args.ignore_sleep:
        sys.exit(f'{device.capabilities.name} is not answering for itself '
                 f'({napping}).\n'
                 'Move the mouse to wake it, then run again — a sleeping one '
                 'photographs as a full set of plausible-looking placeholder '
                 'values.\n'
                 'If that reading is simply wrong for your mouse, '
                 '--ignore-sleep takes them anyway.')

    app = Adw.Application(
        # Not the GUI's own id.  A second process claiming it just wakes
        # the copy already running in your tray and exits, which looks
        # exactly like this script doing nothing at all.
        application_id='io.github.packerlschupfer.PulsarMouseScreenshots',
        flags=Gio.ApplicationFlags.NON_UNIQUE)

    state = {'i': 0, 'win': None}

    def activate(_app):
        Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK if args.theme == 'dark'
            else Adw.ColorScheme.FORCE_LIGHT)
        settings = Gtk.Settings.get_default()
        if settings is not None:
            settings.set_property('gtk-decoration-layout', DECORATION_LAYOUT)
        win = gui.MainWindow(application=app, device=device)
        state['win'] = win
        win.present()
        # The window reads the mouse on a worker thread as it opens; the
        # screenshots are of those values, so give that time to land.
        GLib.timeout_add(3500, nxt)

    def nxt():
        if state['i'] >= len(wanted):
            app.quit()
            return False
        name, how = wanted[state['i']]
        state['i'] += 1
        try:
            err = shoot(state['win'], name, how)
        except Exception as e:                  # one bad shot, not the run
            err = f'{type(e).__name__}: {e}'
        results.append((name, err))
        print(f'{"skip" if err else "ok  "}  {name}'
              + (f'   ({err})' if err else ''))
        GLib.timeout_add(400, nxt)
        return False

    def nav_select(win, page):
        """Move the sidebar selection too, so the highlight matches the page."""
        names = [n for n, _label, _icon in win._nav_pages]
        if page not in names:
            return False
        listbox = find_child(win, Gtk.ListBox)
        if listbox is not None:
            row = listbox.get_row_at_index(names.index(page))
            if row is not None:
                listbox.select_row(row)
        win._view_stack.set_visible_child_name(page)
        return True

    def fit(win, page):
        """Size the window to the page it is showing.

        The pages differ hugely — Home is a logo and four rows, Performance
        is every setting the mouse has — so one fixed height either crops
        the long one or leaves the short one two-thirds empty.  Ask the
        page's content how tall it wants to be and add the header bar.
        """
        page_widget = win._view_stack.get_child_by_name(page)
        if page_widget is None:
            return
        # Most pages are a Gtk.ScrolledWindow around their content (see
        # MainWindow._wrap_page), but Home is a plain box - measuring the
        # scrolled window itself would report its minimum, not the page's.
        content = (page_widget.get_child()
                   if isinstance(page_widget, Gtk.ScrolledWindow)
                   else page_widget)
        if content is None:
            return
        _min, nat, _a, _b = content.measure(Gtk.Orientation.VERTICAL, WIDTH)
        height = max(MIN_HEIGHT, min(MAX_HEIGHT, nat + 70))
        win.set_default_size(WIDTH, height)

    def shoot(win, name, how):
        kind, what = how.split(':', 1)
        win.set_default_size(WIDTH, MIN_HEIGHT)
        if kind == 'page':
            if not nav_select(win, what):
                return f'this mouse has no {what} page'
            settle(0.5)
            fit(win, what)
            settle(0.9)
            return capture(win.get_title(), os.path.join(args.out, name + '.png'))

        # Dialogs: opened through the same handlers the UI uses, so what
        # ends up in the picture is what a user would see.
        win.set_default_size(WIDTH, MIN_HEIGHT)
        if what == 'test':
            win._on_test_clicked(None)
            title, settle_for = 'Input Test', 1.2
        elif what == 'remap':
            caps = device.capabilities
            btn, label = next(iter(caps.buttons.items()))
            label = (caps.button_labels or {}).get(btn, btn)
            win._on_button_row_activated(None, caps.buttons[btn], label)
            title, settle_for = f'Remap {label}', 1.2
        elif what == 'color':
            if not device.capabilities.has_stage_colors:
                return 'this mouse has no per-stage LED colours'
            nav_select(win, 'performance')
            settle(0.8)
            if not getattr(win, '_color_buttons', None):
                return 'no colour buttons were built'
            win._color_buttons[0]._on_clicked(None)
            title, settle_for = 'Pick a Color', 1.2
        else:
            return f'unknown dialog {what!r}'

        settle(settle_for)
        err = capture(title, os.path.join(args.out, name + '.png'))
        for w in app.get_windows():
            if w is not win:
                w.close()
        settle(0.4)
        return err

    def settle(seconds):
        """Let GTK finish laying out and drawing before the camera clicks."""
        deadline = time.time() + seconds
        ctx = GLib.MainContext.default()
        while time.time() < deadline:
            while ctx.pending():
                ctx.iteration(False)
            time.sleep(0.02)

    def find_child(widget, cls):
        if isinstance(widget, cls):
            return widget
        child = widget.get_first_child() if hasattr(widget, 'get_first_child') else None
        while child is not None:
            found = find_child(child, cls)
            if found is not None:
                return found
            child = child.get_next_sibling()
        return None

    app.connect('activate', activate)
    # Nothing should take this long; if it does, say so rather than hang.
    GLib.timeout_add_seconds(180, lambda: (print('timed out'), app.quit())[1])
    app.connect('shutdown', lambda _a: None)
    app.run([])

    print()
    print(f'{device.capabilities.name}: '
          f'{sum(1 for _n, e in results if not e)} of {len(results)} taken '
          f'into {args.out}/')
    skipped = [(n, e) for n, e in results if e]
    if skipped:
        print('not taken:')
        for n, e in skipped:
            print(f'  {n}: {e}')
    # It can fall asleep mid-run, which is how the trap in asleep() gets
    # you even when the mouse was awake at the start: the shots before that
    # are real and the ones after it aren't, and nothing in the output says
    # which were which.
    late = None if napping else asleep(device)
    if late:
        print()
        print(f'!!  the mouse stopped answering for itself partway through '
              f'({late}).')
        print('    Anything shot after it fell asleep shows placeholder '
              'values — wake it and run again.')
    print('09-tray.png is taken by hand — see docs/screenshots.md')
    return 0


if __name__ == '__main__':
    sys.exit(main())
