# Custom city models: what the game supports and the plan

> **2026-11-23: custom city models are switched OFF.** Every city uses stock art. The models, scripts and tools
> stay in the repo; `python3 tools/build_dlc.py --landmarks` builds them back in (`--redraw-button` adds the debug
> buttons). Before resuming, read "2026-11-23 evening: STATUS" in §8: several earlier results are invalid.

Status (2026-11-22 evening): **Plan A implemented for one city, Barad-dûr. Built and installed, not yet checked in game.**
Steps 1 and 2 (stock model, then a re-shipped old model) were skipped at the user's request. A new Barad-dûr
centrepiece was built directly, inside the envelope of the models that rendered on 2026-11-21 (see "Implementation"
below). Every other city is untouched (stock art).
The Blender models from the first attempt are still in `tools/capitals/` (scripts) and `build/capitals/out/` (builds).
Those builds are not used.

## Implementation (Plan A, first landmark)

| Piece | Where |
|---|---|
| Landmark table (one row per landmark: name keys, typed-name aliases, model, fScale) | `tools/landmarks/landmarks.py` |
| Model script (Barad-dûr v2: whole-tile fortress + tower + Eye, world units, see "render envelope") | `tools/landmarks/models/barad_dur.py` |
| Blender driver → `build/landmarks/out/` + `build/landmarks/preview/` | `tools/landmarks/build_models.py` |
| In-game script (name key → `SetNumRealBuilding`, synced events only) | `tools/landmarks/MEC_Landmarks.lua` |
| Pack integration (building rows, text, `WonderDefines`, Lua hook, DB check) | `tools/build_dlc.py` → `build_landmarks()` |
| Offline Lua test (found / DCN / capture / rename / typed names / stock cities) | `tools/landmarks/test_landmarks.py` |

- Building `BUILDING_MEC_LM_BARAD_DUR`: `Cost -1`, no gameplay, `ArtDefineTag MEC_LM_BARAD_DUR`, no variation flags,
  **`DisplayPosition 32`**. `DisplayPosition` is a bit mask of art slots (1/2/4/64 wonders, 8 lighthouse,
  16 harbor, 32 palace), and a building with 0 gets no map art at all. 32 is the palace slot at the city centre,
  which ME palaces leave empty. It shows in the city's building list as "Barad-dûr (landmark)".
- Matching uses `city:GetNameKey()` only. That's `TXT_KEY_CITY_NAME_MEC_BARAD_DUR` for the Mordor capital and for
  Dynamic City Naming. A name a player types is matched case-insensitively against the aliases. The localised name is
  never used (it differs between clients and would desync).
- Model envelope: flat shading only, the template's stock rectangular tree cut (`civ5model.write_model(hex_cut=False)`),
  1 building model + tree cut, 512² DIFF / 256² SREF, `Wonder_DecisionTree`, no FX bones. Size limits: see
  "The render envelope" below (enforced by the build).

```
blender -b --factory-startup -P tools/landmarks/build_models.py      # model + preview
python3 tools/build.py && python3 tools/build_dlc.py --zip --landmarks   # pack WITH landmarks (default since 2026-11-23: all cities stock)
python3 tools/build_dlc.py --zip --landmark-stock-art                # diagnostic: Polynesian palace instead of our model
build/venv/bin/python tools/landmarks/test_landmarks.py              # Lua logic test (needs lupa in build/venv)
```

**In-game check:** start as Mordor (or found/rename a city "Barad Dur"). Expect the black tower with the Eye in
the middle of Barad-dûr's tile, stock houses around it, and every other city unchanged. `Lua.log` shows
`MEC_Landmarks: active, 1 landmark(s)` and `... BUILDING_MEC_LM_BARAD_DUR = 1`.
- Tile blank (no houses either): the art did not resolve. Rebuild with `--landmark-stock-art`. If the palace shows,
  our asset is at fault. If nothing shows, the mechanism is (slot, tag); then go to Plan B1.
- Nothing extra drawn, houses fine: the building is missing (check `Lua.log`) or slot 32 isn't drawn for
  non-palace buildings; try `DISPLAY_POSITION` 64 in `landmarks.py`.
- Size or placement off: change `scale` in `landmarks.py` (no model rebuild needed).

2026-11-22 later: the user confirmed in game that Barad-dûr renders at 0.25 (small tower beside the houses).
Raising fScale to 1.0 (same file, so 106 world units tall) left the **whole city tile empty**.

### The render envelope (the backbone for every landmark)

