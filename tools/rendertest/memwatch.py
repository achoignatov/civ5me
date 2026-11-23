#!/usr/bin/env python3
"""Passive memory recorder for the empty-city-tile hunt (docs/CITY_MODELS.md §8).

Civ 5 is a 32-bit program (4 GB address space under Proton's large-address-aware mode). Hypothesis: in some
launches the address space gets so full or fragmented that big model allocations fail, and stay failing
for that session, while small ones still fit.

This never touches the game: it reads /proc/<pid>/status and /proc/<pid>/maps once per interval while a
CivilizationV*.exe process runs and writes one CSV per launch to build/rendertest/mem/<start>.csv:
  t (s since start), vm_size_mb, vm_peak_mb, rss_mb, free_mb (below 4 GB), largest_gap_mb, gaps_ge_16mb
and prints a one-line summary when the game exits. Usage:
  python3 tools/rendertest/memwatch.py [--hours 6] [--interval 1]
"""
import os
import sys
import time

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT = os.path.join(ROOT, 'build', 'rendertest', 'mem')
MB = 1 << 20
TOP = 1 << 32
LOW = 0x10000


def find_game():
    for pid in os.listdir('/proc'):
        if not pid.isdigit():
            continue
        try:
            comm = open('/proc/%s/comm' % pid).read().strip()
        except OSError:
            continue
        # the game process itself ("CivilizationV_D" / "CivilizationV.e"), not steam.exe or the Proton wrapper
        if comm.startswith('CivilizationV'):
            return int(pid)
    return None


def sample(pid):
    st = {}
    for line in open('/proc/%d/status' % pid):
        k, _, v = line.partition(':')
        if k in ('VmSize', 'VmPeak', 'VmRSS'):
            st[k] = int(v.split()[0]) * 1024
    regs = []
    for line in open('/proc/%d/maps' % pid):
        a, b = (int(x, 16) for x in line.split(None, 1)[0].split('-'))
        if a < TOP:
            regs.append((a, min(b, TOP)))
    regs.sort()
    gaps, prev = [], LOW
    for a, b in regs:
        if a > prev:
            gaps.append(a - prev)
        prev = max(prev, b)
    if TOP > prev:
        gaps.append(TOP - prev)
    return (st.get('VmSize', 0) / MB, st.get('VmPeak', 0) / MB, st.get('VmRSS', 0) / MB,
            sum(gaps) / MB, max(gaps or [0]) / MB, sum(1 for g in gaps if g >= 16 * MB))


def main():
    hours = float(sys.argv[sys.argv.index('--hours') + 1]) if '--hours' in sys.argv else 6.0
    step = float(sys.argv[sys.argv.index('--interval') + 1]) if '--interval' in sys.argv else 1.0
    os.makedirs(OUT, exist_ok=True)
    end = time.time() + hours * 3600
    print('memwatch: waiting for Civ 5 (until %s)' % time.strftime('%H:%M', time.localtime(end)), flush=True)
    while time.time() < end:
        pid = find_game()
        if not pid:
            time.sleep(2)
            continue
        t0 = time.time()
        name = os.path.join(OUT, time.strftime('%Y%m%d-%H%M%S', time.localtime(t0)) + '.csv')
        print('memwatch: pid %d -> %s' % (pid, name), flush=True)
        worst_gap, peak = 1e9, 0
        with open(name, 'w') as f:
            f.write('t,vm_size_mb,vm_peak_mb,rss_mb,free_mb,largest_gap_mb,gaps_ge_16mb\n')
            while True:
                try:
                    s = sample(pid)
                except (OSError, ValueError):
                    break
                f.write('%.1f,%.0f,%.0f,%.0f,%.0f,%.1f,%d\n' % ((time.time() - t0,) + s))
                f.flush()
                worst_gap, peak = min(worst_gap, s[4]), max(peak, s[1])
                time.sleep(step)
        print('memwatch: game exited after %.0f s: VmPeak %.0f MB, smallest "largest free gap" %.1f MB  (%s)'
              % (time.time() - t0, peak, worst_gap, os.path.basename(name)), flush=True)
    print('memwatch: time limit reached', flush=True)


if __name__ == '__main__':
    main()
