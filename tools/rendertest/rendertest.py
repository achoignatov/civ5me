#!/usr/bin/env python3
"""Automated in-game render test (Linux / Proton / Xwayland). TEMPORARY diagnostic tool.

    python3 tools/build.py && python3 tools/build_dlc.py --rendertest [other flags]
    python3 tools/rendertest/rendertest.py run [label]

Installs dist/DLC_Shared/Shared into the game, sets LeaderHead=1 in config.ini, launches Civ 5 through
Steam, clicks legal screen -> Single Player -> Play Now (last settings), waits for MEC_RenderTest.lua's
RT_SHOT lines and captures the window for each (build/rendertest/shots/<time>_<label>/). Then closes the
game and restores config.ini. Never run while someone is playing.
"""
import os, re, shutil, struct, subprocess, sys, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
RT = os.path.join(ROOT, 'build', 'rendertest')
GAME = os.path.expanduser("~/.local/share/Steam/steamapps/common/Sid Meier's Civilization V")
USER = os.path.expanduser("~/.local/share/Steam/steamapps/compatdata/8930/pfx/drive_c/users/steamuser/"
                          "Documents/My Games/Sid Meier's Civilization 5")
BACKUP = os.path.expanduser('~/civ5-backup-rendertest')


def game_pids():
    out = subprocess.run(['ps', '-eo', 'pid=,comm='], capture_output=True, text=True).stdout
    return [int(l.split()[0]) for l in out.splitlines() if 'CivilizationV' in l.split(None, 1)[-1]]


def install():
    if game_pids():
        sys.exit('Civ 5 is running; not installing')
    src = os.path.join(ROOT, 'dist', 'DLC_Shared', 'Shared')
    dst = os.path.join(GAME, 'Assets', 'DLC', 'Shared')
    subprocess.run(['rsync', '-a', '--delete', os.path.join(src, 'MiddleEarth') + '/',
                    os.path.join(dst, 'MiddleEarth') + '/'], check=True)
    shutil.copy2(os.path.join(src, 'Upgrade1.Civ5Pkg'), os.path.join(dst, 'Upgrade1.Civ5Pkg'))
    cache = os.path.join(USER, 'cache')
    if os.path.isdir(cache):
        os.makedirs(BACKUP, exist_ok=True)
        shutil.move(cache, os.path.join(BACKUP, 'cache-' + time.strftime('%m%d-%H%M%S')))


def set_config(text, key, value):
    pat = re.compile(r'^(%s\s*=).*$' % re.escape(key), re.M)
    assert pat.search(text), key
    return pat.sub(lambda m: m.group(1) + ' ' + value, text, count=1)


def find_window():
    out = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True).stdout
    best = None
    for l in out.splitlines():
        m = re.search(r'(0x[0-9a-f]+) "([^"]*Civilization V[^"]*)".*?(\d+)x(\d+)\+', l)
        if m:
            area = int(m.group(3)) * int(m.group(4))
            if best is None or area > best[1]:
                best = (m.group(1), area)
    return best[0] if best else None


def xinput(win, kind, *a):
    if kind == 'key':
        subprocess.run([sys.executable, os.path.join(HERE, 'xinput.py'), 'key', a[0]], check=False)
        return
    out = subprocess.run(['xwininfo', '-id', win], capture_output=True, text=True).stdout
    if 'Width:' not in out:
        return
    w = int(re.search(r'Width: (\d+)', out).group(1))
    h = int(re.search(r'Height: (\d+)', out).group(1))
    subprocess.run([sys.executable, os.path.join(HERE, 'xinput.py'), 'click', str(int(w * a[0])), str(int(h * a[1]))],
                   check=False)


def write_png(path, rgb):
    h, w, _ = rgb.shape
    raw = b''.join(b'\0' + rgb[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw, 6)) + chunk(b'IEND', b''))


