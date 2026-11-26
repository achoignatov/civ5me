"""Shared helpers for the procedural loading-screen scenes (Blender + numpy): noise, mesh building, node trees,
thick swept/lathed armour primitives, the Cycles EXR render. Used by mordor.py (shire.py predates it).
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.append(os.path.join(ROOT, 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages'))
import numpy as np
import bpy, bmesh

# --------------------------------------------------------------------------- noise (numpy, deterministic)
def _hash(ix, iy, seed):
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263 + (seed * 1013904223 & 0xFFFFFFF)) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)

def vnoise(x, y, seed=0):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    xi, yi = np.floor(x), np.floor(y)
    fx, fy = x - xi, y - yi
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    xi = xi.astype(np.int64); yi = yi.astype(np.int64)
    a = _hash(xi, yi, seed); b = _hash(xi + 1, yi, seed)
    c = _hash(xi, yi + 1, seed); d = _hash(xi + 1, yi + 1, seed)
    return (a + (b - a) * ux) + ((c + (d - c) * ux) - (a + (b - a) * ux)) * uy

def fbm(x, y, octaves=5, seed=0, lac=2.03, gain=0.5):
    s, amp, norm = 0.0, 1.0, 0.0
    for o in range(octaves):
        s = s + amp * (vnoise(x, y, seed + o * 17) * 2 - 1)
        norm += amp; amp *= gain; x = x * lac + 3.1; y = y * lac - 1.7
    return s / norm

def ridged(x, y, octaves=6, seed=0):
    s, amp, norm, w = 0.0, 1.0, 0.0, 1.0
    for o in range(octaves):
        n = 1 - np.abs(vnoise(x, y, seed + o * 31) * 2 - 1)
        n = n * n * w
        w = np.clip(n * 1.6, 0, 1)
        s = s + amp * n; norm += amp; amp *= 0.5; x = x * 2.1 + 5.3; y = y * 2.1 - 2.9
    return s / norm

def fbm3(p, octaves=4, seed=0):
    """cheap 3-D noise: sum of 2-D fbm over the three coordinate planes"""
    return (fbm(p[..., 0], p[..., 1], octaves, seed) + fbm(p[..., 1], p[..., 2], octaves, seed + 5)
            + fbm(p[..., 2], p[..., 0], octaves, seed + 9)) / 3

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)

def nrm(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)

# --------------------------------------------------------------------------- geometry accumulation
class Geo:
    """vertices + polygons (any size) gathered per material, turned into one Blender object each"""
    def __init__(self):
        self.V = []; self.F = []; self.n = 0
    def add(self, V, F):
        V = np.asarray(V, np.float64).reshape(-1, 3)
        self.V.append(V)
        if isinstance(F, np.ndarray):
            self.F.extend((F + self.n).tolist())
        else:
            self.F.extend([[i + self.n for i in f] for f in F])
        self.n += len(V)
    def add_vf(self, vf):
        self.add(*vf)
    def transform(self, M):
        """apply a 4x4 matrix to everything added so far"""
        M = np.asarray(M)
        self.V = [v @ M[:3, :3].T + M[:3, 3] for v in self.V]

def mesh_obj(name, V, F, coll=None, recalc=True):
    V = np.asarray(V, np.float32).reshape(-1, 3)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set('co', V.ravel())
    if F:
        sizes = np.array([len(f) for f in F], np.int32)
        flat = np.fromiter((i for f in F for i in f), np.int32, int(sizes.sum()))
        me.loops.add(len(flat))
        me.loops.foreach_set('vertex_index', flat)
        me.polygons.add(len(F))
        me.polygons.foreach_set('loop_start', np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.int32))
        me.polygons.foreach_set('loop_total', sizes)
    me.update(calc_edges=True)
    me.validate()
    if recalc and F:
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me)
    (coll or bpy.context.scene.collection).objects.link(ob)
    return ob

def geo_obj(name, g, material, smooth=True, bevel=None, coll=None):
    if not g.V:
        return None
    ob = mesh_obj(name, np.concatenate(g.V), g.F, coll)
    ob.data.materials.append(material)
    if smooth:
        ob.data.polygons.foreach_set('use_smooth', np.ones(len(ob.data.polygons), bool))
    if bevel:
        b = ob.modifiers.new('bevel', 'BEVEL')
        b.width = bevel; b.segments = 2; b.limit_method = 'ANGLE'; b.angle_limit = math.radians(32)
        b.harden_normals = True
    return ob

def set_attr(ob, name, vals, dom='POINT', typ='FLOAT'):
    a = ob.data.attributes.new(name, typ, dom)
    a.data.foreach_set('vector' if typ == 'FLOAT_VECTOR' else 'value', np.asarray(vals, np.float32).ravel())

def grid_faces(rows, cols, off=0):
    idx = np.arange(rows * cols).reshape(rows, cols) + off
    a = idx[:-1, :-1].ravel(); b = idx[:-1, 1:].ravel(); c = idx[1:, 1:].ravel(); d = idx[1:, :-1].ravel()
    return np.stack([a, b, c, d], 1)

def sweep(S, closed_along=False, cap=True):
    """S (N, K, 3): N cross-sections of K points each (each section a closed loop) -> tube/solid"""
    S = np.asarray(S, np.float64)
    N, K, _ = S.shape
    i = np.arange(N if closed_along else N - 1)[:, None]
    k = np.arange(K)[None, :]
    i2 = (i + 1) % N; k2 = (k + 1) % K
    F = np.stack(np.broadcast_arrays(i * K + k, i * K + k2, i2 * K + k2, i2 * K + k), -1).reshape(-1, 4).tolist()
    if cap and not closed_along:
        F.append(list(range(K))[::-1]); F.append([(N - 1) * K + kk for kk in range(K)])
    return S.reshape(-1, 3), F

def frames(P, ref):
    """parallel-transport frames along a polyline: tangents T, normals N (start near ref), binormals B"""
    P = np.asarray(P, np.float64)
    T = nrm(np.gradient(P, axis=0))
    N = np.empty_like(P)
    r = np.asarray(ref, np.float64)
    n = r - T[0] * np.dot(r, T[0])
    if np.linalg.norm(n) < 1e-6:
        n = np.cross(T[0], [0.31, 0.53, 0.79])
    N[0] = n / np.linalg.norm(n)
    for i in range(1, len(P)):
        n = N[i - 1] - T[i] * np.dot(N[i - 1], T[i])
        N[i] = n / np.linalg.norm(n)
    return T, N, np.cross(T, N)

def tube(P, rx, ry=None, ref=(0, 0, 1), K=10, cap=True):
    """sweep an ellipse (rx along the frame normal, ry along the binormal) along a polyline"""
    P = np.asarray(P, np.float64)
    rx = np.broadcast_to(np.asarray(rx, np.float64), (len(P),))
    ry = rx if ry is None else np.broadcast_to(np.asarray(ry, np.float64), (len(P),))
    T, N, B = frames(P, ref)
    a = np.linspace(0, 2 * math.pi, K, endpoint=False)
    S = (P[:, None] + np.cos(a)[None, :, None] * (rx[:, None, None] * N[:, None])
         + np.sin(a)[None, :, None] * (ry[:, None, None] * B[:, None]))
    return sweep(S, cap=cap)

def spike(base, d, length, r0, K=6, bend=None, bend_amt=0.0, ref=(0, 0, 1), n=7, flat=1.0):
    d = nrm(d)
    t = np.linspace(0, 1, n)
    P = np.asarray(base)[None] + d[None] * (t * length)[:, None]
    if bend is not None:
        P = P + nrm(bend)[None] * (bend_amt * length * t ** 2)[:, None]
    r = r0 * (1 - t) ** 1.1 + 1e-4
    return tube(P, r, r * flat, ref=ref, K=K)

def slab(P, th):
    """thick sheet from a (nu, nv, 3) grid: outer surface P, inner offset by -normal*th, walls round the edge"""
    P = np.asarray(P, np.float64)
    nu, nv, _ = P.shape
    du = np.gradient(P, axis=0); dv = np.gradient(P, axis=1)
    n = nrm(np.cross(du, dv) + 1e-12)
    th = np.broadcast_to(np.asarray(th, np.float64), (nu, nv))
    Q = P - n * th[..., None]
    V = np.concatenate([P.reshape(-1, 3), Q.reshape(-1, 3)])
    F = grid_faces(nu, nv).tolist() + grid_faces(nu, nv, nu * nv)[:, ::-1].tolist()
    idx = np.arange(nu * nv).reshape(nu, nv)
    ring = np.concatenate([idx[0, :], idx[1:, -1], idx[-1, -2::-1], idx[-2:0:-1, 0]])
    m = len(ring)
    for j in range(m):
        a, b = ring[j], ring[(j + 1) % m]
        F.append([int(a), int(b), int(b + nu * nv), int(a + nu * nv)])
    return V, F

def sphere_grid(c, r, nlat=12, nlon=16, noise_amp=0.0, seed=0, nscale=1.5, squash=(1, 1, 1), flat_bottom=None,
                sharp=0.0):
    """lat-long ball (as a capped sweep) optionally displaced by 3-D noise: rocks, boulders, skull domes"""
    lat = np.linspace(-math.pi / 2 + 0.12, math.pi / 2 - 0.12, nlat)
    lon = np.linspace(0, 2 * math.pi, nlon, endpoint=False)
    U = np.stack([np.cos(lat)[:, None] * np.cos(lon)[None], np.cos(lat)[:, None] * np.sin(lon)[None],
                  np.repeat(np.sin(lat)[:, None], nlon, 1)], -1)
    rr = r * (1 + noise_amp * fbm3(U * nscale + seed * 7.3, 5, seed))
    if sharp:      # ridges and broken facets
        rr = rr - r * sharp * np.abs(fbm3(U * nscale * 2.7 + seed * 3.1, 4, seed + 1))
    P = U * rr[..., None] * np.asarray(squash)
    if flat_bottom is not None:
        P[..., 2] = np.maximum(P[..., 2], flat_bottom)
    return sweep(np.asarray(c) + P, cap=True)

class Limb:
    """an axis p0 -> p1 with a radius r(t, theta); theta 0 = `fwd` (projected), +90 deg = axis x fwd"""
    def __init__(self, p0, p1, fwd, rfun):
        self.p0 = np.asarray(p0, np.float64); self.p1 = np.asarray(p1, np.float64)
        ax = self.p1 - self.p0; self.L = np.linalg.norm(ax); self.A = ax / self.L
        f = np.asarray(fwd, np.float64); f = f - self.A * np.dot(f, self.A); self.F = f / np.linalg.norm(f)
        self.S = np.cross(self.A, self.F)
        self.r = rfun
    def radial(self, th):
        th = np.asarray(th, np.float64)
        return np.cos(th)[..., None] * self.F + np.sin(th)[..., None] * self.S
    def pt(self, t, th, extra=0.0):
        t, th, extra = np.broadcast_arrays(np.asarray(t, np.float64), np.asarray(th, np.float64),
                                           np.asarray(extra, np.float64))
        r = self.r(t, th) + extra
        return self.p0 + self.A * (t * self.L)[..., None] + self.radial(th) * r[..., None]

def ell(ts, ws, ds, dfront=None):
    """elliptic section: half-width ws (the theta=90 side), half-depth ds (theta=0/180); profiles over t"""
    def r(t, th):
        w = np.interp(t, ts, ws); d = np.interp(t, ts, ds)
        if dfront is not None:
            d = np.where(np.cos(th) > 0, np.interp(t, ts, dfront), d)
        c, s = np.cos(th), np.sin(th)
        return 1.0 / np.sqrt((c / d) ** 2 + (s / w) ** 2)
    return r

def band(limb, th0, th1, nth, t_top, t_bot, lift=0.01, flare=0.02, thick=0.012, rows=4, closed=False, fpow=1.5,
         wobble=0.0, seed=0):
    """a thick armour plate wrapped round a limb: from t_top(theta) to t_bot(theta), flaring out by `flare` towards
    the t_bot edge (so stacked bands overlap like shingles). Returns (V, F)."""
    th = np.linspace(th0, th1, nth, endpoint=not closed)
    tt = np.asarray(t_top(th) if callable(t_top) else np.full(nth, t_top), np.float64)
    tb = np.asarray(t_bot(th) if callable(t_bot) else np.full(nth, t_bot), np.float64)
    s = np.linspace(0, 1, rows)
    T = tt[:, None] + (tb - tt)[:, None] * s[None]
    E = lift + flare * s[None] ** fpow + np.zeros_like(T)
    if wobble:
        E = E + wobble * fbm(th[:, None] * 3 + seed, s[None] * 2, 3, seed)
    TH = np.repeat(th[:, None], rows, 1)
    outer = limb.pt(T, TH, E)
    inner = limb.pt(T[:, ::-1], TH[:, ::-1], E[:, ::-1] - thick)
    S = np.concatenate([outer, inner], 1)
    return sweep(S, closed_along=closed, cap=not closed)

def lames(g, limb, t0, t1, n, th0=-math.pi, th1=math.pi, nth=40, lift=0.012, flare=0.022, thick=0.01,
          overlap=0.35, closed=True, lift_step=0.0, rows=4):
    """n overlapping bands stacked from t0 to t1 (flaring towards t1)"""
    edges = np.linspace(t0, t1, n + 1)
    dt = (t1 - t0) / n
    for i in range(n):
        g.add_vf(band(limb, th0, th1, nth, edges[i], edges[i + 1] + overlap * dt * 0.5, lift + lift_step * i,
                      flare, thick, rows, closed))

def torus(c, axis, R, r, n=24, k=8):
    axis = nrm(axis)
    a = np.linspace(0, 2 * math.pi, n, endpoint=False)
    T, N, B = frames(np.stack([np.zeros(3), axis]), (0.3, 0.5, 0.8))
    c = np.asarray(c, np.float64)
    P = c + R * (np.cos(a)[:, None] * N[0] + np.sin(a)[:, None] * B[0])
    rad = nrm(P - c)
    b = np.linspace(0, 2 * math.pi, k, endpoint=False)
    S = P[:, None] + r * (np.cos(b)[None, :, None] * rad[:, None] + np.sin(b)[None, :, None] * axis[None, None])
    return sweep(S, closed_along=True)

# --------------------------------------------------------------------------- shader nodes
class NB:
    """tiny node-tree builder"""
    def __init__(self, tree):
        self.t = tree
        self.t.nodes.clear()
    def n(self, typ, **kw):
        nd = self.t.nodes.new(typ)
        for k, v in kw.items():
            if k.startswith('i_'):
                nd.inputs[k[2:].replace('_', ' ')].default_value = v
            else:
                setattr(nd, k, v)
        return nd
    def l(self, a, b):
        self.t.links.new(a, b)
        return b
    def math(self, op, a, b=None, **kw):
        nd = self.n('ShaderNodeMath', operation=op, **kw)
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): nd.inputs[i].default_value = v
            else: self.l(v, nd.inputs[i])
        return nd.outputs[0]
    def maprange(self, v, f0, f1, t0=0.0, t1=1.0):
        nd = self.n('ShaderNodeMapRange', i_From_Min=f0, i_From_Max=f1, i_To_Min=t0, i_To_Max=t1)
        self.l(v, nd.inputs['Value'])
        return nd.outputs['Result']
    def mix(self, fac, a, b):
        nd = self.n('ShaderNodeMix', data_type='RGBA')
        for sock, v in ((nd.inputs['Factor'], fac), (nd.inputs[6], a), (nd.inputs[7], b)):
            if isinstance(v, (int, float)): sock.default_value = v
            elif isinstance(v, tuple): sock.default_value = v
            else: self.l(v, sock)
        return nd.outputs[2]

def new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nb = NB(m.node_tree)
    nb.out = nb.n('ShaderNodeOutputMaterial')
    return m, nb

def rgb(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c) + (1.0,)

def ramp(nb, stops, fac):
    r = nb.n('ShaderNodeValToRGB')
    els = r.color_ramp.elements
    while len(els) > len(stops):
        els.remove(els[-1])
    while len(els) < len(stops):
        els.new(0.5)
    for e, (p, c) in zip(els, stops):
        e.position = p; e.color = rgb(c) if isinstance(c, str) else c
    nb.l(fac, r.inputs['Fac'])
    return r

def noise(nb, vec, scale, detail=4, rough=0.55, dim=None):
    nd = nb.n('ShaderNodeTexNoise', i_Scale=scale, i_Detail=detail, i_Roughness=rough)
    if dim: nd.noise_dimensions = dim
    if vec is not None: nb.l(vec, nd.inputs['Vector'])
    return nd

def attr(nb, name, typ='GEOMETRY'):
    a = nb.n('ShaderNodeAttribute', attribute_name=name)
    a.attribute_type = typ
    return a

# --------------------------------------------------------------------------- render (linear EXR + depth)
def render(out, res_x, res_y, samples, threshold=0.006, bounces=(6, 3, 3, 2)):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False          # no OpenImageDenoise in this Blender build
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = threshold
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces, sc.cycles.volume_bounces = bounces
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.light_sampling_threshold = 0.01
    sc.cycles.sample_clamp_indirect = 3.0
    sc.render.resolution_x = res_x; sc.render.resolution_y = res_y; sc.render.resolution_percentage = 100
    sc.render.threads_mode = 'AUTO'
    sc.view_settings.view_transform = 'Standard'
    sc.render.film_transparent = False
    sc.view_layers[0].use_pass_z = True
    sc.use_nodes = True
    t = sc.node_tree; t.nodes.clear()
    rl = t.nodes.new('CompositorNodeRLayers')
    fo = t.nodes.new('CompositorNodeOutputFile')
    fo.base_path = os.path.dirname(out)
    fo.format.file_format = 'OPEN_EXR'; fo.format.color_depth = '32'; fo.format.exr_codec = 'ZIP'
    fo.file_slots.clear()
    fo.file_slots.new(os.path.basename(out) + '_rgb')
    fo.file_slots.new(os.path.basename(out) + '_z')
    t.links.new(rl.outputs['Image'], fo.inputs[0])
    t.links.new(rl.outputs['Depth'], fo.inputs[1])
    comp = t.nodes.new('CompositorNodeComposite'); t.links.new(rl.outputs['Image'], comp.inputs[0])
    sc.render.filepath = out + '_preview.png'
    sc.frame_set(1)
    bpy.ops.render.render(write_still=True)
    for s in ('_rgb', '_z'):
        src = out + s + '0001.exr'
        if os.path.exists(src):
            os.replace(src, out + s + '.exr')

# --------------------------------------------------------------------------- post-processing helpers (numpy)
def load_image(path, ch):
    im = bpy.data.images.load(path)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    a = a.reshape(h, w, 4)[::-1]           # blender stores bottom-up
    return a[..., :ch].copy()

def box(a, r, axis):
    if r < 1:
        return a
    c = np.cumsum(np.pad(a, [(r + 1, r) if i == axis else (0, 0) for i in range(a.ndim)], mode='edge'), axis=axis)
    hi = np.take(c, np.arange(2 * r + 1, c.shape[axis]), axis=axis)
    lo = np.take(c, np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
    return (hi - lo) / (2 * r + 1)

def blur(a, sigma):
    r = max(1, int(sigma * 0.85))
    for _ in range(3):
        a = box(box(a, r, 0), r, 1)
    return a

def down(a, f):
    h, w = a.shape[0] // f * f, a.shape[1] // f * f
    return a[:h, :w].reshape(h // f, f, w // f, f, -1).mean((1, 3))

def up(a, shape):
    h, w = shape[:2]
    ys = (np.arange(h) + 0.5) * a.shape[0] / h - 0.5
    xs = (np.arange(w) + 0.5) * a.shape[1] / w - 0.5
    y0 = np.clip(np.floor(ys).astype(int), 0, a.shape[0] - 1); y1 = np.clip(y0 + 1, 0, a.shape[0] - 1)
    x0 = np.clip(np.floor(xs).astype(int), 0, a.shape[1] - 1); x1 = np.clip(x0 + 1, 0, a.shape[1] - 1)
    fy = np.clip(ys - y0, 0, 1)[:, None, None]; fx = np.clip(xs - x0, 0, 1)[None, :, None]
    t = a[y0][:, x0] * (1 - fx) + a[y0][:, x1] * fx
    b = a[y1][:, x0] * (1 - fx) + a[y1][:, x1] * fx
    return t * (1 - fy) + b * fy

def aces(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)

def srgb(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.clip(x, 0, None), 1 / 2.4) - 0.055)

def save_png(path, rgb8):
    H, W, _ = rgb8.shape
    im = bpy.data.images.new('out', W, H, alpha=True)
    px = np.ones((H, W, 4), np.float32)
    px[..., :3] = rgb8[::-1] / 255.0
    im.pixels.foreach_set(px.ravel())
    im.filepath_raw = path; im.file_format = 'PNG'
    im.save()

def save_dds(path, rgb8):
    """uncompressed 32-bit A8R8G8B8 DDS, no mipmaps (UI textures don't need them)"""
    import struct
    H, W, _ = rgb8.shape
    hdr = struct.pack('<4sIIIIIII44x', b'DDS ', 124, 0x1 | 0x2 | 0x4 | 0x8 | 0x1000, H, W, W * 4, 0, 1)
    pf = struct.pack('<IIIIIIII', 32, 0x41, 0, 32, 0x00FF0000, 0x0000FF00, 0x000000FF, 0xFF000000)
    caps = struct.pack('<IIII4x', 0x1000, 0, 0, 0)
    bgra = np.empty((H, W, 4), np.uint8)
    bgra[..., 0] = rgb8[..., 2]; bgra[..., 1] = rgb8[..., 1]; bgra[..., 2] = rgb8[..., 0]; bgra[..., 3] = 255
    with open(path, 'wb') as f:
        f.write(hdr + pf + caps)
        f.write(bgra.tobytes())
    assert os.path.getsize(path) == 128 + W * H * 4
