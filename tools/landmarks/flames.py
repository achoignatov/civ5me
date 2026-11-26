"""Animated FLAMES: a model effect of flame-tongue cards that lick upwards, sway and die away (the Balrog, 2026-11-26).

Built on the proven machinery of puffs.py (Bag End's pipe smoke, in game since v6/v7):
  * the stock industrial-lighthouse effect's material (FXShader_Skinned, AlphaMode 8 = ADDITIVE), up to 30 cards;
  * one card per bone; each bone's POSITION follows a D3K8uC8u curve (the stock oil rig's format) and its ROTATION a
    D4nK16uC15u curve;
  * a card is hidden EDGE-ON (turned 90 degrees about its own up axis: the game's camera never turns).
New here:
  * the cards are TALL tongues anchored at their foot, each with its own cell of a texture ATLAS (7 painted flame
    tongues and a soft glow), so neighbouring flames differ;
  * the full rotation q = tilt(X) * roll(Y) * yaw(Z): the yaw opens and closes the tongue (its width), the roll sways
    it, and the TILT leans the card back to face the game's camera (about 50 degrees above the horizon), so a flame
    shows its full height instead of being foreshortened;
  * a life cycle per tongue: born narrow at its emitter, it opens, rises and sways, then thins away while rising
    further; hidden, it drops back to its emitter and is born again. Lives of 0.75-1.5 s, many cycles per loop
    (T = 6 s: 255 position ticks of 24 ms, 900 rotation spans of 7 ms), every tongue out of phase.
Effects hang on a bone and are drawn in the model's FILE units (positions here are file units relative to the bone);
the VisEffect Scale is 1.0.
"""
import copy
import math
import os
import random
import struct

import numpy as np

import dds
import gr2
import granim
import lmodel
import puffs

CAM_ELEV = 52.0        # the game camera's angle above the horizon (degrees): cards lean back to face it
COLS, ROWS = 4, 2      # atlas: 7 tongues + 1 soft glow (the last cell)
CW, CH = 128, 256
ALPHA = 0.72           # tongue opacity (v2: persistent cards overlap all the time; additive)


# --------------------------------------------------------------------------- the atlas
def _noise2(px_w, px_h, cells, rng):
    g = rng.random((cells[1] + 3, cells[0] + 3))
    ys = np.linspace(0, cells[1], px_h)
    xs = np.linspace(0, cells[0], px_w)
    yi, xi = np.floor(ys).astype(int), np.floor(xs).astype(int)
    fy, fx = ys - yi, xs - xi
    fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
    a = g[yi][:, xi] * (1 - fx) + g[yi][:, xi + 1] * fx
    b = g[yi + 1][:, xi] * (1 - fx) + g[yi + 1][:, xi + 1] * fx
    return a * (1 - fy)[:, None] + b * fy[:, None]


def _ramp(T):
    """Flame colour by 'temperature' 0..1: deep red -> orange -> yellow -> white-yellow."""
    keys = [(0.0, (90, 12, 0)), (0.25, (205, 52, 6)), (0.5, (255, 122, 24)), (0.72, (255, 188, 64)),
            (0.9, (255, 232, 150)), (1.0, (255, 250, 215))]
    out = np.zeros(T.shape + (3,), np.float32)
    for (t0, c0), (t1, c1) in zip(keys, keys[1:]):
        m = (T >= t0) & (T <= t1)
        u = ((T - t0) / (t1 - t0))[m][:, None]
        out[m] = np.array(c0, np.float32) * (1 - u) + np.array(c1, np.float32) * u
    return out


def tongue(seed, w=CW, h=CH, double=False):
    """One painted flame tongue (RGBA float, top row first): a wavering body with a hot core near its foot, ragged
    edges, a sharp licking tip."""
    rng = np.random.default_rng(seed)
    v = 1.0 - (np.arange(h) + 0.5) / h                       # 1 at the top row, 0 at the bottom
    x = (np.arange(w) + 0.5) / w * 2 - 1
    X, V = np.meshgrid(x, v)
    ph = rng.random(3) * 6.28
    f1, f2 = 0.8 + 0.6 * rng.random(), 1.8 + 1.2 * rng.random()
    amp = 0.16 + 0.12 * rng.random()
    c = amp * (np.sin(6.283 * f1 * V + ph[0]) * 0.7 + 0.3 * np.sin(6.283 * f2 * V + ph[1])) * V ** 1.1
    width = 0.78 * np.sqrt(np.clip(V, 0, 1)) ** 0.6 * np.clip(1 - V, 0, 1) ** 0.85 * 1.55
    width = np.maximum(width, 1e-3)
    n = _noise2(w, h, (5, 9), rng) * 0.6 + _noise2(w, h, (11, 20), rng) * 0.4
    r = np.abs(X - c) / width
    I = np.clip(1.15 - r + 0.55 * (n - 0.5), 0, 1)
    if double:                                              # a second, smaller tip splitting off
        c2 = c + (0.35 if rng.random() < 0.5 else -0.35) * np.clip((V - 0.35) / 0.6, 0, 1) ** 1.4
        w2 = width * 0.55
        r2 = np.abs(X - c2) / w2
        I2 = np.clip(1.1 - r2 + 0.5 * (n - 0.5), 0, 1) * (V > 0.3)
        I = np.maximum(I, I2)
    I = I ** 1.15 * np.clip(V / 0.1, 0, 1) ** 0.7
    temp = np.clip(I * (1.05 - 0.75 * V) + 0.15 * (n - 0.5), 0, 1)
    rgb = _ramp(temp)
    a = np.clip(I * (0.55 + 0.6 * (1 - V)), 0, 1) * ALPHA
    a *= np.clip((1 - np.abs(X)) / 0.08, 0, 1) * np.clip((1 - V) / 0.03, 0, 1)
    return np.concatenate([rgb, (a * 255)[..., None]], -1)


