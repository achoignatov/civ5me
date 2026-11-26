"""Post-process the Mordor render: smoke haze, drifting reek, bloom on fire, filmic tonemap, grade, grain.

  blender -b --factory-startup -P tools/splash/post_mordor.py -- build/splash/<name> [--dds out.dds] [--exposure 1.0]
          [--panel]  (outline the loading screen's info panel, for checking the composition)

Reads <name>_rgb.exr, <name>_z.exr, <name>_meta.json; writes <name>_final.png (and a DDS when asked).
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from splashlib import ROOT, load_image, blur, down, up, aces, srgb, save_png, save_dds, fbm, nrm
import numpy as np

ARGS = sys.argv[sys.argv.index('--') + 1:]
BASE = ARGS[0] if os.path.isabs(ARGS[0]) else os.path.join(ROOT, ARGS[0])
def arg(name, default):
    return type(default)(ARGS[ARGS.index(name) + 1]) if name in ARGS else default
EXPOSURE = arg('--exposure', 1.0)
SMOKE = arg('--smoke', 1.0)
DDS = arg('--dds', '')


def main():
    meta = json.load(open(BASE + '_meta.json'))
    img = load_image(BASE + '_rgb.exr', 3).astype(np.float64)
    z = load_image(BASE + '_z.exr', 1)[..., 0].astype(np.float64)
    H, W = z.shape
    Mx = np.array(meta['cam_matrix'])
    t = meta['sensor'] / 2 / meta['lens']
    xs = ((np.arange(W) + 0.5) / W * 2 - 1) * t
    ys = (1 - (np.arange(H) + 0.5) / H * 2) * t * H / W
    d = np.stack(np.broadcast_arrays(xs[None, :], ys[:, None], -np.ones((H, 1))), -1)
    d = d @ Mx[:3, :3].T
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    cam = Mx[:3, 3]
    sky = z > 1.0e5
    dist = np.where(sky, 1e5, z)
    U = np.arange(W)[None, :] / W; V = np.arange(H)[:, None] / H
    sc = W / 960.0

    # direction to Doom's crater, for warm haze
    doom = np.array(meta['doom']) + [0, 0, meta['doom_h']]
    dd = nrm(doom - cam)
    cosd = np.clip(d @ dd, -1, 1)
    warmth = np.clip((cosd - 0.6) / 0.4, 0, 1) ** 2

    # --- aerial perspective: smoky brown, warmer toward Doom, thicker low down
    haze_col = np.array([0.016, 0.013, 0.012]) + np.array([0.11, 0.028, 0.007]) * warmth[..., None]
    f = 1 - np.exp(-(dist / 2600.0) ** 0.85)
    f *= 0.92
    f = np.where(sky, 0.0, f)
    img = img * (1 - f[..., None]) + haze_col * f[..., None]

    # --- drifting reek: layered screen-space smoke behind the crag (depth gated), lit orange from below
    n1 = fbm(U * 5.0, V * 14.0, 6, 101)
    n2 = fbm(U * 13.0 + n1, V * 30.0, 5, 102)
    smoke = np.clip((n1 * 0.8 + n2 * 0.35) * 1.4 + 0.15, 0, 1)
    band = np.exp(-((V - 0.60) / 0.16) ** 2)                 # thickest along the plain, below the horizon
    band2 = np.exp(-((V - 0.36) / 0.10) ** 2) * 0.5          # a higher layer across Doom's flank
    behind = np.clip((dist - 12.0) / 30.0, 0, 1)
    amt = smoke * (band + band2) * behind * 0.55 * SMOKE
    under = np.clip((V - 0.35) / 0.4, 0, 1)
    smoke_col = np.array([0.020, 0.018, 0.018]) + np.array([0.10, 0.028, 0.006]) * (under * 0.25 + warmth * 1.0)[..., None]
    img = img * (1 - amt[..., None]) + smoke_col * amt[..., None]
    # ground smoke curling round the crag's foot (in front of the far plain, behind Sauron)
    n3 = fbm(U * 9.0, V * 18.0 - U * 3, 6, 103)
    low = np.clip((n3 + 0.1) * 1.6, 0, 1) * np.exp(-((V - 0.84) / 0.12) ** 2) * np.clip((dist - 3.0) / 6.0, 0, 1)
    img = img * (1 - 0.45 * SMOKE * low[..., None]) + np.array([0.05, 0.016, 0.006]) * (0.45 * SMOKE * low)[..., None]

    # --- bloom (fire, eye, ring, embers)
    bright = np.clip(img - 0.9, 0, None)
    bl = np.zeros_like(img)
    for s, wgt in ((3, 0.6), (12, 0.45), (40, 0.35), (110, 0.25)):
        sm = down(bright, 4)
        bl += up(blur(sm, s * sc / 4), img.shape) * wgt
    img = img + bl * 0.35

    # --- grade + tonemap
    img = aces(img * EXPOSURE)
    lum = (img * np.array([0.2126, 0.7152, 0.0722])).sum(-1, keepdims=True)
    # cool, desaturated shadows; warm highlights
    sh = np.clip(1 - lum * 4, 0, 1)
    img = img + sh * np.array([-0.004, 0.0, 0.006]) * 1.0
    img = lum + (img - lum) * 1.08
    vx = (U - 0.42); vy = (V - 0.5)
    v = 1 - 0.55 * np.clip((vx ** 2 * 1.0 + vy ** 2 * 1.5) * 2.4, 0, 1) ** 1.4
    img = np.clip(img * v[..., None], 0, 1)
    out = srgb(img)
    rng = np.random.default_rng(0)
    grain = rng.normal(0, 0.012, out.shape[:2])[..., None]
    out = np.clip(out + grain * (0.4 + 0.6 * (1 - out)), 0, 1)
    out = np.clip(out * 255 + rng.uniform(-0.5, 0.5, out.shape), 0, 255).astype(np.uint8)
    if '--panel' in ARGS:
        x0, x1, y0, y1 = int(0.49 * W), int(0.67 * W), int(0.28 * H), int(0.70 * H)
        for xx in (x0, x1): out[y0:y1, xx] = (0, 255, 0)
        for yy in (y0, y1): out[yy, x0:x1] = (0, 255, 0)
    save_png(BASE + '_final.png', out)
    if DDS:
        save_dds(DDS if os.path.isabs(DDS) else os.path.join(ROOT, DDS), out)
    print('wrote', BASE + '_final.png', out.shape)


main()
