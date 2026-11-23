"""Build the Middle-earth pack as a custom DLC (Assets/DLC/MiddleEarth) that works in multiplayer WITHOUT MPPatch.

Input : dist/Middle Earth MP (v 1)   (the merged mod, built by build.py)
        vendor/civ5/vanilla_bnw.db        (the game's own database, BNW + all DLC, no mods)
        vendor/civ5/InGame_BNW.lua        (Assets/DLC/Expansion2/UI/InGame/InGame.lua)
Output: dist/DLC/MiddleEarth/ (+ zip)

How the mod parts are translated (DLC packages only accept XML data, no SQL, no InGameUIAddin):
  * database: the final modded DB is computed (mod XML + SQL replayed on the vanilla DB), diffed against
    vanilla, and written as plain XML (<Table>, <Delete>, <Update>, <Row>). Verified by replaying it.
  * text: Language_* tables are moved into <TextData> files.
  * audio: Audio_* rows are converted to the native AudioDefines / Audio2DScripts / Audio3DScripts format.
  * art & sounds: copied as loose files (as the original mods imported them into the VFS).
  * map scripts: self-contained files in Maps/ (<MapDirectory>).
  * in-game Lua: InGame.lua is overridden through a UISkin (like EUI / MP mod packs) to load the scripts.
"""
import os, re, sys, shutil, sqlite3, hashlib, zipfile, collections, uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dbreplay
sys.path.insert(0, os.path.join(HERE, 'landmarks'))
import landmarks

ROOT = os.path.normpath(os.path.join(HERE, '..'))
MOD = os.path.join(ROOT, 'dist', 'Middle Earth MP (v 1)')
MODINFO = os.path.join(MOD, 'Middle Earth MP (v 1).modinfo')
VANILLA = os.path.join(ROOT, 'vendor', 'civ5', 'vanilla_bnw.db')
INGAME_BNW = os.path.join(ROOT, 'vendor', 'civ5', 'InGame_BNW.lua')
SRC = os.path.join(ROOT, 'src')
OUT = os.path.join(ROOT, 'dist', 'DLC', 'MiddleEarth')
TMP = os.path.join(ROOT, 'build', 'tmp')
DLC_GUID = '{3c9a6f2e-5b1d-4e7a-8f4c-2d6b9e1a7c53}'
MAP_KEYS = ['TaHugeRndWw', 'TaLrgRndNww', 'TaHugeRndNww', 'TaLrgRndWw', 'TaStdRndWw', 'TaStdRndNww']
DATA_EXT = ('.xml', '.sql', '.lua', '.modinfo', '.pdf', '.civ5map')
SKIP_TABLES_PREFIX = ('Language_', 'Audio_')
# Per-city landmark models (docs/CITY_MODELS.md) are ON by default since 2026-11-24: Barad-dur (and Mount Doom) show
# the known-good base model vendor/landmarks/BaradDur (landmarks.EXTERNAL_ART), one turn after founding.
# --no-landmarks: every city uses stock art (--landmarks is accepted and changes nothing).
# --landmark-tests: add the diagnostic variants ("Barad Test 1..3"; only with our Blender models, EXTERNAL_ART = None).
# --landmark-stock-art shows the stock Polynesian palace instead (diagnostic).
LANDMARKS_ON = '--no-landmarks' not in sys.argv


def q(v):
    return escape(str(v), {'"': '&quot;'})


def colinfo(db, t):
    return [(c[1], (c[2] or '').lower(), c[4], c[5]) for c in db.execute('pragma table_info("%s")' % t)]


def fmt(v, typ):
    if isinstance(v, float):
        return repr(v)
    if typ == 'boolean' and isinstance(v, int) and v in (0, 1):
        return 'true' if v else 'false'
    return str(v)