What the evidence says (stock numbers measured from the game's own `WonderModels.fpk` etc.: model bbox × fScale):

| asset | fScale | world footprint | world height | renders |
|---|---|---|---|---|
| our first Barad-dûr | 0.25 | ±6 | 26 | yes |
| **same file** | **1.0** | ±24 | **106** | **no, tile empty** |
| custom Minas Tirith (2026-11-21) | 0.77 | ±24 | 46 | yes |
| stock Machu Picchu | **1.0** | ±23 | 19 | yes |
| stock Neuschwanstein / Red Fort | 0.2 / 0.15 | ±30 / ±23 | 24 / 7 | yes |
| tallest stock: Spaceship, CN Tower | 0.08 / 0.5 | ±13 / ±17 | **58** / 39 | yes |

- fScale itself is not the problem (stock uses up to 1.0). Footprints the size of the tile are normal.
  Tree-cut stencils up to ±50 are normal (Machu Picchu, Neuschwanstein).
- The failing case is the only asset ever tested that was far taller than anything the game ships. **Height
  is the variable.** The exact limit lies somewhere between 47 and 106 and is not needed: we stay inside the
  proven range.
- The city hexagon is about 24 world units from the centre to its flat east/west sides and 27.7 to its north/south
  corners. Minas Tirith's 31.2-unit base at fScale 0.77 filled it exactly.
- (The old city-state failures of 2026-11-21 are a different matter: they were not size-related. Harad, 13 tall,
  failed while Minas Tirith, 46 tall, rendered. Not relevant while only Barad-dûr exists.)

**Rules, enforced by `tools/landmarks/build_models.py` (`landmarks.ENVELOPE`); the build refuses a model that
breaks one:**
1. Author models in **world units**: origin at the tile centre, ground z = 0, -Y = south = towards the camera.
2. Every vertex inside the city hexagon. Height ≤ **48**. Lowest point ≥ -4.
3. ≤ 22,000 vertices and ≤ 20,000 triangles (largest stock wonders: ~22k vertices).
4. `fScale` stays at the proven **0.25**. The writer multiplies the vertices by 4 (1/fScale).
5. Unchanged from the version that rendered: flat shading, the stock rectangular tree cut, 1 building model + tree
   cut, 512² DIFF / 256² SREF, `Wonder_DecisionTree`, no FX bones.

**Barad-dûr v2** (built under these rules): a hexagonal fortress filling the whole tile. It has an outer wall with
spiked corner bastions and a fire-lit gate facing the camera, an inner terrace with six lesser towers and flying
buttresses, a four-tier great tower with fiery window slits, and the iron crown of two prongs. The Eye is about 9 units
tall, tilted towards the camera, with a fire shell, a yellow iris, a black slit pupil and a corona of flames.
Size: 47.3 tall, ±23.6 wide; 20,942 vertices, 8,994 triangles.
**Awaiting the in-game test.** If it fails despite the envelope, the next step is an in-game bisection of height
(e.g. the same model scaled to heights 26 / 36 / 47), with the user's go-ahead.

Goal: give individual cities their own landmark model, chosen **by city name**. For example, only the city named
Barad-dûr shows the tower with the Eye. Every other city keeps the stock city art. We add models one at a time and
check each one in the game before starting the next.

---

## 1. How Civ 5 draws a city

The findings below come from the game files, the game database (`vendor/civ5/vanilla_bnw.db`, `build/tmp/final.db`),
disassembly done in the earlier session, and the earlier in-game render tests (screenshots in
`../civ5me-backup-20261122-prerevert/removed/build/rendertest/shots/`).

### 1.1 Two layers make up a city tile

| Layer | Defined in | Keyed by | Per city? |
|---|---|---|---|
| **Houses** (the generic town that grows with population) | `<CityDefines>` → `BuildingArtInfos/Culture/Era/PopulationBuildings` | owner's `ArtStyleType` (culture) + era + population | **No.** Per culture only, decided inside the exe |
| **Building art** (castle, colosseum, lighthouse, harbor, stadium, palace variants, wonders) | `<WonderDefines>` → `WonderArtInfo/Type` + `fScale` + `.fxsxml` | `Buildings.ArtDefineTag` of each building **the city has** | **Yes.** It depends on which buildings the city has |

The **building layer is the only layer that can differ between two cities of the same civ.** Any per-city model has
to come from that layer.

### 1.2 How a building's art name is chosen (from the exe, `0x6cd0a0`)

```
if   Buildings.ArtInfoCulturalVariation  -> name = <owner ArtStylePrefix> + " " + ArtDefineTag   ("POLYNESIAN PALACE")
elif ArtInfoEraVariation / RandomVariation -> era / random variant of the tag                     ("LIGHTHOUSE", ...)
else                                       -> name = ArtDefineTag                                 (plain tag)
```

Stock examples: `BUILDING_CASTLE`/`COLOSSEUM`/`PALACE` use cultural variation (stock only defines
`POLYNESIAN CASTLE/COLESSEUM/PALACE`, in `DLC_03/Buildings/Civ5ArtDefines_Wonders_Polynesia.xml`).
`LIGHTHOUSE`/`HARBOR` use era variation and `STADIUM` uses random variation. Every one of the 140 stock buildings
has an `ArtDefineTag`.

So **a building with a plain, unique `ArtDefineTag` and a matching `WonderArtInfo` gets its own model.** The owner's
civ, culture and prefix don't affect it.

### 1.3 Hard facts from earlier work (do not re-learn these)

1. **Only DLC packages can add `WonderDefines`.** Mods (.modinfo) can't. Our pack is attached to the free
   `Upgrade 1` package (see README), so it can use `<WonderDefines>`. Loose `.gr2/.dds/.fxsxml` files in the package
   folder load. No `.fpk` is needed.
2. **If one building's art doesn't resolve, the city's model can't be assembled and the engine draws nothing on
   that tile: no houses and no landmark** (the city still works). We fixed this once already for ME unique
   buildings (`src/Fixes/MEMP_ArtFixes.xml`). It is also exactly the "empty tile" seen in the render tests.
   **So a broken landmark doesn't fall back to stock. It blanks the whole city tile.** We have to verify every model
   in the game before shipping it.
3. **Building art is drawn on the city's centre tile.** The render tests showed palace-hooked models (Tom Bombadil,
   Crissaegrim, Alatar, Smaug's Lair, Esgaroth) centred on the city hex.
4. Our own `.gr2` writer **can** produce models the game draws: uncompressed, stock Polynesian palace type tree,
   meshes under 32k verts. Bag End, Tom Bombadil, Crissaegrim and others rendered on 2026-11-21. But about half
   of the 40 models never rendered (Dale, Bree, Pallando, Rivendell, …), and after the overnight "optimisation"
   rebuild **none** rendered. The cause is unknown. It is **not** the presence of a `DecisionTree`/FX trigger
   (Pallando had them and failed, Dale had none and failed). So whatever the city mechanism is, the **assets are
   the unproven part** and must be brought in under tight control (§4).
5. Houses can't be removed for one city. They are culture-wide. Removing them for every ME city was tried and
   reverted.
6. MP: anything that changes game state from Lua must run identically on every client. `GameEvents.*` and
   `Game.Rand` do. UI `Events.*` don't. `METSL_InGame.lua` (loaded via the `InGame.lua` override) already works this
   way.

### 1.4 Things the game does *not* offer

- No Lua API to attach a 3D model to a plot or city. Visuals follow game state only.
- No per-city art field in the database. `ArtStyleType`/`ArtStylePrefix` belong to the civilization or minor civ,
  not to the city.
- No art keyed by city name anywhere in the art defines.

So "override by name" has to be built ourselves: **name → (Lua) → a building in that city → (art define) → model.**

---

## 2. Plan A (recommended): one invisible "landmark building" per named city

### 2.1 How it works

1. **One dummy building per landmark**, e.g. `BUILDING_MEC_LM_BARAD_DUR`, in its own building class:
   - `ArtDefineTag = "MEC_LM_BARAD_DUR"`, with all three variation flags off, so the plain tag is used (§1.2).
   - No gameplay: `Cost = -1`, `FaithCost = -1`, no prereq tech, no yields, `NeverCapture = 0`,
     `ConquestProb = 100`. The Lua re-applies it anyway (below). It can't be built, bought or sold.
   - A description like "Barad-dûr (landmark)". It will show in the city's building list. That's harmless and
     arguably nice. We can hide it from the city screen and the Civilopedia later if wanted.
2. **One `WonderArtInfo` per landmark** in our DLC's `WonderDefines` file:
   ```xml
   <WonderArtInfo>
     <Type>MEC_LM_BARAD_DUR</Type>
     <WonderArtState state="Any"><fScale>0.2</fScale><Granny>MEC_BaradDur.fxsxml</Granny></WonderArtState>
   </WonderArtInfo>
   ```
3. **A name → landmark table** (game data, e.g. table `MEC_CityLandmarks(CityNameKey, BuildingType)`, or a Lua
   table). Keys are the `TXT_KEY_…` city names. Dynamic City Naming already stores keys via `city:SetName(key)`, and
   city-state cities are named from their own text keys. Matching on the key works in every language.
   Optionally, also match the localized display name so a player who types "Barad-dûr" into a renamed city gets it
   too.
4. **`MEC_Landmarks.lua`**, loaded next to `METSL_InGame.lua` from the `InGame.lua` override:
   - `Sync(city)`: look up `city:GetNameKey()` (fall back to `GetName()`). Give the matching landmark building with
     `city:SetNumRealBuilding(id, 1)` and remove any other landmark building (`SetNumRealBuilding(other, 0)`).
   - Called from `GameEvents.PlayerCityFounded` and `GameEvents.CityCaptureComplete`, **after** the DCN renaming
     (call it from the same handler, or register it later), and once for all cities on load. Also called from
     `GameEvents.PlayerDoTurn` for that player's cities, which catches manual renames within a turn with no
     extra hooks.
   - Only uses synced events and is fully deterministic, so it is MP-safe.
5. **Fallback is automatic.** A city whose name isn't in the table never gets a landmark building, so it shows
   exactly the stock art. That's the behaviour you asked for.

### 2.2 Why this is better than the palace hook (old approach)

| | Palace + `ArtStylePrefix` (old) | Landmark building (Plan A) |
|---|---|---|
| Keyed by | civilization (capital only) | **city name** |
| Capital captured or moved | landmark jumps to the new palace city, or disappears from Barad-dûr | follows the name: Barad-dûr stays Barad-dûr under any owner |
| City-states | per minor civ (fine) | same table, by name (fine) |
| Secondary named cities (Minas Morgul, Osgiliath, …) | impossible | just another table row |
| Touches stock rows | `BUILDING_PALACE` flags, every civ's prefix | **nothing stock**, only new rows |
| A broken model blanks | every capital using it | only that one city |

### 2.3 Open questions, answered by the first experiment (§4 step 1)

- **Q1:** Does a *non-wonder, non-cultural* building with a plain tag render through `WonderArtInfo` like the
  palace did? Expected yes: lighthouse/harbor/stadium are ordinary buildings that do exactly this.
- **Q2:** Where does it render: centre tile (like the palace), or an adjacent "wonder slot"? Expected: centre.
- **Q3:** How does it sit next to the **stock houses**, which stay this time? The landmark must work as the
  centrepiece of a town, not fill the hex edge to edge. That changes the model design: a smaller footprint, the
  houses around it. See §3.
- **Q4:** Does `SetNumRealBuilding` from `PlayerCityFounded` refresh the city art immediately, or only on the next
  turn or reload?

### 2.4 Plan B (only if Q1 fails)

If building art doesn't render for a dummy building:

- **B1, palace hook again, per civilization.** `BUILDING_PALACE.ArtInfoCulturalVariation = 1`, each ME civ and minor
  civ gets its own `ArtStylePrefix` (`MEC_MORDOR`), and `MEC_MORDOR PALACE` points to the model. This covers capitals
  and city-states, not arbitrary names (§2.2 drawbacks). It is proven to work.
- **B2, a model for every city:** a per-culture `CityDefines` set (our own house sets) for each ME civ. Every Mordor
  city then looks "Mordor", and the capital adds B1. This is the "custom model for every possible city" variant.
  It needs an `ArtStyleType` per civ, and many more models (era × size).

B1 was the old approach. Use it only as the fallback.

---

## 3. Model design rules for this plan

These differ from the first attempt:

1. **Houses stay.** The landmark is a centrepiece: a tower, a hall or a gate with a small base, roughly the size of
   a stock wonder. It should not be a full-hex diorama with its own terrain. Size the footprint after the step 1
   screenshot.
2. **Copy the stock wonder envelope** to start with: stock-like vertex/triangle counts (~≤20k), 512² DIFF / 256² SREF,
   the same `.fxsxml` structure as a stock wonder (two models + tree cut, `Wonder_DecisionTree`). Add particle FX
   only after the plain model works.
3. **One model per build and test cycle.** Never change the pipeline and the models at the same time again.

---

## 4. Step-by-step procedure

Each step ends in an in-game check, which needs the user's go-ahead (the game is never launched without it).

**Step 0: offline preparation (no game)**
- Add the landmark plumbing to `tools/build_dlc.py` behind a flag: building rows, building class, text,
  the `WonderDefines` file, the Lua script and the name table. Database check with `dbreplay.py` (no errors, stock
  rows untouched).
- Add a Lua test through `tools/mockciv.lua`: founding/capture/rename gives and removes the right building
  deterministically.

**Step 1: prove the mechanism with a stock model (separate the mechanism from our assets)**
- Map `MEC_LM_BARAD_DUR` to a **stock** art file the game certainly loads, e.g. `Poly_Palace.fxsxml` (Polynesian
  palace) or a stock wonder `.fxsxml`.
- In game: found or rename a city "Barad-dûr", or start as Mordor (the capital gets the name). Expected result:
  a stock Polynesian palace on that city tile, houses around it, all other cities stock.
- Answers Q1–Q4. If it fails, go to Plan B1 and stop here.

**Step 2: the first custom model, Barad-dûr**
- Rebuild only `MEC_BaradDur` from `tools/capitals/models/`, redesigned as a centrepiece (§3).
- Before testing it, check that our `.gr2` writer still produces a model the game draws. Re-ship one model
  **byte-identical to a build that rendered on 2026-11-21** (Tom Bombadil from git `76c8629`,
  `build/capitals/out/MEC_TomBombadilsHouse.*`) under the Barad-dûr tag. If that renders, the pipeline is fine and
  any failure is in the new model. If it doesn't, the packaging is at fault.
- Then the real Barad-dûr model. Iterate on scale (`fScale`), footprint and look from in-game screenshots.

**Step 3: one city per cycle**
- Add one row to the name table, one model and one `WonderArtInfo`. Build, install, check in game, commit.
- If a model blanks its tile (§1.3 fact 2), compare it with the last model that worked (vert count, textures,
  materials, bones) and bisect. Don't touch the other models.
- Suggested order: capitals first (Barad-dûr, Minas Tirith, Bag End, Edoras, Orthanc, Erebor, …), then the
  city-states, then secondary named cities.

**Step 4 (later): polish**
- Particle effects (FX bones, `ftsxml`), one model at a time.
- Hide the landmark buildings from the city screen and the Civilopedia if they bother you.
- Era states (`WonderArtState` per era) if a landmark should change over time.

---

## 5. Risks

| Risk | Effect | Mitigation |
|---|---|---|
| A landmark's art fails to load | that city's tile is blank (houses too) | verify each model in game; one model per cycle; the stock-model and known-good-model steps isolate the cause |
| Unknown cause of the 2026-11-21 render failures comes back | models silently invisible | step 2 known-good re-ship; stay inside the stock asset envelope; bisect against the last working model |
| Landmark overlaps stock houses awkwardly | ugly city | design as a centrepiece (§3); tune `fScale` from screenshots |
| MP desync | game breaks | only `GameEvents` + deterministic code; the building has no gameplay effect anyway |
| Players with different pack versions | desync / missing art | already the rule: every player installs the identical build |
| EUI or other `InGame.lua` overrides | Lua not loaded, so no landmarks (cities stay stock, nothing breaks) | known limitation, same as METSL |

---

## 6. Animation and effects (Barad-dûr v3: the living Eye)

Status (2026-11-22 evening): built, installed, **not yet checked in game**. v2 (static) rendered beautifully.

### What the engine offers (all found in the stock game files)

| Need | Stock precedent | How we use it |
|---|---|---|
| A building part that moves | **United Nations** wonder: its `.gr2` holds a static model (`BuildingShader`), the tree cut and a **skinned model** (`BuildingShader_Skinned`, vertices with BoneWeights/BoneIndices). `United_Nations_Idle.gr2` (Animation `ec="1000"`) loops through `United_Nations_DecistionTree.ddtxml` | The Eye is a 3rd, skinned model in our `.gr2`. Its bone `eyepivot` is turned by `MEC_LM_BaradDur_Idle.gr2`, played by the UN's own decision tree |
| Fire | Great Lighthouse: `TimedTrigger` → `ART_DEF_VEFFECT_GREAT_LIGHTHOUSE` → particle `ART_DEF_PEFFECT_GREAT_LIGHTHOUSE_FIRE` on a bone | Our VisEffects (`MEDLC_Landmarks_VisEffects.xml`) reuse that particle system at our scale, on 8 bones round the Eye's rim and 1 behind it. They are children of `eyepivot`, so they turn with the gaze (the Spaceship's exhaust bones move with its launch animation the same way) |
| A beam of light | Industrial lighthouse: model effect `FX_Ind_Lighthouse` = 5 stacked additive planes (`FXShader_Skinned`), turned by its own `IdleA` animation | `MEC_EyeBeam` = that mesh/material/skeleton, aimed south, tilted down 34°, our fiery texture, turned by **the same gaze curve**. It hangs on a **static** bone at the Eye's pivot, so it can never inherit the Eye's turn twice |

