"""Sculpting with signed distance fields (numpy), for organic landmarks (the Balrog, 2026-11-26).

A Field is a regular grid of truncated signed distances (negative inside). Primitives (ellipsoids, tapered capsules,
chains of them, rounded boxes) are blended in with a smooth minimum, so muscles, skull and limbs flow into each
other like a sculpt; cavities are carved with a smooth maximum; noise displaces the surface. The surface is meshed by
MARCHING TETRAHEDRA (vectorised, no tables: every cube is split into the 6 Kuhn tetrahedra round its diagonal) and
then decimated in Blender to the game's budget, while the full-resolution mesh is kept as the source of the baked
ambient occlusion and relief shading (bake.py, b.hires).

Only primitives' bounding boxes are evaluated, so a big grid stays cheap. Units = in-game units.
"""
import itertools
import math

import numpy as np


# --------------------------------------------------------------------------- noise
def _hash3(i, j, k, seed):
    n = (i * 73856093) ^ (j * 19349663) ^ (k * 83492791) ^ (seed * 2654435761)
    n = n.astype(np.int64) & 0xffffffff
    n = (n ^ (n >> 13)) * 1274126177 & 0xffffffff
    n = n ^ (n >> 16)
    return (n & 0xffff).astype(np.float32) / 65535.0


def vnoise3(x, y, z, seed=0):
    """Smooth value noise in [0, 1] at arrays of points."""
    xi, yi, zi = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - xi, y - yi, z - zi
    ux, uy, uz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    xi, yi, zi = xi.astype(np.int64), yi.astype(np.int64), zi.astype(np.int64)
    out = 0.0
    for dx, dy, dz in itertools.product((0, 1), repeat=3):
        w = (ux if dx else 1 - ux) * (uy if dy else 1 - uy) * (uz if dz else 1 - uz)
        out = out + w * _hash3(xi + dx, yi + dy, zi + dz, seed)
    return out


def fbm3(x, y, z, octaves=4, seed=0, lac=2.0, gain=0.5):
    """Fractal noise, about -0.5 .. 0.5."""
    tot, amp, norm, f = 0.0, 1.0, 0.0, 1.0
    for o in range(octaves):
        tot = tot + amp * vnoise3(x * f, y * f, z * f, seed + 17 * o)
        norm += amp
        amp *= gain
        f *= lac
    return tot / norm - 0.5


def ridged3(x, y, z, octaves=3, seed=0):
    """Ridged noise 0..1: sharp crests (muscle fibres, sinews when stretched)."""
    tot, amp, norm, f = 0.0, 1.0, 0.0, 1.0
    for o in range(octaves):
        n = 1.0 - np.abs(2.0 * vnoise3(x * f, y * f, z * f, seed + 31 * o) - 1.0)
        tot = tot + amp * n * n
        norm += amp
        amp *= 0.5
        f *= 2.0
    return tot / norm


# --------------------------------------------------------------------------- primitives: fn(X, Y, Z) -> distance, bbox
def _rot(R):
    return None if R is None else np.asarray(R, np.float64)[:3, :3]


def ellipsoid(c, r, R=None):
    """Ellipsoid at c with radii r (rotation R, 3x3 or 4x4: local -> world)."""
    c = np.asarray(c, float)
    r = np.asarray(r, float)
    M = _rot(R)

    def f(X, Y, Z):
        px, py, pz = X - c[0], Y - c[1], Z - c[2]
        if M is not None:      # world -> local = M^T
            px, py, pz = (M[0, 0] * px + M[1, 0] * py + M[2, 0] * pz, M[0, 1] * px + M[1, 1] * py + M[2, 1] * pz,
                          M[0, 2] * px + M[1, 2] * py + M[2, 2] * pz)
        k0 = np.sqrt((px / r[0]) ** 2 + (py / r[1]) ** 2 + (pz / r[2]) ** 2)
        k1 = np.sqrt((px / r[0] ** 2) ** 2 + (py / r[1] ** 2) ** 2 + (pz / r[2] ** 2) ** 2)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)
    m = r.max()
    return f, (c - m, c + m)


