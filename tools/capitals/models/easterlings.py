"""Rhûn: a royal city of the Easterlings by the Sea of Rhûn.

Lore and film features modelled (Tolkien gives the Easterlings no named capital; this
follows the books' "Men of the East" with their wains, and the film's Easterling look):
  * a walled city on the open plain beside the inland Sea of Rhûn;
  * walls of rammed earth faced with timber, red-lacquered gate towers with tiered,
    upturned roofs; the king's hall: a great tiered palace on a stepped stone platform
    with sweeping dark-tiled roofs trimmed in gold (the film's gilded Easterling armour);
  * a camp of round felt tents and covered wains (the Wainriders) outside the walls;
  * red and gold banners.
"""
import math

from blib import (material, hexcol as h, box, ring, cyl, cone, lathe, terrain_polar, blob, strut, curve, prism,
                  tree, hipped, pyramid, dome, window_row, T)

SEA_Y = 17.0


def ground(x, y):
    z = 0.5 + 0.4 * math.sin(x * 0.25) * math.sin(y * 0.3)
    if y > SEA_Y:
        z = -0.8
    elif y > SEA_Y - 3:
        z = min(z, 0.5 - 1.3 * (y - (SEA_Y - 3)) / 3)
    return z


def pagoda_roof(b, mat, trim, x, y, z, w, d, hgt, rz=0.0, flare=0.6):
    """Hipped roof with flared, upturned eaves and a gold ridge."""
    hipped(b, mat, x, y, z, w, d, hgt, rz=rz, overhang=flare, ridge=0.6)
    ca, sa = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = x + ca * sx * (w / 2 + flare) - sa * sy * (d / 2 + flare)
            cy = y + sa * sx * (w / 2 + flare) + ca * sy * (d / 2 + flare)
            strut(b, trim, (cx, cy, z - 0.05), (cx + (cx - x) * 0.08, cy + (cy - y) * 0.08, z + 0.7), 0.12, 0.0, n=4)


