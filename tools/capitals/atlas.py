"""Turn a blib.Builder into game-ready arrays + a texture atlas (runs inside Blender for mathutils).

Texturing scheme (instead of a unique per-face bake, which wastes texels on thousands of tiny
islands): every material owns a few cells of a 1024x1024 atlas, one per ambient-occlusion level.
Each face is planar-mapped (dominant axis) into a cell of its material; the cell is picked by the
face's ambient occlusion, which is ray-cast here. Height-ramp materials (terrain) pick a cell per
height band, steep faces use the material's rock colour.
"""
import math
import random

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

import blib

ATLAS = 1024
AO_LEVELS = (1.0, 0.84, 0.68, 0.52)
WORLD_PER_CELL = 7.0      # world units covered by one cell before a face gets squashed
INSET = 0.12              # keep UVs away from cell borders (mip-map bleeding)
ZBANDS = 9


# --------------------------------------------------------------------------- noise swatches
def _value_noise(n, freq, rng):
    g = rng.random((freq + 2, freq + 2))
    xs = np.linspace(0, freq, n, endpoint=False)
    i = xs.astype(int)
    f = xs - i
    f = f * f * (3 - 2 * f)
    a = g[i][:, i] * (1 - f)[None, :] + g[i][:, i + 1] * f[None, :]
    bb = g[i + 1][:, i] * (1 - f)[None, :] + g[i + 1][:, i + 1] * f[None, :]
    return a * (1 - f)[:, None] + bb * f[:, None]


def _fbm(n, base, rng, octaves=4):
    out = np.zeros((n, n))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * _value_noise(n, max(1, int(base * 2 ** o)), rng)
        tot += amp
        amp *= 0.5
    return out / tot


def swatch(color, color2, noise, courses, course_dark, n, rng, grain=0.05):
    c1 = np.array(color, np.float32)
    img = np.tile(c1, (n, n, 1))
    if color2 is not None and noise > 0:
        f = _fbm(n, max(1.0, noise * WORLD_PER_CELL * 0.6), rng)
        f = np.clip((f - 0.3) / 0.4, 0, 1)[..., None]
        img = img * (1 - f) + np.array(color2, np.float32) * f
    img = img * (1 + grain * (rng.random((n, n, 1)) - 0.5) * 2)
    if courses > 0:
        rows = np.arange(n) / n * WORLD_PER_CELL / courses
        line = (rows % 1.0) < 0.1
        img[line] *= course_dark
        # staggered vertical joints between blocks
        cols = np.arange(n) / n * WORLD_PER_CELL / (courses * 1.6)
        for r in range(n):
            k = int(rows[r])
            j = ((cols + 0.5 * (k % 2)) % 1.0) < 0.06
            img[r, j] *= (course_dark + 1) / 2
    return np.clip(img, 0, 1)


# --------------------------------------------------------------------------- main
class Result:
    pass


