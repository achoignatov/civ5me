"""Build the landmark models: Blender modelling -> texture atlas -> .gr2/.fxsxml/.dds (+ preview).

Run:  blender -b --factory-startup -P tools/landmarks/build_models.py -- [module ...] [--no-preview]
Output: build/landmarks/out/<model>.{gr2,fxsxml}, <model>_DIFF.dds, <model>_SREF.dds
        build/landmarks/preview/<model>.png

Landmarks now ship as tile improvements (docs/LANDMARKS.md); a row's own 'envelope' sets its limits.
Legacy defaults from the city-art path (landmarks.ENVELOPE):
  * models are authored in WORLD units (origin = tile centre, ground z = 0, south = -Y = towards the camera);
  * the build REFUSES a model outside the envelope: every vertex inside the city hexagon, height
    <= max_height, vertex/triangle counts <= the largest stock wonders;
  * written vertices are multiplied by 1/fScale, so the WonderArtInfo fScale stays at the proven 0.25;
  * flat shading only, the stock template's rectangular "Tree cut", 1 building model + tree cut,
    512x512 DIFF / 256x256 SREF, Wonder_DecisionTree, no effect bones (particles come later).
The model library (blib, atlas) and the .gr2 writer (civ5model, gr2) live in tools/capitals/.
"""
import importlib
import json
import math
import os
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'models'))
sys.path.insert(0, os.path.join(HERE, '..', 'capitals'))
# numpy for Blender's Python: build/venv (same Python version as Blender)
sys.path.append(os.path.join(HERE, '..', '..', 'build', 'venv', 'lib', 'python%d.%d' % sys.version_info[:2],
                             'site-packages'))

import atlas  # noqa: E402
import blib  # noqa: E402
import civ5model  # noqa: E402
import dds  # noqa: E402
import gr2  # noqa: E402
import pipeline  # noqa: E402  (reset(), preview(), _shrink())
import numpy as np  # noqa: E402
from landmarks import ALL_LANDMARKS, ENVELOPE, LANDMARKS, OUT, PREVIEW, envelope, manifest_path  # noqa: E402

GAME_DIFF = 512
GAME_SREF = 256
BAKED_DIFF = 1024        # baked models (module BAKE = True): 1024 DIFF / 512 SREF, like the larger stock wonders
BAKED_SREF = 512
WORK = os.path.join(os.path.dirname(PREVIEW), 'work')
GLOW_KEYS = ('DOOR_GLOW', 'GATE_GLOW')   # rig effect keys drawn as a still additive picture (glow.py, glow_effect())


def in_hex(x, y, slack=0.05, env=ENVELOPE):
    """Pointy-top city hexagon: flat sides east/west at hex_in, corners north/south at hex_out."""
    hin = env['hex_in'] + slack
    for k in range(6):
        a = math.radians(60 * k)            # outward normals of the 6 sides: 0, 60, ... degrees
        if x * math.cos(a) + y * math.sin(a) > hin:
            return False
    return True


def check_envelope(name, verts, tris, env=ENVELOPE):
    ENVELOPE = env          # noqa: N806  (this landmark's envelope, see landmarks.envelope)
    errs = []
    if len(verts) > ENVELOPE['max_verts']:
        errs.append('%d vertices > %d' % (len(verts), ENVELOPE['max_verts']))
    if len(tris) > ENVELOPE['max_tris']:
        errs.append('%d triangles > %d' % (len(tris), ENVELOPE['max_tris']))
    zs = [v[0][2] for v in verts]
    if max(zs) > ENVELOPE['max_height']:
        errs.append('height %.1f > %.1f' % (max(zs), ENVELOPE['max_height']))
    if min(zs) < ENVELOPE['min_z']:
        errs.append('lowest point %.1f < %.1f' % (min(zs), ENVELOPE['min_z']))
    out = [v[0] for v in verts if not in_hex(v[0][0], v[0][1], env=env)]
    if out:
        far = max(out, key=lambda p: math.hypot(p[0], p[1]))
        errs.append('%d vertices outside the city hexagon (e.g. %.1f, %.1f)' % (len(out), far[0], far[1]))
    if errs:
        raise SystemExit('%s is OUTSIDE the render envelope: %s' % (name, '; '.join(errs)))


def _make(mod_fn, seed, baked=False):
    """Run a model function into a fresh Builder and texture it.
    baked=False: flat shading + the swatch atlas (tools/capitals/atlas.py);
    baked=True: the model's own smooth shading + a real unwrap and baked textures (bake.py, high fidelity)."""
    pipeline.reset()
    blib.SEG[0] = 1.0
    blib.FILL[0] = 1.0
    b = blib.Builder(seed=seed)
    mod_fn(b)
    if baked:
        import bake
        return bake.process(b, px=BAKED_DIFF)
    b.fsmooth = [False] * len(b.faces)          # flat shading everywhere (see module docstring)
    return atlas.process(b)