The skinned material differs from the static one in exactly two fields (`ShaderSet BuildingShader_Skinned`,
`SkinBoneCount 32`), the same difference as in the UN's file. Effect sizes are multiplied by the building's fScale
(stock: Great Lighthouse fire 2.2 at fScale 0.05, lighthouse beam 15.8 at 0.05).

### Animation format (verified, `tools/landmarks/granim.py`)

Every animated orientation in the stock game uses `D4nK16uC15u` (degree 2), so ours does too. Decoding the stock
lighthouse beam showed:
- **The curve:** a clamped quadratic B-spline. The knots are listed as `[0, eps, h, 2h, …, T]` uint16 × (T/65535).
- **Each quaternion control:** stored in 3 × 15 bits plus swizzle and sign bits; table entry 0 is scale √2/32767, offset −1/√2.

`granim.self_test()` checks this against the stock beam's steady 18°/s turn. The build reads every written
animation back and checks the decoded gaze against the intended one (max error 1.3°).

### The gaze (one 6 s loop, `GAZE` in the model module)

Right (40–44°) → flick further right (54°) → hold → **snap left** (−42°, 0.3 s) → hold left 1 s → swing back right
(0.8 s). The loop is 6 s because every stock animation sequence in these decision trees is declared with
`duration="6.0"`. Once the game shows how that value is used, the right-hand hold can be shortened to the
requested 2–3 s.

