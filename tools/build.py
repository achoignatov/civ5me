"""Assemble the merged, multiplayer-ready "Middle-earth Multiplayer Pack" mod.

Sources: ../mods/<original six mods>  +  ../src (new / replaced files)
Output : ../dist/Middle Earth MP (v 1)/  and a zip next to it.
"""
import os, re, shutil, hashlib, zipfile, sys
from xml.sax.saxutils import escape

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))
MODS = os.path.join(ROOT, 'mods')
SRC = os.path.join(ROOT, 'src')
MOD_ID = 'b5c3a2e1-7d4f-4e2a-9c61-3f8e0d2b7a41'
VERSION = 1
OUTNAME = 'Middle Earth MP (v %d)' % VERSION
OUT = os.path.join(ROOT, 'dist', OUTNAME)

# (original mod folder, subfolder in the merged mod, files to drop) -- load order matters
PARTS = [
    ('Middle Earth Soundtrack (v 1)', 'Soundtrack', []),
    ('Middle Earth Only (v 3)', 'MEOnly', []),
    ('Middle Earth Civilizations (v 9)', 'MEC', []),
    ('Middle Earth City States (v 1)', 'MECS', []),
    ('Middle Earth Barbarians (GK or BNW) (v 3)', 'MEB', []),
    ('Middle Earth True Start Location (v 2)', 'METSL', [
        # single-player-only setup screen and the WorldBuilder-map hooks it relied on
        r'^Game Setup/', r'^LUA/MapGenerator\.lua$', r'^LUA/WorldBuilderRandomItems\.lua$',
        r'^LUA/METSL_Loading\.lua$', r'^LUA/METSL_Defines\.lua$', r'^LUA/METSL_Functions\.lua$',
        r'^LUA/METSL_Utils\.lua$', r'^LUA/METSL_CityNames\.lua$', r'^Maps/.*\.Civ5Map$',
    ]),
]

# mods this pack replaces (blocked so nobody runs both) + blocks inherited from the originals
BLOCKS = [
    ('6724fecd-91d2-44fe-884d-abb59be314ad', 'Middle Earth Soundtrack'),
    ('65b7def1-337c-4f88-9f84-2fb2213417e6', 'Middle Earth Only'),
    ('8c42df36-e23b-4cf5-9ed2-534ac386cf48', 'Middle Earth Civilizations'),
    ('46830894-7582-4a69-8c5a-1837e053a9de', 'Middle Earth City States'),
    ('360bb9a3-07d0-4935-b0e9-a22be98b590f', 'Middle Earth Barbarians'),
    ('9f1a1884-17be-4f9f-bbbf-37143a130eb3', 'Middle Earth True Start Location'),
    ('fdc54097-1a86-4942-bd90-26d1436ee07a', 'Lord of the Rings Civ5'),
    ('36e88483-48fe-4545-b85f-bafc50dde315', 'Yet (not) Another Earth Maps Pack'),
    ('d425ef7b-8f85-4ade-abff-bf795978c86b', 'Middle Earth Map Pack'),
]

MAP_KEYS = ['TaHugeRndWw', 'TaLrgRndNww', 'TaHugeRndNww', 'TaLrgRndWw', 'TaStdRndWw', 'TaStdRndNww']


