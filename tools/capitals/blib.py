"""Procedural modelling helpers for the capital models (run inside Blender).

Geometry is accumulated in a Builder (plain Python lists) and turned into one Blender
mesh at the end, which keeps scripts fast and deterministic. Units are Civ 5 model
units: the stock palace is about 45 x 45 units with Z up; the camera looks from -Y.
"""
import math
import random

import bpy
from mathutils import Matrix, Vector

# --------------------------------------------------------------------------- materials
# name -> dict(color, color2=None, noise=scale, rough, courses=spacing)
PALETTE = {}


def material(name, color, color2=None, noise=0.0, courses=0.0, course_dark=0.75, emission=0.0, detail=4.0,
             zramp=None, slope_color=None, slope_start=0.55, ao=True, spec=None, refl=None):
    """spec: specular strength 0..1 (SREF rgb = colour * spec, default 0.3); refl: SREF alpha 0..255
    (environment reflection, default 6). Gold / ithildin use high values to shine."""
    """zramp: [(z, color), ...] colours by height (terrain); slope_color tints steep faces (rock)."""
    PALETTE[name] = dict(color=color, color2=color2, noise=noise, courses=courses,
                         course_dark=course_dark, emission=emission, detail=detail, zramp=zramp,
                         slope_color=slope_color, slope_start=slope_start, ao=ao, spec=spec, refl=refl)
    return name