def glow_cell(w=CW, h=CH):
    """A soft orange heat glow (the light round the burning head)."""
    yy, xx = np.mgrid[0:h, 0:w]
    u = (xx + 0.5) / w * 2 - 1
    v = (yy + 0.5) / h * 2 - 1
    r = np.hypot(u, v)
    a = 0.75 * np.exp(-(r / 0.5) ** 2) + 0.25 * np.exp(-(r / 0.22) ** 2)
    a *= np.clip((1 - r) / 0.25, 0, 1)
    T = np.clip(0.35 + 0.55 * np.exp(-(r / 0.3) ** 2), 0, 1)
    return np.concatenate([_ramp(T), (a * 255)[..., None]], -1)


def atlas(path):
    img = np.zeros((ROWS * CH, COLS * CW, 4), np.float32)
    k = 0
    for r in range(ROWS):
        for c in range(COLS):
            cell = glow_cell() if k == COLS * ROWS - 1 else tongue(101 + 7 * k, double=k in (2, 5))
            img[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW] = cell
            k += 1
    dds.write_dxt3(path, np.clip(img, 0, 255).astype(np.uint8), alpha_keep=0.3)
    return img


def cell_uv(k):
    """(u0, v0, u1, v1) of atlas cell k, v down from the top (DirectX)."""
    r, c = divmod(k, COLS)
    pu, pv = 1.5 / (COLS * CW), 1.5 / (ROWS * CH)
    return (c / COLS + pu, r / ROWS + pv, (c + 1) / COLS - pu, (r + 1) / ROWS - pv)


GLOW_CELL = COLS * ROWS - 1


# --------------------------------------------------------------------------- rotations
def _qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)


def _qaxis(axis, deg):
    h = math.radians(deg) / 2
    v = [0.0, 0.0, 0.0]
    v[axis] = math.sin(h)
    return (v[0], v[1], v[2], math.cos(h))


def card_quat(yaw, roll, tilt):
    """Yaw about the card's up axis (width), then roll in its plane (sway), then tilt back about +X."""
    return _qmul(_qaxis(0, tilt), _qmul(_qaxis(1, roll), _qaxis(2, yaw)))


def qrotate(q, v):
    x, y, z, w = q
    p = (v[0], v[1], v[2], 0.0)
    r = _qmul(_qmul(q, p), (-x, -y, -z, w))
    return r[:3]


def _rot_curve(qfn, T, spans):
    one_over = 65535.0 / T
    h = T / spans
    knots = [0.0, 0.002] + [h * i for i in range(1, spans)] + [T]
    ctrl, prev = [], None
    for t in puffs.greville(T, spans):
        q = qfn(t)
        if prev is not None and sum(a * b for a, b in zip(q, prev)) < 0:
            q = tuple(-c for c in q)
        prev = q
        ctrl += list(granim.quat_encode(q))
    return dict(knots=[int(round(k * one_over)) for k in knots], controls=ctrl, one_over=one_over, entries=0x0000)


# --------------------------------------------------------------------------- tongues
class Tongue:
    """One card: w x h (file units), atlas cell, an emitter (x, y, z) in file units relative to the effect's bone,
    a life (period = T / cycles), a phase; rise and sway in file units."""

    def __init__(self, base, w, h, cell, T, cycles, phase, rise, sway, open_yaw=8.0, glow=False, seed=0):
        self.base, self.w, self.h, self.cell = base, w, h, cell
        self.P = T / cycles
        self.phase, self.rise, self.sway = phase, rise, sway
        self.open_yaw, self.glow = open_yaw, glow
        r = random.Random(seed)
        self.ph2, self.ph3, self.f3 = r.random(), r.random(), 2 + r.randint(0, 2)
        self.T = T

    def u(self, t):
        return (t / self.P + self.phase) % 1.0

    def pos(self, t):
        if self.glow:       # the glow breathes in place
            return self.base
        u = self.u(t)
        bx, by, bz = self.base
        if u > 0.93 or u < 0.03:            # hidden: back at the emitter
            return (bx, by, bz)
        return (bx + self.sway * math.sin(6.283 * (0.9 * u + self.ph2)) * u,
                by, bz + self.rise * u ** 1.3)

    def yaw(self, t):
        if self.glow:       # width = light: slow breathing and a quicker shimmer (whole cycles over the loop)
            T = self.T
            b = 0.72 + 0.16 * math.sin(6.283 * 2 * t / T + self.ph2 * 6.283) + \
                0.08 * math.sin(6.283 * 9 * t / T + self.ph3 * 6.283)
            return math.degrees(math.acos(max(0.05, min(1.0, b))))
        u = self.u(t)
        if u < 0.05 or u > 0.9:
            return 90.0
        if u < 0.22:
            s = (u - 0.05) / 0.17
            op = 90.0 - (90.0 - self.open_yaw) * (s * s * (3 - 2 * s))
        elif u > 0.62:
            s = (u - 0.62) / 0.28
            op = self.open_yaw + (90.0 - self.open_yaw) * (s * s * (3 - 2 * s))
        else:
            op = self.open_yaw
        # shimmer of the width while alive
        return min(90.0, op + 14.0 * abs(math.sin(6.283 * (self.f3 * u + self.ph3))))

    def roll(self, t):
        if self.glow:
            return 0.0
        u = self.u(t)
        return 11.0 * math.sin(6.283 * (1.2 * u + self.ph3)) * (0.4 + u)

    def quat(self, t):
        return card_quat(self.yaw(t), self.roll(t), -CAM_ELEV)


