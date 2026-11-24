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
| Every other city and city-state | Stock art | |

**Next:** the user's in-game verdict on Minas Tirith, then the other 11 capitals one at a time (§7).

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

- **Which city:** a city gets a landmark when its name **key** is in the row's `name_keys` (the same with or without
  Dynamic City Naming), or a player typed one of its `aliases` (case-insensitive). The landmark follows the name,
  not the owner: a captured Barad-dûr keeps the Eye; a city renamed away loses it on the next turn.
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
| Gondor | Minas Tirith (`MEC_MINAS_TIRITH`) | `minas_tirith.py`, `Scale` 0.25, fits its hex (started from the draft `tools/capitals/models/gondor.py`) | **Installed**, awaiting test |
| Dwarves | Erebor (`MEC_EREBOR`) | draft `dwarves.py` | To build |
| Hobbits | The Shire (`MEC_THE_SHIRE`) | draft `hobbits.py` (Bag End) | To build |
| High Elves | Rivendell (`MEC_RIVENDELL`) | draft `high_elves.py` | To build |
| Wood Elves | Northern Mirkwood (`MEC_NORTHERN_MIRKWOOD`) | draft `wood_elves.py` | To build |
| Isengard | Isengard (`MEC_ISENGARD`) | draft `isengard.py` | To build |
| Rohan | Edoras (`MEC_EDORAS`) | draft `rohan.py` | To build |
| Arnor | Annúminas (`MEC_ANNUMINAS`) | draft `arnor.py` | To build |
| Angmar | Carn Dûm (`MEC_CARN_DUN`) | draft `angmar.py` | To build |
| Easterlings | Rhûn (`MEC_RHUN`) | draft `easterlings.py` | To build |
| Southrons | Harad (`MEC_HARAD`) | draft `southrons.py` | To build |
| Umbar | Umbar (`MEC_UMBAR`) | draft `umbar.py` | To build |

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