def hexcol(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def _srgb_to_lin(c):
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def make_blender_material(name):
    p = PALETTE[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.8
    c1 = _srgb_to_lin(p['color']) + (1.0,)
    col_socket = None
    if p['color2'] is not None and p['noise'] > 0:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = p['noise']
        nz.inputs['Detail'].default_value = p['detail']
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = 0.3
        ramp.color_ramp.elements[1].position = 0.7
        ramp.color_ramp.elements[0].color = c1
        ramp.color_ramp.elements[1].color = _srgb_to_lin(p['color2']) + (1.0,)
        nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
        col_socket = ramp.outputs['Color']
    if p['zramp']:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
        nz = nt.nodes.new('ShaderNodeTexNoise')
        nz.inputs['Scale'].default_value = 0.15
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
        jit = nt.nodes.new('ShaderNodeMath'); jit.operation = 'MULTIPLY_ADD'
        nt.links.new(nz.outputs['Fac'], jit.inputs[0])
        jit.inputs[1].default_value = 8.0
        nt.links.new(sep.outputs['Z'], jit.inputs[2])
        zs = [z for z, _ in p['zramp']]
        lo, hi = min(zs) - 1, max(zs) + 1
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['From Min'].default_value = lo
        mr.inputs['From Max'].default_value = hi
        nt.links.new(jit.outputs[0], mr.inputs['Value'])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        els = ramp.color_ramp.elements
        for i, (z, c) in enumerate(p['zramp']):
            e = els[i] if i < 2 else els.new(0)
            e.position = (z - lo) / (hi - lo)
            e.color = _srgb_to_lin(c) + (1.0,)
        nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])
        col_socket = ramp.outputs['Color']
        # fine colour noise on top
        nz2 = nt.nodes.new('ShaderNodeTexNoise')
        nz2.inputs['Scale'].default_value = 1.2
        nt.links.new(tc.outputs['Object'], nz2.inputs['Vector'])
        ov = nt.nodes.new('ShaderNodeMix'); ov.data_type = 'RGBA'; ov.blend_type = 'OVERLAY'
        ov.inputs['Factor'].default_value = 0.35
        nt.links.new(col_socket, ov.inputs['A'])
        nt.links.new(nz2.outputs['Color'], ov.inputs['B'])
        col_socket = ov.outputs['Result']
    if p['slope_color'] is not None:
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        sep2 = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(geo.outputs['Normal'], sep2.inputs['Vector'])
        mr2 = nt.nodes.new('ShaderNodeMapRange')
        mr2.inputs['From Min'].default_value = p['slope_start'] + 0.15
        mr2.inputs['From Max'].default_value = p['slope_start']
        nt.links.new(sep2.outputs['Z'], mr2.inputs['Value'])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'
        nt.links.new(mr2.outputs['Result'], mx.inputs['Factor'])
        if col_socket is not None:
            nt.links.new(col_socket, mx.inputs['A'])
        else:
            mx.inputs['A'].default_value = c1
        mx.inputs['B'].default_value = _srgb_to_lin(p['slope_color']) + (1.0,)
        col_socket = mx.outputs['Result']
    if p['courses'] > 0:
        # horizontal masonry courses: thin darker lines every `courses` units in Z
        tc = nt.nodes.new('ShaderNodeTexCoord')
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Object'], sep.inputs['Vector'])
        mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'DIVIDE'
        mul.inputs[1].default_value = p['courses']
        nt.links.new(sep.outputs['Z'], mul.inputs[0])
        fr = nt.nodes.new('ShaderNodeMath'); fr.operation = 'FRACT'
        nt.links.new(mul.outputs[0], fr.inputs[0])
        st = nt.nodes.new('ShaderNodeMath'); st.operation = 'LESS_THAN'
        st.inputs[1].default_value = 0.12
        nt.links.new(fr.outputs[0], st.inputs[0])
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        nt.links.new(st.outputs[0], mix.inputs['Factor'])
        if col_socket is not None:
            nt.links.new(col_socket, mix.inputs['A'])
        else:
            mix.inputs['A'].default_value = c1
        d = p['course_dark']
        base = p['color']
        mix.inputs['B'].default_value = _srgb_to_lin(tuple(x * d for x in base)) + (1.0,)
        col_socket = mix.outputs['Result']
    if col_socket is not None:
        nt.links.new(col_socket, bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = c1
    return m


# --------------------------------------------------------------------------- builder
class Builder:
    def __init__(self, seed=1):
        self.verts = []
        self.faces = []
        self.fmat = []
        self.fsmooth = []
        self.mat_names = []
        self.rng = random.Random(seed)
        self.fx = []   # (bone name, (x, y, z), visual effect name)

    def _mi(self, name):
        if name not in self.mat_names:
            assert name in PALETTE, name
            self.mat_names.append(name)
        return self.mat_names.index(name)

    def add(self, verts, faces, mat, smooth=False, M=None):
        base = len(self.verts)
        if M is not None:
            verts = [tuple(M @ Vector(v)) for v in verts]
        self.verts.extend(tuple(v) for v in verts)
        mi = self._mi(mat)
        for f in faces:
            self.faces.append(tuple(base + i for i in f))
            self.fmat.append(mi)
            self.fsmooth.append(smooth)

    def tri_count(self):
        return sum(len(f) - 2 for f in self.faces)

    def to_object(self, name):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.verts, [], self.faces)
        me.validate(clean_customdata=False)
        for n in self.mat_names:
            me.materials.append(make_blender_material(n))
        me.polygons.foreach_set('material_index', self.fmat[:len(me.polygons)])
        me.polygons.foreach_set('use_smooth', self.fsmooth[:len(me.polygons)])
        me.update()
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob


def T(x=0.0, y=0.0, z=0.0, rz=0.0, s=1.0, rx=0.0, ry=0.0):
    """Transform: scale, then rotate X, Y, Z (degrees), then translate."""
    S = Matrix.Diagonal((s, s, s, 1)) if not isinstance(s, (tuple, list)) else Matrix.Diagonal((s[0], s[1], s[2], 1))
    R = Matrix.Rotation(math.radians(rz), 4, 'Z') @ Matrix.Rotation(math.radians(ry), 4, 'Y') @ Matrix.Rotation(math.radians(rx), 4, 'X')
    return Matrix.Translation((x, y, z)) @ R @ S


# --------------------------------------------------------------------------- primitives
def box(b, mat, x, y, z, sx, sy, sz, rz=0.0, M=None, top=True, bottom=None):
    """Axis box centred on (x, y), from z to z+sz, rotated rz degrees around its centre.
    The bottom face is skipped for upright boxes (it sits on something) but kept when M tilts the box."""
    if bottom is None:
        bottom = M is not None
    hx, hy = sx / 2, sy / 2
    v = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0),
         (-hx, -hy, sz), (hx, -hy, sz), (hx, hy, sz), (-hx, hy, sz)]
    f = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    if top:
        f.append((4, 5, 6, 7))
    if bottom:
        f.append((3, 2, 1, 0))
    m = T(x, y, z, rz)
    if M is not None:
        m = M @ m
    b.add(v, f, mat, M=m)


