"""Minimal X11 input for the render test (XTest via ctypes): click / key on the game window.

    python3 xinput.py click [x y]     # left click at window-relative x, y (default: centre)
    python3 xinput.py key Return      # press and release a key (X keysym name)
"""
import ctypes
import ctypes.util
import re
import subprocess
import sys
import time

X = ctypes.cdll.LoadLibrary(ctypes.util.find_library('X11') or 'libX11.so.6')
XT = ctypes.cdll.LoadLibrary(ctypes.util.find_library('Xtst') or 'libXtst.so.6')
X.XOpenDisplay.restype = ctypes.c_void_p
X.XStringToKeysym.restype = ctypes.c_ulong
X.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
for f in (XT.XTestFakeKeyEvent, XT.XTestFakeButtonEvent, XT.XTestFakeMotionEvent, X.XFlush, X.XSync):
    pass
XT.XTestFakeKeyEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
XT.XTestFakeButtonEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong]
XT.XTestFakeMotionEvent.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
X.XFlush.argtypes = [ctypes.c_void_p]
X.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]


def game_window():
    out = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True).stdout
    best = None
    for l in out.splitlines():
        m = re.search(r'(0x[0-9a-f]+) "([^"]*Civilization V[^"]*)".*?(\d+)x(\d+)\+(-?\d+)\+(-?\d+)', l)
        if m:
            w, h = int(m.group(3)), int(m.group(4))
            if best is None or w * h > best[1] * best[2]:
                best = (m.group(1), w, h, int(m.group(5)), int(m.group(6)))
    return best


def main(a):
    d = X.XOpenDisplay(None)
    if not d:
        sys.exit('no display')
    win = game_window()
    if a[0] == 'click':
        wx, wy = (win[3], win[4]) if win else (0, 0)
        x = int(a[1]) if len(a) > 2 else (win[1] // 2 if win else 960)
        y = int(a[2]) if len(a) > 2 else (win[2] // 2 if win else 540)
        XT.XTestFakeMotionEvent(d, -1, wx + x, wy + y, 0)
        X.XSync(d, 0)
        time.sleep(0.15)
        XT.XTestFakeButtonEvent(d, 1, 1, 0)
        X.XSync(d, 0)
        time.sleep(0.08)
        XT.XTestFakeButtonEvent(d, 1, 0, 0)
    elif a[0] == 'key':
        kc = X.XKeysymToKeycode(d, X.XStringToKeysym(a[1].encode()))
        XT.XTestFakeKeyEvent(d, kc, 1, 0)
        X.XSync(d, 0)
        time.sleep(0.08)
        XT.XTestFakeKeyEvent(d, kc, 0, 0)
    X.XSync(d, 0)
    X.XFlush(d)


if __name__ == '__main__':
    main(sys.argv[1:])