### Files (`tools/landmarks/`)

| | |
|---|---|
| `lmodel.py` | building `.gr2` (tree cut + static + skinned Eye), idle animation, `.fxsxml`, trigger files |
| `granim.py` | the curve codec + spline fit + stock self-test |
| `beam.py` | the beam effect (`MEC_EyeBeam.*`) |
| `preview_anim.py` | renders frames of the loop **from the written game files** (decoded curves, skinning by bone) → `build/landmarks/preview/<model>_anim.png` |
| `landmarks.py` | `EFFECTS` (effect names, particle/model, scale), `BEAM_TILT`, `DIAGNOSTICS` |

### In-game check: one game, four cities

Every layer that could blank the tile is isolated. Found Barad-dûr (or play Mordor), plus three more cities, and
**rename** them (city screen):

| City name | Shows | If this one is blank... |
|---|---|---|
| `Barad Test 1` | v2 static model (the proven form, control) | something outside the models (install / cache) |
| `Barad Test 2` | + skinned Eye with the looking-around animation, no effects | the skinned model or the animation file |
| `Barad Test 3` | + the fire on the Eye | the fire effects |
| `Barad Dur` | + the beam (the real landmark) | the beam effect |

Expected: the Eye turns right, flicks, snaps left, swings back; fire around it moves with it; an orange searchlight
sweeps the land in step. Sizes to tune after the first look: `EFFECTS[...]['scale']` and `BEAM_TILT` in
`landmarks.py` (fire size, beam length/width), the gaze keys in the model module. Drop the test variants with
`python3 tools/build_dlc.py --zip --no-landmark-tests` once everything is confirmed.