# Detail level for curved primitives (lathe/cyl/cone/sphere/blob/dome segments and rings, ring
# segments, crenel spacing). pipeline.build_one lowers it when a model is over the triangle
# budget: every piece stays clean, closed geometry (no mesh decimation, which flips faces).
SEG = [1.0]


def detail(n, lo=6):
    """Segment count n at the current detail level (small counts are left alone)."""
    return n if n <= lo or SEG[0] >= 1.0 else max(lo, int(round(n * SEG[0])))


def lathe(b, mat, profile, n=16, x=0.0, y=0.0, z=0.0, smooth=True, M=None, a0=0.0, a1=360.0, jitter=0.0):
    """Revolve a profile [(r, z), ...] (bottom to top) around the Z axis."""
    n = detail(n)
    full = abs((a1 - a0) - 360.0) < 1e-6
    if full and len(profile) >= 2:
        # close open ends (a tube's open end shows its inside, which the game culls: holes)
        profile = list(profile)
        if profile[0][0] > 1e-6 and M is not None:     # upright pieces stand on something
            profile.insert(0, (0.0, profile[0][1]))
        if profile[-1][0] > 1e-6:
            profile.append((0.0, profile[-1][1]))
    segs = n if full else max(1, n)
    cols = segs if full else segs + 1
    v = []
    idx = []
    for (r, hz) in profile:
        row = []
        if r <= 1e-6:
            v.append((0.0, 0.0, hz))
            row = [len(v) - 1] * cols
        else:
            for k in range(cols):
                a = math.radians(a0 + (a1 - a0) * k / segs)
                rr = r * (1 + (b.rng.uniform(-jitter, jitter) if jitter else 0))
                v.append((rr * math.cos(a), rr * math.sin(a), hz))
                row.append(len(v) - 1)
        idx.append(row)
    f = []
    for i in range(len(profile) - 1):
        for k in range(segs):
            k2 = (k + 1) % cols if full else k + 1
            a, bb, c, d = idx[i][k], idx[i][k2], idx[i + 1][k2], idx[i + 1][k]
            quad = [a, bb, c, d]
            # collapse degenerate (apex) quads into triangles
            uq = []
            for q in quad:
                if q not in uq:
                    uq.append(q)
            if len(uq) >= 3:
                f.append(tuple(uq))
    m = T(x, y, z)
    if M is not None:
        m = M @ m
    b.add(v, f, mat, smooth=smooth, M=m)


def cyl(b, mat, x, y, z, r, h, n=16, r2=None, top=True, smooth=False, M=None):
    top = True   # open tops show back faces, which the game culls (see-through holes)
    r2 = r if r2 is None else r2
    prof = [(r, 0), (r2, h)]
    if top:
        prof.append((0, h))
    lathe(b, mat, prof, n, x, y, z, smooth=smooth, M=M)
    if top and smooth:
        pass


def cone(b, mat, x, y, z, r, h, n=12, M=None, smooth=False):
    lathe(b, mat, [(r, 0), (0, h)], n, x, y, z, smooth=smooth, M=M)


def sphere(b, mat, x, y, z, r, n=12, rings=8, M=None, squash=1.0):
    rings = detail(rings, 3)
    prof = []
    for i in range(rings + 1):
        t = math.pi * i / rings - math.pi / 2
        prof.append((r * math.cos(t), r * math.sin(t) * squash))
    prof[0] = (0, prof[0][1])
    prof[-1] = (0, prof[-1][1])
    lathe(b, mat, prof, n, x, y, z, smooth=True, M=M)


def dome(b, mat, x, y, z, r, n=16, rings=5, h=None, M=None):
    h = r if h is None else h
    rings = detail(rings, 3)
    prof = [(r * math.cos(math.pi / 2 * i / rings), h * math.sin(math.pi / 2 * i / rings)) for i in range(rings + 1)]
    prof[-1] = (0, h)
    lathe(b, mat, prof, n, x, y, z, smooth=True, M=M)


