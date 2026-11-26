"""Animate a landmark's flames FROM THE WRITTEN GAME FILES and render frames (+ a GIF): the Balrog, 2026-11-26.

Run:  blender -b --factory-startup -P tools/landmarks/preview_flames.py -- MEC_LM_Balrog [--frames 12] [--fps 8]
                [--view game|head|both] [--scale 0.25] [--size 800x600]
Output: build/landmarks/preview/<model>_flames_<view>.png (contact sheet) and build/landmarks/gif/<model>_flames_<view>.gif

Reads <model>.gr2 + <model>_Idle.gr2 (every model posed like the engine: preview_lean.read_meshes / pose), the
trigger file (bone -> effect), each model effect's .gr2 and IdleA (card quads, their D3K8uC8u positions and
D4nK16uC15u rotations decoded as stored, puffs.evaluate / granim.sample_quat_curve), places every card on its bone
(the bone's world matrix at time t, so the head's flames turn with the head) in file units x the improvement Scale,
and draws them additively (colour x alpha added). Stock particle fires are drawn as small emissive markers only.
"""
import math
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'capitals')]
sys.path.append(os.path.join(HERE, '..', '..', 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2],
                             'site-packages'))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Quaternion, Vector  # noqa: E402

import dds  # noqa: E402
import gr2  # noqa: E402
import granim  # noqa: E402
import puffs  # noqa: E402
from landmarks import EFFECTS, OUT, PREVIEW  # noqa: E402
from preview_lean import read_meshes  # noqa: E402
from render_gif import Animation  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))


def bone_worlds(bones, anim, model, t):
    world = {}
    for name, parent, rest, _inv in bones:
        loc = anim.local(model, name, t) if anim else None
        loc = rest if loc is None else loc
        world[name] = (world[bones[parent][0]] @ loc) if parent >= 0 else loc
    return world


def posed(bones, mesh, world):
    inv = {n: i for n, _, _, i in bones}
    mats = [world[b] @ inv[b] for b in mesh['binds']]
    P = np.array(mesh['pos'], np.float64)
    if len(mats) == 1 or all(len(ws) == 1 and ws[0][0] == 0 for ws in mesh['w']):
        M = np.array(mats[0])
        return P @ M[:3, :3].T + M[:3, 3]
    out = np.zeros_like(P)
    for i, (p, ws) in enumerate(zip(mesh['pos'], mesh['w'])):
        acc = Vector((0.0, 0.0, 0.0))
        for bi, w in ws:
            acc += w * (mats[bi] @ Vector(p))
        out[i] = acc
    return out


