"""Make the recoloured particle systems (.psb) listed in capitals.PARTICLES.

A simple Civ 5 .psb particle system stores its colour as three floats at byte 504 (found by
comparing the stock gold / silver / uranium glitter files, which differ only there and in
count/size). The stock file is read (read-only) from the game's EffectData.fpk.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import capitals  # noqa: E402
import fpk  # noqa: E402

GAME = os.environ.get('CIV5_DIR', os.path.expanduser("~/.local/share/Steam/steamapps/common/Sid Meier's Civilization V"))
COLOR_OFFSET = 504


def make(out_dir):
    src = dict(fpk.entries(os.path.join(GAME, 'Resource', 'Common', 'EffectData.fpk')))
    os.makedirs(out_dir, exist_ok=True)
    for name, (stock, rgb, fn) in capitals.PARTICLES.items():
        data = bytearray(src[stock])
        old = struct.unpack_from('<3f', data, COLOR_OFFSET)
        assert all(0.0 <= c <= 1.0 for c in old), (stock, old)   # sanity: really the colour slot
        struct.pack_into('<3f', data, COLOR_OFFSET, *rgb)
        open(os.path.join(out_dir, fn), 'wb').write(data)
        print('particle %s: %s colour %s -> %s' % (fn, stock, tuple(round(c, 2) for c in old), rgb))


if __name__ == '__main__':
    make(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '..', 'build', 'capitals', 'out'))