def ring(b, mat, r_in, r_out, z, h, a0=0.0, a1=360.0, n=48, x=0.0, y=0.0, M=None, top=True, inner=True):
    """Annular wall segment between angles a0..a1 (degrees)."""
    full = abs((a1 - a0) - 360.0) < 1e-6
    segs = max(2, int(detail(n) * (a1 - a0) / 360.0))
    cols = segs if full else segs + 1
    v = []
    for k in range(cols):
        a = math.radians(a0 + (a1 - a0) * k / segs)
        c, s = math.cos(a), math.sin(a)
        v += [(r_in * c, r_in * s, 0), (r_out * c, r_out * s, 0), (r_out * c, r_out * s, h), (r_in * c, r_in * s, h)]
    f = []
    for k in range(segs):
        k2 = (k + 1) % cols
        a, c = 4 * k, 4 * k2
        f.append((a + 1, c + 1, c + 2, a + 2))  # outer
        if inner:
            f.append((c + 0, a + 0, a + 3, c + 3))  # inner
        if top:
            f.append((a + 2, c + 2, c + 3, a + 3))
    if not full:
        f.append((0, 1, 2, 3))
        e = 4 * (cols - 1)
        f.append((e + 3, e + 2, e + 1, e))
    m = T(x, y, z)
    if M is not None:
        m = M @ m
    b.add(v, f, mat, M=m)


def crenels(b, mat, r, z, a0, a1, size=0.6, h=0.6, step=1.6, x=0.0, y=0.0, depth=None):
    depth = size if depth is None else depth
    length = math.radians(a1 - a0) * r
    k = max(1, int(length / (step / min(1.0, max(0.6, SEG[0])))))
    for i in range(k + 1):
        a = a0 + (a1 - a0) * i / k
        ar = math.radians(a)
        box(b, mat, x + r * math.cos(ar), y + r * math.sin(ar), z, depth, size, h, rz=a)


def gable(b, mat, x, y, z, length, width, h, rz=0.0, overhang=0.3, M=None, ends=True):
    """Pitched roof prism: ridge along local X."""
    L, W = length / 2 + overhang, width / 2 + overhang
    v = [(-L, -W, 0), (L, -W, 0), (L, 0, h), (-L, 0, h), (-L, W, 0), (L, W, 0)]
    f = [(0, 1, 2, 3), (5, 4, 3, 2)]
    if ends:
        f += [(1, 5, 2), (4, 0, 3)]
    m = T(x, y, z, rz)
    if M is not None:
        m = M @ m
    b.add(v, f, mat, M=m)


def hipped(b, mat, x, y, z, length, width, h, rz=0.0, overhang=0.3, ridge=0.5):
    L, W = length / 2 + overhang, width / 2 + overhang
    r = max(0.0, L - W) * ridge + 0.01
    v = [(-L, -W, 0), (L, -W, 0), (L, W, 0), (-L, W, 0), (-r, 0, h), (r, 0, h)]
    f = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4), (3, 2, 1, 0)]
    b.add(v, f, mat, M=T(x, y, z, rz))


def pyramid(b, mat, x, y, z, sx, sy, h, rz=0.0):
    hx, hy = sx / 2, sy / 2
    v = [(-hx, -hy, 0), (hx, -hy, 0), (hx, hy, 0), (-hx, hy, 0), (0, 0, h)]
    f = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
    b.add(v, f, mat, M=T(x, y, z, rz))


def prism(b, mat, pts, z, h, top=True, M=None, smooth=False):
    """Extrude a CCW polygon [(x, y), ...] from z to z+h."""
    n = len(pts)
    v = [(p[0], p[1], z) for p in pts] + [(p[0], p[1], z + h) for p in pts]
    f = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    if top:
        f.append(tuple(range(n, 2 * n)))
    b.add(v, f, mat, M=M, smooth=smooth)