def cone(a, b, ra, rb):
    """A round cone (tapered capsule) from a (radius ra) to b (radius rb)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ba = b - a
    L2 = float(ba @ ba) or 1e-9

    def f(X, Y, Z):
        px, py, pz = X - a[0], Y - a[1], Z - a[2]
        t = np.clip((px * ba[0] + py * ba[1] + pz * ba[2]) / L2, 0.0, 1.0)
        dx, dy, dz = px - t * ba[0], py - t * ba[1], pz - t * ba[2]
        return np.sqrt(dx * dx + dy * dy + dz * dz) - (ra + (rb - ra) * t)
    m = max(ra, rb)
    return f, (np.minimum(a, b) - m, np.maximum(a, b) + m)


def rbox(c, half, R=None, rad=0.5):
    """A rounded box: centre c, half sizes, corner radius rad (rotation R local -> world)."""
    c = np.asarray(c, float)
    hs = np.asarray(half, float) - rad
    M = _rot(R)

    def f(X, Y, Z):
        px, py, pz = X - c[0], Y - c[1], Z - c[2]
        if M is not None:
            px, py, pz = (M[0, 0] * px + M[1, 0] * py + M[2, 0] * pz, M[0, 1] * px + M[1, 1] * py + M[2, 1] * pz,
                          M[0, 2] * px + M[1, 2] * py + M[2, 2] * pz)
        qx, qy, qz = np.abs(px) - hs[0], np.abs(py) - hs[1], np.abs(pz) - hs[2]
        out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
        return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0.0) - rad
    m = float(np.linalg.norm(half))
    return f, (c - m, c + m)


def chain(pts, radii):
    """Tapered tube along a polyline (list of primitives: one round cone per segment, joined by a plain min)."""
    return [cone(pts[i], pts[i + 1], radii[i], radii[i + 1]) for i in range(len(pts) - 1)]


def union_hard(prims):
    """Several primitives as one (hard min), e.g. a chain."""
    fs = [p[0] for p in prims]
    lo = np.min([p[1][0] for p in prims], 0)
    hi = np.max([p[1][1] for p in prims], 0)

    def f(X, Y, Z):
        d = fs[0](X, Y, Z)
        for g in fs[1:]:
            d = np.minimum(d, g(X, Y, Z))
        return d
    return f, (lo, hi)


# --------------------------------------------------------------------------- the field
def smin(a, b, k):
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b * (1 - h) + a * h - k * h * (1 - h)


def smax(a, b, k):
    return -smin(-a, -b, k)


class Field:
    def __init__(self, lo, hi, step, far=4.0):
        self.lo = np.asarray(lo, float)
        self.step = float(step)
        self.n = np.ceil((np.asarray(hi, float) - self.lo) / step).astype(int) + 1
        self.far = far
        self.F = np.full(tuple(self.n), far, np.float32)

    def _region(self, bb, pad):
        i0 = np.clip(np.floor((bb[0] - pad - self.lo) / self.step).astype(int), 0, self.n - 1)
        i1 = np.clip(np.ceil((bb[1] + pad - self.lo) / self.step).astype(int) + 1, 0, self.n)
        if np.any(i1 <= i0):
            return None
        sl = tuple(slice(a, b) for a, b in zip(i0, i1))
        ax = [self.lo[d] + self.step * np.arange(i0[d], i1[d]) for d in range(3)]
        X, Y, Z = np.meshgrid(*ax, indexing='ij')
        return sl, X, Y, Z

    def add(self, prim, k=0.0):
        f, bb = prim
        r = self._region(bb, k + self.far)
        if r is None:
            return
        sl, X, Y, Z = r
        self.F[sl] = smin(self.F[sl], f(X, Y, Z).astype(np.float32), k)

    def sub(self, prim, k=0.0):
        f, bb = prim
        r = self._region(bb, k + 1.0)
        if r is None:
            return
        sl, X, Y, Z = r
        self.F[sl] = smax(self.F[sl], -f(X, Y, Z).astype(np.float32), k)

    def intersect(self, prim, k=0.0):
        """Keep only what is inside prim (e.g. cut everything below the ground)."""
        f, bb = prim
        X, Y, Z = self.coords()
        self.F = smax(self.F, f(X, Y, Z).astype(np.float32), k)

    def coords(self, sl=None):
        ax = [self.lo[d] + self.step * np.arange(self.n[d]) for d in range(3)]
        return np.meshgrid(*ax, indexing='ij')

    def displace(self, fn, band=3.0):
        """F += fn(X, Y, Z) where the surface is near (|F| < band): fn returns an offset (positive = dig in)."""
        idx = np.nonzero(np.abs(self.F) < band)
        X = self.lo[0] + self.step * idx[0]
        Y = self.lo[1] + self.step * idx[1]
        Z = self.lo[2] + self.step * idx[2]
        self.F[idx] += fn(X, Y, Z).astype(np.float32)

    def mesh(self):
        return marching_tets(self.F, self.lo, self.step)


# --------------------------------------------------------------------------- meshing
_CORNERS = np.array([(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0), (0, 0, 1), (1, 0, 1), (0, 1, 1), (1, 1, 1)])
_TETS = [(0, p[0], p[0] + p[1], 7) for p in itertools.permutations((1, 2, 4))]


def marching_tets(F, lo, step):
    """Iso-surface F = 0 -> (verts float64 Nx3, tris int Mx3), outward winding (counter-clockwise from outside)."""
    nx, ny, nz = F.shape
    inside = F < 0
    cx, cy, cz = nx - 1, ny - 1, nz - 1
    anyin = np.zeros((cx, cy, cz), bool)
    allin = np.ones((cx, cy, cz), bool)
    for (a, b, c) in _CORNERS:
        s = inside[a:a + cx, b:b + cy, c:c + cz]
        anyin |= s
        allin &= s
    act = np.nonzero(anyin & ~allin)
    I, J, K = (x.astype(np.int64) for x in act)
    stride = np.array([ny * nz, nz, 1], np.int64)
    base = I * stride[0] + J * stride[1] + K * stride[2]
    corner_off = _CORNERS @ stride
    Ff = F.ravel()
    edges_a, edges_b, tri_edges, tri_dir = [], [], [], []
    ntot = nx * ny * nz
    for tet in _TETS:
        g = base[:, None] + corner_off[list(tet)][None, :]          # N x 4 global point indices
        v = Ff[g]
        m = v < 0
        nin = m.sum(1)
        order = np.argsort(~m, axis=1, kind='stable')                # inside corners first
        go = np.take_along_axis(g, order, 1)
        for n_in in (1, 2, 3):
            sel = nin == n_in
            if not sel.any():
                continue
            q = go[sel]
            if n_in == 1:
                tris = [((0, 1), (0, 2), (0, 3))]
            elif n_in == 3:
                tris = [((3, 0), (3, 1), (3, 2))]
            else:
                tris = [((0, 2), (0, 3), (1, 3)), ((0, 2), (1, 3), (1, 2))]
            ins = q[:, :n_in]
            outs = q[:, n_in:]
            for tr in tris:
                ks = []
                for (i_, j_) in tr:
                    a_, b_ = q[:, i_], q[:, j_]
                    ks.append(np.minimum(a_, b_) * ntot + np.maximum(a_, b_))
                tri_edges.append(np.stack(ks, 1))
                tri_dir.append((ins, outs))
    E = np.concatenate(tri_edges, 0)
    uniq, inv = np.unique(E.ravel(), return_inverse=True)
    ga, gb = uniq // ntot, uniq % ntot

    def pos(gi):
        i = gi // stride[0]
        j = (gi // stride[1]) % ny
        k = gi % nz
        return np.stack([lo[0] + step * i, lo[1] + step * j, lo[2] + step * k], 1)
    va, vb = Ff[ga].astype(np.float64), Ff[gb].astype(np.float64)
    t = np.clip(va / np.where(np.abs(va - vb) < 1e-12, 1e-12, va - vb), 0.0, 1.0)
    pa, pb = pos(ga), pos(gb)
    verts = pa + (pb - pa) * t[:, None]
    tris = inv.reshape(-1, 3)
    # winding: the normal must point from the inside corners towards the outside ones
    cin = np.concatenate([pos(i.ravel()).reshape(i.shape + (3,)).mean(1) for i, _ in tri_dir], 0)
    cout = np.concatenate([pos(o.ravel()).reshape(o.shape + (3,)).mean(1) for _, o in tri_dir], 0)
    p0, p1, p2 = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    nrm = np.cross(p1 - p0, p2 - p0)
    flip = (nrm * (cout - cin)).sum(1) < 0
    tris[flip] = tris[flip][:, ::-1]
    # drop degenerate triangles (a corner exactly on the surface)
    ok = (tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2]) & (tris[:, 0] != tris[:, 2])
    area = np.linalg.norm(nrm, axis=1)
    ok &= area > 1e-10
    return verts, tris[ok]


def drop_small(verts, tris, min_tris=200):
    """Remove disconnected bits with fewer than min_tris triangles (noise specks)."""
    n = len(verts)
    parent = np.arange(n)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    # union-find over edges (vectorised by repeated pointer jumping)
    a = np.concatenate([tris[:, 0], tris[:, 1]])
    b = np.concatenate([tris[:, 1], tris[:, 2]])
    lab = np.arange(n)
    for _ in range(200):
        la, lb = lab[a], lab[b]
        m = np.minimum(la, lb)
        new = lab.copy()
        np.minimum.at(new, a, m)
        np.minimum.at(new, b, m)
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    tl = lab[tris[:, 0]]
    ids, cnt = np.unique(tl, return_counts=True)
    keep = set(ids[cnt >= min_tris].tolist())
    ok = np.isin(tl, list(keep))
    tris = tris[ok]
    used = np.unique(tris)
    remap = -np.ones(n, np.int64)
    remap[used] = np.arange(len(used))
    return verts[used], remap[tris]


# --------------------------------------------------------------------------- Blender: decimate, hand to a builder
def to_blender(name, verts, tris):
    import bpy
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', np.asarray(verts, np.float32).ravel())
    me.loops.add(len(tris) * 3)
    me.loops.foreach_set('vertex_index', np.asarray(tris, np.int32).ravel())
    me.polygons.add(len(tris))
    me.polygons.foreach_set('loop_start', np.arange(0, len(tris) * 3, 3, dtype=np.int32))
    me.update(calc_edges=True)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def from_blender(ob, apply=True):
    import bpy
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg) if apply else ob
    me = ev.to_mesh()
    me.calc_loop_triangles()
    v = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', v)
    t = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get('vertices', t)
    ev.to_mesh_clear()
    return v.reshape(-1, 3).astype(np.float64), t.reshape(-1, 3)


def decimate(verts, tris, target_tris, name='dec'):
    """Collapse-decimate to about target_tris triangles (Blender), returns (verts, tris)."""
    import bpy
    if len(tris) <= target_tris:
        return verts, tris
    ob = to_blender(name, verts, tris)
    mod = ob.modifiers.new('D', 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = target_tris / len(tris)
    mod.use_collapse_triangulate = True
    v, t = from_blender(ob)
    me = ob.data
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return v, t


def smooth_mesh(verts, tris, iters=2, lam=0.5):
    """Laplacian smoothing (umbrella) to take the grid's facets off."""
    n = len(verts)
    V = verts.copy()
    a = np.concatenate([tris[:, 0], tris[:, 1], tris[:, 2], tris[:, 1], tris[:, 2], tris[:, 0]])
    b = np.concatenate([tris[:, 1], tris[:, 2], tris[:, 0], tris[:, 0], tris[:, 1], tris[:, 2]])
    deg = np.bincount(a, minlength=n).astype(np.float64)
    for _ in range(iters):
        acc = np.zeros_like(V)
        for d in range(3):
            acc[:, d] = np.bincount(a, weights=V[b, d], minlength=n)
        avg = acc / np.maximum(deg, 1)[:, None]
        V = V + lam * (avg - V)
    return V


def add_to_builder(b, verts, tris, mat_fn, hires=None):
    """Hand a mesh to a blib Builder, one material per face from mat_fn(centroids Nx3) -> names (or one name). The
    mesh given here should already be decimated to the game's budget; `hires` (verts, tris), the full-resolution
    surface, is kept on the builder as a source of the AO / relief bake (bake.py b.hires)."""
    cen = verts[tris].mean(1)
    names = mat_fn(cen) if callable(mat_fn) else [mat_fn] * len(tris)
    base = len(b.verts)
    b.verts.extend(tuple(map(float, p)) for p in verts)
    for f, nm in zip(tris, names):
        b.faces.append((base + int(f[0]), base + int(f[1]), base + int(f[2])))
        b.fmat.append(b._mi(str(nm)))
        b.fsmooth.append(True)
    if hires is not None:
        if not hasattr(b, 'hires'):
            b.hires = []
        b.hires.append(hires)