class Steady(Tongue):
    """A PERSISTENT tongue (the Balrog v2, 2026-11-26; the user: "consistent and persistent flames, not random flashes;
    the same at any zoom"): always open (never edge-on, so no card ever turns visibly or pops in close-ups), it sways
    in its plane, breathes in width (yaw 0..~32 degrees: 100..85 percent), bobs a little and drifts sideways, all slow
    (whole cycles of the loop: 1.5-6 s) with a faint quicker shimmer. Several out of phase on one spot make the fire's
    shape change all the time."""

    def __init__(self, base, w, h, cell, T, seed=0, tilt=None):
        r = random.Random(seed)
        super().__init__(base, w, h, cell, T, 1, 0.0, 0.0, 0.0, seed=seed)
        self.tilt = -CAM_ELEV if tilt is None else tilt      # lean back; nearly upright on sloping limbs
        self.n_sway = r.choice((2, 3, 4))          # cycles per loop
        self.n_bob = r.choice((3, 4, 5, 6))
        self.n_breathe = r.choice((3, 4, 5))
        self.n_shim = r.choice((10, 12, 14))
        self.ph = [r.random() for _ in range(6)]
        self.sway_deg = r.uniform(5.0, 9.0)
        self.bob = h * r.uniform(0.05, 0.09)
        self.drift = w * r.uniform(0.06, 0.12)
        self.rise = self.bob
        self.sway = self.drift

    def u(self, t):
        return 0.5                                  # (never hidden: verify checks every moment)

    def _s(self, n, ph, t):
        return math.sin(2 * math.pi * (n * t / self.T + ph))

    def pos(self, t):
        return self.base            # v3: never moves; only turns a little about its foot (see write)

    def yaw(self, t):
        return 16.0 + 13.0 * self._s(self.n_breathe, self.ph[2], t) + 3.0 * self._s(self.n_shim, self.ph[3], t)

    def roll(self, t):
        return self.sway_deg * self._s(self.n_sway, self.ph[0], t) + 2.0 * self._s(self.n_shim + 3, self.ph[4], t)

    def quat(self, t):
        return card_quat(self.yaw(t), self.roll(t), self.tilt)


def steady_tongues(emitters, T, rng, per=2, size=1.0, sink=0.04, tilt=None):
    """Persistent tongues on emitters [(x, y, z, scale)] (file units relative to the bone): per tongues each, of
    different heights and atlas cells; their feet sunk a little into the surface so no edge shows."""
    out = []
    for (x, y, z, s) in emitters:
        cells = rng.sample(range(GLOW_CELL), per)
        for j in range(per):
            hh = s * size * (1.0 if j == 0 else rng.uniform(0.6, 0.85))
            out.append(Steady((x + rng.uniform(-0.18, 0.18) * hh * 0.5, y - 0.02 * j * hh, z - sink * hh),
                              hh * rng.uniform(0.5, 0.62), hh, cells[j], T, seed=rng.randint(0, 10 ** 6), tilt=tilt))
    return out


def emitters_tongues(emitters, T, rng, per=2, size=1.0, cell_pool=None):
    """emitters: [(x, y, z, scale)] in file units relative to the bone. per = tongues per emitter."""
    out = []
    cells = cell_pool or list(range(GLOW_CELL))
    for (x, y, z, s) in emitters:
        for j in range(per):
            hh = s * size * rng.uniform(0.75, 1.25)
            out.append(Tongue((x + rng.uniform(-0.15, 0.15) * hh, y + rng.uniform(-0.1, 0.1) * hh, z),
                              hh * rng.uniform(0.45, 0.6), hh, rng.choice(cells), T, rng.choice((4, 5, 6, 7)),
                              rng.random(), hh * rng.uniform(0.35, 0.6), hh * rng.uniform(0.08, 0.18),
                              seed=rng.randint(0, 10 ** 6)))
    return out


# --------------------------------------------------------------------------- writing
def rest_quat(tg):
    """The tongue's rest orientation: its mean breathing width, no sway, its lean."""
    ys = [tg.yaw(tg.T * i / 64) for i in range(64)]
    tilt = getattr(tg, 'tilt', -CAM_ELEV)
    return card_quat(sum(ys) / len(ys), 0.0, tilt)


def _qconj(q):
    return (-q[0], -q[1], -q[2], q[3])


