"""Sauron in his armour (the films' Second Age Dark Lord), built from swept/lathed plates: splashlib primitives.

Local frame: feet at the origin, +x = his RIGHT, +y = forward (where he faces), +z = up; about 3.0 tall to the top
of the helm (the crown blades rise another 0.7). He stands with the mace in his right hand, its flanged head resting
on the rock, and his left arm reaching forward with the One Ring on his middle finger (references:
screenshots/sauron-splash-1.webp, -2.webp, the stock DOM_Mordor.dds).

build() returns {material name: Geo}.
"""
import math
from collections import defaultdict
import numpy as np
from splashlib import (Geo, Limb, ell, band, lames, tube, spike, slab, torus, sphere_grid, nrm, fbm, vnoise,
                       smoothstep)

D = math.radians
UP = np.array([0.0, 0.0, 1.0])
FWD = np.array([0.0, 1.0, 0.0])
RIGHT = np.array([1.0, 0.0, 0.0])

J = dict(
    pelvis=(0.0, 0.0, 1.43), chest=(0.0, 0.03, 2.05), neck=(0.0, 0.05, 2.50), head_top=(0.0, 0.09, 2.98),
    r_sh=(0.43, 0.0, 2.32), l_sh=(-0.43, 0.02, 2.32),
    r_el=(0.64, 0.02, 1.79), r_wr=(0.72, 0.22, 1.35),
    l_el=(-0.80, 0.30, 2.13), l_wr=(-1.04, 0.72, 2.30),
    r_hip=(0.19, 0.0, 1.38), l_hip=(-0.19, 0.02, 1.38),
    r_kn=(0.29, 0.08, 0.78), r_an=(0.35, -0.02, 0.11), r_toe=(0.40, 0.30, 0.03),
    l_kn=(-0.30, 0.30, 0.92), l_an=(-0.36, 0.36, 0.30), l_toe=(-0.39, 0.66, 0.22),
    mace_head=(1.10, 0.70, 0.30),
)
J = {k: np.array(v) for k, v in J.items()}
LEFT_ROCK_TOP = 0.20          # the rock under his left foot (the scene puts a boulder there)