def terrain(b, height, x0, x1, y0, y1, nx, ny, matfn, keep=None, smooth=True, skirt=-4.0):
    """Height field z = height(x, y). matfn(x, y, z, slope) -> material name per quad.
    keep(x, y) -> bool drops quads outside an irregular footprint. Border edges get a skirt down to `skirt`."""
    hs = [[height(x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny) for i in range(nx + 1)] for j in range(ny + 1)]
    vid = {}
    verts = []

    def V(i, j, z=None):
        key = (i, j, z is not None)
        if key not in vid:
            x = x0 + (x1 - x0) * i / nx
            y = y0 + (y1 - y0) * j / ny
            verts.append((x, y, hs[j][i] if z is None else z))
            vid[key] = len(verts) - 1
        return vid[key]

    quads = {}
    for j in range(ny):
        for i in range(nx):
            cx = x0 + (x1 - x0) * (i + 0.5) / nx
            cy = y0 + (y1 - y0) * (j + 0.5) / ny
            if keep is not None and not keep(cx, cy):
                continue
            quads[(i, j)] = True
    groups = {}
    dx, dy = (x1 - x0) / nx, (y1 - y0) / ny
    for (i, j) in quads:
        z00, z10, z11, z01 = hs[j][i], hs[j][i + 1], hs[j + 1][i + 1], hs[j + 1][i]
        slope = math.hypot((z10 + z11 - z00 - z01) / (2 * dx), (z01 + z11 - z00 - z10) / (2 * dy))
        cz = (z00 + z10 + z11 + z01) / 4
        cx = x0 + dx * (i + 0.5)
        cy = y0 + dy * (j + 0.5)
        m = matfn(cx, cy, cz, slope)
        groups.setdefault(m, []).append((V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1)))
    # skirt along open edges
    sk = []
    for (i, j) in quads:
        for (di, dj, a, c) in ((0, -1, (i, j), (i + 1, j)), (1, 0, (i + 1, j), (i + 1, j + 1)),
                               (0, 1, (i + 1, j + 1), (i, j + 1)), (-1, 0, (i, j + 1), (i, j))):
            if (i + di, j + dj) not in quads:
                # wound so the skirt faces OUT of the height field (2026-11-24: it faced inwards = back faces)
                sk.append((V(*c), V(*a), V(a[0], a[1], skirt), V(c[0], c[1], skirt)))
    base = len(b.verts)
    b.verts.extend(verts)
    for m, fs in groups.items():
        mi = b._mi(m)
        for f in fs:
            b.faces.append(tuple(base + k for k in f))
            b.fmat.append(mi)
            b.fsmooth.append(smooth)
    if sk:
        mi = b._mi(list(groups.keys())[0]) if groups else 0
        sm = PALETTE and next(iter(groups))
        for f in sk:
            b.faces.append(tuple(base + k for k in f))
            b.fmat.append(b._mi(SKIRT_MAT[0]) if SKIRT_MAT[0] else mi)
            b.fsmooth.append(False)


SKIRT_MAT = [None]


def blob(b, mat, x, y, z, r, n=8, rings=5, squash=0.8, jitter=0.18, M=None):
    """Irregular rounded blob (tree crowns, bushes, rocks)."""
    rings = detail(rings, 3)
    prof = []
    for i in range(rings + 1):
        t = math.pi * i / rings - math.pi / 2
        prof.append((r * math.cos(t), r * math.sin(t) * squash))
    prof[0] = (0, prof[0][1])
    prof[-1] = (0, prof[-1][1])
    lathe(b, mat, prof, n, x, y, z + r * squash, smooth=True, M=M, jitter=jitter)


def tree(b, x, y, z, h=4.0, r=1.6, trunk='bark', leaves='leaves', crowns=3):
    cyl(b, trunk, x, y, z, 0.18 * h / 4 + 0.08, h * 0.55, n=6, r2=0.1, top=False)
    for k in range(crowns):
        ox = b.rng.uniform(-0.35, 0.35) * r
        oy = b.rng.uniform(-0.35, 0.35) * r
        rr = r * b.rng.uniform(0.7, 1.0)
        blob(b, leaves, x + ox, y + oy, z + h * 0.45 + k * 0.15 * h, rr, n=7, rings=4)