def write(out_dir, name, tongues, T, spans=600):
    """Writes <name>.gr2/.fxsxml, <name>_IdleA.gr2, <name>_DIFF.dds; returns the file names.

    v3 (2026-11-26, the user: flames "perfect when zoomed out, crazy all over the place when zoomed in", the same for
    v1's popping and v2's persistent tongues): the REST POSE IS THE FINISHED FIRE. Every card is written in place (its
    foot, lean and mean width baked into the vertices) on its own bone AT ITS FOOT, and the animation only TURNS each
    bone a few degrees about it (sway, breathing width) on the proven D4nK16uC15u rotation curves; positions are
    constant (D3Constant32f). No position curves (D3K8uC8u), no big offsets: whatever the engine does with the
    animation at a given zoom (likely level of detail: the rest pose far away, the full curves near), every flame
    stays where it belongs."""
    assert len(tongues) <= 30, 'FXShader_Skinned: at most 32 bones (World + cards)'
    f = gr2.read(lmodel.FX_TEMPLATE)
    root = f.root()
    skel = root['Skeletons'][0]
    proto = skel['Bones'][1]
    bones = [lmodel.make_bone(skel['Bones'][0], 'World', -1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))]
    names = ['c%02d' % i for i in range(len(tongues))]
    feet = [tuple(float(c) for c in tg.base) for tg in tongues]
    for n, ft in zip(names, feet):
        bones.append(lmodel.make_bone(proto, n, 0, ft, ft))
    skel['Bones'] = bones
    mesh = root['Meshes'][0]
    vd = mesh['PrimaryVertexData']
    members = vd['Vertices'].members
    vb = bytearray()
    tris = []
    rests = [rest_quat(tg) for tg in tongues]
    for i, (tg, ft, q0) in enumerate(zip(tongues, feet, rests)):
        u0, v0, u1, v1 = cell_uv(tg.cell)
        hw = tg.w / 2
        z0, z1 = (-tg.h / 2, tg.h / 2) if tg.glow else (-0.06 * tg.h, 0.94 * tg.h)   # tongues: anchored at the foot
        nx, ny, nz = qrotate(q0, (0.0, -1.0, 0.0))
        tx, ty, tz = qrotate(q0, (1.0, 0.0, 0.0))
        bx, by, bz = qrotate(q0, (0.0, 0.0, -1.0))
        for (x, z, u, v) in ((-hw, z0, u0, v1), (hw, z0, u1, v1), (hw, z1, u1, v0), (-hw, z1, u0, v0)):
            px, py, pz = qrotate(q0, (x, -0.01 * i, z))
            vb += struct.pack('<3f4B4B12f', ft[0] + px, ft[1] + py, ft[2] + pz, 255, 0, 0, 0, i, 0, 0, 0,
                              nx, ny, nz, tx, ty, tz, bx, by, bz, u, v, 0.0)
        b = 4 * i
        tris += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
    vd['Vertices'] = gr2.Variant(members, bytes(vb))
    mesh['PrimaryTopology'].update(lmodel.topology(tris))
    bb0 = mesh['BoneBindings'][0]
    mesh['BoneBindings'] = []
    for n, tg in zip(names, tongues):
        bb = copy.deepcopy(bb0)
        bb['BoneName'] = n
        r = max(tg.w, tg.h)
        bb['OBBMin'], bb['OBBMax'] = [-r, -r, -r], [r, r, r]
        mesh['BoneBindings'].append(bb)
    tex = name + '_DIFF.dds'

    def swap(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and 'FX_Ind_Lighthouse_base_01' in v:
                    o[k] = tex
                else:
                    swap(v)
        elif isinstance(o, list):
            for x in o:
                swap(x)
        elif isinstance(o, gr2.Variant):
            swap(o.value)
    swap(root['Materials'])
    root['FromFileName'] = name + '.blend'
    os.makedirs(out_dir, exist_ok=True)
    gr2.write(os.path.join(out_dir, name + '.gr2'), f.root_type, root, f.tag)
    atlas(os.path.join(out_dir, tex))

    a = gr2.read(lmodel.ANIM_TEMPLATE)
    ar = a.root()
    curves = lmodel.Curves(ar)
    tracks = [lmodel.track(curves, 'World')]
    for n, tg, ft, q0 in zip(names, tongues, feet, rests):
        rel = (lambda tg_, q0_: (lambda t: _qmul(tg_.quat(t), _qconj(q0_))))(tg, q0)
        tracks.append(lmodel.track(curves, n, local=ft, yaw=_rot_curve(rel, T, spans)))
    tg_ = ar['TrackGroups'][0]
    tg_['TransformTracks'] = sorted(tracks, key=lambda t: t['Name'].lower())
    ar['Animations'][0]['Duration'] = float(T)
    ar['Animations'][0]['Name'] = name + '_IdleA'
    ar['FromFileName'] = name + '.blend'
    gr2.write(os.path.join(out_dir, name + '_IdleA.gr2'), a.root_type, ar, a.tag)
    verify(os.path.join(out_dir, name + '_IdleA.gr2'), names, tongues, T, rests, feet)

    L = ['<Asset>', '\t<Mesh file="%s.gr2"/>' % name,
         '\t<Animation file="%s_IdleA.gr2" name="IdleA" ec="1000" source="Max"/>' % name,
         '\t<Texture file="FX_Blk_Blk4x4.dds"/>', '\t<Texture file="FX_Wht_Wht4x4.dds"/>',
         '\t<Texture file="%s"/>' % tex,
         '\t<DecisionTree file="AnimatedModelEffect_DecisionTree.ddtxml" source="Tool"/>', '</Asset>']
    with open(os.path.join(out_dir, name + '.fxsxml'), 'w', newline='\r\n') as fh:
        fh.write('\n'.join(L) + '\n')
    return [name + '.gr2', name + '_IdleA.gr2', name + '.fxsxml', tex]


def write_still(out_dir, name, tongues):
    """v4 (2026-11-26, the user's in-game video screenshots/flame-flicker.mp4): sets whose cards the engine animated
    jumped between poses from frame to frame (smeared streaks), while the sets it drew in their rest pose were steady.
    So the flames are now STILL, built exactly like the proven glows (glow.py: the Eye's eyes, Erebor's gate, the
    Balrog's eyes): every card baked in place (foot, lean, mean width) on ONE bone at the origin, every animation
    track identity. Same cards, same amount and placement as before."""
    f = gr2.read(lmodel.FX_TEMPLATE)
    root = f.root()
    mesh = root['Meshes'][0]
    vd = mesh['PrimaryVertexData']
    members = vd['Vertices'].members
    vb = bytearray()
    tris = []
    pts = []
    for i, tg in enumerate(tongues):
        q0 = rest_quat(tg)
        ft = tg.base
        u0, v0, u1, v1 = cell_uv(tg.cell)
        hw = tg.w / 2
        z0, z1 = (-tg.h / 2, tg.h / 2) if tg.glow else (-0.06 * tg.h, 0.94 * tg.h)
        nx, ny, nz = qrotate(q0, (0.0, -1.0, 0.0))
        tx, ty, tz = qrotate(q0, (1.0, 0.0, 0.0))
        bx, by, bz = qrotate(q0, (0.0, 0.0, -1.0))
        for (x, z, u, v) in ((-hw, z0, u0, v1), (hw, z0, u1, v1), (hw, z1, u1, v0), (-hw, z1, u0, v0)):
            px, py, pz = qrotate(q0, (x, -0.01 * i, z))
            p = (ft[0] + px, ft[1] + py, ft[2] + pz)
            pts.append(p)
            vb += struct.pack('<3f4B4B12f', *p, 255, 0, 0, 0, 0, 0, 0, 0, nx, ny, nz, tx, ty, tz, bx, by, bz, u, v, 0.0)
        b = 4 * i
        tris += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
    vd['Vertices'] = gr2.Variant(members, bytes(vb))
    mesh['PrimaryTopology'].update(lmodel.topology(tris))
    lo, hi = lmodel.obb(pts)
    for bb in mesh['BoneBindings']:
        bb['OBBMin'], bb['OBBMax'] = ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0])
    mesh['BoneBindings'][0]['OBBMin'], mesh['BoneBindings'][0]['OBBMax'] = lo, hi
    tex = name + '_DIFF.dds'

    def swap(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and 'FX_Ind_Lighthouse_base_01' in v:
                    o[k] = tex
                else:
                    swap(v)
        elif isinstance(o, list):
            for x in o:
                swap(x)
        elif isinstance(o, gr2.Variant):
            swap(o.value)
    swap(root['Materials'])
    root['FromFileName'] = name + '.blend'
    os.makedirs(out_dir, exist_ok=True)
    gr2.write(os.path.join(out_dir, name + '.gr2'), f.root_type, root, f.tag)
    atlas(os.path.join(out_dir, tex))
    # the animation: the stock IdleA with every track still (as glow.write)
    a = gr2.read(lmodel.ANIM_TEMPLATE)
    ar = a.root()
    curves = lmodel.Curves(ar)
    local = {b['Name']: b['Transform']['Position'] for b in root['Skeletons'][0]['Bones']}
    for t in ar['TrackGroups'][0]['TransformTracks']:
        p = local[t['Name']]
        t['PositionCurve'] = curves.const3(p) if any(abs(x) > 1e-9 for x in p) else curves.identity(3)
        t['OrientationCurve'] = curves.identity(4)
    ar['Animations'][0]['Name'] = name + '_IdleA'
    ar['FromFileName'] = name + '.blend'
    gr2.write(os.path.join(out_dir, name + '_IdleA.gr2'), a.root_type, ar, a.tag)
    binds = [bb['BoneName'] for bb in mesh['BoneBindings']]
    print('  flames %s: %d still cards on bone %s (glow layout), every track identity' % (name, len(tongues), binds[0]))
    L = ['<Asset>', '\t<Mesh file="%s.gr2"/>' % name,
         '\t<Animation file="%s_IdleA.gr2" name="IdleA" ec="1000" source="Max"/>' % name,
         '\t<Texture file="FX_Blk_Blk4x4.dds"/>', '\t<Texture file="FX_Wht_Wht4x4.dds"/>',
         '\t<Texture file="%s"/>' % tex,
         '\t<DecisionTree file="AnimatedModelEffect_DecisionTree.ddtxml" source="Tool"/>', '</Asset>']
    with open(os.path.join(out_dir, name + '.fxsxml'), 'w', newline='\r\n') as fh:
        fh.write('\n'.join(L) + '\n')
    return [name + '.gr2', name + '_IdleA.gr2', name + '.fxsxml', tex]


def verify(path, names, tongues, T, rests, feet):
    """Read the written curves back: positions constant at the feet, each decoded rotation = the wanted turn about the
    foot; also the largest turn (how far a tongue's tip can swing, in degrees)."""
    r = gr2.read(path).root()
    tr = {t['Name']: t for t in r['TrackGroups'][0]['TransformTracks']}
    worst_q, biggest = 0.0, 0.0
    for n, tg, q0, ft in zip(names, tongues, rests, feet):
        pv = tr[n]['PositionCurve']['CurveData'].value
        assert 'CurveDataHeader_D3Constant32f' in pv and all(abs(a - b) < 1e-4 for a, b in zip(pv['Controls'], ft)), n
        qv = tr[n]['OrientationCurve']['CurveData'].value
        for i in range(97):
            t = T * (i + 0.37) / 97
            q = granim.sample_quat_curve(qv, t)
            w = _qmul(tg.quat(t), _qconj(q0))
            worst_q = max(worst_q, 1 - abs(sum(a * b for a, b in zip(q, w))) / math.sqrt(sum(a * a for a in q)))
            biggest = max(biggest, math.degrees(2 * math.acos(min(1.0, abs(w[3])))))
    print('  flames check %s: %d cards at rest in place, rotation 1-|dot| <= %.5f, largest turn %.1f deg' % (
        os.path.basename(path), len(tongues), worst_q, biggest))
    assert worst_q < 0.002, worst_q


def overlays(path_dds, tongues, bone_world, k, t):
    """The cards at time t for the preview (in-game units, additive): [(positions, faces, uvs, image)]."""
    img = dds.decode_dxt3(path_dds)
    out = []
    for tg in tongues:
        if not tg.glow and tg.yaw(t) >= 89.5:
            continue
        q = rest_quat(tg)                   # v4: the flames are still
        px, py, pz = tg.pos(t)
        hw = tg.w / 2
        z0, z1 = (-tg.h / 2, tg.h / 2) if tg.glow else (-0.06 * tg.h, 0.94 * tg.h)
        u0, v0, u1, v1 = cell_uv(tg.cell)
        P = []
        for (x, z) in ((-hw, z0), (hw, z0), (hw, z1), (-hw, z1)):
            rx, ry, rz = qrotate(q, (x, 0.0, z))
            P.append((bone_world[0] + (px + rx) / k, bone_world[1] + (py + ry) / k, bone_world[2] + (pz + rz) / k))
        out.append((P, [(0, 1, 2, 3)], [(u0, v1), (u1, v1), (u1, v0), (u0, v0)], img))
    return out


# --------------------------------------------------------------------------- v5: real fire (the stock fire pit's way)
FIRE_TEMPLATE = os.path.join(lmodel.VENDOR, 'fxm_fire_pit_01.gr2')        # stock (EffectData.fpk): the tipi fire pit
FIRE_STOCK = os.path.join(lmodel.VENDOR, 'fx_fire_pit')                   # its textures (EffectTextures.fpk), for us


def _stock_rgba(name):
    from PIL import Image
    im = Image.open(os.path.join(FIRE_STOCK, name.lower()))
    im.load()
    return np.asarray(im.convert('RGBA'), np.float32)


def _up(a, w, h):
    from PIL import Image
    return np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), np.float32)