```
blender -b --factory-startup -P tools/landmarks/build_models.py      # models, animation, beam (+ checks)
blender -b --factory-startup -P tools/landmarks/preview_anim.py      # loop preview from the game files
python3 tools/build.py && python3 tools/build_dlc.py --zip
build/venv/bin/python tools/landmarks/test_landmarks.py
```

---

## 7. Offline check: animated GIFs (`tools/landmarks/render_gif.py`)

Verify model, animation and effects **without starting the game**. The tool reads only the written game files and
handles them the way the engine does:

- **Art define → model:** `WonderArtInfo` (tag → `.fxsxml`, fScale) → `.fxsxml` (mesh, `Animation ec="1000"`,
  `TimedTrigger`).
- **Animation:** every track of every model is evaluated from the stored curves (`DaIdentity`, `D3Constant32f`,
  `D4Constant32f`, `D4nK16uC15u` with its stored knots). Bones are chained to their parents, and vertices are skinned
  with the file's own `InverseWorldTransform`s.
- **Effects:** the trigger file's (bone, event) pairs lead to the VisEffect. **Model effects** (e.g. the beam) are
  loaded recursively with their own animation. **Particle effects** get an animated fire *stand-in*, because the game's
  particle files can't be rendered outside it. The caption says so. Effects inherit the building's fScale.
- **Not covered:** decision trees and lighting are simplified. The view is the city tile with its 6 neighbours drawn
  on the ground.

```
blender -b --factory-startup -P tools/landmarks/render_gif.py -- barad_dur            # both views, one full loop
blender -b --factory-startup -P tools/landmarks/render_gif.py -- MEC_LM_BARAD_DUR_T2  # a diagnostic variant
        options: --view game|close|both  --fps 12  --size 640x480  --seconds S
```
Output: `build/landmarks/gif/<TAG>_game.gif` (the strategic camera, as in the game) and `<TAG>_close.gif` (the
top of the landmark). About 30 s for both views of Barad-dûr. A missing file, an unknown effect or an unsupported
curve format stops the render with its name. That's the point: such a file would also fail in the game.

Use it after every model/animation change, and keep the in-game test for what it can't show: particle looks,
real lighting and effect sizes. Calibrate those once per effect type in game.

## 8. Why a landmark city sometimes renders empty (investigation 2026-11-22)

Symptom: two consecutive launches, same install, same map/start (TSL puts Mordor at 64,28 every time).
Launch 1: Barad-dûr with Eye, fire and beam. Launch 2: the city tile is completely empty, with no houses either.
`Lua.log` of the empty run shows `BUILDING_MEC_LM_BARAD_DUR = 1`, so the gameplay side is identical. The
difference is purely in the renderer. Screenshots: `rendered-barad-dur.png`, `empty-barad-dur.png`.

### What the engine does (CivilizationV_DX11.exe, static disassembly)

| Step | Address | Behaviour |
|---|---|---|
| Art name → id | `0x6cd050` | Name lookup in the art-name table `0xa344a8`. Returns **-1** if the name doesn't exist. Deterministic. |
| Queue to renderer | `0x6d9770` → `0x6d2370` | Command 0x25 (size 0x70), art id at payload +0x18. No check here. |
| Render handler | `0x602580` | Per `DisplayPosition`: 16 → `0x602697`, 64 → `0x602be5`, **32 (palace/landmark) → `0x602e08`**. Each does `cmp [cmd+4],-1 / je skip`. **A missing art tag is ignored: nothing is drawn, and the tile stays.** |
| Instantiate | `0x4e1140` | `id < count`, `info->model loaded` (`0x850e90`), `info+0xcf4 != -1`. **If any check fails** → "Tried to instantiate a wonder that has not been initialized in the library" → `0x4dee60` **destroys the city's whole model group**: the empty tile. |
| Bind | `0x4e71f0` (`cvWonderLibrary::BindAsset`) | Loads the `.fxsxml`/`.gr2` once, while the art XML is parsed at startup (`City_System::Startup`, main menu). `ReloadAssets` exists but nothing calls it. |

So **the only abnormal way to get an empty city tile is a building whose art name exists but whose wonder asset is
not loaded when the city instantiates it.** Our landmark is the only such asset in the game. Stock wonders come
from preloaded `.fpk` paks. Our models are loose files (1.3-1.4 MB uncompressed `.gr2`, plus the T1-T3 diagnostic
copies).

### Corrections to earlier beliefs

