"""Painted height maps + colour maps for Smaug's Lair (numpy only; used by bake.py's palette option `heightimg`).

The bake turns a height map into relief lighting (a bump map baked as object-space normals and compared with the
unbumped normals: every coin rim and scale edge catches the light in the texture, at no vertex cost) and darkens its
hollows; the colour map is the albedo. Both images tile.

  coin_heap   a heap of coins seen from above: overlapping, tilted, rimmed gold coins (some silver and copper, a few
              gems), z-buffered so they lie on each other; tiles in x and y. Mapped from above (object x, y / period).
  dragon_scales  Smaug's hide in body coordinates (u along the body in scale rows, v round it: 0 = the spine, 0.5 = the
              belly): overlapping keeled scales whose free edges point to the tail, big ridge scales along the spine,
              the golden transverse plates of the belly; crimson on the back, red on the flanks, gold underneath, scars.
Every function returns (height float32 HxW in 0..1, albedo uint8 HxWx3 sRGB), top row first.
"""
import math

import numpy as np


def _wrap_offsets(cx, cy, R, W, H):
    offs = []
    for dx in (-W, 0, W):
        for dy in (-H, 0, H):
            if -R <= cx + dx < W + R and -R <= cy + dy < H + R:
                offs.append((dx, dy))
    return offs


def coin_heap(seed, px=2048, period=10.0, layers=5, density=1.15, r_units=(0.3, 0.46)):
    rng = np.random.default_rng(seed)
    s = px / period                                    # pixels per unit
    hgt = np.zeros((px, px), np.float32)
    alb = np.zeros((px, px, 3), np.float32)
    alb[:] = (0.24, 0.16, 0.06)                         # the dark gaps between coins
    golds = [np.array(c, np.float32) for c in ((0.93, 0.74, 0.30), (0.86, 0.64, 0.22), (0.78, 0.56, 0.18),
                                               (0.97, 0.82, 0.42), (0.70, 0.50, 0.17))]
    n_per = int(period * period / (math.pi * np.mean(r_units) ** 2) * density)
    for layer in range(layers):
        for _ in range(n_per):
            cx, cy = rng.uniform(0, px), rng.uniform(0, px)
            r = rng.uniform(*r_units) * s
            tilt = math.radians(rng.uniform(0, 72) if rng.uniform() < 0.8 else rng.uniform(72, 86))
            ca, phi = math.cos(tilt), rng.uniform(0, math.pi)
            kind = rng.uniform()
            if kind < 0.012:
                col = np.array([(0.62, 0.08, 0.1), (0.1, 0.45, 0.2), (0.12, 0.2, 0.62)][int(rng.integers(3))], np.float32)
                r *= 0.6
                ca = max(ca, 0.7)
                gem = True
            else:
                gem = False
                if kind < 0.06:
                    col = np.array((0.78, 0.78, 0.76), np.float32)          # silver
                elif kind < 0.09:
                    col = np.array((0.66, 0.38, 0.2), np.float32)           # copper
                else:
                    col = golds[int(rng.integers(len(golds)))] * rng.uniform(0.92, 1.06)
            base = layer + rng.uniform(0, 0.9)
            slope = math.sin(tilt) * 1.2                                    # rises across the tilted coin
            R = int(r) + 3
            yy, xx = np.mgrid[-R:R + 1, -R:R + 1].astype(np.float32)
            cp, sp = math.cos(phi), math.sin(phi)
            a = xx * cp + yy * sp                                           # along the tilt axis (foreshortened)
            b = -xx * sp + yy * cp
            rr = np.sqrt((a / ca) ** 2 + b ** 2) / r                         # 1 at the coin's edge
            inside = rr <= 1.0
            if not inside.any():
                continue
            h = base + slope * (a / (r * ca + 1e-6)) * 0.5
            if gem:
                h = h + 0.5 * np.sqrt(np.clip(1 - rr ** 2, 0, 1))
                c = col[None, None, :] * (0.7 + 0.6 * np.clip(1 - rr, 0, 1))[..., None]
                c = np.where(((a > 0.1 * r) & (b < -0.1 * r) & (rr < 0.5))[..., None], 0.95, c)
            else:
                rim = np.clip((rr - 0.8) / 0.12, 0, 1) * np.clip((1.0 - rr) / 0.06, 0, 1)
                emb = 0.09 * np.exp(-((rr / 0.42) ** 2))                    # the stamped head in the middle
                h = h + 0.12 * rim + emb
                light = 0.88 + 0.22 * rim + 0.5 * emb - 0.18 * (rr > 0.94) + 0.1 * (a / (r * ca + 1e-6))
                c = col[None, None, :] * light[..., None]
            for dx, dy in _wrap_offsets(cx, cy, R, px, px):
                x0, y0 = int(cx + dx) - R, int(cy + dy) - R
                xa, ya, xb, yb = max(0, x0), max(0, y0), min(px, x0 + 2 * R + 1), min(px, y0 + 2 * R + 1)
                if xa >= xb or ya >= yb:
                    continue
                sl = (slice(ya - y0, yb - y0), slice(xa - x0, xb - x0))
                m = inside[sl] & (h[sl] > hgt[ya:yb, xa:xb])
                hgt[ya:yb, xa:xb] = np.where(m, h[sl], hgt[ya:yb, xa:xb])
                alb[ya:yb, xa:xb] = np.where(m[..., None], c[sl], alb[ya:yb, xa:xb])
    hgt = (hgt - hgt.min()) / (hgt.max() - hgt.min() + 1e-6)
    return hgt, np.clip(np.rint(np.clip(alb, 0, 1) * 255), 0, 255).astype(np.uint8)