FIRE_SPEED = 184       # vertical scroll speed of the fire = the stock fire pit's (the user: "the animations are great";
EMBER_SPEED = 189      # the surge they saw was the effect restarting every second: improvements.BALROG_FIRE_LOOP)


def uv_map(path, r, g, b, a):
    """A UV-scrolling map like the stock ones (4x4 A8R8G8B8 + mips, one colour). Decoded from the stock set
    (fx_uv_lefttoright/righttoleft/bottomtotop/toptobottom/_slow/_slow02): R = horizontal direction (255 +, 0 -),
    B = horizontal speed, G = vertical direction (255 up), A = vertical speed (255 fastest, 105 'slow', 58 'slow02')."""
    d = bytearray(open(os.path.join(FIRE_STOCK, 'fx_fire_pit_fire_uv_01.dds'), 'rb').read())
    for i in range(128, len(d), 4):
        d[i:i + 4] = bytes((b, g, r, a))             # BGRA in memory
    open(path, 'wb').write(bytes(d))


def even_density(img, keep=0.3):
    """Flatten the fire photo's density bands along the scroll: each row's mean alpha pulled towards the overall mean
    (keep = how much of the variation stays), smoothed with wrap-round so the tile stays seamless."""
    a = img[..., 3]
    m = a.mean(1)
    k = np.exp(-0.5 * (np.arange(-24, 25) / 8.0) ** 2)
    k /= k.sum()
    mm = np.convolve(np.r_[m[-24:], m, m[:24]], k, mode='same')[24:-24]
    target = mm.mean() * (mm / mm.mean()) ** keep
    out = img.copy()
    out[..., 3] = np.clip(a * (target / np.maximum(mm, 1e-3))[:, None], 0, 255)
    return out