def build(b):
    material('earthwall', h('a08560'), h('8f7653'), noise=2.0, courses=0.7, course_dark=0.85)
    material('lacquer', h('8c2a1e'), h('7a2318'), noise=3.0)
    material('tiles', h('3a2c2a'), h('463532'), noise=4.0, courses=0.35, course_dark=0.7)
    material('egold', h('cfa53a'), h('b38b28'), noise=3.0)
    material('felt', h('d8cdb4'), h('c7baa0'), noise=3.0)
    material('feltred', h('9a3a2a'))
    material('steppe', h('a39a5e'), h('8f8a52'), noise=0.4)
    material('platform', h('8d867a'), h('7a7468'), noise=2.0, courses=0.6, course_dark=0.85)
    material('rhunsea', h('3f6f86'), h('4f809a'), noise=0.6, ao=False)

    road = [(0, -30), (0, -12)]
    from blib import near_path

    def mat(x, y, z, s):
        return 'dirt' if near_path(x, y, road, 1.2) else 'steppe'
    terrain_polar(b, ground, mat, R=31, cy=0, nr=30, na=100)
    lathe(b, 'rhunsea', [(30.0, 0), (0, 0)], n=48, x=0, y=0, z=0.1, smooth=False, a0=0, a1=180)

    # --- city walls (square), corner and gate towers with tiered red roofs
    W, D = 13.5, 11.0
    cy = 1.0
    corners = [(-W, cy - D), (W, cy - D), (W, cy + D), (-W, cy + D)]
    for i in range(4):
        (x0, y0), (x1, y1) = corners[i], corners[(i + 1) % 4]
        L = math.hypot(x1 - x0, y1 - y0)
        ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
        if i == 0:   # south wall with the gate gap
            for s in (-1, 1):
                seg = (W - 2.2)
                box(b, 'earthwall', s * (2.2 + seg / 2), y0, 0.0, seg, 1.4, 4.0)
        else:
            box(b, 'earthwall', (x0 + x1) / 2, (y0 + y1) / 2, 0.0, L, 1.4, 4.0, rz=ang)
        # timber parapet
        k = int(L / 1.0)
        for j in range(k + 1):
            t = j / k
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if i == 0 and abs(x) < 2.4:
                continue
            box(b, 'lacquer', x, y, 4.0, 0.35, 0.35, 0.7, rz=ang)
        tower(b, x0, y0, 0.0, 2.4, 7.0)
    for s in (-1, 1):
        tower(b, s * 2.6, cy - D, 0.0, 2.2, 8.0)
    box(b, 'lacquer', 0, cy - D, 5.6, 4.6, 1.6, 1.0)
    pagoda_roof(b, 'tiles', 'egold', 0, cy - D, 6.6, 4.8, 1.8, 1.2, flare=0.5)

    # --- the king's palace: stepped platform, three tiers of sweeping roofs
    px, py = 0.0, 5.0
    for i, (w, d, hgt) in enumerate(((16.0, 11.0, 0.9), (13.0, 8.5, 0.9), (10.5, 6.5, 0.9))):
        box(b, 'platform', px, py, 0.4 + 0.9 * i, w, d, hgt)
    pz = 0.4 + 2.7
    for i in range(6):
        box(b, 'platform', px, py - 5.5 - 0.5 * i, 0.4 + 2.7 - 0.45 * (i + 1), 3.4, 0.5, 0.45)
    tiers = [(9.0, 5.6, 3.0), (7.0, 4.4, 2.4), (5.0, 3.2, 2.0)]
    z = pz
    for i, (w, d, hgt) in enumerate(tiers):
        box(b, 'lacquer', px, py, z, w, d, hgt)
        # gold-trimmed columns on the front
        for k in range(5):
            x = px - w / 2 + 0.4 + (w - 0.8) * k / 4
            box(b, 'egold', x, py - d / 2 - 0.08, z, 0.3, 0.2, hgt)
        window_row(b, 'window', px - w / 2 + 1, py - d / 2 - 0.1, px + w / 2 - 1, py - d / 2 - 0.1, z + hgt * 0.4, 4,
                   w=0.4, h=hgt * 0.4, out=0.0)
        pagoda_roof(b, 'tiles', 'egold', px, py, z + hgt, w + 0.8, d + 0.8, 1.6 if i < 2 else 2.8, flare=1.0)
        box(b, 'egold', px, py, z + hgt - 0.12, w + 2.6, d + 2.6, 0.12)
        z += hgt + (1.0 if i < 2 else 0)
    lathe(b, 'egold', [(0.3, 0), (0.2, 1.5), (0.0, 2.6)], n=6, x=px, y=py, z=z + 1.8, smooth=False)

    # --- houses inside the walls
    rng = b.rng
    for k in range(120):
        x, y = rng.uniform(-W + 2, W - 2), rng.uniform(cy - D + 2.5, cy + D - 2)
        if abs(x - px) < 9 and abs(y - py) < 7:
            continue
        if abs(x) < 2.0:
            continue
        if rng.random() < 0.6:
            continue
        w, d = rng.uniform(1.6, 2.4), rng.uniform(1.4, 2.0)
        box(b, 'earthwall', x, y, 0.3, w, d, 1.6)
        pagoda_roof(b, rng.choice(['tiles', 'tiles', 'lacquer']), 'egold', x, y, 1.9, w, d, 0.9, flare=0.3)

    # --- the Wainriders' camp outside the walls: felt tents and covered wains
    for k in range(10):
        a = math.radians(200 + 140 * k / 9)
        r = 20.0 + rng.uniform(-1.5, 1.5)
        x, y = r * math.cos(a), r * math.sin(a) + 2
        cyl(b, 'felt' if k % 3 else 'feltred', x, y, 0.3, 1.5, 1.2, n=10)
        dome(b, 'felt' if k % 3 else 'feltred', x, y, 1.5, 1.6, n=10, rings=3, h=1.0)
    for k in range(6):
        a = math.radians(215 + 110 * k / 5)
        r = 16.5
        x, y = r * math.cos(a), r * math.sin(a) + 1
        ang = math.degrees(a) + 90
        wain(b, x, y, ang)
    # red and gold banners at the gate
    for s in (-1, 1):
        cyl(b, 'iron', s * 4.2, cy - D - 1.4, 0.3, 0.06, 7.0, n=4)
        box(b, 'feltred', s * 4.2 + 0.55, cy - D - 1.4, 4.4, 1.0, 0.05, 2.6)
        box(b, 'egold', s * 4.2 + 0.55, cy - D - 1.43, 4.3, 1.0, 0.05, 0.2)


def tower(b, x, y, z, w, hgt):
    box(b, 'earthwall', x, y, z, w, w, hgt)
    box(b, 'lacquer', x, y, z + hgt, w * 0.85, w * 0.85, 1.4)
    pagoda_roof(b, 'tiles', 'egold', x, y, z + hgt + 1.4, w * 0.9, w * 0.9, 1.4, flare=0.55)


def wain(b, x, y, ang):
    """A covered war-wagon of the Wainriders."""
    box(b, 'wood', x, y, 0.9, 3.0, 1.5, 0.5, rz=ang)
    ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    for sx in (-1, 1):
        for sy in (-1, 1):
            wx = x + ca * sx * 1.0 - sa * sy * 0.8
            wy = y + sa * sx * 1.0 + ca * sy * 0.8
            lathe(b, 'wood', [(0, 0), (0.55, 0), (0.55, 0.15), (0, 0.15)], n=8, M=T(wx, wy, 0.75, rz=ang, rx=90 * sy), smooth=False)
    # arched felt cover
    lathe(b, 'felt', [(0, 0), (0.8, 0), (0.8, 2.6), (0, 2.6)], n=10, M=T(x - ca * 1.3, y - sa * 1.3, 1.4, rz=ang - 90, rx=90),
          smooth=True)