def dragon_scales(seed, rows=8, nv=32, cell=64):
    """W = rows * cell (u: along the body, rows of scales), H = nv * cell (v: round the body). Cells are square in
    the world when the body coordinates give u = (length / scale size) / rows and v = angle / 2pi.
    Painted on a canvas two rows longer than the tile, from the tail end to the head end (head-ward scales lie over
    the ones behind them), then cropped: every pixel shows the same scale as one period further, so it tiles."""
    W, H = rows * cell, nv * cell
    E = 2 * cell                                          # extra canvas each side in u
    WE = W + 2 * E
    hgt = np.zeros((H, WE), np.float32) - 1.0
    alb = np.zeros((H, WE, 3), np.float32)
    alb[:] = (0.08, 0.03, 0.02)
    back = np.array((0.21, 0.08, 0.05), np.float32)       # dark umber-red on the spine (the film's Smaug)
    flank = np.array((0.36, 0.13, 0.07), np.float32)
    belly = np.array((0.6, 0.38, 0.17), np.float32)       # dull gold underneath
    ember = np.array((0.95, 0.55, 0.16), np.float32)      # flecks of ember-orange and gold in the scales
    yy, xx = np.mgrid[0:H, 0:WE].astype(np.float32)
    v = yy / H                                            # 0 = spine, 0.5 = belly
    dv = np.minimum(np.abs(v - 0.5), 0.5)
    BAND = 0.1                                            # belly plates within +-BAND of v = 0.5
    t = np.clip((dv - BAND) / (0.5 - BAND), 0, 1)
    basecol = np.where((dv < BAND)[..., None], belly, flank * (1 - t[..., None] ** 1.5) + back * t[..., None] ** 1.5)

    def rnd(row, k, salt):                                # the same for the same scale one period on
        return np.random.default_rng((seed, row % rows, k, salt)).uniform()
    for row in range(rows + 2, -3, -1):                   # tail end first
        for k in range(nv):
            vc = (k + 0.5 + 0.5 * (row % 2)) / nv
            dvc = min(abs(vc - 0.5), 0.5)
            if dvc < BAND - 0.5 / nv:
                continue                                  # belly: plates instead (below)
            uc = E + (row + 0.2) * cell
            ridge = dvc > 0.5 - 1.0 / nv                  # the big ridge scales on the spine
            ru, rv = cell * (0.85 if not ridge else 1.0), cell * (0.62 if not ridge else 0.8)
            var = 0.85 + 0.27 * rnd(row, k, 1)
            scar = rnd(row, k, 2) < 0.025
            for dyw in (-H, 0, H):
                cx, cy = uc, vc * H + dyw
                x0, x1 = int(max(0, cx - ru - 2)), int(min(WE, cx + ru + 2))
                y0, y1 = int(max(0, cy - rv - 2)), int(min(H, cy + rv + 2))
                if x0 >= x1 or y0 >= y1:
                    continue
                a = (xx[y0:y1, x0:x1] - cx) / ru         # -1 (covered front) .. +1 (free edge, towards the tail)
                b = (yy[y0:y1, x0:x1] - cy) / rv
                rr = np.sqrt(np.maximum(a, 0) ** 2 + b ** 2) * (a >= 0) + \
                    np.sqrt((a / 1.4) ** 2 + (b * (1 + 0.35 * np.clip(-a, 0, 1))) ** 2) * (a < 0)
                m = rr <= 1.0
                h = 0.55 + 0.35 * (a + 1) / 2 - 0.25 * np.abs(b) + 0.06 * np.exp(-(b / 0.15) ** 2)    # keel
                h = h - 0.6 * np.clip((rr - 0.86) / 0.14, 0, 1)                                       # edge
                shade = (0.78 + 0.32 * (a + 1) / 2 + 0.1 * np.exp(-(b / 0.18) ** 2)) * var
                shade = shade * (1.0 - 0.45 * np.clip((rr - 0.84) / 0.16, 0, 1))
                if scar:
                    shade = shade * (0.55 + 0.45 * np.abs(np.sin((a * 3 + b * 5) * 3)))
                col = basecol[y0:y1, x0:x1] * shade[..., None]
                if rnd(row, k, 4) < 0.22:                 # an ember fleck on this scale
                    fa, fb = rnd(row, k, 5) * 0.8 - 0.2, rnd(row, k, 6) * 0.8 - 0.4
                    fl = np.exp(-(((a - fa) / 0.16) ** 2 + ((b - fb) / 0.16) ** 2))
                    col = col * (1 - fl[..., None]) + ember * (0.6 + 0.5 * rnd(row, k, 7)) * fl[..., None]
                hgt[y0:y1, x0:x1] = np.where(m, h + (1.0 if not ridge else 1.3), hgt[y0:y1, x0:x1])
                alb[y0:y1, x0:x1] = np.where(m[..., None], col, alb[y0:y1, x0:x1])
    bandm = dv < BAND                                     # belly plates, each overlapping the one behind it
    for row in range(rows + 2, -3, -1):
        cx = E + (row + 0.1) * cell
        x0, x1 = int(max(0, cx - cell * 0.75)), int(min(WE, cx + cell * 0.75))
        if x0 >= x1:
            continue
        a = (xx[:, x0:x1] - cx) / (cell * 0.72)
        m = bandm[:, x0:x1] & (np.abs(a) <= 1.0)
        edge = np.clip((np.abs(dv[:, x0:x1]) - (BAND - 0.012)) / 0.012, 0, 1)
        h = 1.1 + 0.4 * (a + 1) / 2 - 0.5 * np.clip((a - 0.82) / 0.18, 0, 1) - 0.4 * edge
        shade = (0.8 + 0.3 * (a + 1) / 2 - 0.4 * np.clip((a - 0.85) / 0.15, 0, 1) - 0.3 * edge) * \
            (0.9 + 0.18 * rnd(row, 999, 3))
        hgt[:, x0:x1] = np.where(m, h, hgt[:, x0:x1])
        alb[:, x0:x1] = np.where(m[..., None], basecol[:, x0:x1] * shade[..., None], alb[:, x0:x1])
    hgt, alb = hgt[:, E:E + W], alb[:, E:E + W]
    hgt = np.clip(hgt, -1, None)
    hgt = (hgt - hgt.min()) / (hgt.max() - hgt.min() + 1e-6)
    return hgt.astype(np.float32), np.clip(np.rint(np.clip(alb, 0, 1) * 255), 0, 255).astype(np.uint8)