def tint_fire(img, stops):
    """Recolour a fire photo by its brightness (Minas Morgul's corpse-light: the same moving fire, in ghostly green).
    stops = [(brightness 0..1, (r, g, b))]; alpha unchanged."""
    L = (0.3 * img[..., 0] + 0.55 * img[..., 1] + 0.15 * img[..., 2]) / 255.0
    L = L / max(1e-3, float(np.percentile(L[img[..., 3] > 8], 99))) if (img[..., 3] > 8).any() else L
    out = img.copy()
    out[..., :3] = _ramp_stops(np.clip(L, 0, 1), stops)
    return out


def _ramp_stops(T, stops):
    out = np.zeros(T.shape + (3,), np.float32)
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        m = (T >= t0) & (T <= t1)
        u = ((T - t0) / max(1e-6, t1 - t0))[m][:, None]
        out[m] = np.array(c0, np.float32) * (1 - u) + np.array(c1, np.float32) * u
    return out


def soft_masks(seeds=(5, 6, 7, 8)):
    """Silhouettes for rising VAPOUR (Minas Morgul's green mist): broad soft columns with ragged, wispy edges that
    thin away upwards, instead of flame tongues (white, the shape in alpha; top row first)."""
    out = []
    for s in seeds:
        rng = np.random.default_rng(s)
        h, w = 256, 128
        v = 1.0 - (np.arange(h) + 0.5) / h
        x = (np.arange(w) + 0.5) / w * 2 - 1
        X, V = np.meshgrid(x, v)
        n = _noise2(w, h, (4, 7), rng) * 0.6 + _noise2(w, h, (9, 16), rng) * 0.4
        c = 0.18 * np.sin(6.283 * (0.7 * V + rng.random()))
        width = 0.55 + 0.35 * V
        r = np.abs(X - c) / width
        a = np.clip(1.0 - r ** 1.6 + 0.6 * (n - 0.5), 0, 1) * np.clip(V / 0.12, 0, 1) ** 0.8 * (1 - V) ** 1.3
        a *= np.clip((1 - np.abs(X)) / 0.15, 0, 1)
        m = np.zeros((h, w, 4), np.float32)
        m[..., :3] = 255
        m[..., 3] = np.clip(a * 1.25, 0, 1) * 255
        out.append(m)
    return out


def fire_textures(out_dir, prefix, tint=None, speed=None, ember_speed=None, soft=False, ember_tint=None):
    """Our variants of the stock fire: 4 copies of its scrolling fire photo (FX_Fire_Pit_Fire_base_01), shifted in
    phase along the scroll and mirrored, so neighbouring flames never show the same fire at the same moment; 4 flame
    silhouettes for the alpha lookup (the stock one, mirrored, and two tongues of our own). Returns (bases, masks).
    Minas Morgul (2026-11-26): tint = colour stops (tint_fire) for a green witch-fire, its embers recoloured too
    (<prefix>_Ember.dds, used by write_fire instead of the stock embers); speed = the scroll speed (UV map alpha,
    255 fastest, 105 'slow'); soft = vapour silhouettes (soft_masks) instead of flame tongues."""
    base = even_density(_up(_stock_rgba('fx_fire_pit_fire_base_01.dds'), 128, 256))
    if tint:
        base = tint_fire(base, tint)
        emb = _stock_rgba('fx_fire_pit_fire_base_02.dds')
        emb = tint_fire(emb, ember_tint or tint)
        dds.write_dxt3(os.path.join(out_dir, prefix + '_Ember.dds'), np.clip(emb, 0, 255).astype(np.uint8))
    mask = _up(_stock_rgba('fx_fire_pit_fire_alpha_01.dds'), 128, 256)
    bases, masks = [], []
    for k, (roll, mirror) in enumerate(((0, False), (96, True), (160, False), (224, True))):
        b = np.roll(base, roll, axis=0)
        if mirror:
            b = b[:, ::-1]
        n = '%s_FireB%d.dds' % (prefix, k)
        dds.write_dxt3(os.path.join(out_dir, n), b.astype(np.uint8))
        bases.append(n)
    ours = []
    for seed, dbl in ((211, False), (223, True)):            # tongues of our own, as silhouettes (white, alpha)
        t = tongue(seed, 128, 256, double=dbl)
        a = np.clip(t[..., 3] / ALPHA / 255.0, 0, 1)
        a = np.clip(a * 1.6, 0, 1) ** 0.8
        m = np.zeros((256, 128, 4), np.float32)
        m[..., :3] = 255
        m[..., 3] = a * 255
        ours.append(m)
    for k, m in enumerate(soft_masks() if soft else (mask, mask[:, ::-1], ours[0], ours[1])):
        n = '%s_FireM%d.dds' % (prefix, k)
        dds.write_dxt3(os.path.join(out_dir, n), np.clip(m, 0, 255).astype(np.uint8))
        masks.append(n)
    uv_map(os.path.join(out_dir, prefix + '_FireUV.dds'), 133, 255, 0, speed or FIRE_SPEED)
    uv_map(os.path.join(out_dir, prefix + '_EmberUV.dds'), 133, 255, 0, ember_speed or EMBER_SPEED)
    return bases, masks