- **"An unresolved art tag blanks the whole tile"** (§1.3 fact 2, `src/Fixes/MEMP_ArtFixes.xml`): **false** for
  slots 16/32/64. The handler skips id -1. ME palaces (`PALACE`, a tag that doesn't exist because the original
  mod's `MEC_UnitArtInfoCulturalVariation.xml` switches `ArtInfoCulturalVariation` off for every building) simply
  draw nothing. The same applies to Castle/Colosseum. The original mods' "disappearing cities" were most likely
  **not** caused by this path. The inherited bugs that do exist are cosmetic: no palace/castle/colosseum art for ME
  civs, plus trailing spaces in every ME `ArtStylePrefix` (`"EUROPEAN "`, `"European "`).
- **The render envelope / "height is the variable"** rested on one launch per size. The same file now renders in
  one launch and not in the next, so the fScale 1.0 failure (and the 2026-11-21 per-model "never renders" list) may
  just be this same failure. Not proven either way.

### Not yet proven: what makes the asset "not loaded" in some launches

Candidates, cheapest test first (all need the game, so only with the user's go-ahead):
1. **Per launch vs per city.** In an empty-tile launch, reload a save (or found/rename a second "Barad Dur").
   Still empty in that launch while a fresh launch renders it → the bind failed at startup (per launch).
   It appears after reload → the failure is decided at city creation time.
2. **Loose-file loading.** Ship the landmark art inside an `.fpk` listed under `<Paks>` in the package, like every
   stock DLC. If the empty tiles stop, the loose-file load was the race.
3. **Load pressure.** Build with `--no-landmark-tests` (drops T1-T3: two extra 1.3 MB models bound at startup) and
   compare the hit rate over several launches.

### Follow-up investigation (2026-11-22 evening): what was ruled out

Static disassembly of `CivilizationV_DX11.exe`, the six original mods and the installed pack. **No root cause proven.**
Everything on the wonder path is deterministic, so it can't produce 3-in-10 results on its own:

| Checked | Result |
|---|---|
| Wonder library load (`0x4e21d0` ← `0x498af0`) | once at startup, synchronous; `WonderDefines` files collected, array sized from a count over all files (`0x626850`), names registered first-wins (`0x4e5e80`) |
| Asset cache (`0x844ff0`) | synchronous load ("Warning, synchronous load" is only a diagnostic); file existence checked in the VFS first |
| Bind checks (`0x4e7150`, `0x4e4ed0`, `0x851160`) | entry must be empty, asset must have meshes, ≤ 32 named parts; all deterministic |
| Other callers of the group destroy `0x4dee60` | `0x601fd0` = city-removed handler, `0x5fd050` = destroy all cities; normal paths |
| Render handler `0x602580` | a building message for a plot with no city visual yet is dropped (houses stay); id -1 skipped |
| VFS name overrides (all `Resource/**/*.fpk` + loose stock files indexed) | only `UI/InGame.lua` (intended) and **37 METSL terrain textures incl. 9 height maps `*_h.dds`** override stock with different content; heights are similar (max 148-195 vs stock 140-189; `afri_desert_h` 234 vs 156), deterministic |
| Mod Lua (`METSL_InGame`, `Wood_Elves_Units_Promotions`, `MEC_Landmarks`) | no `Events.SerialEvent*` city calls; nothing that touches city visuals |
| Map | terrain is fixed data (64,28 = plains **hill** next to mountains 65,28 / 65,29); **resources and some city-state starts are re-rolled each game** (`Map.Rand`), so two launches are never the same map |

New evidence from the two screenshots (19:27 empty, 19:29 rendered): in the empty launch an **orange fire glow is
visible on the ground just west of the city tile**, and the city's ground decal is drawn. That suggests the landmark
instance (and its effects) was created and the city's model group was hidden or torn down afterwards, i.e. not the
"never bound" path assumed above. Unconfirmed.

Small real defects found on the way (not the cause): `Database.log` "columns StrategicViewType, TileType are not unique"
at DLC load (one SV insert file aborts); referenced but missing files `elf_swordsman_v3.fxsxml`, `dwarf cannon.dds`,
`goblin_worker.dds`, `sv_englishlongbowman.dds`; stray text `ff` after `</ArtStyleType>` in `MECS_City_States_EXP.xml`.

Next: needs in-game runs (user's go-ahead): (1) `--no-landmarks`, several launches: do stock cities go empty at all?
(2) `--landmark-stock-art`: does the stock Polynesian palace go empty at the same rate? (3) in an empty launch, save
and reload: does it come back?

### In-game measurements (2026-11-22 night, tools/rendertest/)

- **Harness:** `python3 tools/build_dlc.py --rendertest` + `build/venv/bin/python tools/rendertest/rendertest.py run <label>`
  (founds the capital with the real Found mission, 4 comparison cities, shots in build/rendertest/shots/). TEMPORARY.
- `steam -applaunch 8930` starts **CivilizationV.exe = DX9**, not DX11. The user plays DX11. `tools/rendertest/exe_probe.py
  install` puts the (instrumented) DX11 exe in its place for a run; `restore` puts both originals back.
- Reproduced on DX9 and DX11: Barad-dûr draws for ~0.2 s, then the **whole tile** (houses + landmark) vanishes; its fire
  particles keep running; removing and re-adding the building in the same launch does not bring it back.
- **DX11 probe run (empty tile):** the landmark was instantiated normally (`0x4e1140`, caller slot handler, art id 85/89,
  city group 0), the "not initialized" branch never ran, and the city-group destroy `0x4dee60` was **never called**.
  So the §8 "destroy" explanation is wrong: the group survives and stops being drawn.
- Ruled out statically since: library reload during a game (loads once at startup, frees at exit); decision-tree
  randomness (UN tree picks by wonder state); NaN in our gaze curve (±54°, one hemisphere); the old per-model
  render list (no size or effect pattern); the art-set refresh `0x4e1310`/`0x4e0b40` (re-adds every matching group).

### In-game results 2026-11-23 (debug buttons, tools/landmarks/MEC_RedrawCities.lua)

- Lua-fired `Events.SerialEventCityDestroyed/Created` really rebuild a city's art (verified on a good launch).
- **The failure is per launch.** In a bad launch, every redraw and every variant of OUR model (full, T1 static, T2, T3)
  draws an empty tile, every click, consistently. In the same city, the stock Polynesian palace and the plain houses draw
  fine on every click. In a good launch, all variants draw.
- The user reports the same sporadic symptom with the six ORIGINAL mods (stock buildings only): cities missing after
  founding, or vanishing when they grow and their model is updated. So our models only expose an older problem.
- Memory snapshot of a bad launch (`build/rendertest/mem/bad-*.maps`): 32-bit LARGE_ADDRESS_AWARE exe, VmSize 2.65 GB,
  **VmPeak 3731 MB (3.64 GiB) of 4096 MB**, largest free block 933 MB at the time, GPU (DXVK) mappings only 110 MB.

Hypothesis under test: address-space pressure (VmPeak ~365 MB below the 4 GB ceiling) makes allocations for big
or loose assets fail in some launches, and the result sticks for the session. Small stock assets still fit.
Probes (Cycle landmark button, single player): `_STOCK` small stock mesh from .fpk; `_BIG` Colossus (big
stock mesh, .fpk); `_LOOSE` the identical small stock mesh as a loose file. `tools/rendertest/memwatch.py`
records VmSize/VmPeak/largest free gap per second per launch (build/rendertest/mem/*.csv).

| bad launch: _BIG | _LOOSE | means |
|---|---|---|
| empty | draws | size/allocation (memory), not our files |
| draws | empty | loose-file loading path |
| empty | empty | both / something about non-palace art |
| draws | draws | specific to our gr2/textures (format, uncompressed gr2, our DDS) |

### Results 2026-11-23 ~17:00: memory ruled out; stock vs ours is decided by the FILE

- 3 runs: Barad-dûr all variants fine in runs 1-2 while Mount Doom's custom variants all failed; run 3 both failed.
  In every bad case ALL stock probes drew: small (.fpk), BIG Colossus (.fpk) and the small stock mesh as a LOOSE
  file. So size and loose-file loading are ruled out.
- memwatch: VmPeak 3731-3732 MB in good AND bad launches, reached at startup. **Memory is ruled out.**
- User: a switched-in custom model **draws for several frames, then vanishes** (with the houses).
- DDS headers match stock (DXT3, full mip chains, exact sizes).
- gr2 layout is identical to stock (same type tree). Two differences:
  1. **Every stock .gr2 stores ALL strings as CRC32 hashes** (127/127 data strings, 201-264/201-264 type names in
     palace, Colossus, Great Lighthouse) and the header's StringDatabaseCRC = 2. Ours store real text, StringDatabaseCRC 0.
     If the engine treats string fields as hashes, it reads per-launch heap addresses from our files.
  2. Stock BoneBindings OBBMin/OBBMax = 0; ours are real boxes.
- New probes (tools/landmarks/probes.py, gr2.write(hashed=True)): `_T1H` (hashed), `_T1Z` (zero OBB), `_T1HZ` (both),
  all made from Test 1, in the Cycle button after Test 1.

### 2026-11-23 ~17:15: hashed names ruled out; SECTION LAYOUT is the new prime suspect (fix installed)

- Hashed-name probes drew a red missing-material box in a good launch: the engine honours StringDatabaseCRC=2 and
  can't resolve our names, so plain text is right. Dropped.
- Mount Doom now shows Barad-dur's files (`art_of`). Next run: both cities failed together, so it follows the ASSET.
- **Granny section layout.** Every stock .gr2 (palace, Colossus, Great Lighthouse, United Nations, lighthouse beam)
  puts the main objects in sec0, rigid vertices / indices in sec1 / sec2, skinned vertices / indices in sec3 / sec4,
  and the type tree in sec6. Animation files use sec0 + sec6. Our writer put EVERYTHING into sec0. The always-working
  `_LOOSE` probe is a stock-layout file through the same loose-file path.
- `gr2.write(sections=True)` writes the stock layout (verified: decodes to the same model; old layout still
  byte-identical; section use matches the UN and the beam exactly). build_dlc converts every landmark .gr2 at
  copy time (`probes.to_stock_sections`). Control probe `_T1F` = Test 1 in the OLD layout.
- Expected if right: no more empty landmark tiles, and in a "bad" launch only `T1 OLD layout` fails.
- The original mods: 90 of their 165 .gr2 (unit meshes, incl. Mordor's Orc Settler/Worker, Gondor, Dwarves, Isengard)
  also keep their vertices in sec0 (community export tools). Possibly the same bug behind their vanishing cities; unproven.

### 2026-11-23 ~18:00: SIZE decides it (fScale-only probes, same mesh)

7 runs, Barad-dur (capital, first city) and Mount Doom (second city), both showing Barad-dur's files:
- Mount Doom: Test 1 at 50% and 25% ALWAYS draw; 75%, 90%, 100% never.
- Barad-dur: varies by game: everything (incl. 100%), or 90% and below, or 75% and below. Never worse than Mount Doom.
- Smaller map + fewer city states: same result.
- The size probes are the SAME file (same mesh, vertex count, textures); only `fScale` differs. So a budget on model
  count or complexity can't explain it; the world-space extent does. Bounding-sphere radius (from the T1 OBB,
  centre at mid-height): 100% ~43, 90% ~39, 75% ~32, **50% ~21.6**, 25% ~10.8, vs ~24 hex centre-to-edge.
  50% is the largest size whose sphere stays inside the city's own hex.
- Capital vs second city: the capital usually has more explored land around it.
- No hidden engine setting for model budgets: the exe's settings strings (around FOWLevel/Terrain64Chunks) are exactly
  the keys already in GraphicsSettingsDX11.ini / config.ini.

Tests (debug buttons): Cycle left = capital only, right = other cities only (budget test: set the capital to
"no landmark", try Mount Doom at 100%). New "Reveal area" button (SP): reveals and lights every plot within 3 tiles
of your cities and rebuilds their art (fog-of-war test).

### 2026-11-23 ~18:10: fog ruled out; capital vs other city; art-slot probes

- Same limits again (capital <= 90%, second city <= 50%). Lua.log: "Reveal area" was clicked when Barad-dur was the only
  city (9 plots revealed, 10 made visible), and it still stopped at 90%. **Fog of war is ruled out** for the capital.
  The budget test (capital on "no landmark" while the other city tries full size) was not done yet.
- Constant over 8 runs: the CAPITAL does better (75-100%, varies per game), the second city is capped at 50% exactly,
  whatever the name or files. The landmark uses DisplayPosition 32, the PALACE slot; only capitals have a palace.
  Hypothesis: slot-32 art is fitted to a palace area of the city layout (bigger in capitals; the layout varies per game).
- Probes `_P1/_P2/_P4/_P64`: full-size Test 1 art (shared WonderArtInfo) through art slots 1, 2, 4 (land wonders,
  castle, colosseum) and 64 (Machu Picchu, the biggest stock model).

### 2026-11-23 evening: STATUS (read this first; several results above are INVALID)

**Invalid, do not build on them:** every result from the "Cycle landmark" debug button before ~18:30, i.e. the size
steps (90/75/50/25%), the art-slot steps (1/2/4/64), and the stock/BIG/LOOSE comparisons. The button looked buildings
up with `GameInfo.Buildings["TYPE"]`, which returned the WRONG row in game for some of our rows (log: `_P32` gave
`_LOOSE`, `_T2`). The Buildings table has 22 ID gaps. Also, redraw-then-add (Lua `SerialEventCityDestroyed/Created`,
then `SetNumRealBuilding`) can leave even stock art undrawn, so redraw-based tests are unreliable. All scripts now
build Type->ID maps by iterating `GameInfo.Buildings()`.

**Solid:**
- Lua-side state is always correct (logs show the building on the city).
- Ruled out: memory / address space (VmPeak identical in good and bad launches), fog of war, DDS format, gr2 section
  layout, hashed names (hashed = red missing-material box), zeroed OBB.
- User's own launches, no tools: the capital (Barad-dur) usually draws at founding; a second city with the SAME files
  (Mount Doom via `art_of`) never did. In the user's bad case the WHOLE tile (houses too) is empty.
- Automated runs (tools/rendertest, 2026-11-23, 6 launches, plain and probe DX11 exe): the custom landmark NEVER drew,
  in any city, in any slot, at any size. In the last two, all 36 capitals + city-states had BUILDING_MEC_LM_BARAD_DUR at
  founding (no redraws): 0/36 drew, and the HOUSES STAYED (a different symptom from the user's empty tile, matching the
  engine skipping an unregistered art id). Cutting our WonderDefines from 22 entries to 2 changed nothing.
  The instrumented probe exe must not be used for render checks (exe_probe.py install_plain = unmodified DX11).

**Open:** why the harness launches never draw the landmark (different from the user's launches: rsync install, cache
moved, config LeaderHead/LoggingEnabled, Play Now, InitCity founding). Until that's understood, the harness can't
test this bug. Installed state: palace slot, 2 landmark entries, no debug buttons (--no-landmark-tests --no-redraw-button).

## 9. Mount Doom (2026-11-22 night): a new volcano in Barad-dûr's style

The earlier Krakatoa-heightmap draft (commit `9ab94f8`) was reset away, so the build installed at 22:02 had no
Mount Doom (the stock city in `mount-doom.png`). It's been replaced with a new procedural model, `tools/landmarks/models/mount_doom.py`.

**Which city.** Name key `TXT_KEY_CITY_NAME_MEC_MOUNT_DOOM` (Mordor's city list, or Dynamic City Naming, which stores
the same key), or a player-typed "Mount Doom". "Orodruin" gets no volcano. Covered by `test_landmarks.py`.

**Model** (world units, inside the envelope: 46.9 tall, 20.5k verts, 9.4k tris). Lore: "huge base ... and above
that ... its tall central cone ... capped with a jagged crater". A polar height field with a broad ash shoulder
(z ≈ 20) and a steep chimney cone up to a jagged, breached rim (z ≈ 40). The crater holds a lava lake with crust floes and glowing cracks.
Five lava rivers (ribbons draped on the surface, in channels carved into the field, scorched banks) run into pools on the plain.
There are also the Sammath Naur (a black gate red-lit from within, on a ledge, with iron posts) and Sauron's Road (a causeway climbing from the
east edge in a switchback to the door). Gorgoroth has cinder cones, slag boulders and glowing fissures. The palette is Barad-dûr's.

**Animation and effects: the same proven structure as Barad-dûr v3** (skinned 2nd model + `_Idle.gr2` +
`United_Nations_DecistionTree`). The skinned part is three Nazgûl on fell beasts circling the summit (orbit r 14.8,
z 43.5). They are identical and 120° apart, so the 6 s loop turns the part by 120° and loops seamlessly. The effects hang on
static bones (children of `eyeroot`):
| bone | effect (landmarks.EFFECTS) | particle |
|---|---|---|
| fxerupt, fxerupt2 | DOOM_ERUPTION 3.0, DOOM_ERUPTION_SMALL 1.8 | stock Krakatoa `VOLCANIC_ERUPTION_01` (Krakatoa size ≈ 2.6) |
| fxcrater | DOOM_CRATER_FIRE 1.3 | `GREAT_LIGHTHOUSE_FIRE` (as on the Eye) |
| fxlake0-2, fxbreach, fxvent* | DOOM_VENT_FIRE 0.45 | same |
| fxdoor | DOOM_DOOR_FIRE 0.35 | same |

`build_models.py` now writes the Eye beam only for a landmark whose rig has an `EYE_BEAM` bone (otherwise Mount Doom's
orbit would have overwritten the beam's gaze). Diagnostic cities: "Doom Test 1" (static, no effects), "Doom Test 2"
(+ beasts), "Doom Test 3" (+ effects = the full landmark, since there's no beam).

**In-game check:** found or rename a city "Mount Doom". Effect sizes are the only untested numbers: if the ash column is
too small or too big, change `scale` in `landmarks.EFFECTS['DOOM_*']` (no model rebuild needed).