class Effect:
    """A model effect: its card quads (per card bone), texture, and decoded curves."""

    def __init__(self, fxs):
        txt = open(os.path.join(OUT, fxs)).read()
        mesh = re.search(r'Mesh file="([^"]+)"', txt).group(1)
        anim = re.search(r'Animation file="([^"]+)"', txt).group(1)
        tex = [t for t in re.findall(r'Texture file="([^"]+)"', txt) if not t.startswith('FX_')][0]
        r = gr2.read(os.path.join(OUT, mesh)).root()
        skel = [b['Name'] for b in r['Skeletons'][0]['Bones']]
        from render_gif import gmat
        self.inv = {b['Name']: gmat(b['InverseWorldTransform']) for b in r['Skeletons'][0]['Bones']}
        me = r['Meshes'][0]
        v = me['PrimaryVertexData']['Vertices'].value
        binds = [b['BoneName'] for b in me['BoneBindings']]
        self.quads = {}
        if isinstance(v, (bytes, bytearray)):
            recs = [struct.unpack_from('<3f4B4B12f', v, i * 64) for i in range(len(v) // 64)]
            recs = [(r_[0:3], r_[7], r_[20:22]) for r_ in recs]
        else:
            recs = [(tuple(x['Position']), x['BoneIndices'][0], tuple(x['TextureCoordinates0'][:2])) for x in v]
        for pos, bi, uv in recs:
            self.quads.setdefault(binds[bi], []).append((pos, uv))
        a = gr2.read(os.path.join(OUT, anim)).root()
        self.T = a['Animations'][0]['Duration']
        self.tracks = {t['Name']: t for t in a['TrackGroups'][0]['TransformTracks']}
        self.img = dds.decode_dxt3(os.path.join(OUT, tex))
        self.name = fxs

    def card_matrix(self, bn, t):
        tr = self.tracks.get(bn)
        if tr is None:
            return Matrix.Identity(4)
        t = t % self.T
        pc = tr['PositionCurve']['CurveData']
        oc = tr['OrientationCurve']['CurveData']
        hdr = list(pc.value.keys())[0] if isinstance(pc.value, dict) else ''
        if 'D3K8uC8u' in hdr:
            p = puffs.evaluate(pc.value, self.T, t)
        elif 'D3Constant32f' in hdr:
            p = pc.value['Controls']
        else:
            p = (0.0, 0.0, 0.0)
        ohdr = list(oc.value.keys())[0]
        if 'D4nK16uC15u' in ohdr:
            q = granim.sample_quat_curve(oc.value, t)
            Q = Quaternion((q[3], q[0], q[1], q[2]))
            Q.normalize()
            R = Q.to_matrix().to_4x4()
        else:
            R = Matrix.Identity(4)
        return Matrix.Translation(p) @ R @ self.inv.get(bn, Matrix.Identity(4))


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []

    def opt(k, d):
        return argv[argv.index(k) + 1] if k in argv else d
    vals = {opt(k, None) for k in ('--frames', '--fps', '--view', '--scale', '--size')}
    name = [a for a in argv if not a.startswith('--') and a not in vals][0]
    scale = float(opt('--scale', 0.25))
    nfr = int(opt('--frames', 12))
    fps = float(opt('--fps', 8))
    W, H = (int(x) for x in opt('--size', '800x600').split('x'))
    anim = Animation(os.path.join(OUT, name + '_Idle.gr2'))
    meshes = read_meshes(os.path.join(OUT, name + '.gr2'))
    # effects: trigger file -> (bone, VisEffect) -> model effect file
    trig = open(os.path.join(OUT, 'FX_Triggers_%s.ftsxml' % name)).read()
    pairs = re.findall(r'event="([^"]+)" bone="([^"]+)"', trig)
    by_name = {e['name']: e for e in EFFECTS.values()}
    effects, particles = [], []
    cache = {}
    for ev, bone in pairs:
        e = by_name[ev]
        if e.get('file'):
            if e['file'] not in cache:
                cache[e['file']] = Effect(e['file'])
            effects.append((bone, cache[e['file']]))
        else:
            particles.append((bone, e))
    skinned = [(m, b, me) for m, b, me in meshes if len(b) > 1]
    eye_model, eye_bones = skinned[0][0], skinned[0][1]
    print('flames preview: %d meshes, %d model effects (%s), %d particle fires' % (
        len(meshes), len(effects), sorted({e.name for _, e in effects}), len(particles)))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    objs = []
    for model, bones, me in meshes:
        bm = bpy.data.meshes.new(me['name'])
        bm.from_pydata([(0.0, 0.0, 0.0)] * len(me['pos']), [], me['tris'])
        bm.update()
        uvl = bm.uv_layers.new()
        for poly in bm.polygons:
            for li in poly.loop_indices:
                u, v = me['uv'][bm.loops[li].vertex_index]
                uvl.data[li].uv = (u, 1.0 - v)
        bm.polygons.foreach_set('use_smooth', [True] * len(bm.polygons))
        img = dds.decode_dxt3(os.path.join(OUT, me['tex']))
        im = bpy.data.images.new(me['name'], img.shape[1], img.shape[0])
        im.pixels.foreach_set((np.flipud(img).astype(np.float32) / 255.0).ravel())
        mat = bpy.data.materials.new(me['name'])
        mat.use_nodes = True
        tn = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tn.image = im
        mat.node_tree.links.new(tn.outputs['Color'], mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = 0.85
        bm.materials.append(mat)
        ob = bpy.data.objects.new(me['name'], bm)
        sc.collection.objects.link(ob)
        objs.append((ob, model, bones, me))
    # the cards: one object per effect instance, rebuilt per frame
    add_mats = {}

    def additive(eff):
        if eff.name in add_mats:
            return add_mats[eff.name]
        img = eff.img
        im = bpy.data.images.new('fx_' + eff.name, img.shape[1], img.shape[0], alpha=True)
        im.pixels.foreach_set((np.flipud(img).astype(np.float32) / 255.0).ravel())
        m = bpy.data.materials.new('fx_' + eff.name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.remove(nt.nodes['Principled BSDF'])
        tn = nt.nodes.new('ShaderNodeTexImage')
        tn.image = im
        mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
        mul.inputs['Factor'].default_value = 1.0
        nt.links.new(tn.outputs['Color'], mul.inputs['A'])
        nt.links.new(tn.outputs['Alpha'], mul.inputs['B'])
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Strength'].default_value = 1.6
        nt.links.new(mul.outputs['Result'], em.inputs['Color'])
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        ad = nt.nodes.new('ShaderNodeAddShader')
        nt.links.new(tr.outputs[0], ad.inputs[0])
        nt.links.new(em.outputs[0], ad.inputs[1])
        nt.links.new(ad.outputs[0], nt.nodes['Material Output'].inputs[0])
        add_mats[eff.name] = m
        return m
    fx_objs = []
    for bone, eff in effects:
        bm = bpy.data.meshes.new('fx')
        nq = sum(len(q) // 4 for q in eff.quads.values())
        bm.from_pydata([(0.0, 0.0, 0.0)] * (nq * 4), [], [(4 * i, 4 * i + 1, 4 * i + 2, 4 * i + 3) for i in range(nq)])
        bm.update()
        uvl = bm.uv_layers.new()
        uvs = [uv for bn in sorted(eff.quads) for (_, uv) in eff.quads[bn]]
        for poly in bm.polygons:
            for li in poly.loop_indices:
                u, v = uvs[bm.loops[li].vertex_index]
                uvl.data[li].uv = (u, 1.0 - v)
        bm.materials.append(additive(eff))
        ob = bpy.data.objects.new('fx', bm)
        ob.visible_shadow = False
        sc.collection.objects.link(ob)
        fx_objs.append((ob, bone, eff))
    # particle fire markers
    pmat = bpy.data.materials.new('pfire')
    pmat.use_nodes = True
    pn = pmat.node_tree
    pn.nodes.remove(pn.nodes['Principled BSDF'])
    pe = pn.nodes.new('ShaderNodeEmission')
    pe.inputs['Color'].default_value = (1.0, 0.45, 0.08, 1.0)
    pe.inputs['Strength'].default_value = 5.0
    pn.links.new(pe.outputs[0], pn.nodes['Material Output'].inputs[0])
    p_objs = []
    for bone, e in particles:
        bpy.ops.mesh.primitive_ico_sphere_add(radius=0.8, subdivisions=1)
        o = bpy.context.active_object
        o.data.materials.append(pmat)
        o.visible_shadow = False
        p_objs.append((o, bone))
    # ground, light, world
    bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -0.03))
    g = bpy.context.active_object
    gm = bpy.data.materials.new('g'); gm.use_nodes = True
    gm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.2, 0.17, 0.12, 1)
    g.data.materials.append(gm)
    sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN'))
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-30))
    sc.collection.objects.link(sun)
    w = bpy.data.worlds.new('w'); w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.45, 0.5, 0.6, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
    sc.world = w
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 24
    sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.view_settings.view_transform = 'Standard'
    views = {'game': ((0.0, -205.0, 255.0), (0.0, -6.0, 32.0), 36), 'head': ((0.0, -88.0, 128.0), (0.0, -20.0, 76.0), 38)}
    which = ['game', 'head'] if opt('--view', 'both') == 'both' else [opt('--view', 'both')]
    T = max([eff.T for _, eff in effects] + [1.0])
    times = [i / fps for i in range(nfr)]
    gif_dir = os.path.join(os.path.dirname(PREVIEW), 'gif')
    os.makedirs(os.path.join(gif_dir, 'frames'), exist_ok=True)
    frames = {v: [] for v in which}
    for fi, t in enumerate(times):
        worlds = {}
        for ob, model, bones, me in objs:
            wd = bone_worlds(bones, anim, model, t % anim.duration)
            worlds[model] = wd
            P = posed(bones, me, wd) * scale
            ob.data.vertices.foreach_set('co', P.astype(np.float32).ravel())
            ob.data.update()
        ew = worlds[eye_model]
        for ob, bone, eff in fx_objs:
            Bm = ew[bone]
            co = []
            for bn in sorted(eff.quads):
                M = Bm @ eff.card_matrix(bn, t)
                for (p, _) in eff.quads[bn]:
                    co.append(tuple((M @ Vector(p)) * scale))
            ob.data.vertices.foreach_set('co', np.array(co, np.float32).ravel())
            ob.data.update()
        for o, bone in p_objs:
            o.location = (ew[bone].to_translation()) * scale
        for v in which:
            loc, tgt, lens = views[v]
            cam = bpy.data.objects.get('cam_' + v)
            if cam is None:
                cam = bpy.data.objects.new('cam_' + v, bpy.data.cameras.new('cam_' + v))
                cam.data.lens = lens
                cam.data.clip_end = 3000
                cam.location = loc
                cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
                sc.collection.objects.link(cam)
            sc.camera = cam
            p = os.path.join(gif_dir, 'frames', '%s_flames_%s_%03d.png' % (name, v, fi))
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            frames[v].append(p)
        print('frame %d/%d t=%.2f' % (fi + 1, nfr, t))
    py = os.path.join(ROOT, 'build', 'venv', 'bin', 'python')
    for v, fl in frames.items():
        gif = os.path.join(gif_dir, '%s_flames_%s.gif' % (name, v))
        sheet = os.path.join(PREVIEW, '%s_flames_%s.png' % (name, v))
        code = ('import sys; from PIL import Image; fs=[Image.open(p).convert("RGB") for p in sys.argv[3:]];'
                'fs[0].save(sys.argv[1], save_all=True, append_images=fs[1:], duration=int(1000/%g), loop=0);'
                'n=len(fs); c=4; r=(n+c-1)//c; w,h=fs[0].size; s=Image.new("RGB",(c*w//2,r*h//2));'
                '[s.paste(f.resize((w//2,h//2)),((i%%c)*w//2,(i//c)*h//2)) for i,f in enumerate(fs)]; s.save(sys.argv[2])'
                % fps)
        subprocess.run([py, '-I', '-c', code, gif, sheet] + fl, check=True)
        print('flames preview:', gif, sheet)


if __name__ == '__main__':
    main()