def _textures(res, base, diff_px=GAME_DIFF, sref_px=GAME_SREF):
    alpha = np.full(res.image.shape[:2] + (1,), 255, np.uint8)
    diff = np.concatenate([res.image, alpha], -1)
    dn, sn = base + '_DIFF.dds', base + '_SREF.dds'
    dds.write_dxt3(os.path.join(OUT, dn), pipeline._shrink(diff, diff_px))
    dds.write_dxt3(os.path.join(OUT, sn), pipeline._shrink(res.sref, sref_px))
    return dn, sn


def _model_units(verts, k):
    return [((p[0] * k, p[1] * k, p[2] * k), n, t, bn, uv) for (p, n, t, bn, uv) in verts]


def _bbox(verts):
    zs = [v[0] for v in verts]
    return [(round(min(p[i] for p in zs), 1), round(max(p[i] for p in zs), 1)) for i in range(3)]


def build_one(lm, do_preview=True):
    t0 = time.time()
    name = lm['model']
    mod = importlib.import_module(lm['module'])
    importlib.reload(mod)
    seed = zlib.crc32(name.encode()) & 0xffff
    k = 1.0 / lm['scale']                       # world units -> model units at the WonderArtInfo fScale
    animated = lm.get('animated') and hasattr(mod, 'build_eye')
    files = []

    # the whole landmark as ONE static model: the proven form (and the envelope check of everything)
    args = lm.get('build_args', {})          # e.g. Moria's size variants (landmarks.py)
    baked = getattr(mod, 'BAKE', False)
    bake_px = getattr(mod, 'BAKE_PX', BAKED_DIFF)             # module override (Barad-dur v5: 2048)
    res = _make(lambda b: mod.build(b, **args), seed, baked) if not (animated and baked) else None
    env = envelope(lm)
    sname = name + '_Static' if animated else name
    cut = lm.get('tree_cut')
    glow_fx = None
    if res is not None:     # the whole landmark as one static model (skipped for baked animated models: their
        check_envelope(name, res.verts, res.tris, env)          # tower and Eye are baked and checked below)
        dn, sn = _textures(res, sname, *((BAKED_DIFF, BAKED_SREF) if baked else (GAME_DIFF, GAME_SREF)))
        size = civ5model.write_model(OUT, sname, _model_units(res.verts, k), res.tris, dn, sn, fx=(), wonder=True,
                                     hex_cut=False, tree_cut=cut * k if cut else None)
        files += [sname + '.gr2', dn, sn]
        print('%-20s tris %6d  verts %6d  gr2 %7d bytes  WORLD bbox %s  fScale %.2f  envelope OK' % (
            sname, len(res.tris), len(res.verts), size, _bbox(res.verts), lm['scale']))
        preview_res, preview_dn = res, dn
    if not animated:
        files.append(name + '.fxsxml')
    else:
        if res is not None:
            os.remove(os.path.join(OUT, sname + '.fxsxml'))  # the T1 variant gets its own .fxsxml below
        import beam
        import lmodel
        # the tower without the Eye, and the Eye alone (its own small texture); baked models bake both
        if baked:
            import bake
            pipeline.reset()
            blib.SEG[0] = blib.FILL[0] = 1.0
            bt = blib.Builder(seed=seed)
            mod.build(bt, eye=False)
            tower = bake.process(bt, px=bake_px)
            tdn, tsn = _textures(tower, name, bake_px, bake_px // 2)
            pipeline.reset()
            blib.SEG[0] = blib.FILL[0] = 1.0
            be = blib.Builder(seed=seed)
            mod.build_eye(be)
            epx = getattr(mod, 'EYE_PX', 512)          # Moria v4: the skinned part holds most of the model: 2048
            eye = bake.process(be, px=epx, ao_samples=getattr(mod, 'EYE_AO', 4))
            edn, esn = _textures(eye, name + '_Eye', epx, epx // 2)
            if hasattr(mod, 'PIVOT_MATS'):          # only these materials move with eyepivot; the rest stays still
                eye.still = [m_ not in mod.PIVOT_MATS for m_ in eye.vmat]
        else:
            tower = _make(lambda b: mod.build(b, eye=False), seed)
            tdn, tsn = _textures(tower, name)
            eye = _make(mod.build_eye, seed)
            edn, esn = _textures(eye, name + '_Eye', 256, 128)
        for part, r in (('tower', tower), ('eye', eye)):
            assert len(r.verts) <= env['max_verts'] and len(r.tris) <= env['max_tris'], (part, len(r.verts))
        check_envelope(name + ' (tower)', tower.verts, tower.tris, env)
        check_envelope(name + ' (eye)', eye.verts, eye.tris, env)
        print('%-20s baked tower: %d verts %d tris %spx, Eye: %d verts, WORLD bbox %s' % (
            name, len(tower.verts), len(tower.tris), bake_px if baked else GAME_DIFF, len(eye.verts),
            _bbox(tower.verts + eye.verts)))
        if res is None:
            preview_res, preview_dn = tower, tdn
        rig = mod.rig()
        pivot = tuple(c * k for c in mod.EYE_C)
        bones = [(bn_, parent, tuple(c * k for c in pos)) for bn_, parent, pos, _ in rig]
        size, bone_list = lmodel.write_building(
            OUT, name, dict(verts=_model_units(tower.verts, k), tris=tower.tris, diffuse=tdn, sref=tsn),
            eye=dict(verts=_model_units(eye.verts, k), tris=eye.tris, diffuse=edn, sref=esn,
                     still=getattr(eye, 'still', None)),
            rig=dict(pivot=pivot, bones=bones))
        idle, curve = lmodel.write_idle(OUT, name, bone_list, mod.GAZE)
        verify_animation(os.path.join(OUT, idle), name, bone_list, mod.GAZE)
        # effects
        from landmarks import EFFECTS, BEAM_TILT
        fire = [(bn_, EFFECTS[key]['name']) for bn_, _, _, key in rig if key and key != 'EYE_BEAM']
        beam_trig = [(bn_, EFFECTS[key]['name']) for bn_, _, _, key in rig if key == 'EYE_BEAM']
        trig_full, trig_fire = 'FX_Triggers_%s.ftsxml' % name, 'FX_Triggers_%s_Fire.ftsxml' % name
        lmodel.write_triggers(os.path.join(OUT, trig_full), fire + beam_trig)
        lmodel.write_triggers(os.path.join(OUT, trig_fire), fire)
        if beam_trig:                       # only the Eye has the beam (it follows that model's GAZE)
            files += beam.write(OUT, mod.GAZE, getattr(mod, 'BEAM_TILT', BEAM_TILT))
        glow_fx = None
        if any(key in GLOW_KEYS for _, _, _, key in rig):     # a still, additive glowing picture (glow.py)
            import glow
            glow_fx = mod.glow_effect(k)
            files += glow.write(OUT, **glow_fx)
        ename = name + '_Eye'
        tex = ['Generic_Grey_8.dds', tdn, tsn, edn, esn]
        fx_bones = [b_[0] for b_ in rig if b_[3]]
        fire_bones = [b_[0] for b_ in rig if b_[3] and b_[3] != 'EYE_BEAM']
        assert len(bone_list) <= 32, 'skinned part: at most 32 bones (SkinBoneCount)'
        W = lmodel.write_fxsxml
        W(os.path.join(OUT, name + '.fxsxml'), name + '.gr2', tex, animation=idle, triggers_file=trig_full,
          trigger_model=ename, bones=fx_bones, decision_tree=lmodel.ANIMATED_DT)                       # full
        if res is not None:
            W(os.path.join(OUT, name + '_T1.fxsxml'), sname + '.gr2', ['Generic_Grey_8.dds', dn, sn])  # static
        W(os.path.join(OUT, name + '_T2.fxsxml'), name + '.gr2', tex, animation=idle,
          decision_tree=lmodel.ANIMATED_DT)                                                             # + animation
        W(os.path.join(OUT, name + '_T3.fxsxml'), name + '.gr2', tex, animation=idle, triggers_file=trig_fire,
          trigger_model=ename, bones=fire_bones, decision_tree=lmodel.ANIMATED_DT)                     # + fire
        files += [name + '.gr2', idle, tdn, tsn, edn, esn, trig_full, trig_fire,
                  name + '.fxsxml', name + '_T2.fxsxml', name + '_T3.fxsxml'] + (
                     [name + '_T1.fxsxml'] if res is not None else [])
        print('%-20s animated: tower %d verts, Eye %d verts + %d bones, gaze loop %.1f s, %d effects  (%.1fs)' % (
            name, len(tower.verts), len(eye.verts), len(bone_list), mod.GAZE['T'], len(fire + beam_trig),
            time.time() - t0))
    for f_ in files:
        assert os.path.exists(os.path.join(OUT, f_)), f_
    json.dump({'files': sorted(set(files))}, open(manifest_path(lm), 'w'), indent=1)
    if do_preview:
        # preview in world units, with the true city hexagon (and its neighbours) drawn on the ground
        hin, hout = blib.HEX_IN, blib.HEX_OUT
        pipeline.PREVIEW, pipeline.WORK = PREVIEW, WORK
        blib.HEX_IN, blib.HEX_OUT = env['hex_in'], env['hex_out']
        try:
            overlays = []
            if animated and glow_fx:        # the additive glow, at its bone, in in-game units
                gpos = next(pos for bn_, _, pos, key in mod.rig() if key in GLOW_KEYS)
                for (x0, x1, z0, z1, y) in glow_fx['quads']:
                    P = [(gpos[0] + x / k, gpos[1] + y / k, gpos[2] + z / k) for x, z in ((x0, z0), (x1, z0), (x1, z1), (x0, z1))]
                    overlays.append((P, [(0, 1, 2, 3)], [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)],
                                     dds.decode_dxt3(os.path.join(OUT, glow_fx['name'] + '_DIFF.dds'))))
            pv, pt, pimg = preview_res.verts, preview_res.tris, dds.decode_dxt3(os.path.join(OUT, preview_dn))
            if animated and baked and hasattr(mod, 'PIVOT_MATS'):
                # the skinned part holds half the landmark: show both parts together (textures side by side)
                eimg = dds.decode_dxt3(os.path.join(OUT, edn))
                if eimg.shape == pimg.shape:
                    pv = [(v[0], v[1], v[2], v[3], (v[4][0] / 2, v[4][1])) for v in tower.verts] + \
                         [(v[0], v[1], v[2], v[3], (0.5 + v[4][0] / 2, v[4][1])) for v in eye.verts]
                    nt_ = len(tower.verts)
                    pt = list(tower.tris) + [(a + nt_, b + nt_, c + nt_) for a, b, c in eye.tris]
                    pimg = np.concatenate([pimg, eimg], axis=1)
            pipeline.preview(name, pv, pt, pimg, extra=getattr(mod, 'PREVIEW', ()), overlays=overlays)
            if animated and baked:      # the Eye on its own (its own texture), seen from the game's angle
                pipeline.preview(name + '_Eye', eye.verts, eye.tris, dds.decode_dxt3(os.path.join(OUT, edn)),
                                 extra=getattr(mod, 'PREVIEW_EYE', ()))
        finally:
            blib.HEX_IN, blib.HEX_OUT = hin, hout


def verify_animation(path, name, bones, gaze):
    """Read the written idle animation back: track groups = models, tracks = bones (sorted), and the
    decoded gaze curve follows gaze['fn'] (within 3 degrees; the curve is a smoothed fit)."""
    import granim
    r = gr2.read(path).root()
    tgs = {tg['Name']: tg for tg in r['TrackGroups']}
    assert set(tgs) == {'Tree cut', name, name + '_Eye'}, set(tgs)
    tracks = [t['Name'] for t in tgs[name + '_Eye']['TransformTracks']]
    assert tracks == sorted(b[0] for b in bones), tracks
    t = [t for t in tgs[name + '_Eye']['TransformTracks'] if t['Name'] == 'eyepivot'][0]
    v = t['OrientationCurve']['CurveData'].value
    kc = [x['UInt16'] for x in v['KnotsControls']]
    knots, quats = granim.decode_curve(kc, v['OneOverKnotScale'], v['ScaleOffsetTableEntries'])
    degs = [granim.quat_yaw_deg(q) for q in quats]
    T = gaze['T']
    worst = max(abs(granim.evaluate(degs, T, T * i / 240) - gaze['fn'](T * i / 240)) for i in range(241))
    pos = t['PositionCurve']['CurveData'].value['Controls']
    assert worst < 3.0, 'gaze curve off by %.1f degrees' % worst
    print('  animation check: %d track groups, eye tracks %s, gaze error max %.2f deg, pivot at %s' % (
        len(tgs), tracks, worst, [round(x, 1) for x in pos]))


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    names = [a for a in argv if not a.startswith('--')]
    for d in (OUT, PREVIEW, WORK):
        os.makedirs(d, exist_ok=True)
    for lm in (ALL_LANDMARKS if names else LANDMARKS):      # named modules: also rows not enabled
        if names and lm['module'] not in names:
            continue
        if lm.get('art_of'):                    # shows another row's files: nothing of its own to build
            continue
        build_one(lm, '--no-preview' not in argv)


if __name__ == '__main__':
    main()