def md5(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest().upper()


def read_modinfo(folder):
    mi = [f for f in os.listdir(folder) if f.endswith('.modinfo')][0]
    t = open(os.path.join(folder, mi), 'rb').read().decode('utf-8-sig')
    files = {}
    for m in re.finditer(r'<File md5="\w+" import="(\d)">([^<]+)</File>', t):
        files[m.group(2).replace('\\', '/')] = m.group(1)
    actions = re.findall(r'<UpdateDatabase>([^<]+)</UpdateDatabase>', re.search(r'<OnModActivated>(.*?)</OnModActivated>', t, re.S).group(1))
    return files, [a.replace('\\', '/') for a in actions]


def main():
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    file_entries = []   # (relpath, import)
    actions = []

    for orig, sub, drops in PARTS:
        src_root = os.path.join(MODS, orig)
        files, acts = read_modinfo(src_root)
        for rel, imp in sorted(files.items()):
            if any(re.search(d, rel) for d in drops):
                continue
            dst = os.path.join(OUT, sub, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(src_root, rel), dst)
            file_entries.append((sub + '/' + rel, imp))
        for a in acts:
            assert not any(re.search(d, a) for d in drops), a
            actions.append(sub + '/' + a)
        # credits / docs (not loaded by the game)
        for f in os.listdir(src_root):
            if f.lower().endswith('.pdf'):
                shutil.copy2(os.path.join(src_root, f), os.path.join(OUT, sub, f))

    # overlay new / replaced files from src (all imported into the VFS)
    known = {e[0] for e in file_entries}
    for dirpath, _, fnames in os.walk(SRC):
        for fn in fnames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, SRC).replace(os.sep, '/')
            dst = os.path.join(OUT, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(full, dst)
            if rel not in known:   # replaced files keep their original import flag
                # new Lua (map scripts, map data, shared code) goes into the VFS so include() finds it
                file_entries.append((rel, '1'))

    # fixes on top of the original mods (applied last)
    actions.append('Fixes/MEMP_ArtFixes.xml')

    entry_points = [
        ('InGameUIAddin', 'MEC/Wood Elves/LUA/Wood_Elves_Units_Promotions.lua', 'Wood Elf Unit Promotions', ''),
        ('InGameUIAddin', 'METSL/LUA/METSL_InGame.lua', 'METSL_InGame', 'Middle-earth TSL: city-state cleanup and dynamic city naming'),
    ]
    for k in MAP_KEYS:
        entry_points.append(('MapScript', 'METSL/Maps/METSL_%s.lua' % k, 'METSL_%s' % k, ''))
    for _, f, _, _ in entry_points:
        assert os.path.exists(os.path.join(OUT, f)), f
    for a in actions:
        assert os.path.exists(os.path.join(OUT, a)), a

    desc = ("All of Yenyang's Middle-earth mods merged into one multiplayer-compatible package: "
            "Middle Earth Civilizations, City States, Barbarians, Only, Soundtrack and True Start Location.[NEWLINE][NEWLINE]"
            "The True Start Location maps are rebuilt as regular map scripts (pick a 'Middle-earth TSL' map type), so they work "
            "in multiplayer (with MPPatch), hotseat and single player. All map settings (city-state placement, resources, natural "
            "wonders, dynamic city naming, canonical resource regions, civilization start resources) are map options that the game "
            "syncs to every player.[NEWLINE][NEWLINE]Do NOT enable the original six Middle Earth mods together with this pack.")

    L = []
    L.append('<?xml version="1.0" encoding="utf-8"?>')
    L.append('<Mod id="%s" version="%d">' % (MOD_ID, VERSION))
    L.append('  <Properties>')
    L.append('    <Name>Middle Earth Multiplayer Pack</Name>')
    L.append('    <Stability>Beta</Stability>')
    L.append('    <Teaser>Yenyang\'s Middle-earth civilizations, city-states, barbarians, soundtrack and True Start Location maps - multiplayer ready</Teaser>')
    L.append('    <Description>%s</Description>' % escape(desc))
    L.append('    <Authors>Yenyang (original mods); multiplayer conversion</Authors>')
    L.append('    <SpecialThanks>Gedemon, FramedArchitecture, Nomad or What, vadoalmax, TJ, LastSword</SpecialThanks>')
    L.append('    <HideSetupGame>0</HideSetupGame>')
    L.append('    <AffectsSavedGames>1</AffectsSavedGames>')
    L.append('    <MinCompatibleSaveVersion>0</MinCompatibleSaveVersion>')
    L.append('    <SupportsSinglePlayer>1</SupportsSinglePlayer>')
    L.append('    <SupportsMultiplayer>1</SupportsMultiplayer>')
    L.append('    <SupportsHotSeat>1</SupportsHotSeat>')
    L.append('    <SupportsMac>1</SupportsMac>')
    L.append('    <ReloadAudioSystem>1</ReloadAudioSystem>')
    L.append('    <ReloadLandmarkSystem>1</ReloadLandmarkSystem>')
    L.append('    <ReloadStrategicViewSystem>1</ReloadStrategicViewSystem>')
    L.append('    <ReloadUnitSystem>1</ReloadUnitSystem>')
    L.append('  </Properties>')
    L.append('  <Dependencies>')
    L.append('    <Dlc id="6DA07636-4123-4018-B643-6575B4EC336B" minversion="0" maxversion="999" />')
    L.append('    <Dlc id="0E3751A1-F840-4e1b-9706-519BF484E59D" minversion="0" maxversion="999" />')
    L.append('  </Dependencies>')
    L.append('  <References />')
    L.append('  <Blocks>')
    for bid, title in BLOCKS:
        L.append('    <Mod id="%s" minversion="0" maxversion="999" title="%s" />' % (bid, escape(title)))
    L.append('  </Blocks>')
    L.append('  <Files>')
    for rel, imp in file_entries:
        L.append('    <File md5="%s" import="%s">%s</File>' % (md5(os.path.join(OUT, rel)), imp, escape(rel)))
    L.append('  </Files>')
    L.append('  <Actions>')
    L.append('    <OnModActivated>')
    for a in actions:
        L.append('      <UpdateDatabase>%s</UpdateDatabase>' % escape(a))
    L.append('    </OnModActivated>')
    L.append('  </Actions>')
    L.append('  <EntryPoints>')
    for typ, f, name, d in entry_points:
        L.append('    <EntryPoint type="%s" file="%s">' % (typ, escape(f)))
        L.append('      <Name>%s</Name>' % escape(name))
        L.append('      <Description>%s</Description>' % escape(d))
        L.append('    </EntryPoint>')
    L.append('  </EntryPoints>')
    L.append('</Mod>')
    with open(os.path.join(OUT, OUTNAME + '.modinfo'), 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('\n'.join(L) + '\n')

    # basename collisions among VFS-imported files (the VFS is flat)
    seen = {}
    for rel, imp in file_entries:
        if imp != '1':
            continue
        b = os.path.basename(rel).lower()
        h = md5(os.path.join(OUT, rel))
        if b in seen and seen[b][1] != h:
            print('NOTE: VFS name collision (different content, same as in the original mods):', rel, seen[b][0])
        seen.setdefault(b, (rel, h))

    shutil.copy2(os.path.join(ROOT, 'README.md'), os.path.join(OUT, 'README.md'))
    print('files: %d  actions: %d  entry points: %d' % (len(file_entries), len(actions), len(entry_points)))
    if '--zip' in sys.argv:
        z = os.path.join(ROOT, 'dist', OUTNAME + '.zip')
        if os.path.exists(z):
            os.remove(z)
        with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _, fnames in os.walk(OUT):
                for fn in fnames:
                    full = os.path.join(dirpath, fn)
                    zf.write(full, os.path.relpath(full, os.path.dirname(OUT)))
        print('zip:', z, os.path.getsize(z) // (1 << 20), 'MB')


if __name__ == '__main__':
    main()