def build(seed=1):
    G = defaultdict(Geo)
    iron, dark, mail, cloth = G['iron'], G['iron_dark'], G['mail'], G['cloth']
    rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------ torso
    torso = Limb(J['pelvis'], J['neck'], FWD,
                 ell([0, .12, .3, .55, .78, .92, 1], [.28, .27, .29, .38, .45, .41, .18],
                     [.19, .18, .19, .24, .265, .23, .15]))
    dark.add_vf(band(torso, -math.pi, math.pi, 40, 0.0, 1.0, lift=0.0, flare=0.0, thick=0.05, closed=True))
    # abdomen lames (overlapping downward: edge at the lower t)
    edges = np.linspace(0.56, 0.12, 6)
    for i in range(5):
        iron.add_vf(band(torso, -math.pi, math.pi, 44, edges[i], edges[i + 1] - 0.03, lift=0.016, flare=0.02,
                         thick=0.01, closed=True))
    # breastplate + chevron plates (V pointing down at the sternum)
    iron.add_vf(band(torso, -math.pi, math.pi, 48, 0.97, 0.52, lift=0.022, flare=0.012, thick=0.012, closed=True,
                     rows=6))
    for i, (top, bot) in enumerate([(0.96, 0.80), (0.86, 0.70), (0.76, 0.60), (0.66, 0.50)]):
        k = 0.11 + 0.02 * i
        iron.add_vf(band(torso, -D(105), D(105), 36,
                         lambda th, top=top, k=k: top - k * (1 - np.abs(th) / D(105)) ** 1.3,
                         lambda th, bot=bot, k=k: bot - k * (1 - np.abs(th) / D(105)) ** 1.3 - 0.02,
                         lift=0.036 + 0.004 * (3 - i), flare=0.022, thick=0.01, rows=5))
    # sternum ridge
    P = torso.pt(np.linspace(0.97, 0.40, 14), 0.0, 0.075)
    iron.add_vf(tube(P, np.linspace(0.016, 0.01, 14), np.linspace(0.008, 0.005, 14), ref=FWD, K=4))
    # back plate ribs (seen past the cloak edge)
    for th in (D(150), D(-150), D(180)):
        P = torso.pt(np.linspace(0.95, 0.5, 8), th, 0.04)
        iron.add_vf(tube(P, 0.015, 0.009, ref=torso.radial(th), K=4))

    # belt and tassets
    dark.add_vf(band(torso, -math.pi, math.pi, 48, 0.17, 0.03, lift=0.035, flare=0.0, thick=0.02, closed=True))
    buckle = torso.pt(0.10, 0.0, 0.06)
    iron.add_vf(spike(buckle - FWD * 0.01, FWD + UP * -0.2, 0.06, 0.06, K=5, flat=0.6))
    skirt = Limb(J['pelvis'] + UP * 0.05, J['pelvis'] - UP * 0.72 + FWD * 0.06, FWD,
                 ell([0, 1], [.27, .44], [.19, .34]))
    mail.add_vf(band(skirt, -math.pi, math.pi, 48, 0.0, 0.62, lift=0.0, flare=0.03, thick=0.01, closed=True, rows=8,
                     wobble=0.012))
    for th0, th1 in ((D(18), D(150)), (D(-150), D(-18))):
        edges = np.linspace(0.02, 0.66, 4)
        for i in range(3):
            iron.add_vf(band(skirt, th0, th1, 22, edges[i], edges[i + 1] + 0.06, lift=0.03 + 0.004 * i, flare=0.025,
                             thick=0.01, rows=4))

    # gorget and neck
    neck = Limb(torso.pt(0.86, 0, -0.2), J['neck'] + UP * 0.14, FWD, ell([0, 1], [.19, .12], [.16, .12]))
    for i in range(3):
        iron.add_vf(band(neck, -math.pi, math.pi, 36, 0.95 - i * 0.28, 0.62 - i * 0.28, lift=0.02, flare=0.035,
                         thick=0.01, closed=True))

    # ------------------------------------------------------------------ helmet
    head = Limb(J['neck'] + FWD * 0.03, J['head_top'], FWD,
                ell([0, .25, .55, .8, .95, 1], [.125, .142, .145, .128, .08, .02],
                    [.135, .15, .15, .13, .08, .02], [.15, .18, .175, .15, .09, .02]))
    iron.add_vf(band(head, -math.pi, math.pi, 40, 1.0, -0.05, lift=0.0, flare=0.0, thick=0.03, closed=True, rows=10))
    # face mask: a long downward wedge with eye slits; plates either side
    iron.add_vf(band(head, -D(80), D(80), 34, lambda th: 0.80 - 0.1 * np.abs(th) / D(80),
                     lambda th: -0.58 + 0.62 * (np.abs(th) / D(80)) ** 1.25,
                     lift=0.014, flare=0.11, thick=0.012, rows=10, fpow=1.6))
    for sgn in (1, -1):
        iron.add_vf(band(head, sgn * D(40), sgn * D(125), 16, 0.72, 0.05, lift=0.03, flare=0.05, thick=0.01, rows=6))
        iron.add_vf(band(head, sgn * D(60), sgn * D(150), 14, 0.55, -0.15, lift=0.045, flare=0.06, thick=0.01, rows=5))
        # eye slit: a dark recess on the mask
        c = head.pt(0.56, sgn * D(22), 0.03)
        G['void'].add_vf(tube(np.stack([c - head.S * sgn * 0.035 + UP * 0.006, c + head.S * sgn * 0.035 - UP * 0.004]),
                              0.0055, 0.016, ref=head.F, K=6))
    # brow ridge and nose blade
    P = head.pt(np.linspace(0.92, -0.55, 18), 0.0, np.linspace(0.03, 0.15, 18))
    iron.add_vf(tube(P, np.linspace(0.012, 0.004, 18), np.linspace(0.024, 0.006, 18), ref=FWD, K=4))
    P = head.pt(0.66, np.linspace(-D(70), D(70), 15), 0.03 + 0.012 * np.cos(np.linspace(-1.2, 1.2, 15)))
    iron.add_vf(tube(P, 0.012, 0.006, ref=UP, K=4))
    # the crown: tall flat blades, the front ones tallest, leaning out a little
    for th, L, w in ((0, .66, .06), (D(26), .82, .06), (D(-26), .82, .06), (D(55), .62, .055), (D(-55), .62, .055),
                     (D(86), .46, .05), (D(-86), .46, .05), (D(118), .32, .045), (D(-118), .32, .045),
                     (D(150), .22, .04), (D(-150), .22, .04)):
        b = head.pt(0.70, th, 0.035)
        out = head.radial(th)
        t = np.linspace(0, 1, 10)
        lean = 0.16 + 0.30 * abs(math.sin(th)) + 0.15 * (1 - math.cos(th)) / 2
        P = b + np.outer(t * L, nrm(head.A + out * lean)) + np.outer(t ** 2 * L * 0.08, out)
        tang = np.cross(head.A, out)
        iron.add_vf(tube(P, w * (1 - t) ** 0.8 + 0.002, 0.012 * (1 - t) + 0.002, ref=tang, K=4))
    # crown circlet
    P = head.pt(0.70, np.linspace(-math.pi, math.pi, 40), 0.03)
    iron.add_vf(tube(P, 0.022, 0.012, ref=UP, K=4))

    # ------------------------------------------------------------------ arms
    def arm(sh, el, wr, side):
        out = RIGHT * side
        up_arm = Limb(sh, el, out, ell([0, 1], [.125, .105], [.12, .10]))
        fore = Limb(el, wr, out, ell([0, .7, 1], [.10, .088, .078], [.092, .08, .07]))
        dark.add_vf(band(up_arm, -math.pi, math.pi, 20, -0.1, 1.05, lift=0.0, flare=0.0, thick=0.03, closed=True))
        dark.add_vf(band(fore, -math.pi, math.pi, 20, -0.05, 1.02, lift=0.0, flare=0.0, thick=0.03, closed=True))
        lames(iron, up_arm, 0.25, 0.92, 4, nth=28, lift=0.015, flare=0.02)
        # couter (elbow) with a back spike
        elb = Limb(el - up_arm.A * 0.07, el + fore.A * 0.08, out, ell([0, .5, 1], [.1, .12, .1], [.1, .12, .1]))
        iron.add_vf(band(elb, -math.pi, math.pi, 28, 0.0, 1.0, lift=0.02, flare=0.0, thick=0.01, closed=True, rows=5))
        bdir = nrm(up_arm.A - fore.A)
        iron.add_vf(spike(el + bdir * 0.08, bdir, 0.16, 0.035, K=5))
        # vambrace: lames, a flared cuff and a row of spikes down the outer edge
        lames(iron, fore, 0.05, 0.62, 3, nth=28, lift=0.018, flare=0.018)
        iron.add_vf(band(fore, -math.pi, math.pi, 32, 0.6, 1.08, lift=0.02, flare=0.07, thick=0.01, closed=True))
        for t in (0.2, 0.38, 0.56, 0.78):
            th = math.pi / 2 * side * -1
            b = fore.pt(t, D(90), 0.03)
            d = nrm(fore.radial(D(90)) * 1.0 - fore.A * 0.6)
            iron.add_vf(spike(b, d, 0.07 + 0.05 * t, 0.018, K=4))
        # pauldron: domed lames cascading down the upper arm, ranks of spikes on top
        A = nrm(up_arm.A * 0.55 + out * 0.6 - UP * 0.15)
        apex = sh + UP * 0.13 + out * 0.0
        pd = Limb(apex, apex + A * 0.52, UP,
                  lambda t, th: 0.35 * (0.30 + 0.70 * np.clip(t, 0, 1.2) ** 0.4) * (1 + 0.06 * np.cos(th * 2)))
        th0, th1 = -D(135), D(135)
        tops = [0.0, 0.42, 0.68, 0.9]
        for i in range(3):
            iron.add_vf(band(pd, th0, th1, 48, tops[i] + 0.01, tops[i + 1] + 0.14, lift=0.018 * (3 - i), flare=0.045,
                             thick=0.014, rows=8, fpow=2.0))
        for i, tt in enumerate(tops[1:3]):
            for th in np.linspace(th0 + 0.3, th1 - 0.3, 7 - i):
                b = pd.pt(tt + 0.05, th, 0.012 * (4 - i) + 0.01)
                d = nrm(pd.radial(th) * 0.5 + UP * 0.9 - pd.A * 0.2)
                iron.add_vf(spike(b, d, 0.09 + 0.04 * (2 - i) + 0.03 * rng.random(), 0.022, K=4,
                                  bend=pd.radial(th), bend_amt=0.15))
        # the great spikes: a fan rising from the shoulder cap
        for k, (th, L) in enumerate(((0, .62), (D(22), .55), (D(-22), .55), (D(45), .48), (D(-45), .48),
                                     (D(70), .38), (D(-70), .38), (D(95), .28), (D(-95), .28))):
            b = pd.pt(0.10, th, 0.05)
            d = nrm(pd.radial(th) * 0.45 + UP * 0.85 + out * 0.2)
            iron.add_vf(spike(b, d, L, 0.045, K=4, bend=out, bend_amt=0.18, flat=0.45, ref=np.cross(d, out)))
        return fore

    r_fore = arm(J['r_sh'], J['r_el'], J['r_wr'], 1)
    l_fore = arm(J['l_sh'], J['l_el'], J['l_wr'], -1)

    # ------------------------------------------------------------------ hands
    def finger(base, d, curl_axis, lengths, r0, g_iron, ring=False):
        p = base.copy(); dd = nrm(d); r = r0
        for i, L in enumerate(lengths):
            q = p + dd * L
            P = np.stack([p, (p + q) / 2, q])
            g_iron.add_vf(tube(P, [r * 1.05, r, r * 0.92], [r * 0.9, r * 0.85, r * 0.8], ref=curl_axis, K=7))
            if ring and i == 0:
                G['ring'].add_vf(torus(p + dd * L * 0.45, dd, r * 1.15, r * 0.3, n=28, k=8))
            p = q; r *= 0.82
            ang = D(16 + 6 * i)
            dd = nrm(dd * math.cos(ang) + np.cross(curl_axis, dd) * math.sin(ang))
        g_iron.add_vf(spike(p, dd, 0.035, r * 0.95, K=5, bend=np.cross(curl_axis, dd), bend_amt=0.4))

    # left: open, reaching, palm facing down-forward, fingers spread like claws
    fdir = nrm(J['l_wr'] - J['l_el'])
    hd = nrm(fdir + UP * 0.25)
    palm_n = nrm(-UP + FWD * 0.35 - hd * np.dot(-UP + FWD * 0.35, hd))
    lat = nrm(np.cross(hd, palm_n))
    if lat[0] < 0: lat = -lat                       # +lat toward his right (the thumb side for the left hand)
    palm = Limb(J['l_wr'], J['l_wr'] + hd * 0.17, -palm_n, ell([0, 1], [.065, .078], [.034, .028]))
    iron.add_vf(band(palm, -math.pi, math.pi, 20, -0.1, 1.0, lift=0.0, flare=0.0, thick=0.04, closed=True))
    lames(iron, palm, 0.05, 0.95, 3, th0=-D(80), th1=D(80), nth=14, closed=False, lift=0.006, flare=0.012)
    curl = nrm(np.cross(hd, palm_n))                # bending toward the palm
    K = J['l_wr'] + hd * 0.17
    for j, (off, spread, L) in enumerate(((0.055, 14, .07), (0.018, 4, .078), (-0.018, -7, .074), (-0.052, -19, .06))):
        d = nrm(hd * math.cos(D(spread)) + lat * math.sin(D(spread)))
        finger(K + lat * off, d, curl, [L, L * 0.8, L * 0.6], 0.022, iron, ring=(j == 1))
    finger(J['l_wr'] + hd * 0.05 + lat * 0.065 + palm_n * 0.025, nrm(hd * 0.6 + lat * 0.7 + palm_n * 0.3), curl,
           [0.06, 0.05], 0.024, iron)
    G['ring_light'] = K + lat * 0.018 + hd * 0.04 - palm_n * 0.05

    # right: fist round the mace haft
    mace_dir = nrm(J['mace_head'] - J['r_wr'])
    grip = J['r_wr'] + nrm(J['r_wr'] - J['r_el']) * 0.07
    palm = Limb(J['r_wr'], grip + nrm(J['r_wr'] - J['r_el']) * 0.03, RIGHT, ell([0, 1], [.05, .055], [.04, .04]))
    iron.add_vf(band(palm, -math.pi, math.pi, 20, -0.1, 1.0, lift=0.0, flare=0.0, thick=0.04, closed=True))
    for k in range(4):
        c = grip + mace_dir * (-0.045 + 0.03 * k)
        a = np.linspace(D(-40), D(250), 12)
        T_, N_, B_ = (mace_dir, nrm(np.cross(mace_dir, UP)), None)
        B_ = np.cross(mace_dir, N_)
        P = c + 0.042 * (np.cos(a)[:, None] * N_ + np.sin(a)[:, None] * B_)
        iron.add_vf(tube(P, 0.016, 0.014, ref=mace_dir, K=6))

    # ------------------------------------------------------------------ the mace
    top = grip - mace_dir * 0.42
    head_c = J['mace_head'] - mace_dir * 0.05
    P = np.stack([top + (head_c - top) * t for t in np.linspace(0, 1, 30)])
    dark.add_vf(tube(P, 0.024, ref=UP, K=10))
    for t in np.linspace(0.0, 0.95, 9):
        iron.add_vf(tube(np.stack([P[0] + (P[-1] - P[0]) * t, P[0] + (P[-1] - P[0]) * (t + 0.012)]), 0.032, ref=UP,
                         K=10))
    iron.add_vf(spike(top + mace_dir * 0.02, -mace_dir, 0.12, 0.035, K=6))
    core0 = head_c - mace_dir * 0.30
    iron.add_vf(tube(np.stack([core0 + mace_dir * 0.32 * t for t in np.linspace(0, 1, 6)]),
                     [0.035, 0.05, 0.06, 0.06, 0.05, 0.04], ref=UP, K=12))
    T_, N_, B_ = mace_dir, nrm(np.cross(mace_dir, UP)), None
    B_ = np.cross(mace_dir, N_)
    s = np.linspace(0, 1, 16)
    for k in range(7):
        a = 2 * math.pi * k / 7
        rad = math.cos(a) * N_ + math.sin(a) * B_
        side = np.cross(mace_dir, rad)
        # a hooked blade: grows out of the core, sweeps back toward the haft
        ext = 0.045 + 0.16 * np.sin(np.pi * s) ** 0.8 * (0.6 + 0.4 * s)
        hook = -0.06 * s ** 2
        inner = core0[None] + np.outer(s * 0.36, mace_dir) + np.outer(np.full(16, 0.04), rad)
        outer = core0[None] + np.outer(s * 0.36 + hook, mace_dir) + rad[None] * ext[:, None]
        grid = np.stack([inner, (inner + outer) / 2, outer], 1)
        grid = grid + side[None, None] * 0.009
        iron.add_vf(slab(grid, 0.018))
    iron.add_vf(spike(head_c + mace_dir * 0.03, mace_dir, 0.16, 0.04, K=6))

    # ------------------------------------------------------------------ legs
    def leg(hip, kn, an, toe, side):
        out = RIGHT * side
        thigh = Limb(hip, kn, FWD, ell([0, 1], [.17, .13], [.17, .13]))
        shin = Limb(kn, an, FWD, ell([0, .35, 1], [.125, .118, .085], [.13, .122, .088]))
        dark.add_vf(band(thigh, -math.pi, math.pi, 22, -0.05, 1.05, lift=0.0, flare=0.0, thick=0.04, closed=True))
        dark.add_vf(band(shin, -math.pi, math.pi, 22, -0.05, 1.05, lift=0.0, flare=0.0, thick=0.04, closed=True))
        lames(iron, thigh, 0.12, 0.88, 4, th0=-D(140), th1=D(140), nth=30, closed=False, lift=0.016, flare=0.02)
        # poleyn (knee) with a forward spike, side wings
        kl = Limb(kn - thigh.A * 0.08, kn + shin.A * 0.1, FWD, ell([0, .5, 1], [.12, .14, .12], [.13, .16, .13]))
        iron.add_vf(band(kl, -D(150), D(150), 30, 0.0, 1.0, lift=0.022, flare=0.0, thick=0.012, rows=6))
        kd = nrm(thigh.F + shin.F)
        iron.add_vf(spike(kn + kd * 0.17, nrm(kd - UP * 0.25), 0.13, 0.04, K=5))
        iron.add_vf(spike(kl.pt(0.5, D(90) * side, 0.05), nrm(out + UP * 0.3), 0.08, 0.028, K=4))
        # greave: long plates, ridged front
        lames(iron, shin, 0.12, 0.98, 3, nth=32, lift=0.02, flare=0.03)
        P = shin.pt(np.linspace(0.12, 0.95, 10), 0.0, 0.045)
        iron.add_vf(tube(P, 0.012, 0.007, ref=FWD, K=4))
        # sabaton
        foot = Limb(an + UP * 0.03, toe, UP, ell([0, .6, 1], [.07, .06, .015], [.08, .05, .012]))
        lames(iron, foot, 0.0, 1.0, 5, th0=-D(110), th1=D(110), nth=20, closed=False, lift=0.0, flare=0.012)
        dark.add_vf(band(foot, -math.pi, math.pi, 18, 0.0, 0.95, lift=-0.01, flare=0.0, thick=0.03, closed=True))

    leg(J['r_hip'], J['r_kn'], J['r_an'], J['r_toe'], 1)
    leg(J['l_hip'], J['l_kn'], J['l_an'], J['l_toe'], -1)

    # ------------------------------------------------------------------ cloth: tabard and cloak
    # front tabard, hanging from the belt between the legs, ragged hem
    nu, nv = 18, 40
    u = np.linspace(-1, 1, nu)[:, None]; v = np.linspace(0, 1, nv)[None, :]
    top_c = torso.pt(0.08, 0.0, 0.06)
    hem = 1.32 - 0.12 * np.abs(fbm(u * 3 + 2, 0, 3, 4)) - 0.05 * (np.abs(np.sin(u * 9.0)) > 0.8)
    L = v * hem
    width = 0.15 + 0.07 * v
    P = (top_c[None, None] + RIGHT[None, None] * (u * width)[..., None] - UP[None, None] * L[..., None]
         + FWD[None, None] * (0.05 + 0.10 * np.sin(np.pi * np.clip(v, 0, 1) * 0.8) + 0.035 * np.cos(u * 7.5 + 0.8) * v)[..., None])
    cloth.add_vf(slab(P, 0.012))

    # under-robe: from the belt to the rock, parted at the front so the greaves show
    nu, nv = 70, 50
    u = np.linspace(0, 1, nu)[:, None]; v = np.linspace(0, 1, nv)[None, :]
    phi = D(38) + u * D(284)
    hemv = 1 - 0.05 * np.abs(fbm(u * 11, 2.0, 4, 13)) - 0.03 * (vnoise(u * 70, 0.5, 6) > 0.7)
    vv = v * hemv
    rr = 1.0 / np.sqrt((np.cos(phi) / 0.24) ** 2 + (np.sin(phi) / 0.33) ** 2) + 0.05
    rr = rr + 0.30 * vv ** 1.3 + (0.03 * np.sin(u * 2 * np.pi * 9 + 2 * fbm(u * 3, v, 3, 17)) * (0.2 + vv))
    x = -np.sin(phi) * rr; y = np.cos(phi) * rr
    z = 1.50 - vv * 1.47
    x = x - 0.12 * vv ** 2; y = y - 0.06 * vv ** 2
    cloth.add_vf(slab(np.stack(np.broadcast_arrays(x, y, z), -1), 0.012))

    # the cloak: from the back of the shoulders down to the rock, spread and blown toward his left & back
    nu, nv = 120, 90
    u = np.linspace(0, 1, nu)[:, None]; v = np.linspace(0, 1, nv)[None, :]
    phi = D(70) + u * D(220)                                  # around the back, his left side first
    z_top = 2.40
    rt = 1.0 / np.sqrt((np.cos(phi) / 0.28) ** 2 + (np.sin(phi) / 0.54) ** 2) + 0.03
    fold = (0.085 * np.sin(u * 2 * np.pi * 7.5 + 2.0 * fbm(u * 4, v * 1.5, 3, 7)) + 0.035 * np.sin(u * 2 * np.pi * 17 + 3 * v))
    hemv = 1 - 0.07 * np.abs(fbm(u * 9, 1.0, 4, 11)) ** 1.5 - 0.04 * (vnoise(u * 60, 0.5, 5) > 0.75)
    vv = v * hemv
    r = rt + (0.82 - rt) * vv ** 0.9 + fold * (0.15 + vv)
    z = z_top - vv * 2.42 + 0.06 * np.sin(u * np.pi) * 0
    x = np.sin(phi) * r * -1                                 # phi measured from front toward his LEFT (-x)
    y = np.cos(phi) * r
    wind = vv ** 1.6
    x = x - 0.38 * wind                                      # toward his left
    y = y - 0.40 * wind
    z = np.maximum(z + 0.15 * wind * (1 - u), 0.02 + 0.03 * fbm(x * 3, y * 3, 2, 2))
    P = np.stack(np.broadcast_arrays(x, y, z), -1)
    cloth.add_vf(slab(P, 0.014))
    # shoulder clasps
    for sx in (1, -1):
        dark.add_vf(sphere_grid(np.array([0.28 * sx, -0.12, 2.38]), 0.055, 8, 10, squash=(1, 0.5, 1)))
    return G