def capture(win, path, half=True):
    import numpy as np
    d = subprocess.run(['xwd', '-id', win, '-silent'], capture_output=True, timeout=30).stdout
    if len(d) < 100:
        return False
    h = struct.unpack('>25I', d[:100])
    hs, w, hh, bpl, ncol = h[0], h[4], h[5], h[12], h[19]
    a = np.frombuffer(d, np.uint8, count=bpl * hh, offset=hs + ncol * 12).reshape(hh, bpl)[:, :w * 4]
    rgb = a.reshape(hh, w, 4)[:, :, 2::-1]
    if half:
        rgb = rgb[:hh // 2 * 2, :w // 2 * 2].reshape(hh // 2, 2, w // 2, 2, 3).mean((1, 3)).astype(np.uint8)
    write_png(path, np.ascontiguousarray(rgb))
    return True


def run(label='', timeout=900):
    install()
    cfg = os.path.join(USER, 'config.ini')
    orig = open(cfg, encoding='latin-1', newline='').read()   # keep CRLF
    os.makedirs(RT, exist_ok=True)
    shutil.copy2(cfg, os.path.join(RT, 'config.ini.orig'))
    c = set_config(set_config(orig, 'LeaderHead', '1'), 'LoggingEnabled', '1')
    open(cfg, 'w', encoding='latin-1', newline='').write(c)
    shots = os.path.join(RT, 'shots', time.strftime('%m%d-%H%M%S') + ('_' + label if label else ''))
    os.makedirs(shots, exist_ok=True)
    log = os.path.join(USER, 'Logs', 'Lua.log')
    t0 = time.time()
    done = False
    try:
        subprocess.Popen(['steam', '-applaunch', '8930'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        seen, win, menu, last_status = 0, None, None, 0
        while time.time() - t0 < timeout:
            time.sleep(0.5)
            if not win:
                win = find_window()
                menu = time.time() if win else None
            if menu and time.time() - menu > 25:
                menu = None
                for step in (('key', 'Return'), ('wait', 6), ('click', 0.5, 0.329), ('wait', 3), ('click', 0.5, 0.329)):
                    if step[0] == 'wait':
                        time.sleep(step[1])
                    else:
                        xinput(win, *step)
                print('%6.1f menus clicked' % (time.time() - t0), flush=True)
            if win and not game_pids():
                print('%6.1f GAME EXITED / CRASHED' % (time.time() - t0), flush=True)
                break
            if win and time.time() - last_status > 30:
                last_status = time.time()
                capture(win, os.path.join(shots, 'status_%04d.png' % int(time.time() - t0)))
            if not os.path.exists(log) or os.path.getmtime(log) < t0:
                continue
            lines = open(log, encoding='latin-1', errors='replace').read().splitlines()
            for l in lines[seen:]:
                if 'RT_' in l or 'Runtime Error' in l or 'MEC_Landmarks' in l or 'METSL DCN' in l:
                    print('%6.1f %s' % (time.time() - t0, l.strip()[:240]), flush=True)
                m = re.search(r'RT_SHOT (\d+) (\S+)', l)
                if m and win:
                    capture(win, os.path.join(shots, '%02d_%s.png' % (int(m.group(1)), m.group(2))))
                if 'RT_DONE' in l:
                    done = True
            seen = len(lines)
            if done:
                break
    finally:
        for f in ('Lua.log', 'Database.log', 'net_message_debug.log'):
            p = os.path.join(USER, 'Logs', f)
            if os.path.exists(p):
                shutil.copy2(p, shots)
        for pid in game_pids():
            try:
                os.kill(pid, 15)
            except ProcessLookupError:
                pass
        for _ in range(60):
            if not game_pids():
                break
            time.sleep(0.5)
        open(cfg, 'w', encoding='latin-1', newline='').write(orig)
        print('config.ini restored; shots:', shots, 'DONE' if done else 'TIMEOUT', flush=True)
    return shots


if __name__ == '__main__':
    a = sys.argv[1:]
    if a and a[0] == 'run':
        run(a[1] if len(a) > 1 else '')
    elif a and a[0] == 'install':
        install()
