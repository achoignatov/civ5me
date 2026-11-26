# Capital landmarks: custom 3D models for Middle-earth cities

Each Middle-earth capital gets its own hand-built, high-resolution 3D landmark. A landmark is drawn as a purely
visual **tile improvement** that a script places on the capital's tile. The city's own art (houses, palace,
wonders) is never touched. This works reliably on every city and city-state, at any size tested so far.

**Current state (production):**

| City | Landmark | Art |
|---|---|---|
| Barad-dûr (Mordor's capital) | The Dark Tower as in the films, with the living Eye of Sauron: 242 units high, about two hexes wide | `vendor/landmarks/BaradDur5` (model `tools/landmarks/models/barad_dur_v5.py`) |
| Moria (the Goblins' capital) | v4 (first draft, awaiting the in-game test): the Walls of Moria under Caradhras, Celebdil and Fanuidhol; the Doors of Durin with a real additive ithildin glow; holly trees, the lake, the Watcher's swaying tentacles | `vendor/landmarks/Moria4` (model `tools/landmarks/models/moria_v4.py`) |
| Minas Tirith (Gondor's capital) | The seven circles cut into Mount Mindolluin, the prow, ~350 houses, the Citadel with the Tower of Ecthelion, the Court of the Fountain with the White Tree in blossom, the King's banner swinging in the wind; fits its own hex | `vendor/landmarks/MinasTirith` (model `tools/landmarks/models/minas_tirith.py`) |
| Edoras (Rohan's capital) | v2, after the film (`edoras.jpg`): a great crag with a jointed sheer face over dry tussock slopes, ~100 weathered longhouses under heavy thatch on its foot, the log wall with wall-walk, watchtowers and gatehouse, a stone stair up a spur to Meduseld's compound (antique-gold thatch, horse-head gables, lesser and spired halls), barrows with simbelmynë, the Snowbourn; the banner of the Mark swings. The plain is the game's own ground | `vendor/landmarks/Edoras` (model `tools/landmarks/models/edoras.py`) |
| Erebor (the Dwarves' capital) | First draft, after the films' prologue: the Lonely Mountain (snow-capped summit, gullies, arms), the Front Gate cut in a dressed face at the head of its valley (stepped portal, gable head with the gilded crown and seven stars, pilasters, a gallery of lit windows, blue-and-gold banners), the doors ajar with a warm additive gold glow, two colossal dwarf warriors leaning on their axes, the River Running from culverts under the threshold, a dwarven bridge, Ravenhill's guard-post, five braziers; fits its own hex | `vendor/landmarks/Erebor` (model `tools/landmarks/models/erebor.py`) |
| Isengard (Saruman's capital) | First draft: the Ring of Isengard cut by its gate (pylons, iron doors, banners of the White Hand), the plain torn into fiery pits with scaffolds, treadwheel cranes, chimneys, felled trees, the pillared road; Orthanc in black glossy stone (four faceted piers, knife-edged roots, fins, lancet windows, stair, door, balcony, four horns) and **Saruman on the summit** (7.8 high, above slimmer 7-unit horns: user's touch-up) with his staff (an additive white light) and the palantír glowing bright orange (after `screenshots/saruman.webp`); six pit fires; fits its own hex | `vendor/landmarks/Orthanc` (model `tools/landmarks/models/orthanc.py`) |
| The Shire (the Hobbits' capital) | v4, after `screenshots/bag-end.webp`: the tile is Bag End's garden at ground level with the white picket fence on it near the edge; the big Hill (covering the middle, where the stock houses stand) in ~1,600 cut-out tufts of painted grass and flowers, the great tree (branches and ~600 cut-out leaf clusters) and the brick chimney; the arched stone front, the green round door (10.8 across), two round windows glowing with flickering candlelight; stepping stones, sunflowers; **Bilbo and Gandalf sitting on the grass, puffing in turn** (Gandalf in a long grey robe draped to the grass, belt, scarf, bell sleeves, battered hat, gnarled staff; both with hands, faces and hair in detail): soft clouds rise before each face, spread and thin away in 1.6 s, every 4.3-5.5 s, never together (our animated model effect `puffs.py`); the chimney smoking | `vendor/landmarks/BagEnd` (model `tools/landmarks/models/bag_end.py`) |
| Entwood (city-state) | v2 (2026-11-25, after `screenshots/treebeard.webp`, the book and the film; v1's size and sway approved in game): **Treebeard** filling his hex, 110 high, with a high-resolution face (its own mesh: wrinkles, knots, crow's feet, irises) and a denser beard (its own mesh); Merry and Pippin small and detailed (seated ~7 units: jackets, waistcoats with buttons, open Lórien cloaks with leaf brooches, faces, curls, hands, toes) on his shoulders; gnarled limbs of twisted bark cords, a hunched trunk, the tall head with the heavy brow, deep eyes under hooded lids, the long knotted nose, the lichen beard "twiggy at the roots, mossy at the ends", ram-like horns and a crown of branches with leaves (some turning), hanging moss; seven-toed feet running on as roots over a forest floor of ferns. **He leans slowly back and forth like a tree in the wind** (24 s loop, the whole body bending from the ankles) | `vendor/landmarks/Treebeard` (model `tools/landmarks/models/treebeard.py`) |
| Smaug's Lair (city-state) | v5 (2026-11-26; gold v3 and dragon v4 approved in game): **the hoard of Erebor spilling into all six neighbouring hexes** with treasures and the Arkenstone; **Smaug asleep on it** after *The Hobbit* ch. 12 and the film: coiled over the heap, rolled to show the long pale gem-crusted belly (bare patch at the left breast), painted scales, horns, fangs, dorsal spikes; the right wing folded over his back, **the left wing spread and draped over the gold inside his coil like a bat's** (humerus from under the chest, forearm, thumb claw hooked in the coins, four bowed knuckled fingers, membranes in slack folds with branching veins, scalloped trailing edge, the last panel hanging from his flank). Six static models in one gr2 (no skinned part). Still for now | `vendor/landmarks/Smaug` (model `tools/landmarks/models/smaug.py`) |
| Every other city and city-state | Stock art | |

**Next:** the user's in-game verdict on Treebeard (does the blended multi-mesh skin draw and sway?), on Erebor (glow, braziers' size) and Orthanc (Saruman's readability, the staff's light, pit fires) and Bag End (chimney smoke size, window glow), then the other 7 capitals one at a time (§7).

**Size rule (user, 2026-11-25):** a landmark fits its OWN hex and does not overlap the neighbouring tiles (Moria v4
at ±54 looked overwhelming next to stock mountains; at `Scale` 0.134 it is "perfect"). New models are authored 1:1
in in-game units (`Scale` 0.25) with the row's `envelope` `hex_in` ≈ 33.6, so the build refuses anything outside the
hex. (Barad-dûr v5 still spans two hexes; it predates the rule.)

## 1. How it works

```
GameEvents (synced, every client)      MEC_LandmarkImprovements.lua            the city's plot
  PlayerCityFounded   ---------------> Sync(city): wanted landmark?  -------> Plot:SetImprovementType(id, -1)
  CityCaptureComplete                  differs from the plot? set it                  |
  SetPopulation, PlayerDoTurn          same? do nothing                               v
  game load: all cities                                                  improvement art rows (GameData)
                                                                         ArtDefine_Landmarks -> .fxsxml -> .gr2
native houses + buildings (engine, untouched) ---------------------->    drawn together on the city tile
```

- **Which city:** a city gets a landmark when its name **key** is in the row's `name_keys`, or a player typed one of
  its `aliases` (case-insensitive), or it is the **original capital** of the row's `civ` whatever it is called
  (`City:IsOriginalCapital()`, `City:GetOriginalOwner()`, both used by stock scripts). The last rule exists because
  the Third Age maps' dynamic city names rename a city by its founding tile (2026-11-25: the Hobbits' capital
  founded as The Shire became Bag End and lost its landmark). A captured capital keeps its landmark; any other city
  renamed away loses it on the next turn.
- **The improvement:** no gameplay (no yields, no Build row, `Permanent`), so workers can never build it. Founding and
  capture clear a city plot's improvement (`CvCity::init` in the game DLL), so the script re-applies it on those
  events and checks every city on every turn. Syncing twice changes nothing.
- **Multiplayer:** only `GameEvents` and synchronised data (players, plots, name keys), so every client sets the same
  plots. Never use the localised city name. Never index `GameInfo.X["TYPE"]` directly (it returns wrong rows for some
  of our types); build lookups by iterating the rows.
- **Logging:** every change writes `MEC_LMI: city <key> (x,y) <old> -> <new>, plot now reports <new>` to `Lua.log`.

**Why it is reliable.** Improvements are drawn by the game's landmark system, the one that draws farms, mines and
citadels: one model per plot, at the plot centre, with a fixed layout, built for tile-filling models (stock ones
span ±45 to ±78 units). The DLL hands a city plot's improvement to the renderer like any other plot's
(`CvPlot::updateLayout`). Putting models *inside* the city's own art (dummy buildings + `WonderDefines`, the
project's first approach, in git history up to commit `4f8d08e`) failed at random because that system packs small
pieces into fixed slots around randomly laid-out houses. Do not go back to it.

## 2. Files

| Piece | Where |
|---|---|
| Landmark table, switches, XML/Lua generators | `tools/landmarks/improvements.py` |
| In-game script (template; the table is inserted at build time) | `tools/landmarks/MEC_LandmarkImprovements.lua` |
| Pack integration (art copy, fxsxml, GameData + text, effect defines, Lua hook, checks) | `tools/build_dlc.py` → `build_landmark_improvements()` |
| Offline Lua test (strict mock of the game API) | `tools/landmarks/test_improvements.py` |
| The art that ships: the exact files that drew in game | `vendor/landmarks/<Model>/` (provenance in `SOURCE.md`) |
| Model scripts (Blender) | `tools/landmarks/models/*.py`; first-generation drafts of all 14 capitals and 26 city-states in `tools/capitals/models/*.py` |
| Blender driver, texture baking, gr2 writers | `tools/landmarks/build_models.py`, `bake.py`, `lmodel.py`, `beam.py`, `granim.py`; `tools/capitals/` (`blib.py` primitives, `gr2.py`, `civ5model.py`) |
| Reference art | `eye-as-it-should-be.png` (the film still Barad-dûr v5 follows) |

```
python3 tools/build.py && python3 tools/build_dlc.py --zip     # the pack, landmarks from vendor/ (no Blender needed)
build/venv/bin/python tools/landmarks/test_improvements.py      # Lua logic test (needs lupa in build/venv)
python3 tools/build_dlc.py --zip --no-landmarks                 # the pack without landmarks
```

The build fails if a vendored folder is missing, if an `.fxsxml` names a file (mesh, texture, animation, trigger,
decision tree) that is neither in the pack nor in the game's own `.fpk` packs, if a trigger fires an undefined
`ART_DEF_VEFFECT_MEC_*` effect or uses a bone missing from `BoneUsage`, if the rows change anything but the four
tables below, if a landmark has a Build row, or if a name key is not a real city name of the pack.

## 3. One landmark = these rows (generated from `improvements.IMPROVEMENTS`)

| Table | Row |
|---|---|
| `ArtDefine_LandmarkTypes` | `ART_DEF_IMPROVEMENT_MEC_LM_<KEY>`, LandmarkType `Improvement` |
| `ArtDefine_Landmarks` | Era `Any`, State `Constructed` and `Pillaged` → `MEC_LMI_<Key>.fxsxml`, `Scale`, LayoutHandler `SNAPSHOT`, ResourceType `ART_DEF_RESOURCE_ALL`, TerrainContour 1 |
| `ArtDefine_StrategicView` | TileType `Improvement`, an icon (`SV_Citadel.dds` for now) |
| `Improvements` | `IMPROVEMENT_MEC_LM_<KEY>`, `ArtDefineTag`, `Permanent`, no yields, text `TXT_KEY_IMPROVEMENT_MEC_LM_<KEY>` |

The `.fxsxml` is generated like the stock improvement files: one mesh plus its textures (`Anc_Citadel.fxsxml`). An
animated model adds its idle loop and the stock `LandmarkDecisionTree.ddtxml` (as `Oil_Rig.fxsxml` does); effects
are `TimedTrigger` files on bones listed in `BoneUsage` (as the stock gold mine does). Our effects
(`ART_DEF_VEFFECT_MEC_*`, `improvements.VIS_EFFECTS`) and the beam's model effect (`VIS_MODELS`) are written to
`MEDLC_LandmarkImprovements_VisEffects.xml` / `..._VisEffectModels.xml` and registered in the DLC package.

## 4. What the engine handles (proven in game)

| Item | Proven | Example |
|---|---|---|
| Size | 242 units high, about ±66 × ±74 (two hexes wide); every size from 61 to 242 drew on all 30 cities of one game | Barad-dûr v5 at `Scale` 0.125 to 0.5 |
| Detail | 30.5k vertices in one model part (the writer's limit is 32k: 16-bit indices); 2048² baked DIFF + 1024² SREF | Barad-dûr v5 tower |
| Animation | A skinned part (up to 32 bones) with a looping idle animation | The Eye, 18 bones, 6 s look-around loop |
| Effects | Particle fires and a model-effect beam on bones; they scale with the improvement's `Scale` | 8 Eye fires, a blaze, 6 braziers, the beam |
| Many at once | About 30 landmarks of several types in one game | Size-ladder test |
| Coexistence | Houses and city buildings draw with it | Both capitals |

**Not yet tried:** more than 242 high, more than one 32k part per model, several games in one game process.

**New in Moria v4 (untested in game until the user's test):**
- *The skinned part as a second 32k budget.* Its vertices can sit on two bones: `eyepivot` (moves) or `eyeroot`
  (never moves); a model module's `PIVOT_MATS` names the materials that move, the rest go on `eyeroot`
  (`bake.process` returns each vertex's material, `lmodel.write_building(eye=dict(still=...))`). Moria puts the
  massif in the static part and the doors, trees, lake and rocks in the skinned part; only the tentacles move.
- *A still, additive glowing picture* (`tools/landmarks/glow.py`): the lighthouse-beam FX material on our own quads,
  the picture in the texture's alpha, all tracks still. A rig bone with key `DOOR_GLOW` makes `build_models.py`
  write it; the preview draws it additively. Its quads are in the model's file units, so its VisEffect `Scale` is 1.0.
- *Bake options* (palette entries, opt-in): `tints` (regional colour discs), `snow` (z range + flatness),
  `cavity` (Cycles pointiness), `windows` (rows of dark windows on flat vertical walls, laid out along each wall
  from its normal; Minas Tirith's houses), and `b.ao_distance`.
- *Glow textures keep their lines in the distance:* `dds.write_dxt3(alpha_keep=...)` makes smaller mip levels keep
  part of the brightest alpha instead of the mean (Moria's doors read as a "glowing circle" without it).
- *Open ground is the game's own:* a model whose land is mostly flat (Edoras) sinks its plain just under z 0 and
  drops it (`terrain` `keep`), so the city's real terrain shows round it; only what rises above the ground is
  modelled (hill, barrows, river banks), and things on the plain stand on `max(height, 0)`. Water and roads that lie
  on the plain are ribbons a little above z 0 (the game's ground would hide anything below it).
- *More bake options:* `speckle` (dots of colour: flowers in grass, simbelmynë), and a `glow` with white lines and a
  tiny sigma paints a crisp emblem on a material (the white horse on Rohan's banner).
- *Realism lessons from Edoras v1 → v2 (user: "cartoonish... not a child's toy"):* match a reference image's palette
  (muted, weathered: dry tussock, dark timber, grey rock; no saturated greens or pure gold), its proportions (houses
  small beside the landmark's main mass), thickness (roofs as slabs with eaves and ridge rolls, footings into the
  slope), and density; drop toy-like props (blob trees, tube horses). `vcracks` (bake) paints vertical joints on
  steep rock; `uv_boost` keeps a small but important texture (the banner's emblem) sharp in a crowded atlas.
- *More than one glowing picture:* `build_models.GLOW_KEYS` lists the rig keys drawn by `glow.py` (`DOOR_GLOW`
  Moria, `GATE_GLOW` Erebor); each has its own model effect (`VIS_MODELS`) and file name (`glow_effect()['name']`),
  and its colour comes from `glow_effect()['tex_args']['color']` (Erebor: warm gold).
- *A skinned part where nothing moves* (Erebor: `PIVOT_MATS = set()`, `GAZE` fn = 0): everything is on the still
  bone; the part is just a second 32k budget that carries the effect bones (`fxglow`, `fire0..4`).
- *Orthanc:* a third glow key `STAFF_GLOW` (`MEC_OrthancGlow`: the staff's white light and the palantír's orange
  fire on one quad; a glow line may carry its own colour as a 6th item, `glow.texture`); pit fires reuse
  `TOWER_FIRE` (Barad-dûr's proven braziers); `loft_poly`/`wall_poly` in `orthanc.py` build hard-edged faceted solids
  from horizontal sections (counter-clockwise from above) and panels on an octagon's faces.
- *Bag End:* glow key `WINDOW_GLOW` (`MEC_BagEndGlow`); chimney smoke `CHIMNEY_SMOKE` = the stock BNW particle
  `ART_DEF_PEFFECT_DROMON_IDLE_SMOKE` at VisEffect `Scale` 1.2 (a guess); `PIPE_SMOKE` the same at 0.3 (v2's pipes). Holes are built in their own frame through
  `bag_end.Local` (a builder proxy that applies a matrix), each with a mound behind and a level yard cut in front of a
  curved front. Budget lesson: flat-shaded pieces roughly double their vertices when baked; `build_models.py` now
  prints both parts' counts before checking them.
- *Timed one-shot effects* (Bag End v4): a rig entry may carry a 5th item, trigger times in seconds of the idle loop;
  `build_models.py` then writes one trigger per time with `duration="0"` (as the stock artillery fires
  `CW_CANNON_SMOKE` at `time="0.844"`), so the effect plays once per loop. **Proven in game (v4 test): they re-fire
  on every loop.** A time may be `(time, duration)`: a lasting particle (Bag End: the gentle `DROMON_IDLE_SMOKE`)
  emitted for that long, then left to drift and fade. Lasting effects get `duration` = the loop's length (at least 10).
  Don't use musket/cannon smoke for gentle puffs: they flash and jet sideways ("ballistic missiles", the user).
- *Particle files:* `.psb` (binary, in the `.fpk` packs; the fpk record is `(0, 0, size, offset)`). Not edited yet:
  the stock particles are used as they are.
- *Animated positions* (`tools/landmarks/puffs.py`, Bag End's pipe puffs): a model effect whose bones MOVE, on
  `D3K8uC8u` position curves, the format of the stock oil rig's idle animation (`vendor/civ5/fx_oil_heavy_idlea.gr2`,
  extracted from the game's packs): a clamped quadratic B-spline, 8-bit knots (`OneOverKnotScaleTrunc` = the top 16
  bits of the float 255/duration) and 8-bit controls (byte * scale + offset per axis), one knot per tick. **Proven in
  game (v6): the cards move.** But the spline blends every jump over ~0.2 s, so a card hidden under the ground was
  seen rushing up to the face and back; v7 hides cards EDGE-ON (90 degrees about the vertical, on rotation curves; the
  game's camera never turns, so they have no width) and moves them to/from their hiding place only while edge-on.
  Scale is never animated (the stock game never does). `puffs.evaluate` + `granim.sample_quat_curve` decode written
  curves: always read the schedule back before shipping (it caught a late-binding bug that gave Gandalf Bilbo's
  times). The stock game has no gentle puff particle: musket/cannon smoke flash and jet ("ballistic missiles"), and
  the ship's idle smoke emitted for 0.8 s did not show.
- *Model effects of a module:* `model_effects(out_dir, k)` (files) and `preview_overlays(out_dir)` (additive quads
  for the preview) are picked up by `build_models.py`.
- *Cut-out SPRITES* (Bag End v8, `tools/landmarks/sprites.py` + `bake.py`): the building shader draws texels whose
  DIFF alpha is < 128 as holes (`AlphaMode 8`, `AlphaRef 128`, as in our template); the stock Hanging Gardens paint
  their palms and bushes this way. A palette entry `sprite=<RGBA image>` makes its faces cards: they keep their own
  0..1 coordinates (`b.sprite_uv`), skip the unwrap and all share one copy of the painting in a strip at the bottom
  quarter of the texture; `res.alpha` carries the cut-out into the DIFF (written with `alpha_keep` 0.35 so foliage
  doesn't erode in the far mip levels); `b.normal_fn` gives custom normals (leaves lit as one crown, grass lit like
  the lawn). Cards are single-sided, turned towards the game's camera (it never turns). Without sprite materials
  nothing changes. The preview cuts at 0.5 like the game. Untested in game: the cut-outs on our improvements.
- *Flickering light* (Bag End v9, `MEC_BagEndFlicker`): the same animated cards as the puffs (`puffs.write` with
  `tex_fn=puffs.glow_texture`): an additive card's width is its light, so yaw = acos(brightness) on the rotation
  curve (1,200 spans over 24 s) makes a candle: slow breathing, quick wavering, shimmer and a few gutterings, each
  window its own candle; the core drifts a little like a flame. The still glow (`MEC_BagEndGlow`) stays as the base.
- *Hiding the stock houses:* they can't be removed for one city (culture-wide, decided in the exe), but they are
  drawn at the game's ground level, so a landmark whose land stands above them (about 6 units) hides them, the way
  Erebor's mountain does. Bag End v3 raised its whole garden 6.5 for this; the user rejected the look ("a hexagonal
  pile of dirt"), so v4 is at ground level and only its big Hill covers the tile's middle. Units on the city tile are hidden the same way (their flags
  stay).
- *Grass tufts* (`bag_end.grass_tufts`): three-bladed tufts, each blade two faces a hair apart (one per side; the
  preview's red back-face marking then only shows as slivers at the edges).
- *Braziers* (`BRAZIER`): the Great Lighthouse fire at VisEffect `Scale` 0.35 (a guess; untested).
- *Blended skins of several meshes* (Treebeard, `lmodel.write_building(skins=...)`, `build_models.build_skins`;
  **proven in game 2026-11-25** with 3 meshes; v2 has 5): ONE skinned model `<name>_Eye` holding SEVERAL meshes (each its own
  32k budget and 2048 texture: `<name>_Eye`, `_Eye2`, `_Eye3` textures), every vertex with up to 4 bone weights
  (uint8, summing to 255) indexing the mesh's own BoneBindings, exactly the layout of the stock polder
  (`anc_polder.gr2`: 3 skinned meshes, 2 bindings each, weights 250/5). A module declares `SKIN_PARTS`, `BONES`
  (a chain), `weights(res, suffix)` (by height along the chain; by material for arms and riders) and `MOTIONS`
  (bone -> (pitch, roll, yaw) degrees over `LOOP`), written as D4nK16uC15u curves by `granim.rot_curve_value`
  and read back by `verify_motions`. `tools/landmarks/preview_lean.py` poses the WRITTEN files (decoded weights and
  curves) at several times and renders them: always run it before shipping a skin.
- *Relief bake* (`bake.py`, a builder's `b.relief`): a copy of the model, its bark faces subdivided ~64x and
  displaced by stretched Voronoi plates (F2-F1), is the source of the AO bake and of an object-space normal bake;
  the difference of its normals from those of an undisplaced copy with the same subdivision (not the game
  mesh's smooth normals: simple subdivision is faceted, which gave dark blotches), lit from the sun's side, multiplies
  the albedo. Fine bark
  fissures in the texture at no vertex cost (the building shader has no normal map).
- *Painted relief* (Smaug, `tools/landmarks/treasure.py` + `bake.py`): a palette entry `heightimg=dict(key, height,
  albedo, map='top'|'param', period, bump, cavity)` takes a painted colour map as the albedo and a height map that
  darkens the hollows and drives a Bump node; when any material has one, the bake compares object-space normals with
  and without the bumps (lit from the sun's side, a builder's `b.emboss`) and multiplies the albedo: every coin rim
  and scale edge in the texture, at no vertex cost. `map='top'` = object x, y / period (the coin heap, from above);
  `map='param'` = the builder's BODY COORDINATES (`b.param_uv[face] = [(u, v)]`, a `PARAM` UV layer; Smaug's
  `loft_param`: u = one scale row per perimeter / nv of length, v = angle / 2pi, so the scale count round the body
  is constant and scales shrink on the neck, the tail and the head). `treasure.dragon_scales` tiles in both
  directions (painted on an extended canvas and cropped).
- *A skinned model must not hang on the root bone alone* (Smaug v1, 2026-11-26: six meshes bound only to the root of
  a one-bone skeleton with no curve drew NOTHING in game, while the static part drew). Use a root plus a child bone
  carrying the vertices, driven by a real curve (`MOTIONS`), as Treebeard does, even when nothing should move yet.
- *Smaug v2 drew no skinned part either* (root + child bone with a curve, 5 meshes, spanning +-74): the cause is still
  open (left: a skinned part reaching beyond the own hex, or the number/size of textures). v3 ships the gold as ONE
  static mesh (`STATIC_PX` 2048); the dragon's meshes (`smaug.DRAGON_PARTS`) wait for a small skinned test.
- *Several static models in one landmark* (Smaug v4, `lmodel.write_static_models`, `build_models.build_statics`, a
  module's `STATIC_PARTS = [(suffix, build fn, px)]`, the first being `build`): the stencil plus one static model per
  part, each with its own mesh and texture (`<name>_2_DIFF.dds`...), no animation; the stock improvements are made
  this way (`anc_academy.gr2`: a dozen static models). Untested in game until the user's test.
- *Beyond the own hex:* Smaug's envelope `hex_in` 77.3 (about 2.3 hexes); the gold heightfield is split along the
  city's hexagon on ONE grid (the main heap a skinned mesh, the spills the static part), so the seam is exact.
- *Sprites:* `sprites.hanging_moss` (beard lichen / hanging moss, ragged top), `sprites.fern`,
  `leaf_cluster(autumn=)` (some leaves ochre and rust).
- *City-states:* a row's `minor` (a `MinorCivilizations` type) gives that city-state's ORIGINAL capital the
  landmark whatever it is called (`Player:IsMinorCiv`, `GetMinorCivType`); city-state name keys are checked
  against `MinorCivilization_CityNames`.
- *A skinned part with no effects* is fine: `rig()` may return `[]` (Minas Tirith: only its banner moves); the
  improvement row then has an animation but no `bones`/`trigger`, and its `FX_Triggers_*` file is not vendored.

## 5. Making a model

**Authoring rules:** in-game units, Z up, origin at the hex centre, ground at z = 0, −Y = south = towards the
camera. The hex is about ±34 to its flat sides (E/W); a landmark may spill over the neighbouring hexes. Leave room
for the houses round the tile centre, or let the landmark rise from a crag or wall around them. Keep each part under
32k vertices; use baked textures (`BAKE = True`, `BAKE_PX = 2048`) for the high-fidelity look.

1. Write the model module in `tools/landmarks/models/` (`barad_dur_v5.py` is the template: materials, crag, stages,
   an optional skinned part with `build_eye()`, `rig()`, `GAZE` and effect bones; `PREVIEW` camera views).
2. Add a row to `ALL_LANDMARKS` in `tools/landmarks/landmarks.py` like `BARAD_DUR5`: `scale=0.25` (the writer
   multiplies the vertices by 4), its own `envelope` (size and vertex limits the build enforces), `animated` if it
   has a skinned part, `enabled=False` (the row only drives the Blender build). New effect keys go in
   `landmarks.EFFECTS` (names) and `improvements.VIS_EFFECTS` (sizes).
3. Build and look at the previews:
   `blender -b --factory-startup -P tools/landmarks/build_models.py -- <module>` → `build/landmarks/out/`,
   previews in `build/landmarks/preview/<model>.png` (and `<model>_Eye.png`).
4. Convert every `.gr2` to the stock section layout with zeroed bounding boxes and vendor the files:
   ```
   build/venv/bin/python -c "import sys,json,os,shutil; sys.path[:0]=['tools/landmarks','tools/capitals']; import probes
   M='<Model>'; o='build/landmarks/out'; d='vendor/landmarks/'+M; os.makedirs(d, exist_ok=True)
   for f in json.load(open(o+'/MEC_LM_'+M+'.files.json'))['files']:
       if f.endswith('.fxsxml') and f.startswith('MEC_LM_') or '_Fire.' in f: continue
       (probes.to_stock_sections(o+'/'+f, d+'/'+f, zero_obb=True) if f.endswith('.gr2') else shutil.copy2(o+'/'+f, d))"
   ```
   and add a line to `vendor/landmarks/SOURCE.md`.
5. Add its row to `improvements.IMPROVEMENTS` (key, title, dir, gr2, textures, `scale`, name_keys, aliases;
   animation, bones and trigger only if it has them). `Scale` 0.25 = authored size; 0.5 = twice that.
6. Render test: set `ALL_CITIES` to its key (and `REVEAL_MAP = True`), build, install, check every city and
   city-state draws it. To compare sizes, add rows with other `Scale`s and list them in `TEST_LADDER`: every city
   without a landmark of its own gets one of them by map position `(5x + 3y) mod n`, logged per city.
7. Reset the switches (§6), build, check it appears only on its capital, commit.

## 6. Switches (`tools/landmarks/improvements.py`)

| Switch | Production | Use |
|---|---|---|
| `ALL_CITIES` | `None` | A landmark key: every city and city-state gets it (render test) |
| `TEST_LADDER` | `[]` | Landmark keys spread over every city without its own landmark (size test) |
| `CONTROLS` | `[]` | Control plots next to Mordor's capital: `(letter, key)` |
| `REVEAL_MAP` | `False` | `True` removes the fog for human players (render tests) |

## 7. The capitals

| Civ | Capital (name key) | Model | Status |
|---|---|---|---|
| Mordor | Barad-dûr (`MEC_BARAD_DUR`) | `barad_dur_v5.py`, `Scale` 0.5 | **Done** |
| Goblins | Moria (`MEC_MORIA`) | `moria_v4.py`, `Scale` 0.134 = fits its own hex (v3 `moria.py` kept in `vendor/landmarks/Moria`) | **v4 approved**, size final (2026-11-25); doors redesigned for legibility, awaiting test |
| Gondor | Minas Tirith (`MEC_MINAS_TIRITH`) | `minas_tirith.py`, `Scale` 0.25, fits its hex (started from the draft `tools/capitals/models/gondor.py`) | **Done** (user: "amazing") |
| Dwarves | Erebor (`MEC_EREBOR`) | `erebor.py`, `Scale` 0.25, fits its hex (ideas from the draft `dwarves.py`) | **First draft installed** 2026-11-25, awaiting test |
| Hobbits | The Shire (`MEC_THE_SHIRE`) | `bag_end.py` v4, `Scale` 0.25, fills its hex at ground level | **v4 installed** 2026-11-25, awaiting test |
| High Elves | Rivendell (`MEC_RIVENDELL`) | draft `high_elves.py` | To build |
| Wood Elves | Northern Mirkwood (`MEC_NORTHERN_MIRKWOOD`) | draft `wood_elves.py` | To build |
| Isengard | Isengard (`MEC_ISENGARD`) | `orthanc.py`, `Scale` 0.25, fits its hex (ideas from the draft `isengard.py`); Saruman on the summit | **First draft installed** 2026-11-25, awaiting test |
| Rohan | Edoras (`MEC_EDORAS`) | `edoras.py` v2, `Scale` 0.25, fits its hex (v1 from the draft `rohan.py` was "cartoonish": rebuilt after the film still `edoras.jpg`) | **Done** (user: "look incredible") |
| Arnor | Annúminas (`MEC_ANNUMINAS`) | draft `arnor.py` | To build |
| Angmar | Carn Dûm (`MEC_CARN_DUN`) | draft `angmar.py` | To build |
| Easterlings | Rhûn (`MEC_RHUN`) | draft `easterlings.py` | To build |
| Southrons | Harad (`MEC_HARAD`) | draft `southrons.py` | To build |
| Umbar | Umbar (`MEC_UMBAR`) | draft `umbar.py` | To build |
| (city-state) Smaug's Lair | Smaug's Lair (`TXT_KEY_CITYSTATE_MECS_SMAUGS_LAIR`, minor `MINOR_CIV_MECS_SMAUGS_LAIR`) | `smaug.py`, `Scale` 0.25, spills into the 6 neighbours | v1 and v2: the spills drew, the skinned model never did; v3 (the gold alone, one static mesh) drew, "PERFECT"; **v4: Smaug as four more static models, installed** 2026-11-26, awaiting test |
| (city-state) Entwood | Entwood (`TXT_KEY_CITYSTATE_MECS_ENTWOOD`, minor `MINOR_CIV_MECS_ENTWOOD`) | `treebeard.py`, `Scale` 0.25, fits its hex | v1 size and sway approved; **v2 (detail) installed** 2026-11-25, awaiting test |

The drafts in `tools/capitals/models/` are first-generation, low-detail scripts for the old pipeline: use them for
ideas and layout, and build the real model in `tools/landmarks/models/` by §5.

## 8. Legacy code (not used by the pack)

The first approach's code is still in the tree but is not built by default: dummy landmark buildings
(`tools/landmarks/landmarks.py` rows and `gamedata()`/`wonder_defines()`, `MEC_Landmarks.lua`,
`build_dlc.py --landmark-buildings`), its debug tools (`MEC_RedrawCities.lua`, `probes.py` probes,
`outrig_probe.py`, `tools/rendertest/`) and Barad-dûr v3/v4 (`vendor/landmarks/BaradDur`, `models/barad_dur.py`).
Its notes and measurements are in git history (`docs/CITY_MODELS.md` up to commit `4f8d08e`).
`landmarks.py` is still needed: `ALL_LANDMARKS` rows and `EFFECTS` drive the Blender build, and
`probes.to_stock_sections` converts every shipped `.gr2`.