def periodic_cloud(w, h, seed, beta=1.9, lo_cut=2.0):
    """A seamless (periodic) cloud texture: white noise filtered to a 1/f^beta spectrum in the frequency domain, so it
    tiles in both directions (the shader scrolls it). Values 0..1."""
    rng = np.random.default_rng(seed)
    F = np.fft.fft2(rng.standard_normal((h, w)))
    fy = np.fft.fftfreq(h)[:, None] * h
    fx = np.fft.fftfreq(w)[None, :] * w
    r = np.hypot(fx, fy * (w / h))
    r[0, 0] = 1.0
    F *= 1.0 / np.maximum(r, lo_cut) ** beta
    F[0, 0] = 0.0
    v = np.real(np.fft.ifft2(F))
    v = (v - v.min()) / (v.max() - v.min() + 1e-9)
    return v


def bank_masks(seeds=(31, 32, 33, 34)):
    """Silhouettes for lying FOG (Carn Dum v3, the user: "dense fog ... not steam"): broad banks filling the card with
    soft ragged edges all round, densest a little below the middle; no plume, nothing thinning upwards."""
    out = []
    for s in seeds:
        rng = np.random.default_rng(s)
        h, w = 256, 128
        v = 1.0 - (np.arange(h) + 0.5) / h
        x = (np.arange(w) + 0.5) / w * 2 - 1
        X, V = np.meshgrid(x, v)
        n = _noise2(w, h, (3, 5), rng) * 0.6 + _noise2(w, h, (7, 12), rng) * 0.4
        # v4: a soft ragged OVAL fading to nothing at every edge (v3's banks kept density at their top and bottom
        # edges: in a field of hundreds the cards' rectangles showed as a patchwork)
        r = np.hypot(X / 0.95, (V - 0.47) / 0.47)
        core = np.clip(1.0 - r ** 1.7 + 0.45 * (n - 0.5), 0, 1)
        edge = np.clip((1 - np.abs(X)) / 0.12, 0, 1) * np.clip(V / 0.1, 0, 1) * np.clip((1 - V) / 0.1, 0, 1)
        a = np.clip(core * edge * 1.1, 0, 1)
        m = np.zeros((h, w, 4), np.float32)
        m[..., :3] = 255
        m[..., 3] = np.clip(a * 1.15, 0, 1) * 255
        out.append(m)
    return out


def fog_textures(out_dir, prefix, tint, hspeed=10):
    """The textures for DENSE, LYING FOG drawn with the stock fire material (write_fire): 4 seamless cloud bases
    (periodic_cloud, tinted by the stops), 4 bank silhouettes, a UV map that drifts SIDEWAYS ONLY (vertical speed 0:
    the user: "the fog should not move up at all"; horizontal speed hspeed, very slow), and NO embers (an empty ember
    texture: the stock embers rise like sparks of steam). Returns (bases, masks, other files)."""
    bases, masks = [], []
    for k in range(4):
        c = periodic_cloud(128, 256, 101 + k)
        c2 = periodic_cloud(128, 256, 201 + k, beta=1.4, lo_cut=6.0)
        dens = np.clip(0.62 * c + 0.38 * c2, 0, 1)
        img = np.zeros((256, 128, 4), np.float32)
        img[..., :3] = (255 * (0.55 + 0.45 * dens))[..., None]
        img[..., 3] = 255 * np.clip(0.35 + 0.75 * dens, 0, 1)
        img = tint_fire(img, tint)
        n = '%s_FireB%d.dds' % (prefix, k)
        dds.write_dxt3(os.path.join(out_dir, n), np.clip(img, 0, 255).astype(np.uint8))
        bases.append(n)
    for k, m in enumerate(bank_masks()):
        n = '%s_FireM%d.dds' % (prefix, k)
        dds.write_dxt3(os.path.join(out_dir, n), np.clip(m, 0, 255).astype(np.uint8))
        masks.append(n)
    uv_map(os.path.join(out_dir, prefix + '_FireUV.dds'), 255, 255, hspeed, 0)        # sideways, never up
    uv_map(os.path.join(out_dir, prefix + '_EmberUV.dds'), 255, 255, 0, 0)            # (no embers anyway)
    empty = np.zeros((64, 64, 4), np.uint8)
    dds.write_dxt3(os.path.join(out_dir, prefix + '_Ember.dds'), empty)
    return bases, masks, [prefix + '_FireUV.dds', prefix + '_EmberUV.dds', prefix + '_Ember.dds']