def conifer(b, x, y, z, h=5.0, r=1.2, trunk='bark', leaves='pine', tiers=3):
    cyl(b, trunk, x, y, z, 0.15, h * 0.3, n=5, top=False)
    for k in range(tiers):
        t = k / tiers
        cone(b, leaves, x, y, z + h * (0.2 + 0.25 * k), r * (1 - 0.25 * k), h * (0.8 - 0.2 * k) * 0.6, n=7)


def window_row(b, mat, x0, y0, x1, y1, z, count, w=0.4, h=0.7, out=0.06):
    """Dark window slabs along a wall from (x0,y0) to (x1,y1); normal faces to the right of travel."""
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    nx, ny = math.sin(math.radians(ang)), -math.cos(math.radians(ang))
    # each window is one pane (2 triangles) just in front of the wall, facing outwards; a box
    # cost 10 triangles of which the game only ever shows the front
    dx, dy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    off = out + 0.04
    v, f = [], []
    for i in range(count):
        t = (i + 0.5) / count
        cx, cy = x0 + (x1 - x0) * t + nx * off, y0 + (y1 - y0) * t + ny * off
        k = len(v)
        v += [(cx - dx * w / 2, cy - dy * w / 2, z), (cx + dx * w / 2, cy + dy * w / 2, z),
              (cx + dx * w / 2, cy + dy * w / 2, z + h), (cx - dx * w / 2, cy - dy * w / 2, z + h)]
        f.append((k, k + 1, k + 2, k + 3))       # (dx, dy) x up = the outward normal
    b.add(v, f, mat)


def banner(b, pole, cloth, x, y, z, h=3.0, w=0.8, ch=1.2, rz=0.0):
    cyl(b, pole, x, y, z, 0.06, h, n=4, top=False)
    box(b, cloth, x + 0.06 + w / 2 * math.cos(math.radians(rz)), y + w / 2 * math.sin(math.radians(rz)),
        z + h - ch - 0.1, w, 0.04, ch, rz=rz)


def strut(b, mat, p0, p1, r0, r1=None, n=6, smooth=True):
    """Tapered cylinder from point p0 to p1 (r1=0 makes a spike)."""
    r1 = r0 if r1 is None else r1
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    L = d.length
    if L < 1e-6:
        return
    q = d.normalized().to_track_quat('Z', 'Y')
    M = Matrix.Translation(p0) @ q.to_matrix().to_4x4()
    # closed at both ends: an open start shows its inside (culled back faces) from many angles
    prof = [(0, 0), (r0, 0), (r1, L), (0, L)] if r1 > 0 else [(0, 0), (r0, 0), (0, L)]
    lathe(b, mat, prof, n, M=M, smooth=smooth)


def curve(b, mat, pts, r0, r1, n=6, smooth=True):
    """Chain of struts along a polyline, radius tapering r0 -> r1."""
    k = len(pts) - 1
    for i in range(k):
        ra = r0 + (r1 - r0) * i / k
        rb = r0 + (r1 - r0) * (i + 1) / k
        strut(b, mat, pts[i], pts[i + 1], ra, rb if rb > 0 else 0, n=n, smooth=smooth)


# The city hexagon in model units (the landmarks are drawn at fScale 0.77; the game's hexagon
# is about 48 world units across its flat sides). Civ 5 hexes are "pointy-top": flat sides
# face east and west (+-X), corners point north and south (+-Y). Model origin = tile centre.
HEX_IN = 31.2                       # centre -> middle of a flat side
TERRAIN_NR, TERRAIN_NA = 36, 120    # max rings / spokes of a terrain_polar base (x SEG)
HEX_OUT = HEX_IN / math.cos(math.pi / 6)   # centre -> corner (36.0)


# Design scale of the model being built (its module's FILL, default 1): the pipeline scales the
# finished model by FILL, so a design laid out small fills the tile. The hexagon helpers and the
# base answer in design units (the tile divided by FILL).
FILL = [1.0]


def hex_radius(a):
    """Distance from the tile centre to the hexagon's edge in direction a (radians), in design
    units (see FILL)."""
    d = (a + math.pi / 6) % (math.pi / 3) - math.pi / 6
    return HEX_IN / math.cos(d) / FILL[0]


def in_hex(x, y, margin=0.0):
    """True when (x, y) lies inside the city hexagon shrunk by `margin`."""
    r = math.hypot(x, y)
    return r == 0 or r <= hex_radius(math.atan2(y, x)) - margin