# --------------------------------------------------------------------------- database diff
def build_db_xml(van, fin, outdir):
    files = []
    tables_f = [r[0] for r in fin.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%' order by name")]
    tables_v = set(r[0] for r in van.execute("select name from sqlite_master where type='table'"))

    # 1) new tables
    newdefs = []
    for t in tables_f:
        if t in tables_v or t.startswith(SKIP_TABLES_PREFIX):
            continue
        cols = []
        for name, typ, dflt, pk in colinfo(fin, t):
            a = 'name="%s" type="%s"' % (name, typ or 'text')
            if pk:
                a += ' primarykey="true"'
                if typ == 'integer':
                    a += ' autoincrement="true"'
            if dflt is not None:
                d = dflt.strip("'")
                a += ' default="%s"' % q(d)
            cols.append('\t\t<Column %s/>' % a)
        newdefs.append('\t<Table name="%s">\n%s\n\t</Table>' % (t, '\n'.join(cols)))
    if newdefs:
        p = os.path.join(outdir, 'MEDLC_000_Tables.xml')
        open(p, 'w', encoding='utf-8').write('<?xml version="1.0" encoding="utf-8"?>\n<GameData>\n%s\n</GameData>\n' % '\n'.join(newdefs))
        files.append(p)

    # 2) per table changes
    n = 0
    for t in tables_f:
        if t.startswith(SKIP_TABLES_PREFIX):
            continue
        cinf = colinfo(fin, t)
        types = {c[0]: c[1] for c in cinf}
        cols = [c[0] for c in cinf]
        vcols = [c[0] for c in colinfo(van, t)] if t in tables_v else []
        common = [c for c in cols if c in vcols] if vcols else cols
        out_cols = common  # columns added by ALTER TABLE are dropped (verified unused/default)
        frows = [dict(zip(cols, r)) for r in fin.execute('select * from "%s"' % t)]
        vrows = [dict(zip(vcols, r)) for r in van.execute('select * from "%s"' % t)] if vcols else []
        ops = []
        key = 'Type' if 'Type' in out_cols and len(set(r['Type'] for r in frows)) == len(frows) and \
              len(set(r['Type'] for r in vrows)) == len(vrows) else None
        noid = [c for c in out_cols if c != 'ID']

        def rowxml(r):
            body = ''.join('<%s>%s</%s>' % (c, q(fmt(r[c], types[c])), c) for c in noid if r.get(c) is not None)
            return '\t\t<Row>%s</Row>' % body

        if key:
            vmap = {r[key]: r for r in vrows}
            fmap = {r[key]: r for r in frows}
            for k in vmap:
                if k not in fmap:
                    ops.append('\t\t<Delete %s="%s"/>' % (key, q(k)))
            for r in frows:
                k = r[key]
                if k in vmap:
                    v = vmap[k]
                    ch = [c for c in noid if c in vcols and r.get(c) != v.get(c)]
                    if ch:
                        if any(r.get(c) is None for c in ch):
                            ops.append('\t\t<Delete %s="%s"/>' % (key, q(k)))
                            ops.append(rowxml(r))
                        else:
                            sets = ' '.join('%s="%s"' % (c, q(fmt(r[c], types[c]))) for c in ch)
                            ops.append('\t\t<Update><Where %s="%s"/><Set %s/></Update>' % (key, q(k), sets))
                else:
                    ops.append(rowxml(r))
        else:
            # multiset diff on the non-ID columns
            sig = lambda r: tuple(r.get(c) for c in noid)
            vc = collections.Counter(sig(r) for r in vrows)
            fc = collections.Counter(sig(r) for r in frows)
            removed = [s for s in vc if fc[s] < vc[s]]
            deleted_sigs = set()
            for s in removed:
                where = ' '.join('%s="%s"' % (c, q(fmt(v, types[c]))) for c, v in zip(noid, s) if v is not None)
                if not where:
                    continue
                ops.append('\t\t<Delete %s/>' % where)
                # a Delete matches every row agreeing on the non-null columns: track collateral removals
                for s2 in vc:
                    if all(v is None or v == v2 for v, v2 in zip(s, s2)):
                        deleted_sigs.add(s2)
            cur = collections.Counter({s: c for s, c in vc.items() if s not in deleted_sigs})
            for r in frows:
                s = sig(r)
                if cur[s] > 0:
                    cur[s] -= 1
                else:
                    ops.append(rowxml(r))
        if ops:
            n += 1
            p = os.path.join(outdir, 'MEDLC_%03d_%s.xml' % (n, t))
            open(p, 'w', encoding='utf-8').write('<?xml version="1.0" encoding="utf-8"?>\n<GameData>\n\t<%s>\n%s\n\t</%s>\n</GameData>\n' % (t, '\n'.join(ops), t))
            files.append(p)
    return files


def verify_db(files, fin):
    test = os.path.join(TMP, 'dlc_replay.db')
    shutil.copy(VANILLA, test)
    db = sqlite3.connect(test)
    errs = []
    for f in files:
        dbreplay.load_xml(db, f, errs)
    db.commit()
    bad = 0
    for (t,) in fin.execute("select name from sqlite_master where type='table' and name not like 'sqlite_%'"):
        if t.startswith(SKIP_TABLES_PREFIX):
            continue
        cols = [c for c in [c[1] for c in fin.execute('pragma table_info("%s")' % t)]
                if c != 'ID' and c in [x[1] for x in db.execute('pragma table_info("%s")' % t)]]
        sel = 'select %s from "%s"' % (','.join('"%s"' % c for c in cols), t)
        a = collections.Counter(fin.execute(sel).fetchall())
        try:
            b = collections.Counter(db.execute(sel).fetchall())
        except Exception as e:
            print('VERIFY: missing table', t, e); bad += 1; continue
        if a != b:
            bad += 1
            print('VERIFY MISMATCH', t, 'missing', list((a - b).items())[:2], 'extra', list((b - a).items())[:2])
    return errs, bad


# --------------------------------------------------------------------------- text
def build_text(outdir, actions):
    files = []
    for i, rel in enumerate(actions):
        if not rel.lower().endswith('.xml'):
            continue
        raw = open(os.path.join(MOD, rel), 'rb').read().decode('utf-8-sig', errors='replace')
        root = ET.fromstring(raw.encode('utf-8'))
        lang = [el for el in root if isinstance(el.tag, str) and el.tag.startswith('Language_')]
        if not lang:
            continue
        body = '\n'.join(ET.tostring(el, encoding='unicode') for el in lang)
        p = os.path.join(outdir, 'MEDLC_Text_%03d_%s' % (i, os.path.basename(rel)))
        open(p, 'w', encoding='utf-8').write('<?xml version="1.0" encoding="utf-8"?>\n<GameData>\n%s\n</GameData>\n' % body)
        files.append(p)
    return files


# --------------------------------------------------------------------------- audio
def build_audio(fin, outdir):
    sounds = fin.execute('select SoundID, FileName, LoadType, OnlyLoadOneVariationEachTime, DontCache from Audio_Sounds').fetchall()
    L = ['<?xml version="1.0" encoding="utf-8"?>', '<AudioDefinesFile>', '  <SoundDatas>']
    for sid, fn, lt, one, dc in sounds:
        L.append('    <SoundData>')
        L.append('      <SoundID>%s</SoundID>' % q(sid))
        L.append('      <Filename>%s</Filename>' % q(fn))
        if dc: L.append('      <bDontCache />')
        if one: L.append('      <bOnlyLoadOneVariationEachTime />')
        L.append('      <LoadType>%s</LoadType>' % ('STREAMED' if 'stream' in (lt or '').lower() else 'DYNAMIC_RES'))
        L.append('    </SoundData>')
    L += ['  </SoundDatas>', '</AudioDefinesFile>']
    open(os.path.join(outdir, 'MEDLC_AudioDefines.xml'), 'w', encoding='utf-8').write('\n'.join(L) + '\n')

    def scripts(table, root, coll, item):
        cols = [c[1] for c in fin.execute('pragma table_info(%s)' % table)]
        L = ['<?xml version="1.0" encoding="utf-8"?>', '<%s>' % root, '  <%s>' % coll]
        for r in fin.execute('select * from %s' % table):
            d = dict(zip(cols, r))
            L.append('    <%s>' % item)
            L.append('      <ScriptID>%s</ScriptID>' % q(d['ScriptID']))
            L.append('      <SoundID>%s</SoundID>' % q(d['SoundID']))
            L.append('      <SoundType>%s</SoundType>' % q(d['SoundType']))
            L.append('      <iMaxVolume>%d</iMaxVolume>' % d['MaxVolume'])
            L.append('      <iMinVolume>%d</iMinVolume>' % d['MinVolume'])
            if d.get('IsMusic'): L.append('      <bIsMusic>True</bIsMusic>')
            if d.get('Looping'): L.append('      <bLooping>True</bLooping>')
            if d.get('PitchChangeDown'): L.append('      <iPitchChangeDown>%d</iPitchChangeDown>' % d['PitchChangeDown'])
            if d.get('PitchChangeUp'): L.append('      <iPitchChangeUp>%d</iPitchChangeUp>' % d['PitchChangeUp'])
            if d.get('Priority') not in (None, 1): L.append('      <iPriority>%d</iPriority>' % d['Priority'])
            L.append('    </%s>' % item)
        L += ['  </%s>' % coll, '</%s>' % root]
        return '\n'.join(L) + '\n'
    open(os.path.join(outdir, 'MEDLC_Audio2DScripts.xml'), 'w', encoding='utf-8').write(
        scripts('Audio_2DSounds', 'Script2DFile', 'Script2DSounds', 'Script2DSound'))
    open(os.path.join(outdir, 'MEDLC_Audio3DScripts.xml'), 'w', encoding='utf-8').write(
        scripts('Audio_3DSounds', 'Script3DFile', 'Script3DSounds', 'Script3DSound'))
    return len(sounds)


# --------------------------------------------------------------------------- lua
def strip_includes(src, names):
    for n in names:
        src = re.sub(r'^\s*include\("%s"\)\s*$' % n, '-- (inlined %s)' % n, src, flags=re.M)
    return src


def build_lua():
    lua = os.path.join(SRC, 'METSL', 'LUA')
    defs = open(os.path.join(lua, 'METSL_MapDefs.lua'), encoding='utf-8').read()
    core = strip_includes(open(os.path.join(lua, 'METSL_MapCore.lua'), encoding='utf-8').read(), ['METSL_MapDefs'])
    os.makedirs(os.path.join(OUT, 'Maps'), exist_ok=True)
    for k in MAP_KEYS:
        data = open(os.path.join(lua, 'METSL_MapData_%s.lua' % k), encoding='utf-8').read()
        body = ('-- METSL_%s : Middle-earth True Start Location map script (self-contained DLC build)\n' % k
                + defs + '\n' + data + '\n' + core + '\nMETSL_UseMap("%s")\n' % k)
        open(os.path.join(OUT, 'Maps', 'METSL_%s.lua' % k), 'w', encoding='utf-8', newline='\r\n').write(body)
    ui = os.path.join(OUT, 'UI')
    os.makedirs(ui, exist_ok=True)
    shutil.copy2(os.path.join(lua, 'METSL_MapDefs.lua'), ui)
    shutil.copy2(os.path.join(lua, 'METSL_InGame.lua'), ui)
    shutil.copy2(os.path.join(SRC, 'MEC', 'Wood Elves', 'LUA', 'Wood_Elves_Units_Promotions.lua'), ui)
    ig = open(INGAME_BNW, encoding='latin-1').read()
    anchor = 'g_uiAddins = {};'
    assert anchor in ig
    hook = (anchor + '\n-- Middle-earth DLC: in-game scripts (loaded like mod InGameUIAddins)\n'
            'table.insert(g_uiAddins, ContextPtr:LoadNewContext("METSL_InGame"));\n'
            'table.insert(g_uiAddins, ContextPtr:LoadNewContext("Wood_Elves_Units_Promotions"));\n')
    if LANDMARKS_ON:
        hook += 'table.insert(g_uiAddins, ContextPtr:LoadNewContext("MEC_Landmarks"));\n'
    if '--redraw-button' in sys.argv:    # opt-in debug buttons (empty-tile bug, docs/CITY_MODELS.md §8)
        for ext in ('.lua', '.xml'):
            shutil.copy2(os.path.join(HERE, 'landmarks', 'MEC_RedrawCities' + ext), ui)
        hook += 'table.insert(g_uiAddins, ContextPtr:LoadNewContext("MEC_RedrawCities"));\n'
    if '--rendertest' in sys.argv:      # automated render test harness (tools/rendertest), never in normal builds
        shutil.copy2(os.path.join(HERE, 'rendertest', 'MEC_RenderTest.lua'), ui)
        hook += 'table.insert(g_uiAddins, ContextPtr:LoadNewContext("MEC_RenderTest"));\n'
    civs = [a.split('=', 1)[1] for a in sys.argv if a.startswith('--rendertest-civs=')]
    if civs:                            # test only: Play Now with exactly N major civs (front-end skin override)
        sp = open(os.path.join(os.path.dirname(INGAME_BNW), '..', 'FrontEnd', 'SinglePlayer.lua'), encoding='latin-1').read() \
            if os.path.exists(os.path.join(os.path.dirname(INGAME_BNW), '..', 'FrontEnd', 'SinglePlayer.lua')) else \
            open(os.path.expanduser("~/.local/share/Steam/steamapps/common/Sid Meier's Civilization V/Assets/UI/FrontEnd/SinglePlayer.lua"), encoding='latin-1').read()
        anchor2 = 'function StartGameClick()'
        assert anchor2 in sp
        rt = open(os.path.join(HERE, 'rendertest', 'RT_PlayNow.lua'), encoding='utf-8').read().replace('@@N@@', civs[0])
        os.makedirs(os.path.join(OUT, 'Art'), exist_ok=True)
        open(os.path.join(OUT, 'Art', 'SinglePlayer.lua'), 'w', encoding='latin-1').write(
            sp.replace(anchor2, rt + '\n' + anchor2 + '\n\tRT_SetupPlayers()', 1))
    open(os.path.join(ui, 'InGame.lua'), 'w', encoding='latin-1').write(ig.replace(anchor, hook, 1))


# --------------------------------------------------------------------------- landmarks
def build_landmarks():
    """Landmark buildings + art + effects + in-game script.
    Returns (gamedata, text, wonders, [vis effect defines], [vis effect model defines]) file names.
    --landmark-tests adds the diagnostic variants ("Barad Test 1..3"); off by default (the old --no-landmark-tests is
    accepted and changes nothing)."""
    diag = '--landmark-tests' in sys.argv and not landmarks.EXTERNAL_ART
    # our own Blender models (build/landmarks/out) are only needed when the base model is switched off
    need = [] if landmarks.EXTERNAL_ART else [f for lm in landmarks.LANDMARKS for f in landmarks.asset_files(lm)]
    missing = [f for f in need if not os.path.exists(os.path.join(landmarks.OUT, f))]
    if missing:
        sys.exit('landmark models missing (run: blender -b --factory-startup -P tools/landmarks/build_models.py): %s'
                 % missing)
    stock = '--landmark-stock-art' in sys.argv
    art = os.path.join(OUT, 'Art', 'Landmarks')
    os.makedirs(art, exist_ok=True)
    if not stock:
        import probes
        for f in sorted(set(need)):
            if f.endswith('.gr2'):      # stock section layout (docs/CITY_MODELS.md §8, 2026-11-23)
                probes.to_stock_sections(os.path.join(landmarks.OUT, f), os.path.join(art, f), zero_obb=landmarks.ZERO_OBB)
            else:
                shutil.copy2(os.path.join(landmarks.OUT, f), art)
    if diag and not stock:   # Test 1 rewritten like stock files (hashed strings / zero OBB), tools/landmarks/probes.py
        import probes
        for model in sorted({landmarks.art_model(lm) for lm in landmarks.LANDMARKS if lm.get('animated')}):
            probes.build(model, landmarks.OUT, art)
    if diag:    # the _LOOSE probe: stock palace mesh bytes as a loose file under a new name
        shutil.copy2(os.path.join(ROOT, 'vendor', 'civ5', 'template_poly_palace.gr2'),
                     os.path.join(art, landmarks.LOOSE_MODEL + '.gr2'))
        open(os.path.join(art, landmarks.LOOSE_MODEL + '.fxsxml'), 'w', encoding='utf-8', newline='\r\n').write(
            landmarks.loose_probe_fxsxml())
    if landmarks.EXTERNAL_ART:     # a model not made by us (docs/CITY_MODELS.md §8, "external model")
        x = landmarks.EXTERNAL_ART
        for f in os.listdir(x['dir']):
            if f.lower().endswith(('.gr2', '.dds')):
                shutil.copy2(os.path.join(x['dir'], f), art)      # byte-identical, no conversion
        open(os.path.join(art, x['model'] + '.fxsxml'), 'w', encoding='utf-8', newline='\r\n').write(
            landmarks.external_fxsxml())
    open(os.path.join(art, landmarks.WONDER_XML), 'w', encoding='utf-8', newline='\r\n').write(
        landmarks.wonder_defines(stock_art=stock, with_diagnostics=diag))
    vfx, vmodels = [], []
    if any(lm.get('animated') for lm in landmarks.LANDMARKS) and not stock and not landmarks.EXTERNAL_ART:
        open(os.path.join(art, landmarks.VISEFFECTS_XML), 'w', encoding='utf-8', newline='\r\n').write(
            landmarks.vis_effects())
        open(os.path.join(art, landmarks.VISMODELS_XML), 'w', encoding='utf-8', newline='\r\n').write(
            landmarks.vis_effect_models())
        vfx, vmodels = [landmarks.VISEFFECTS_XML], [landmarks.VISMODELS_XML]
        for x in vfx + vmodels:
            ET.parse(os.path.join(art, x))
    gd = os.path.join(OUT, 'Gameplay', 'XML', landmarks.GAMEDATA_XML)
    open(gd, 'w', encoding='utf-8', newline='\r\n').write(landmarks.gamedata(with_diagnostics=diag))
    tx = os.path.join(OUT, 'Gameplay', 'XML', 'Text', landmarks.TEXT_XML)
    open(tx, 'w', encoding='utf-8', newline='\r\n').write(landmarks.text(with_diagnostics=diag))
    src = open(os.path.join(HERE, 'landmarks', landmarks.LUA), encoding='utf-8').read()
    marker = '-- @@LANDMARK_TABLE@@'
    assert src.count(marker) == 1
    src = re.sub(r'^-- @@LANDMARK_TABLE@@.*$', lambda m: landmarks.lua_table(with_diagnostics=diag), src, count=1,
                 flags=re.M)
    open(os.path.join(OUT, 'UI', landmarks.LUA), 'w', encoding='utf-8').write(src)

    # database check: the rows load without errors on top of the final modded database and touch
    # nothing else (only new rows in BuildingClasses / Buildings)
    test = os.path.join(TMP, 'landmarks_check.db')
    shutil.copy(os.path.join(TMP, 'final.db'), test)
    db = sqlite3.connect(test)
    before = {t: db.execute('select count(*) from "%s"' % t).fetchone()[0]
              for (t,) in db.execute("select name from sqlite_master where type='table'").fetchall()}
    errs = []
    dbreplay.load_xml(db, gd, errs)
    db.commit()
    assert not errs, errs
    for t, n in before.items():
        now = db.execute('select count(*) from "%s"' % t).fetchone()[0]
        exp = n + (len(landmarks.entries(diag)) if t in ('Buildings', 'BuildingClasses') else 0)
        assert now == exp, (t, n, now)
    for e in landmarks.entries(diag):
        r = db.execute('select Cost, ArtDefineTag, DisplayPosition, ArtInfoCulturalVariation, ArtInfoEraVariation, '
                       'ArtInfoRandomVariation from Buildings where Type=?', (e['building'],)).fetchone()
        assert r is not None and r[0] == (1 if landmarks.BUILDABLE and e['keys'] else -1) and r[1] == e['tag'], r
        assert os.path.exists(os.path.join(art, e['fxsxml'])) or stock or e.get('stock'), e['fxsxml']
        assert r[2] == e.get('display', landmarks.DISPLAY_POSITION) and not any(v in (1, 'true') for v in r[3:]), r
    db.close()
    print('landmarks: %d buildings (%s), %d files%s' % (
        len(landmarks.entries(diag)), ', '.join(e['title'] for e in landmarks.entries(diag)), len(need),
        '  [STOCK ART diagnostic]' if stock else ''))
    return landmarks.GAMEDATA_XML, landmarks.TEXT_XML, landmarks.WONDER_XML, vfx, vmodels


# --------------------------------------------------------------------------- assets
def copy_assets(modinfo_text):
    n = 0
    for m in re.finditer(r'<File md5="\w+" import="(\d)">([^<]+)</File>', modinfo_text):
        imp, rel = m.group(1), m.group(2).replace('&amp;', '&')
        if imp != '1' or rel.lower().endswith(DATA_EXT):
            continue
        dst = os.path.join(OUT, 'Art', rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(MOD, rel), dst)
        n += 1
    return n


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, 'Gameplay', 'XML', 'Text'))
    os.makedirs(os.path.join(OUT, 'Sounds', 'XML'))
    os.makedirs(TMP, exist_ok=True)

    final_path = os.path.join(TMP, 'final.db')
    fin, errs = dbreplay.replay(VANILLA, final_path, MODINFO)
    assert not errs, errs
    van = sqlite3.connect(VANILLA)

    gfiles = build_db_xml(van, fin, os.path.join(OUT, 'Gameplay', 'XML'))
    verrs, bad = verify_db(gfiles, fin)
    print('gameplay xml files: %d  replay errors: %d  mismatching tables: %d' % (len(gfiles), len(verrs), bad))
    for e in verrs[:10]:
        print('  ', e)
    if verrs or bad:
        sys.exit('database conversion not exact - aborting')

    mi = open(MODINFO, encoding='utf-8').read()
    actions = re.findall(r'<UpdateDatabase>([^<]+)</UpdateDatabase>', mi)
    tfiles = build_text(os.path.join(OUT, 'Gameplay', 'XML', 'Text'), [a.replace('&amp;', '&') for a in actions])
    nsnd = build_audio(fin, os.path.join(OUT, 'Sounds', 'XML'))
    build_lua()
    nart = copy_assets(mi)
    shutil.copy2(os.path.join(ROOT, 'README.md'), os.path.join(OUT, 'README.md'))
    lmk = build_landmarks() if LANDMARKS_ON else None

    P = ['<?xml version="1.0" encoding="utf-8"?>', '<Civ5Package>',
         '\t<GUID>%s</GUID>' % DLC_GUID,
         '\t<Version>1</Version>',
         '\t<Priority>350</Priority>',
         '\t<PTags>', '\t\t<Tag>Version</Tag>', '\t</PTags>',
         '\t<Name>', '\t\t<Value language="en_US">Middle-earth</Value>', '\t</Name>',
         '\t<Description>', '\t\t<Value language="en_US">Middle-earth civilizations, city-states, barbarians, soundtrack and True Start Location maps (multiplayer DLC build of Yenyang\'s mods)</Value>', '\t</Description>']
    for f in tfiles:
        P.append('\t<TextData>%s</TextData>' % os.path.basename(f))
    for f in gfiles:
        P.append('\t<GameData>%s</GameData>' % os.path.basename(f))
    if lmk:
        P.append('\t<TextData>%s</TextData>' % lmk[1])
        P.append('\t<GameData>%s</GameData>' % lmk[0])
        P.append('\t<WonderDefines>%s</WonderDefines>' % lmk[2])
        P += ['\t<VisEffectInfoDefines>%s</VisEffectInfoDefines>' % x for x in lmk[3]]
        P += ['\t<VisEffectModelDefines>%s</VisEffectModelDefines>' % x for x in lmk[4]]
    P += ['\t<AudioDefines>MEDLC_AudioDefines.xml</AudioDefines>',
          '\t<AudioScripts2D>MEDLC_Audio2DScripts.xml</AudioScripts2D>',
          '\t<AudioScripts3D>MEDLC_Audio3DScripts.xml</AudioScripts3D>',
          '\t<Gameplay>', '\t\t<MapDirectory>Maps</MapDirectory>', '\t</Gameplay>',
          '\t<UISkin name="Expansion2Primary" set="Expansion2" platform="Common">',
          '\t\t<Skin>', '\t\t\t<Directory>Art</Directory>', '\t\t</Skin>',
          '\t\t<GameplaySkin>', '\t\t\t<Directory>UI</Directory>', '\t\t\t<Directory>Art</Directory>', '\t\t</GameplaySkin>',
          '\t</UISkin>', '</Civ5Package>']
    open(os.path.join(OUT, 'MiddleEarth.Civ5Pkg'), 'w', encoding='utf-8', newline='\r\n').write('\n'.join(P) + '\n')

    # every file referenced by name must exist exactly once
    names = collections.Counter(f.lower() for _, _, fs in os.walk(OUT) for f in fs)
    for f in re.findall(r'>([^<>]+\.xml)<', open(os.path.join(OUT, 'MiddleEarth.Civ5Pkg')).read()):
        assert names[f.lower()] == 1, f
    print('text files: %d  sounds: %d  art/sound assets: %d' % (len(tfiles), nsnd, nart))

    if False:
        with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
            for dp, _, fs in os.walk(OUT):
                for fn in fs:
                    full = os.path.join(dp, fn)
                    zf.write(full, os.path.relpath(full, os.path.dirname(OUT)))
        print('zip:', z, os.path.getsize(z) >> 20, 'MB')