def write_fire(out_dir, name, tongues, bases, masks):
    """v5 (2026-11-26, the user: "animated, but without the flicker; it must look like real fire"): the flame cards of
    write_still (in place, the steady layout) drawn the way the game draws its own fires: the stock fire pit's
    FireGrafix material (FXShader, additive), whose SHADER animates the texture over elapsed time: a photographic fire
    scrolling up through a flame-silhouette mask (layer 0) and rising embers (layer 1, stock). A static mesh with no
    skeleton animation at all (the stock fxm_fire_pit_01 has none), so nothing the engine can mis-animate. One mesh per
    (fire phase, silhouette) material; cards spread over them so neighbours differ."""
    f = gr2.read(FIRE_TEMPLATE)
    root = f.root()
    proto_mat = [m for m in root['Materials'] if m['Name'] == '03 - Default'][0]      # fire + embers
    proto_mesh = [m for m in root['Meshes'] if m['Name'] == 'Plane02'][0]
    proto_vd = proto_mesh['PrimaryVertexData']
    members = proto_vd['Vertices'].members
    assert [m.name for m in members] == ['Position', 'Normal', 'Tangent', 'Binormal', 'TextureCoordinates0'], \
        [m.name for m in members]
    skel = root['Skeletons'][0]
    bproto = skel['Bones'][0]
    combos = [(bases[i % len(bases)], masks[(i * 3 + 1) % len(masks)]) for i in range(4)]
    groups = {i: [] for i in range(len(combos))}
    rng = random.Random(zlib_crc(name))
    for tg in tongues:
        groups[rng.randrange(len(combos))].append(tg)
    bones = [lmodel.make_bone(bproto, 'Dummy01', -1, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))]
    mats, vds, topos, meshes = [], [], [], []
    textures = set()
    for gi, (bn, mn) in enumerate(combos):
        cards = groups[gi]
        if not cards:
            continue
        bone = 'Fire%02d' % gi
        bones.append(lmodel.make_bone(bproto, bone, 0, (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
        mat = copy.deepcopy(proto_mat)
        mat['Name'] = '%s_%d' % (name, gi)
        pre = bn.split('_FireB')[0]
        ren = {'FX_Fire_Pit_Fire_base_01.dds': bn, 'FX_Fire_Pit_Fire_alpha_01.dds': mn,
               'FX_Fire_Pit_Fire_UV_01.dds': pre + '_FireUV.dds', 'FX_Fire_Pit_Fire_UV_02.dds': pre + '_EmberUV.dds'}
        ember = pre + '_Ember.dds' if os.path.exists(os.path.join(out_dir, pre + '_Ember.dds')) else None
        if ember:                                    # a tinted fire (Minas Morgul): its own embers too
            ren['FX_Fire_Pit_Fire_base_02.dds'] = ember

        def fix(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, str) and v.lower().endswith('.dds'):
                        base_n = v.replace('\\', '/').split('/')[-1]
                        o[k] = ren.get(base_n, base_n)
                    else:
                        fix(v)
            elif isinstance(o, list):
                for x in o:
                    fix(x)
            elif isinstance(o, gr2.Variant):
                fix(o.value)
        fix(mat)
        for tx in (pre + '_FireUV.dds', ember or 'FX_Fire_Pit_Fire_base_02.dds', pre + '_EmberUV.dds',
                   'FX_Fire_Pit_Fire_alpha_02.dds', bn, mn):
            textures.add(tx)
        vb = bytearray()
        tris = []
        pts = []
        for i, tg in enumerate(cards):
            q0 = rest_quat(tg)
            ft = tg.base
            hw = tg.w / 2
            z0, z1 = (-tg.h / 2, tg.h / 2) if tg.glow else (-0.06 * tg.h, 0.94 * tg.h)
            flip = rng.random() < 0.5                    # mirror half of the cards (more variety)
            nrm = qrotate(q0, (0.0, -1.0, 0.0))
            tan = qrotate(q0, (1.0, 0.0, 0.0))
            bin_ = qrotate(q0, (0.0, 0.0, -1.0))
            for (x, z, u, v) in ((-hw, z0, 0.0, 1.0), (hw, z0, 1.0, 1.0), (hw, z1, 1.0, 0.0), (-hw, z1, 0.0, 0.0)):
                px, py, pz = qrotate(q0, (x, -0.01 * i, z))
                p = (ft[0] + px, ft[1] + py, ft[2] + pz)
                pts.append(p)
                vb += struct.pack('<15f', *p, *nrm, *tan, *bin_, (1.0 - u) if flip else u, v, 0.0)
            b = 4 * i
            tris += [(b, b + 1, b + 2), (b, b + 2, b + 3)]
        vd = {'Vertices': gr2.Variant(members, bytes(vb)),
              'VertexComponentNames': copy.deepcopy(proto_vd['VertexComponentNames']),
              'VertexAnnotationSets': []}
        topo = lmodel.topology(tris)
        mesh = {'Name': bone, 'PrimaryVertexData': vd, 'MorphTargets': [], 'PrimaryTopology': topo,
                'MaterialBindings': [{'Material': mat}],
                'BoneBindings': [{'BoneName': bone, 'OBBMin': [0.0, 0.0, 0.0], 'OBBMax': [0.0, 0.0, 0.0],
                                  'TriangleIndices': []}],
                'ExtendedData': None}
        mats.append(mat); vds.append(vd); topos.append(topo); meshes.append(mesh)
    skel['Bones'] = bones
    skel['Name'] = 'Dummy01'
    model = root['Models'][0]
    model['Skeleton'] = skel
    model['MeshBindings'] = [{'Mesh': m} for m in meshes]
    root.update({'Materials': mats, 'Skeletons': [skel], 'VertexDatas': vds, 'TriTopologies': topos,
                 'Meshes': meshes, 'Models': [model], 'TrackGroups': [], 'Animations': []})
    root['FromFileName'] = name + '.blend'
    os.makedirs(out_dir, exist_ok=True)
    gr2.write(os.path.join(out_dir, name + '.gr2'), f.root_type, root, f.tag)
    # read back: every card on a static mesh with the fire material, the textures as intended
    r = gr2.read(os.path.join(out_dir, name + '.gr2')).root()
    ncards = sum(len(m['PrimaryVertexData']['Vertices'].value) // 60
                 if isinstance(m['PrimaryVertexData']['Vertices'].value, (bytes, bytearray))
                 else len(m['PrimaryVertexData']['Vertices'].value) // 4 for m in r['Meshes']) // \
        (1 if isinstance(r['Meshes'][0]['PrimaryVertexData']['Vertices'].value, (bytes, bytearray)) else 1)
    used = sorted({(x['String'] or '') for m in r['Materials']
                   for x in m['ExtendedData'].value['ParameterSet1']['ParamDataT'] if x['String']})
    assert not r['Animations'] and all(m['ExtendedData'].value['ShaderSet'] == 'FXShader' for m in r['Materials'])
    print('  fire %s: %d cards on %d static meshes (FXShader, no animation), textures %s' % (
        name, len(tongues), len(r['Meshes']), used))
    L = ['<Asset>', '  <Mesh file="%s.gr2" source="Max" />' % name]
    L += ['  <Texture file="%s" source="Max" />' % t for t in sorted(textures)]
    L.append('</Asset>')
    with open(os.path.join(out_dir, name + '.fxsxml'), 'w', newline='\r\n') as fh:
        fh.write('\n'.join(L) + '\n')
    return [name + '.gr2', name + '.fxsxml']


def zlib_crc(s):
    import zlib
    return zlib.crc32(s.encode()) & 0xffff