def terrain_polar(b, height, matfn, R=30.0, sy=1.0, cx=0.0, cy=0.0, nr=22, na=72, edge=-0.4, smooth=True, skirt=-3.0):
    """Height-field over the whole city hexagon (see HEX_IN) whose rim sinks to `edge` so it
    blends into the game's own terrain. matfn(x, y, z, slope) -> material per quad.
    R, sy, cx, cy are kept for the models' signatures; the outline is always the tile's
    hexagon around the origin, so every landmark fills its tile exactly."""
    rows = []
    verts = []
    # resolution cap (stock-wonder triangle budget, see pipeline.MAX_TRIS). Corners (every 60 degrees from 30) are ring vertices.
    nr = min(nr, int(TERRAIN_NR * min(1.0, SEG[0] + 0.2)))
    na = max(12, (min(na, int(TERRAIN_NA * min(1.0, SEG[0] + 0.2))) + 11) // 12 * 12)
    cx, cy = 0.0, 0.0
    for i in range(nr + 1):
        t = i / nr
        row = []
        if i == 0:
            verts.append((cx, cy, height(cx, cy)))
            row = [len(verts) - 1] * na
        else:
            for j in range(na):
                a = 2 * math.pi * j / na
                r = hex_radius(a) * (t ** 0.85)
                x, y = cx + r * math.cos(a), cy + r * math.sin(a)
                z = height(x, y)
                # fade into the surrounding ground near the tile edge: over ~3.7 units for low
                # ground, wider (up to 10) for tall terrain, so cliffs and mountain backdrops get
                # flanks instead of ending in sheer walls on the hexagon's border
                dist = hex_radius(a) - r
                w = min(10.0, max(0.12 * HEX_IN, 0.35 * (z - edge) * FILL[0])) / FILL[0]
                f = min(1.0, max(0.0, dist / w))
                z = edge + (z - edge) * (f * f * (3 - 2 * f))
                verts.append((x, y, z))
                row.append(len(verts) - 1)
        rows.append(row)
    base = len(b.verts)
    b.verts.extend(verts)
    for i in range(nr):
        for j in range(na):
            j2 = (j + 1) % na
            if i == 0:
                f = (rows[0][0], rows[1][j], rows[1][j2])
            else:
                f = (rows[i][j], rows[i + 1][j], rows[i + 1][j2], rows[i][j2])
            ps = [verts[k] for k in f]
            cxx = sum(p[0] for p in ps) / len(ps)
            cyy = sum(p[1] for p in ps) / len(ps)
            czz = sum(p[2] for p in ps) / len(ps)
            # slope from the polygon normal
            ax, ay, az = ps[1][0] - ps[0][0], ps[1][1] - ps[0][1], ps[1][2] - ps[0][2]
            bx, by, bz = ps[-1][0] - ps[0][0], ps[-1][1] - ps[0][1], ps[-1][2] - ps[0][2]
            nx, ny, nz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
            ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
            slope = math.sqrt(nx * nx + ny * ny) / (abs(nz) + 1e-6)
            m = matfn(cxx, cyy, czz, slope)
            # orientation: outward rings -> make faces point up
            if nz < 0:
                f = tuple(reversed(f))
            b.faces.append(tuple(base + k for k in f))
            b.fmat.append(b._mi(m))
            b.fsmooth.append(smooth)
    # skirt under the rim
    last = rows[-1]
    sk = []
    for j in range(na):
        j2 = (j + 1) % na
        p, q = verts[last[j]], verts[last[j2]]
        b.verts.extend([(q[0], q[1], skirt), (p[0], p[1], skirt)])
        n = len(b.verts)
        b.faces.append((base + last[j2], base + last[j], n - 1, n - 2))
        b.fmat.append(b._mi(SKIRT_MAT[0] or m))
        b.fsmooth.append(False)


def near_path(x, y, path, width):
    """True if (x, y) is within width of the polyline path [(x, y), ...]."""
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy or 1e-9
        t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / L2))
        if math.hypot(x - (x0 + t * dx), y - (y0 + t * dy)) < width:
            return True
    return False