# --------------------------------------------------------------------------- "Shared" packaging
# Civ 5 only registers packages whose <Key> signature (over GUID + PTags) is valid, and the signing secret is
# unknown. So the content is attached to the game's own free package "Upgrade 1" (Assets/DLC/Shared), whose
# signed header (GUID, SteamApp, Version, Ownership, Key, PTags) is kept byte-for-byte; we only add a load
# priority (after BNW and all DLC) and our entries. Files live in Assets/DLC/Shared/MiddleEarth/.
UPGRADE1_ORIG = os.path.join(ROOT, 'vendor', 'civ5', 'Upgrade1_original.Civ5Pkg')
SHARED_OUT = os.path.join(ROOT, 'dist', 'DLC_Shared', 'Shared')


def build_shared():
    if os.path.exists(os.path.dirname(SHARED_OUT)):
        shutil.rmtree(os.path.dirname(SHARED_OUT))
    os.makedirs(SHARED_OUT)
    shutil.copytree(OUT, os.path.join(SHARED_OUT, 'MiddleEarth'), ignore=shutil.ignore_patterns('*.Civ5Pkg'))
    ours = open(os.path.join(OUT, 'MiddleEarth.Civ5Pkg'), encoding='utf-8').read()
    body = re.search(r'</Description>\s*(.*?)</Civ5Package>', ours, re.S).group(1)
    body = body.replace('<MapDirectory>Maps</MapDirectory>', '<MapDirectory>MiddleEarth/Maps</MapDirectory>')
    body = body.replace('<Directory>Art</Directory>', '<Directory>MiddleEarth/Art</Directory>')
    body = body.replace('<Directory>UI</Directory>', '<Directory>MiddleEarth/UI</Directory>')
    orig = open(UPGRADE1_ORIG, 'rb').read().decode('ascii')
    assert '<Priority>' not in orig
    new = orig.replace('\t<Version>1</Version>\r\n', '\t<Version>1</Version>\r\n\t<Priority>400</Priority>\r\n', 1)
    new = new.replace('</Civ5Package>', '\r\n\t<!-- ===== Middle-earth pack (added) ===== -->\r\n\t'
                      + body.strip().replace('\n', '\r\n') + '\r\n</Civ5Package>', 1)
    assert new.count('<Priority>') == 1
    # signed header must be unchanged
    for tag in ('GUID', 'SteamApp', 'Version', 'Ownership', 'Key'):
        assert re.findall(r'<%s>[^<]*</%s>' % (tag, tag), orig)[0] in new
    open(os.path.join(SHARED_OUT, 'Upgrade1.Civ5Pkg'), 'wb').write(new.encode('ascii', 'xmlcharrefreplace'))
    ET.fromstring(new.encode())
    print('shared build:', SHARED_OUT)
    if '--zip' in sys.argv:
        z = os.path.join(ROOT, 'dist', 'MiddleEarth_DLC.zip')
        if os.path.exists(z):
            os.remove(z)
        with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
            for dp, _, fs in os.walk(SHARED_OUT):
                for fn in fs:
                    full = os.path.join(dp, fn)
                    zf.write(full, os.path.relpath(full, os.path.dirname(SHARED_OUT)))
        print('zip:', z, os.path.getsize(z) >> 20, 'MB')


if __name__ == '__main__':
    main()
    build_shared()