def process(b, ao_rays=20, ao_dist=2.4, seed=7):
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    P = [Vector(v) for v in b.verts]

    # triangulate (keeps polygon id for shared per-polygon UVs)
    tris, tri_poly = [], []
    for pi, f in enumerate(b.faces):
        if len(f) == 3:
            tris.append(tuple(f)); tri_poly.append(pi)
        elif len(f) == 4:
            a, c, d, e = f
            # split along the shorter diagonal
            if (P[a] - P[d]).length <= (P[c] - P[e]).length:
                tris += [(a, c, d), (a, d, e)]
            else:
                tris += [(a, c, e), (c, d, e)]
            tri_poly += [pi, pi]
        else:
            loops = tessellate_polygon([[P[i] for i in f]])
            for t in loops:
                tris.append((f[t[0]], f[t[1]], f[t[2]])); tri_poly.append(pi)

    # polygon normals (Newell) and areas
    pn, parea, pcen = [], [], []
    for f in b.faces:
        n = Vector((0, 0, 0))
        for i in range(len(f)):
            p, q = P[f[i]], P[f[(i + 1) % len(f)]]
            n.x += (p.y - q.y) * (p.z + q.z)
            n.y += (p.z - q.z) * (p.x + q.x)
            n.z += (p.x - q.x) * (p.y + q.y)
        area = n.length / 2
        pn.append(n.normalized() if area > 1e-12 else Vector((0, 0, 1)))
        parea.append(area)
        pcen.append(sum((P[i] for i in f), Vector()) / len(f))

    # smooth vertex normals (only across smooth polygons sharing a builder vertex)
    vn = [Vector((0, 0, 0)) for _ in P]
    for pi, f in enumerate(b.faces):
        if b.fsmooth[pi]:
            for i in f:
                vn[i] += pn[pi] * max(parea[pi], 1e-6)
    vn = [v.normalized() if v.length > 1e-9 else None for v in vn]

    # ambient occlusion per polygon
    bvh = BVHTree.FromPolygons([tuple(p) for p in P], [tuple(t) for t in tris], all_triangles=True)
    dirs = []
    for k in range(ao_rays):
        u, v = (k + 0.5) / ao_rays, (k * 0.618034) % 1.0
        r = math.sqrt(u)
        th = 2 * math.pi * v
        dirs.append((r * math.cos(th), r * math.sin(th), math.sqrt(max(0.0, 1 - u))))
    ao = []
    for pi in range(len(b.faces)):
        n = pn[pi]
        t = n.orthogonal().normalized()
        bt = n.cross(t)
        o = pcen[pi] + n * 0.03
        hit = 0
        for dx, dy, dz in dirs:
            d = t * dx + bt * dy + n * dz
            if bvh.ray_cast(o, d, ao_dist)[0] is not None:
                hit += 1
        ao.append(1.0 - hit / ao_rays)

    # ---- cells
    mats = b.mat_names
    pal = blib.PALETTE
    cell_keys = []
    for m in mats:
        p = pal[m]
        if p.get('zramp'):
            for z in range(ZBANDS):
                for lv in range(len(AO_LEVELS)):
                    cell_keys.append((m, 'z%d' % z, lv))
        else:
            for lv in range(len(AO_LEVELS)):
                cell_keys.append((m, 'base', lv))
        if p.get('slope_color') is not None:
            for lv in range(len(AO_LEVELS)):
                cell_keys.append((m, 'slope', lv))
    per_row = 1
    while per_row * per_row < len(cell_keys):
        per_row += 1
    cell = (ATLAS // per_row) // 4 * 4
    img = np.zeros((ATLAS, ATLAS, 3), np.float32)
    sref = np.zeros((ATLAS, ATLAS, 4), np.float32)
    cell_uv = {}
    swatches = {}
    for idx, key in enumerate(cell_keys):
        m, kind, lv = key
        p = pal[m]
        if (m, kind) not in swatches:
            if kind.startswith('z'):
                zs = [z for z, _ in p['zramp']]
                zi = int(kind[1:])
                zval = min(zs) + (max(zs) - min(zs)) * zi / (ZBANDS - 1)
                col = _ramp(p['zramp'], zval)
                c2 = tuple(min(1, x * 1.12) for x in col)
                sw = swatch(col, c2, 1.2, 0, 0.8, cell, nrng, grain=0.08)
            elif kind == 'slope':
                c = p['slope_color']
                sw = swatch(c, tuple(x * 0.82 for x in c), 1.0, 0, 0.8, cell, nrng, grain=0.1)
            else:
                sw = swatch(p['color'], p['color2'], p['noise'], p['courses'], p['course_dark'], cell, nrng)
            swatches[(m, kind)] = sw
        r, c = divmod(idx, per_row)
        img[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell] = swatches[(m, kind)] * AO_LEVELS[lv]
        spec = p.get('spec') if p.get('spec') is not None else 0.3
        refl = p.get('refl') if p.get('refl') is not None else 6
        sref[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell, :3] = swatches[(m, kind)] * AO_LEVELS[lv] * spec
        sref[r * cell:(r + 1) * cell, c * cell:(c + 1) * cell, 3] = refl / 255.0
        cell_uv[key] = (c * cell / ATLAS, r * cell / ATLAS, cell / ATLAS)

    # ---- per polygon: cell choice + planar UVs
    zr_min = {}
    for m in mats:
        p = pal[m]
        if p.get('zramp'):
            zs = [z for z, _ in p['zramp']]
            zr_min[m] = (min(zs), max(zs))
    out_verts, out_tris, vindex = [], [], {}
    poly_tris = {}
    for ti, pi in enumerate(tri_poly):
        poly_tris.setdefault(pi, []).append(tris[ti])
    for pi, f in enumerate(b.faces):
        if pi not in poly_tris:
            continue
        m = mats[b.fmat[pi]]
        p = pal[m]
        n = pn[pi]
        smooth = b.fsmooth[pi]
        a = ao[pi]
        bright = 0.42 + 0.58 * a
        lv = min(range(len(AO_LEVELS)), key=lambda i: abs(AO_LEVELS[i] - bright))
        if smooth:
            lv = min(lv, 1) if p.get('zramp') is None else 0   # terrain: no per-face AO patches
        if not p.get('ao', True):
            lv = 0
        if p.get('slope_color') is not None and n.z < p.get('slope_start', 0.55):
            kind = 'slope'
        elif p.get('zramp'):
            lo, hi = zr_min[m]
            zj = pcen[pi].z + rng.uniform(-0.5, 0.5)
            zi = int(round((min(max(zj, lo), hi) - lo) / (hi - lo) * (ZBANDS - 1)))
            kind = 'z%d' % zi
        else:
            kind = 'base'
        u0, v0, cs = cell_uv[(m, kind, lv)]
        # planar projection on the dominant axis; t follows world Z on walls
        ax = max(range(3), key=lambda i: abs(n[i]))
        if ax == 2:
            S = [Vector((1, 0, 0)), Vector((0, -1, 0))]
        elif ax == 0:
            S = [Vector((0, math.copysign(1, n.x), 0)), Vector((0, 0, -1))]
        else:
            S = [Vector((-math.copysign(1, n.y), 0, 0)), Vector((0, 0, -1))]
        st = {i: (P[i].dot(S[0]), P[i].dot(S[1])) for i in f}
        smin = min(x[0] for x in st.values()); tmin = min(x[1] for x in st.values())
        smax = max(x[0] for x in st.values()); tmax = max(x[1] for x in st.values())
        span = max(smax - smin, tmax - tmin, 1e-6)
        scale = 1.0 / max(WORLD_PER_CELL, span)
        # random offset inside the cell when the face is small, so repeats don't line up
        free_s = max(0.0, 1 - (smax - smin) * scale)
        free_t = max(0.0, 1 - (tmax - tmin) * scale)
        os_, ot = rng.random() * free_s, rng.random() * free_t
        usable = cs * (1 - 2 * INSET)
        if smooth:
            # smooth surfaces (terrain, foliage, rocks, domes): one continuous mapping per
            # vertex, so neighbouring polygons in the same cell share their vertices (a
            # per-polygon patch costs ~3 vertices per triangle)
            uvs = {i: _smooth_uv(P[i], vn[i] if vn[i] is not None else n, u0, v0, cs, usable) for i in f}
        for i in f:
            if smooth:
                u, v = uvs[i]
            else:
                s, t = st[i]
                u = u0 + cs * INSET + usable * (os_ + (s - smin) * scale)
                v = v0 + cs * INSET + usable * (ot + (t - tmin) * scale)
            nn = vn[i] if (smooth and vn[i] is not None) else n
            key = (i, round(u, 6), round(v, 6), round(nn.x, 4), round(nn.y, 4), round(nn.z, 4))
            if key not in vindex:
                vindex[key] = len(out_verts)
                out_verts.append([tuple(P[i]), tuple(nn), None, None, (u, v)])
        for t in poly_tris[pi]:
            ids = []
            for i in t:
                if smooth:
                    u, v = uvs[i]
                else:
                    s, tt = st[i]
                    u = u0 + cs * INSET + usable * (os_ + (s - smin) * scale)
                    v = v0 + cs * INSET + usable * (ot + (tt - tmin) * scale)
                nn = vn[i] if (smooth and vn[i] is not None) else n
                ids.append(vindex[(i, round(u, 6), round(v, 6), round(nn.x, 4), round(nn.y, 4), round(nn.z, 4))])
            out_tris.append(tuple(ids))
    # tangents / binormals from UV derivatives (v is DirectX: 0 = top row)
    acc_t = [Vector((0, 0, 0)) for _ in out_verts]
    acc_b = [Vector((0, 0, 0)) for _ in out_verts]
    for (i0, i1, i2) in out_tris:
        p0, p1, p2 = (Vector(out_verts[i][0]) for i in (i0, i1, i2))
        (u0, v0), (u1, v1), (u2, v2) = (out_verts[i][4] for i in (i0, i1, i2))
        d1, d2 = p1 - p0, p2 - p0
        du1, dv1, du2, dv2 = u1 - u0, v1 - v0, u2 - u0, v2 - v0
        det = du1 * dv2 - du2 * dv1
        if abs(det) < 1e-12:
            continue
        r = 1.0 / det
        T = (d1 * dv2 - d2 * dv1) * r
        B = (d2 * du1 - d1 * du2) * r
        for i in (i0, i1, i2):
            acc_t[i] += T
            acc_b[i] += B
    for i, v in enumerate(out_verts):
        n = Vector(v[1])
        t = acc_t[i] - n * n.dot(acc_t[i])
        if t.length < 1e-9:
            t = n.orthogonal()
        t.normalize()
        bb = n.cross(t)
        if bb.dot(acc_b[i]) < 0:
            bb = -bb
        v[2], v[3] = tuple(t), tuple(bb)
    res = Result()
    res.verts = [tuple(v) for v in out_verts]
    res.tris = out_tris
    res.image = np.clip(np.rint(img * 255), 0, 255).astype(np.uint8)  # top row first
    res.sref = np.clip(np.rint(sref * 255), 0, 255).astype(np.uint8)
    res.cells = len(cell_keys)
    res.cell_px = cell
    return res


def _mirror(p):
    """Triangle wave 0..1..0 with period 2: a seamless, continuous coordinate inside a cell."""
    p = p % 2.0
    return p if p <= 1.0 else 2.0 - p


def _smooth_uv(p, nrm, u0, v0, cs, usable):
    """Per-vertex UV for smooth surfaces: planar projection on the vertex normal's dominant
    axis, mirrored every WORLD_PER_CELL units so it never leaves the cell."""
    ax = max(range(3), key=lambda i: abs(nrm[i]))
    if ax == 2:
        s, t = p.x, -p.y
    elif ax == 0:
        s, t = p.y, -p.z
    else:
        s, t = p.x, -p.z
    return (u0 + cs * INSET + usable * _mirror(s / WORLD_PER_CELL),
            v0 + cs * INSET + usable * _mirror(t / WORLD_PER_CELL))


def _ramp(stops, z):
    stops = sorted(stops)
    if z <= stops[0][0]:
        return stops[0][1]
    for (z0, c0), (z1, c1) in zip(stops, stops[1:]):
        if z <= z1:
            t = (z - z0) / (z1 - z0)
            return tuple(a + (bb - a) * t for a, bb in zip(c0, c1))
    return stops[-1][1]
