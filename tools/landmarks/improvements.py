"""Landmark IMPROVEMENTS (docs/LANDMARKS.md).

A landmark is a purely visual tile improvement that MEC_LandmarkImprovements.lua puts on a city's plot with
Plot:SetImprovementType. The city's own art (houses, buildings) is never touched. Improvement art is ordinary
ArtDefine_* database rows; effects use the DLC's VisEffect defines.

Which city gets which landmark: the city's name KEY (synchronised, the same with or without Dynamic City Naming),
or a name a player typed (aliases, case-insensitive). Every other city keeps stock art.

The art is vendored (vendor/landmarks/<Model>/): the exact files that drew in game, so the pack builds without
Blender. The Blender sources are tools/landmarks/models/*.py.

History of tests (all with this mechanism, 2026-11-24): Barad-dur v4 (static) on every city and city-state + control
plots (Elven Battle Tower, stock citadel art): all drew. Moria v3 on every city and city-state: all drew.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
VENDOR = os.path.join(ROOT, 'vendor', 'landmarks')

GAMEDATA_XML = 'MEDLC_LandmarkImprovements.xml'
TEXT_XML = 'MEDLC_Text_LandmarkImprovements.xml'
VISEFFECTS_XML = 'MEDLC_LandmarkImprovements_VisEffects.xml'
VISMODELS_XML = 'MEDLC_LandmarkImprovements_VisEffectModels.xml'
LUA = 'MEC_LandmarkImprovements.lua'

# One row per landmark.
#   key        -> IMPROVEMENT_MEC_LM_<key>, art tag ART_DEF_IMPROVEMENT_MEC_LM_<key>, fxsxml MEC_LMI_<Key>.fxsxml
#   dir        -> vendor/landmarks/<dir>: every file there is copied into the pack as-is
#   gr2 / textures -> what the generated .fxsxml names
#   scale      -> ArtDefine_Landmarks.Scale (in-game size = file size x scale; the hex is about +-32..41)
#   animation  -> (file, name) of an idle loop: played by the stock LandmarkDecisionTree (like the stock oil rig)
#   trigger    -> (ftsxml, model) TimedTrigger for effects on bones; bones = BoneUsage
#   name_keys / aliases -> which cities get it
#   civ        -> ...and that civilization's ORIGINAL capital, whatever it is called (2026-11-25: the Third Age maps'
#                 dynamic city names rename a capital by its founding tile, e.g. the Hobbits' to Bag End/Tuckborough)
#   minor      -> the same for a city-state (MinorCivilizations type): its original capital (Entwood: Treebeard)
BARAD_V5 = dict(dir='BaradDur5', gr2='MEC_LM_BaradDur5.gr2',
                textures=['Generic_Grey_8.dds', 'MEC_LM_BaradDur5_DIFF.dds', 'MEC_LM_BaradDur5_SREF.dds',
                          'MEC_LM_BaradDur5_Eye_DIFF.dds', 'MEC_LM_BaradDur5_Eye_SREF.dds'],
                animation=('MEC_LM_BaradDur5_Idle.gr2', 'Idle'),
                bones=['fxfire%d' % i for i in range(8)] + ['fxcore', 'fxbeam'] + ['fxtower%d' % i for i in range(6)],
                trigger=('FX_Triggers_MEC_LM_BaradDur5.ftsxml', 'MEC_LM_BaradDur5_Eye'))

IMPROVEMENTS = [
    # The Balrog of Moria (tools/landmarks/models/balrog.py, 2026-11-26; replaces Moria v4, the West-gate, kept in
    # vendor/landmarks/Moria4 but no longer packed): the upper half of the Balrog clawing his way out of a molten rift,
    # after the user's screenshots/balrog1.webp and balrog2.webp. Sculpted in signed distance fields (sdf.py), the
    # full sculpt baked into the textures; a hide of charred plates with fire in the seams. The rift (static), the
    # torso, both arms (the hands claw the ground in the neighbouring hexes) and the wings (half-spread) are static
    # models; the neck, head, ram horns and fangs are the skinned part (the head turns slowly, 12 s) carrying the
    # effects: animated flame tongues (flames.py: the crown of the head, the shoulders' mane, each arm; 4 x 30 cards),
    # the stock Great Lighthouse fire on the head (4), arms (6) and the rift (4), and the glow of the eyes and maw
    # (glow.py). Authored 1:1 in in-game units (Scale 0.25): about +-90 x (-62..+50), 100 high (the wings).
    # v2 (2026-11-26, after the first test: "too big; no face or horns; flames too quick, random flashes, crazy when
    # zoomed in"): Scale 0.125 (half: about +-45 x (-31..+25), 49 high); the head and horns a STATIC model (the skinned
    # head never drew, only the effects on its bones; the skinned part is now three stones carrying the bones);
    # ~115k vertices in all (v1 156k; Smaug's 112k draws); flames PERSISTENT (flames.Steady: always open, slow sway,
    # breathing width and bob on a 12 s loop, nothing turns edge-on) + a torso set (BALROG_BODY): 8 x 30 cards.
    # v3: the film's head (balrog1.webp); the flames' REST POSE is the finished fire (flames.write v3). v4 (user:
    # "one layer renders exactly as I want, another flickers massively when zoomed in: drop it; hide the stock
    # buildings"): the stock particle fires removed (only our flame tongues remain); he rises from a rocky mound 6.5
    # high in game (the stock houses, drawn at ground level, are under it), the magma pool on its top.
    dict(key='MORIA', civ='CIVILIZATION_MEC_GOBLINS', title='Moria', dir='Balrog',
         gr2='MEC_LM_Balrog.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_Balrog_DIFF.dds', 'MEC_LM_Balrog_SREF.dds'] +
                  ['MEC_LM_Balrog_%d_%s.dds' % (k, t) for k in (2, 3, 4, 5, 6) for t in ('DIFF', 'SREF')] +
                  ['MEC_LM_Balrog_Eye_DIFF.dds', 'MEC_LM_Balrog_Eye_SREF.dds'],
         animation=('MEC_LM_Balrog_Idle.gr2', 'Idle'),
         bones=['fxglow', 'fxcrown', 'fxheadf', 'fxmane', 'fxbody', 'fxarml', 'fxforel', 'fxarmr', 'fxforer'],
         trigger=('FX_Triggers_MEC_LM_Balrog.ftsxml', 'MEC_LM_Balrog_Eye'),
         scale=0.125,     # v2 (user: 'around half the size')
         name_keys=['TXT_KEY_CITY_NAME_MEC_MORIA'],
         aliases=['Moria', 'Khazad-dum', 'Khazad-dûm', 'Khazad Dum', 'Khazad Dûm']),
    # Minas Tirith (tools/landmarks/models/minas_tirith.py, 2026-11-25): Gondor's capital, fitting its own hex: the seven
    # walled circles cut into Mount Mindolluin, the prow, ~350 houses, bastions and staggered gates, the Citadel with
    # the Tower of Ecthelion and its silver spire, the Court of the Fountain with the White Tree in blossom, and the
    # King's banner swinging on its pole (the only moving part). Static part 28.1k vertices (mountain + the city's
    # stone), skinned part 25.7k (everything built on it, on the still bone eyeroot); 2 x 2048 baked. Authored 1:1 in
    # in-game units: about +-32.5 x (-36..+38) (inside the hex), 62 high with the banner.
    dict(key='MINAS_TIRITH', civ='CIVILIZATION_MEC_GONDOR', title='Minas Tirith', dir='MinasTirith',
         gr2='MEC_LM_MinasTirith.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_MinasTirith_DIFF.dds', 'MEC_LM_MinasTirith_SREF.dds',
                   'MEC_LM_MinasTirith_Eye_DIFF.dds', 'MEC_LM_MinasTirith_Eye_SREF.dds'],
         animation=('MEC_LM_MinasTirith_Idle.gr2', 'Idle'),
         scale=0.25,
         name_keys=['TXT_KEY_CITY_NAME_MEC_MINAS_TIRITH'],
         aliases=['Minas Tirith', 'MinasTirith', 'Minas Anor']),
    # Edoras v2 (tools/landmarks/models/edoras.py, 2026-11-25, after the user's film still edoras.jpg): a great crag
    # with a jointed sheer face and ledges over dry tussock slopes, ~100 weathered longhouses under heavy thatch on its
    # foot, the log wall with wall-walk, watchtowers and gatehouse, rail fences on the climbing road, a stone stair up a
    # spur to Meduseld's compound (antique-gold thatch, gold-bound posts, horse-head gables, lesser and spired halls),
    # the barrows with simbelmynë, the Snowbourn; the banner of the Mark swings (the only moving part). The plain is the
    # game's own ground. Static part 30.0k vertices (the land, stair, fences), skinned 28.9k (wall, buildings, banner).
    dict(key='EDORAS', civ='CIVILIZATION_MEC_ROHAN', title='Edoras', dir='Edoras',
         gr2='MEC_LM_Edoras.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_Edoras_DIFF.dds', 'MEC_LM_Edoras_SREF.dds',
                   'MEC_LM_Edoras_Eye_DIFF.dds', 'MEC_LM_Edoras_Eye_SREF.dds'],
         animation=('MEC_LM_Edoras_Idle.gr2', 'Idle'),
         scale=0.25,
         name_keys=['TXT_KEY_CITY_NAME_MEC_EDORAS'],
         aliases=['Edoras', 'Meduseld']),
    # Erebor (tools/landmarks/models/erebor.py, 2026-11-25), the Dwarves' capital, fitting its own hex: the Lonely
    # Mountain (snow-capped summit, ribbed gullies, arms; the gate valley between the southern ones), the Front Gate
    # cut in a dressed face (stepped portal, gable head with the gilded crown and seven stars, pilasters, a gallery of
    # lit windows, blue-and-gold banners), the doors ajar with a warm additive glow (model effect MEC_EreborGlow on
    # bone fxglow), two colossal dwarf warriors leaning on their axes, the River Running from culverts under the
    # threshold, a dwarven bridge, Ravenhill's guard-post; five braziers (fire0..4: gate x2, bridge x2, Ravenhill).
    # Nothing moves. Static part 23.1k vertices, skinned 10.7k; 2 x 2048 baked. About +-31.5 x (-37..+36), 59 high.
    dict(key='EREBOR', civ='CIVILIZATION_MEC_DWARVES', title='Erebor', dir='Erebor',
         gr2='MEC_LM_Erebor.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_Erebor_DIFF.dds', 'MEC_LM_Erebor_SREF.dds',
                   'MEC_LM_Erebor_Eye_DIFF.dds', 'MEC_LM_Erebor_Eye_SREF.dds'],
         animation=('MEC_LM_Erebor_Idle.gr2', 'Idle'),
         bones=['fxglow'] + ['fire%d' % i for i in range(5)],
         trigger=('FX_Triggers_MEC_LM_Erebor.ftsxml', 'MEC_LM_Erebor_Eye'),
         scale=0.25,
         name_keys=['TXT_KEY_CITY_NAME_MEC_EREBOR'],
         aliases=['Erebor', 'Lonely Mountain', 'The Lonely Mountain']),
    # Orthanc (tools/landmarks/models/orthanc.py, 2026-11-25), Isengard's capital, fitting its own hex: the Ring of
    # Isengard (rugged dark rock, higher in the north) cut by the gate (two pylons, an arch, iron doors, banners of the
    # White Hand); within, the plain torn into fiery pits with timber scaffolds, treadwheel cranes, furnace chimneys,
    # felled trees, a paved road with pillars and chains; Orthanc in black glossy stone (four faceted piers welded round
    # an octagonal core, knife-edged roots, fins, lancet windows, the stair, the door, a balcony, the four horns and the
    # blades between them) and Saruman the White on the summit with his staff and the palantir (user's reference
    # screenshots/saruman.webp). The staff's white light is an additive model effect (MEC_OrthancGlow on bone fxglow);
    # six pit fires (fire0..5, TOWER_FIRE). Nothing moves. Static part 26.8k vertices, skinned 15.8k; 2 x 2048 baked.
    # About +-30.5 x (-32..+34), 64 high.
    dict(key='ORTHANC', civ='CIVILIZATION_MEC_ISENGARD', title='Orthanc', dir='Orthanc',
         gr2='MEC_LM_Orthanc.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_Orthanc_DIFF.dds', 'MEC_LM_Orthanc_SREF.dds',
                   'MEC_LM_Orthanc_Eye_DIFF.dds', 'MEC_LM_Orthanc_Eye_SREF.dds'],
         animation=('MEC_LM_Orthanc_Idle.gr2', 'Idle'),
         bones=['fxglow'] + ['fire%d' % i for i in range(6)],
         trigger=('FX_Triggers_MEC_LM_Orthanc.ftsxml', 'MEC_LM_Orthanc_Eye'),
         scale=0.25,
         name_keys=['TXT_KEY_CITY_NAME_MEC_ISENGARD'],
         aliases=['Isengard', 'Orthanc', 'Angrenost']),
    # Bag End v4 (tools/landmarks/models/bag_end.py, 2026-11-25, after the user's screenshots/bag-end.webp): the tile
    # is Bag End's garden at ground level, the white picket fence on it near the tile's edge (gate in the south-east);
    # the big Hill (25 high, covering the tile's middle and the stock houses there) in tufts of grass, the great tree,
    # the brick chimney; the arched stone front, the green round door (10.8 across), two round windows with a warm
    # additive glow (MEC_BagEndGlow on bone fxglow); stepping stones, sunflowers; Bilbo and Gandalf (x3) sitting on the
    # grass. Smoke: the chimney smokes (smoke0, CHIMNEY_SMOKE); the pipes puff (fxpuff, PIPE_PUFFS = MEC_BagEndPuffs,
    # tools/landmarks/puffs.py): soft cloud cards that rise before each face, spread and thin away in 1.6 s, every
    # 4.3-5.5 s, the two friends never together (24 s schedule). The landmark itself does not move. v8: the great
    # tree (branches + ~600 cut-out leaf-cluster cards) and ~1,600 cut-out grass tufts: painted sprites with alpha,
    # drawn like the stock Hanging Gardens' plants (BuildingShader, AlphaRef 128); figures as before. v9: candlelight
    # flickers in the windows (fxflick, WINDOW_FLICKER = MEC_BagEndFlicker: puffs.py glow cards, width = light), the
    # windows lie along the curved front (v10). v11: Gandalf in a long grey robe (no trousers), Bilbo and he in more
    # detail (hands, faces, hair, clothes). Static
    # part 29.8k vertices, skinned 29.3k; 2 x 2048 baked. 51 high (the tree).
    dict(key='BAG_END', civ='CIVILIZATION_MEC_HOBBITS', title='Bag End', dir='BagEnd',
         gr2='MEC_LM_BagEnd.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_BagEnd_DIFF.dds', 'MEC_LM_BagEnd_SREF.dds',
                   'MEC_LM_BagEnd_Eye_DIFF.dds', 'MEC_LM_BagEnd_Eye_SREF.dds'],
         animation=('MEC_LM_BagEnd_Idle.gr2', 'Idle'),
         bones=['fxglow', 'smoke0', 'fxpuff', 'fxflick'],
         trigger=('FX_Triggers_MEC_LM_BagEnd.ftsxml', 'MEC_LM_BagEnd_Eye'),
         scale=0.25,
         name_keys=['TXT_KEY_CITY_NAME_MEC_THE_SHIRE'],
         aliases=['The Shire', 'Shire', 'Bag End', 'Bag-End']),
    # Treebeard with Merry and Pippin (tools/landmarks/models/treebeard.py, 2026-11-25, after the user's
    # screenshots/treebeard.webp, the book and the film): the landmark of the city-state of Entwood. The forest floor
    # (root mound, seven-toed feet running on as roots, ferns, stones) is static; Treebeard is ONE skinned model of
    # five meshes (bark body / the head and face at high resolution / crown, horns and leaves / lichen beard and
    # hanging moss / Merry and Pippin, small and detailed: v2 after the user's first test), every vertex weighted along
    # a chain of bones from the ankles up: the whole Ent bends slowly like a tree in the wind (24 s loop, two sways back
    # and forth and a side roll; the top travels about 7 units; user: "size and animation perfect"). Static part
    # 14.9k vertices, skins 23.1k / 24.4k / 19.4k / 23.0k / 31.6k; 5 x 2048 + 1024 baked (bark relief baked in). About
    # +-32 x +-34, 110 high. No effects. minor = the city-state's ORIGINAL capital gets it whatever it is called.
    dict(key='TREEBEARD', minor='MINOR_CIV_MECS_ENTWOOD', title='Treebeard', dir='Treebeard',
         gr2='MEC_LM_Treebeard.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_Treebeard_DIFF.dds', 'MEC_LM_Treebeard_SREF.dds',
                   'MEC_LM_Treebeard_Eye_DIFF.dds', 'MEC_LM_Treebeard_Eye_SREF.dds',
                   'MEC_LM_Treebeard_Eye2_DIFF.dds', 'MEC_LM_Treebeard_Eye2_SREF.dds',
                   'MEC_LM_Treebeard_Eye3_DIFF.dds', 'MEC_LM_Treebeard_Eye3_SREF.dds',
                   'MEC_LM_Treebeard_Eye4_DIFF.dds', 'MEC_LM_Treebeard_Eye4_SREF.dds',
                   'MEC_LM_Treebeard_Eye5_DIFF.dds', 'MEC_LM_Treebeard_Eye5_SREF.dds'],
         animation=('MEC_LM_Treebeard_Idle.gr2', 'Idle'),
         scale=0.25,
         name_keys=['TXT_KEY_CITYSTATE_MECS_ENTWOOD'],
         aliases=['Entwood', 'Treebeard']),
    # Smaug's Lair (tools/landmarks/models/smaug.py, 2026-11-26, first draft): the hoard of Erebor with Smaug asleep on
    # it. THE FIRST LANDMARK REACHING INTO THE NEIGHBOURING HEXES: the main heap (19 high) on the city's hex, a floor
    # of gold with lobes flowing into all six neighbours (fading into their ground, loose coins round the edges). Coins
    # and scales are PAINTED RELIEF (tools/landmarks/treasure.py + bake.py heightimg): a coin heap mapped from above,
    # a scale sheet in body coordinates; ~95 treasures (goblets, crowns, swords, shields, helms, chests, gems, the
    # Arkenstone), ~700 loose coins. Smaug: neck, body and tail lofted along a spine coiled over the heap, folded wings
    # with membranes, tucked hind legs, horns, teeth, dorsal spikes. Static part 24.3k vertices (the spills); one
    # skinned model of five meshes on a child bone driven by a still curve (Treebeard's proven layout: the first test,
    # six meshes bound only to the root of a one-bone skeleton without a curve, drew the static part only). v2: the
    # central heap 25 high, Smaug bigger, the film's umber-red hide with ember flecks, the crest round his head.
    # v3 (2026-11-26, after the v2 test drew the spills again but still not the skinned model): THE GOLD ALONE, AS ONE
    # STATIC MESH like every proven static landmark: the central heap (24 high, lumpy) and the spills are one height
    # field and one coin texture (2048), 120 loose coins, 26 treasures; 29.5k vertices. The dragon comes later.
    # v4 (2026-11-26, the user: "the gold piles are PERFECT"): Smaug asleep on the heap, as FOUR MORE STATIC MODELS in
    # the same file (gold, body, head, limbs, belly crust; one texture each; the stock improvements are built this way):
    # The Hobbit ch. 12, "turned partly on one side ... his long pale belly crusted with gems and fragments of gold",
    # the bare patch in the hollow of his left breast, "wings folded like an immeasurable bat", the huge coiled tail with
    # its tip by his snout; the film's wyvern anatomy and umber-red hide with ember flecks (screenshots/smaug-awake.png).
    # About +-73 x (-83..+77), 42 high.
    dict(key='SMAUG', minor='MINOR_CIV_MECS_SMAUGS_LAIR', title="Smaug's Lair", dir='Smaug',
         gr2='MEC_LM_Smaug.gr2',
         textures=['Generic_Grey_8.dds', 'MEC_LM_Smaug_DIFF.dds', 'MEC_LM_Smaug_SREF.dds'] +
                  ['MEC_LM_Smaug_%d_%s.dds' % (k, t) for k in (2, 3, 4, 5) for t in ('DIFF', 'SREF')],
         scale=0.25,
         name_keys=['TXT_KEY_CITYSTATE_MECS_SMAUGS_LAIR'],
         aliases=["Smaug's Lair", 'Smaug']),
    # Barad-dur v5, the film's tower (tools/landmarks/models/barad_dur_v5.py, 2026-11-24 night): crag + five-stage
    # spire with clinging turrets + the two-pronged crown, baked 2048, 30.5k vertices; a skinned Eye (6.3k vertices)
    # with the 6 s look-around loop, a ring of fire + a blaze round it, the searching beam, six braziers on the
    # tower. Authored in in-game units and written x4, so Scale 0.25 = 1:1 (about +-33 x +-37, 121 high).
    # PRODUCTION SIZE x2 (user, 2026-11-24, after the size-ladder test drew every size on every city): Scale 0.5,
    # about +-66 x +-74 (two hexes), 242 high; the fires and beam grow with it.
    # (v3, the Eye of the first release, is kept in vendor/landmarks/BaradDur but no longer packed.)
    dict(BARAD_V5, key='BARAD_DUR', civ='CIVILIZATION_MEC_MORDOR', title='Barad-dûr', scale=0.5,
         name_keys=['TXT_KEY_CITY_NAME_MEC_BARAD_DUR'],
         aliases=['Barad Dur', 'Barad-dur', 'Barad-dûr', 'Barad Dûr', 'Baraddur']),
    # The size-ladder test rows (x0.5 / x1.5 / x2 on every other city, 2026-11-24) are described in docs/LANDMARKS.md
    # (all drew); add rows like dict(BARAD_V5, key='BARAD_X150', title=..., scale=0.375, name_keys=[], aliases=[])
    # and list them in TEST_LADDER to repeat it.
]

# Effects used by the triggers above (VisEffectInfoDefines / VisEffectModelDefines in the DLC package).
# Values as tuned for Barad-dur v3 in the old city-art path (tools/landmarks/landmarks.py EFFECTS, 2026-11-22).
VIS_EFFECTS = [
    # (name, rotation x, scale, particle effect or None, model effect or None)
    # v5: the Eye is 2.56x v3's (EX 3.2 vs 1.25), so its fires are 2.5x; the beam reaches the land from z 110 at
    # 38 degrees (~180 units: the stock beam is ~6.2 units per scale unit); braziers on the tower flanges.
    ('ART_DEF_VEFFECT_MEC_EYE_FIRE', 90.0, 1.0, 'ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE', None),
    ('ART_DEF_VEFFECT_MEC_EYE_BLAZE', 90.0, 2.5, 'ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE', None),
    ('ART_DEF_VEFFECT_MEC_TOWER_FIRE', 90.0, 0.6, 'ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE', None),
    ('ART_DEF_VEFFECT_MEC_EYE_BEAM', 0.0, 29.0, None, 'ART_DEF_MEFFECT_MEC_EYE_BEAM'),
    # (Moria v4's ithildin glow ART_DEF_VEFFECT_MEC_DOOR_GLOW left with Moria v4: the Balrog replaced it 2026-11-26)
    # Erebor: the Front Gate's gold light (file units, Scale 1.0) and its braziers (a guess, about half the tower's
    # braziers of Barad-dur in file units; tune after the in-game test)
    ('ART_DEF_VEFFECT_MEC_GATE_GLOW', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_GATE_GLOW'),
    ('ART_DEF_VEFFECT_MEC_BRAZIER', 90.0, 0.35, 'ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE', None),
    # Orthanc: the white light of Saruman's staff (file units, Scale 1.0)
    ('ART_DEF_VEFFECT_MEC_STAFF_GLOW', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_STAFF_GLOW'),
    # Bag End: the warm light of its windows (file units, Scale 1.0); chimney smoke = the stock idle smoke of the Dromon
    # (BNW particle), its size a guess (tune after the in-game test)
    ('ART_DEF_VEFFECT_MEC_WINDOW_GLOW', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_WINDOW_GLOW'),
    ('ART_DEF_VEFFECT_MEC_CHIMNEY_SMOKE', 90.0, 2.4, 'ART_DEF_PEFFECT_DROMON_IDLE_SMOKE', None),
    # Bag End: the puffs of Bilbo's and Gandalf's pipes: our animated model effect (tools/landmarks/puffs.py, soft
    # cloud cards in file units, Scale 1.0). (v4's musket smoke "like ballistic missiles"; v5's ship smoke did not show.)
    ('ART_DEF_VEFFECT_MEC_PIPE_PUFFS', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_PIPE_PUFFS'),
    # Bag End: candlelight flickering in its windows (puffs.py cards: width = light), file units
    ('ART_DEF_VEFFECT_MEC_WINDOW_FLICKER', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_WINDOW_FLICKER'),
    # the Balrog: the glow of the eyes and maw and the animated flame tongues are model effects in file units (Scale
    # 1.0); the stock Great Lighthouse fire on the head (blaze), arms and the rift, sized after the Eye's (blaze 2.5
    # at improvement Scale 0.5 round a ~21-unit Eye; the Balrog's head is ~30 units, at Scale 0.25). Tune in game.
    ('ART_DEF_VEFFECT_MEC_BALROG_GLOW', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_BALROG_GLOW'),
    ('ART_DEF_VEFFECT_MEC_BALROG_CROWN', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_BALROG_CROWN'),
    ('ART_DEF_VEFFECT_MEC_BALROG_MANE', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_BALROG_MANE'),
    ('ART_DEF_VEFFECT_MEC_BALROG_ARML', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_BALROG_ARML'),
    ('ART_DEF_VEFFECT_MEC_BALROG_ARMR', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_BALROG_ARMR'),
    ('ART_DEF_VEFFECT_MEC_BALROG_HEAD', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_BALROG_HEAD'),
    ('ART_DEF_VEFFECT_MEC_BALROG_BODY', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_BALROG_BODY'),
    ('ART_DEF_VEFFECT_MEC_BALROG_FOREL', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_BALROG_FOREL'),
    ('ART_DEF_VEFFECT_MEC_BALROG_FORER', 0.0, 1.0, None, 'ART_DEF_MEFFECT_MEC_BALROG_FORER'),
    # (v4: the stock lighthouse fires BALROG_BLAZE / FIRE / PIT were removed: they flickered wildly when zoomed in)
]
# fScrollTime = a model effect's LOOP LENGTH: the game restarts the effect every fScrollTime seconds (the stock XCOM
# trooper effects use their animations' lengths, 2.56-3.26 s). Ours were all 1.0 (copied from the beam), so the
# Balrog's fire restarted every second: the scroll and its fade jumped back each second = the once-a-second surge in
# the user's video (screenshots/flame2.mp4), and earlier the 6-12 s flame animations were cut off every second (the
# "crazy" flicker). A row's optional 3rd item is the loop length; the fire gets a long one (it never visibly restarts).
BALROG_FIRE_LOOP = 600.0
VIS_MODELS = [('ART_DEF_MEFFECT_MEC_EYE_BEAM', 'MEC_EyeBeam.fxsxml'),      # file in vendor/landmarks/BaradDur5
              ('ART_DEF_MEFFECT_MEC_GATE_GLOW', 'MEC_EreborGlow.fxsxml'),  # file in vendor/landmarks/Erebor
              ('ART_DEF_MEFFECT_MEC_STAFF_GLOW', 'MEC_OrthancGlow.fxsxml'),  # file in vendor/landmarks/Orthanc
              ('ART_DEF_MEFFECT_MEC_WINDOW_GLOW', 'MEC_BagEndGlow.fxsxml'),  # file in vendor/landmarks/BagEnd
              ('ART_DEF_MEFFECT_MEC_PIPE_PUFFS', 'MEC_BagEndPuffs.fxsxml'),  # file in vendor/landmarks/BagEnd
              ('ART_DEF_MEFFECT_MEC_WINDOW_FLICKER', 'MEC_BagEndFlicker.fxsxml'),  # file in vendor/landmarks/BagEnd
              ('ART_DEF_MEFFECT_MEC_BALROG_GLOW', 'MEC_BalrogGlow.fxsxml'),        # files in vendor/landmarks/Balrog
              ('ART_DEF_MEFFECT_MEC_BALROG_CROWN', 'MEC_BalrogCrown.fxsxml', BALROG_FIRE_LOOP),
              ('ART_DEF_MEFFECT_MEC_BALROG_MANE', 'MEC_BalrogMane.fxsxml', BALROG_FIRE_LOOP),
              ('ART_DEF_MEFFECT_MEC_BALROG_ARML', 'MEC_BalrogArmL.fxsxml', BALROG_FIRE_LOOP),
              ('ART_DEF_MEFFECT_MEC_BALROG_ARMR', 'MEC_BalrogArmR.fxsxml', BALROG_FIRE_LOOP),
              ('ART_DEF_MEFFECT_MEC_BALROG_HEAD', 'MEC_BalrogHead.fxsxml', BALROG_FIRE_LOOP),
              ('ART_DEF_MEFFECT_MEC_BALROG_BODY', 'MEC_BalrogBody.fxsxml', BALROG_FIRE_LOOP),
              ('ART_DEF_MEFFECT_MEC_BALROG_FOREL', 'MEC_BalrogForeL.fxsxml', BALROG_FIRE_LOOP),
              ('ART_DEF_MEFFECT_MEC_BALROG_FORER', 'MEC_BalrogForeR.fxsxml', BALROG_FIRE_LOOP)]

# ----- test switches (all off in a release) -------------------------------------------------------------------
# A key of IMPROVEMENTS: EVERY city and city-state gets that landmark, ignoring the names (render tests).
ALL_CITIES = None
# Keys of IMPROVEMENTS: every city WITHOUT a landmark of its own gets one of them, picked by its map position
# ((5 x + 3 y) mod count, see MEC_LandmarkImprovements.lua; logged per city). [] = off.
TEST_LADDER = []
# Control plots next to the anchor capital: (letter, key). Test 1 used A Barad-dur / B Elven Battle Tower /
# C stock citadel art (all drew); those rows were removed after the test.
CONTROLS = []
ANCHOR_CIV = 'CIVILIZATION_MEC_MORDOR'      # fallback: the first human player's capital
# Fog of war off for human teams.
REVEAL_MAP = True                           # True for render tests; False for a release


def improvement(row):
    return 'IMPROVEMENT_MEC_LM_' + row['key']


def art_tag(row):
    return 'ART_DEF_IMPROVEMENT_MEC_LM_' + row['key']


def own_fxsxml(row):
    return 'MEC_LMI_%s.fxsxml' % row['key'].title().replace('_', '')


def src_dir(row):
    return os.path.join(VENDOR, row['dir'])


def fxsxml_text(row):
    """Like the stock improvement files: mesh + textures; an animated model gets its idle animation and the stock
    LandmarkDecisionTree (Oil_Rig.fxsxml); effects are TimedTriggers on bones (the stock gold mine)."""
    L = ['<Asset>', '  <Mesh file="%s" source="Max" />' % row['gr2']]
    if row.get('animation'):
        L.append('  <Animation file="%s" name="%s" ec="1000" source="Max" layer="None" />' % row['animation'])
    L += ['  <Texture file="%s" source="Max" />' % t for t in row['textures']]
    if row.get('bones'):
        L += ['  <BoneUsage>'] + ['    <Bone name="%s" />' % b for b in row['bones']] + ['  </BoneUsage>']
    if row.get('trigger'):
        L.append('  <TimedTrigger file="%s" source="Tool" model="%s" state="0,1,2,3" />' % row['trigger'])
    if row.get('animation'):
        L.append('  <DecisionTree file="LandmarkDecisionTree.ddtxml" source="Tool" />')
    L.append('</Asset>')
    return '\n'.join(L) + '\n'


def _x(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def gamedata():
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<!-- Middle-earth landmark improvements: purely visual, placed only by MEC_LandmarkImprovements.lua '
         '(no Build row, no yields) -->',
         '<GameData>', '\t<ArtDefine_LandmarkTypes>']
    for r in IMPROVEMENTS:
        L.append('\t\t<Row><Type>%s</Type><LandmarkType>Improvement</LandmarkType><FriendlyName>%s</FriendlyName></Row>'
                 % (art_tag(r), _x(r['title'])))
    L += ['\t</ArtDefine_LandmarkTypes>', '\t<ArtDefine_Landmarks>']
    for r in IMPROVEMENTS:
        for state in ('Constructed', 'Pillaged'):
            L.append('\t\t<Row><Era>Any</Era><State>%s</State><Scale>%s</Scale><ImprovementType>%s</ImprovementType>'
                     '<LayoutHandler>SNAPSHOT</LayoutHandler><ResourceType>ART_DEF_RESOURCE_ALL</ResourceType>'
                     '<Model>%s</Model><TerrainContour>1</TerrainContour></Row>'
                     % (state, r['scale'], art_tag(r), own_fxsxml(r)))
    L += ['\t</ArtDefine_Landmarks>', '\t<ArtDefine_StrategicView>']
    for r in IMPROVEMENTS:
        L.append('\t\t<Row><StrategicViewType>%s</StrategicViewType><TileType>Improvement</TileType>'
                 '<Asset>SV_Citadel.dds</Asset></Row>' % art_tag(r))
    L += ['\t</ArtDefine_StrategicView>', '\t<Improvements>']
    for r in IMPROVEMENTS:
        t = improvement(r)
        L.append('\t\t<Row>')
        for k, v in (('Type', t), ('Description', 'TXT_KEY_' + t), ('Civilopedia', 'TXT_KEY_' + t + '_HELP'),
                     ('Help', 'TXT_KEY_' + t + '_HELP'), ('ArtDefineTag', art_tag(r)),
                     ('Permanent', 'true'), ('PillageGold', 0),
                     ('PortraitIndex', 35), ('IconAtlas', 'TERRAIN_ATLAS')):     # the citadel icon
            L.append('\t\t\t<%s>%s</%s>' % (k, _x(str(v)), k))
        L.append('\t\t</Row>')
    L += ['\t</Improvements>', '</GameData>']
    return '\n'.join(L) + '\n'


def text():
    L = ['<?xml version="1.0" encoding="utf-8"?>', '<GameData>', '\t<Language_en_US>']
    for r in IMPROVEMENTS:
        t = improvement(r)
        L.append('\t\t<Row Tag="TXT_KEY_%s"><Text>%s (landmark)</Text></Row>' % (t, _x(r['title'])))
        L.append('\t\t<Row Tag="TXT_KEY_%s_HELP"><Text>The landmark of %s. Purely visual: no effect on the game.'
                 '</Text></Row>' % (t, _x(r['title'])))
    L += ['\t</Language_en_US>', '</GameData>']
    return '\n'.join(L) + '\n'


def vis_effects():
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<VisEffectArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xsi:noNamespaceSchemaLocation="Civ5ArtDefines_VisEffects.xsd">']
    for name, rotx, scale, particle, model in VIS_EFFECTS:
        L += ['\t<VisEffectArtInfo>', '\t\t<Name>%s</Name>' % name, '\t\t<Transform>',
              '\t\t\t<Translation x="0.0" y="0.0" z="0.0"/>', '\t\t\t<Rotation x="%.1f" y="0.0" z="0.0"/>' % rotx,
              '\t\t\t<Scale>%s</Scale>' % scale, '\t\t</Transform>',
              '\t\t<fBaseDuration>0.01</fBaseDuration>', '\t\t<fBaseDurationScale>1.0</fBaseDurationScale>']
        if particle:
            L += ['\t\t<ParticleEffects>', '\t\t\t<ParticleEffect>', '\t\t\t\t<Name>%s</Name>' % particle,
                  '\t\t\t</ParticleEffect>', '\t\t</ParticleEffects>']
        if model:
            L += ['\t\t<ModelEffects>', '\t\t\t<ModelEffect>', '\t\t\t\t<Name>%s</Name>' % model,
                  '\t\t\t</ModelEffect>', '\t\t</ModelEffects>']
        L.append('\t</VisEffectArtInfo>')
    L.append('</VisEffectArtInfos>')
    return '\n'.join(L) + '\n'


def vis_effect_models():
    L = ['<?xml version="1.0" encoding="utf-8"?>',
         '<VisEffectModelArtInfos xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
         'xmlns:xsd="http://www.w3.org/2001/XMLSchema">']
    for row in VIS_MODELS:
        name, fx = row[:2]
        loop = row[2] if len(row) > 2 else 1.0
        L += ['\t<VisEffectModelArtInfo>', '\t\t<Name>%s</Name>' % name, '\t\t<File>%s</File>' % fx,
              '\t\t<fScale>1.0</fScale>', '\t\t<fScrollTime>%s</fScrollTime>' % loop, '\t</VisEffectModelArtInfo>']
    L.append('</VisEffectModelArtInfos>')
    return '\n'.join(L) + '\n'


def lua_table():
    """Replaces the -- @@LANDMARK_TABLE@@ line of MEC_LandmarkImprovements.lua."""
    def s(v):
        return '"%s"' % v if v is not None else 'false'

    def q(v):   # Lua string literal (UTF-8 kept)
        return '"%s"' % v.replace('\\', '\\\\').replace('"', '\\"')
    defs = ', '.join('{ Improvement = %s, Keys = { %s }, Aliases = { %s }, Civ = %s, Minor = %s }' % (
        q(improvement(r)), ', '.join(q(k) for k in r['name_keys']), ', '.join(q(a) for a in r['aliases']),
        q(r['civ']) if r.get('civ') else 'false', q(r['minor']) if r.get('minor') else 'false')
        for r in IMPROVEMENTS)
    all_cities = next((improvement(r) for r in IMPROVEMENTS if r['key'] == ALL_CITIES), None)
    return ('g_LandmarkDefs = { %s }\n' % defs
            + 'g_AllCities = %s\n' % s(all_cities)
            + 'g_Ladder = { %s }\n' % ', '.join('"IMPROVEMENT_MEC_LM_%s"' % k for k in TEST_LADDER)
            + 'g_Controls = { %s }\n' % ', '.join('{ "%s", "IMPROVEMENT_MEC_LM_%s" }' % (c, k) for c, k in CONTROLS)
            + 'g_AnchorCiv = %s\n' % s(ANCHOR_CIV)
            + 'g_RevealMap = %s' % ('true' if REVEAL_MAP else 'false'))
