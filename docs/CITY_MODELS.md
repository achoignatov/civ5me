# Custom city models: what the game supports and the plan

> **CURRENT STATE (2026-11-24 evening): Moria works. Read §15 first.**
> The only landmark is Moria (Goblins' capital): our own high-fidelity Blender model (v3, §14), given when the city is
> founded. Size limits found in game (§12): footprint +-20 world units in major civ cities, +-16 in city-states, height
> up to ~24-29. With every major capital showing it, 0-2 of ~12 tiles still stay empty per game (cause unknown, §15).
> Fog of war is OFF for testing (`landmarks.REVEAL_MAP`). Barad-dûr and Mount Doom rows are `enabled=False`.
>
> Older notes below (§1-§9) are history. Several results in them are invalid (see "2026-11-23 evening: STATUS" in §8).

Historical status (2026-11-22 evening, superseded by the note above): **Plan A implemented for one city, Barad-dûr. Built and installed, not yet checked in game.**
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
visible on the ground just west of the city tile**, and the city's ground decal is drawn. **(2026-11-23: the user says
this is not true; the fire does not burn beside the tile. Ignore this clue.)** That suggests the landmark
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

### 2026-11-23 late: "one registration" experiment (installed, awaiting the user's test)

Question: does the second city fail because it is a SECOND building + WonderArtInfo bound to the same `.fxsxml`?
`landmarks.ONE_REGISTRATION = True` moves Mount Doom's name key and alias onto Barad-dûr's row, so the pack has ONE
landmark building (`BUILDING_MEC_LM_BARAD_DUR`) and ONE WonderArtInfo, and both cities get it. Read the result:
- Mount Doom (2nd city) now draws -> the second registration was the problem; give each landmark its own copy of the files
  or keep one registration per model.
- Still never draws -> it's the city (slot 32 without a palace / city layout / bounds), not the registration.
`test_landmarks.py` reports the Mount Doom checks as failures while this is on (expected).
**Result (user, 2026-11-23 late):** same behaviour: the capital draws as before, Mount Doom (same building, same
WonderArtInfo) still never draws. **The second registration is ruled out.** The failure belongs to the city (non-capital /
no palace / location), not to the name, building row or art entry.

### 2026-11-23 late: focus = capital 100%. Step 1: static only (installed, awaiting the user's launches)
`landmarks.SHOW_VARIANT = 'T1'`: Barad-dûr shows `MEC_LM_BaradDur_T1.fxsxml` (static fortress + tower, `Wonder_DecisionTree`,
no skinned Eye, no Idle animation, no triggers/effects/beam). (The "fire glowing on the ground west of the tile" clue,
from a screenshot read on 2026-11-22, is WRONG per the user; don't use it.) Plain bisection: static draws in every launch -> the
animated part is the cause; add pieces back one at a time. Static also fails -> next suspect is size (shrink into the hex).

### 2026-11-23 late: "build it later" (user's idea; installed, replaces the static step, which was never tested)
The model is no longer added at founding. `landmarks.BUILDABLE = True`: `BUILDING_MEC_LM_BARAD_DUR` costs 1 production,
can only be built in a city whose name matches (`GameEvents.CityCanConstruct` in MEC_Landmarks.lua, synced data only),
and Lua never gives it (it only removes it after a rename). Until it's built the capital shows stock art; once built
(next turn), the full model (`SHOW_VARIANT = None`) is added to a city whose art already exists. Tests: buildable mode
in test_landmarks.py. If this draws every time, the failure is tied to adding the art in the founding frame.
**Result (user):** 4 tries: the model drew on completion 3 times; the 4th time it did not draw. So adding later does not
make it 100%.

### 2026-11-23 late: given on the next turn, no building to choose (installed)
`BUILDABLE = False`, `GIVE_AT_FOUNDING = False`: the founding and capture events only remove; the owner's next
`PlayerDoTurn` adds the landmark (so it appears at the start of the turn after founding). Loaded games still get it at load.
Full model. Tests: delayed mode in test_landmarks.py.
**Result (user):** when it fails, the houses and everything else on the tile disappear (the known whole-tile symptom).

### 2026-11-23 late: zeroed bounding boxes (built, not installed yet: the game was running)
Field-by-field comparison of our .gr2 with the stock palace: same structure, bone bindings all resolve; differences left
are the BoneBinding OBBMin/OBBMax (stock: always 0; ours: real boxes) and the material FallbackMtl (stock: a hashed name,
ours: empty; UseFallbackMtl = 0 in both, so probably unused). `landmarks.ZERO_OBB = True` writes every landmark .gr2 with
zeroed boxes like stock (the earlier T1Z probe went through the broken Cycle button, so this was never really tested).
Still given on the turn after founding.
**Correction:** the zero-OBB build was NOT tested yet: the user's session 23:30-23:34 ran the previous "next turn" build
(installed 23:29; the zero-OBB install was refused because the game was running). Installed after that session (23:36).

**Session 23:30-23:34 (next-turn build, Lua.log saved in ~/civ5-backup-20261121-capitals/zeroobb-20261123-233610/):**
ONE game process (Lua initialised once, timestamps continuous): new game 1 drew, new game 2 drew, new game 3 failed
(whole tile empty), then loading that game's autosave IN THE SAME PROCESS still failed. Lua side identical every time
(BUILDING_MEC_LM_BARAD_DUR = 1 at 64,28). So the bad state starts at some point inside a session and then sticks for the
rest of that process. Memory (memwatch CSVs 16:47-17:51): VmSize ~2.75 GB, ~1.3 GB free, largest gap ~0.9 GB, flat
across games: no exhaustion. Next: count games per process; does the FIRST game after a fresh start of Civ ever fail?

### 2026-11-23 late: EXTERNAL MODEL test (user: "is it Blender / our pipeline?") - installed
`landmarks.EXTERNAL_ART`: Barad-dûr's landmark shows a model NOT made by us: the community "Blue Mosque" wonder
(github.com/clumsy/Civ5-MP_MODSPACK, Mods/Wonder - Blue Mosque), `Blue_Mosque.gr2` copied byte-identical (Granny
Standard Exporter 2.8.21 from 3ds Max: a reworked stock Hagia Sophia; textures = the stock Hagia Sophia ones from
WonderTextures.fpk). fxsxml written like the stock `hagia_sophia.fxsxml`, fScale 0.05 (stock Hagia Sophia's). Same
mechanism as ours (palace slot 32, given the turn after founding). Files in build/external/bluemosque (gitignored, SOURCE.txt).
Read: it also vanishes the same way -> not Blender / our writer / our files: the mechanism (dummy building in slot 32,
loose art via WonderDefines) is the problem. It never vanishes over many games -> our files are the problem.
Backup: /home/acho/civ5-backup-20261121-capitals/external-20261123-234203


## 10. Stable baseline (2026-11-24): a known-good model that is not ours

### The finding
| Test (same mechanism: dummy building, palace slot 32, `WonderDefines` in the DLC package) | Result |
|---|---|
| Our Barad-dûr (Blender geometry + our Python `.gr2` writer, animated Eye + effects), given at founding | capital drew in most games; the whole tile (houses too) vanished in some; the second city never drew |
| Same, only ONE building/art entry for both cities (`ONE_REGISTRATION`) | no change: registration ruled out |
| Same, built for 1 production a turn later (`BUILDABLE`) | 3/4, then vanished |
| Same, given the turn after founding (`GIVE_AT_FOUNDING = False`) | games 1-2 drew, game 3 vanished, and reloading it in the same process still vanished: the bad state sticks for the rest of the process |
| **A downloaded community model** (`EXTERNAL_ART`, everything else identical) | **5/5 drew** (user, 2026-11-23) |

So the mechanism works; **something in our own model files is what breaks**. The cause inside our files is still
unknown. Candidates, in the order the baseline lets us test them: (1) the animated, skinned Eye + its animation and
decision tree; (2) the timed triggers / particle effects / the beam model effect; (3) size (ours: about 43 world units
from the centre, the base model: about 8 at fScale 0.05, inside the hex); (4) how our writer fills the `.gr2`
(see the field comparison in §8: OBB, FallbackMtl).

### The baseline asset
- `vendor/landmarks/BaradDur/MEC_LM_BaradDur_Base.gr2`: `Blue_Mosque.gr2` byte for byte, renamed. Source, licence
  notes and contents: `vendor/landmarks/BaradDur/SOURCE.md`.
- It uses the game's own Hagia Sophia textures (`WonderTextures.fpk`), so no `.dds` is shipped.
- `tools/landmarks/landmarks.py`: `EXTERNAL_ART` (directory, model name, fScale 0.05, texture list) and
  `external_fxsxml()` (written like the stock `hagia_sophia.fxsxml`, with `Wonder_DecisionTree`).
- `tools/build_dlc.py` `build_landmarks()`: copies the `.gr2` unchanged, writes the `.fxsxml`, and doesn't need
  Blender output (`build/landmarks/out`), our effects or the diagnostic variants while `EXTERNAL_ART` is set.

### Current switches (`tools/landmarks/landmarks.py`)
| Switch | Value | Meaning |
|---|---|---|
| `EXTERNAL_ART` | base model | `None` = our Blender model again (needs `blender -b --factory-startup -P tools/landmarks/build_models.py`) |
| `GIVE_AT_FOUNDING` | `False` | the landmark is added on the owner's first turn after founding (`PlayerDoTurn`), never in the founding event |
| `BUILDABLE` | `False` | `True` = the city builds it for 1 production instead |
| `ONE_REGISTRATION` | `True` | Mount Doom uses Barad-dûr's building (one building, one art entry) |
| `SHOW_VARIANT` | `None` | `'T1'` = our static variant (only with `EXTERNAL_ART = None`) |
| `ZERO_OBB` | `True` | our `.gr2` files written with zeroed bounding boxes like stock (only with `EXTERNAL_ART = None`) |

Build: `python3 tools/build.py && python3 tools/build_dlc.py --zip` (the mod manager's dev build runs the same).
In game: found Barad-dûr (Mordor's capital) or Mount Doom, end the turn: a small Hagia Sophia stands in the city centre.
`Lua.log`: `MEC_Landmarks: ... BUILDING_MEC_LM_BARAD_DUR = 1`.

### How to build on it
Change one thing at a time and test each step over several games in ONE launch of the game (the failure appeared in
game 3 of a session and then stuck until the game was quit):
1. Second city: does Mount Doom draw the base model? (it never drew with our model)
2. Size: same `.gr2`, larger fScale (0.1, 0.2) - does a bigger model start to vanish?
3. Our geometry: our static Barad-dûr in place of the base model (`EXTERNAL_ART = None`, `SHOW_VARIANT = 'T1'`).
4. Then animation, then effects, then the beam.


## 11. (2026-11-24 night) Our Barad-dûr written into the web model's file: did not render. Reverted.


## 12. Moria: our own model, compact (2026-11-24 afternoon, installed, awaiting the user's test)

**What changed**
- Web model removed: `vendor/landmarks/` (Blue Mosque copy), `landmarks.EXTERNAL_ART`, `build/external/`. The unused
  Krakatoa experiment (`tools/krakatoa/`, from the same commits) removed too (still in git history).
- `ONE_REGISTRATION` removed. Barad-dûr and Mount Doom rows kept but `enabled=False`: their 47-unit model fails in some
  games and the bad state then sticks for the whole game process, which would spoil Moria's test.
- Kept from the last two commits because the 5/5 web-model test ran with them: landmark given on the owner's turn AFTER
  founding (`GIVE_AT_FOUNDING = False`), zeroed bounding boxes (`ZERO_OBB = True`), stock section layout.
- New `tools/landmarks/models/moria.py`: a compact port of `tools/capitals/models/goblins.py` (Walls of Moria, Doors of
  Durin in ithildin, holly trees, the Watcher's pool and tentacles, goblin palisade, banners, skull totem). Static only.

**Why compact.** The one solid difference between the web model (drew 5/5) and ours (vanished sometimes) is size:

| | footprint (world units) | height | vertices | fScale |
|---|---|---|---|---|
| web model (Hagia Sophia rework) | +-8 | 13 | 3k + 6k (hill variant) | 0.05 |
| stock Polynesian palace | +-4.5 | 10 | 0.7k | 0.2 |
| our Barad-dûr | +-24 x +-27 | 47 | 21k | 0.25 |
| **Moria (new)** | **+-10.5 x +-12** | **12.7** | **7.8k** | **0.05** |

Vertex format, shader (BuildingShader), 16-bit indices, zeroed bounding boxes and the Tree-cut + building model layout match the web model's; our material comes from the stock BNW palace (one extra `fZBias` global parameter). Per-landmark limits:
a row's `envelope=` tightens `ENVELOPE` (`landmarks.envelope()`), and `tree_cut=` sizes the forest-clearing stencil
(Moria +-10.5, the web model's is +-10.6).

**Test.** Found Moria (Goblins' capital), end the turn: the Doors of Durin stand in the centre, stock houses around them.
Play several games in ONE launch of the game (the old failure showed up in game 3 and then stuck).
`Lua.log`: `MEC_Landmarks: TXT_KEY_CITY_NAME_MEC_MORIA (x,y) BUILDING_MEC_LM_MORIA = 1`.
- Always draws: compact size works for our own files. Next: ithildin glow effects, then a compact Barad-dûr.
- Vanishes: size is not the cause. Remaining differences from the web model: our writer (uncompressed, Blender), no
  hill (HB) variant model, the texture atlas.

**Result 1 (user, 2026-11-24 ~17:05): the compact Moria RENDERED** (added the turn after founding, as designed).

**Step 2: full tile (installed ~17:06, awaiting test).** Same geometry scaled up uniformly (`GROW = 24 / 10.5` in
`models/moria.py`): +-24 x +-27.7, 29 high, same 7.8k vertices, same fScale 0.05, tree cut +-24. If it vanishes, scale
back down (GROW between 1 and 2.29) to find the limit.

**Result 2 (user, ~17:10): full tile did NOT render.** `Lua.log` shows the building was given
(`TXT_KEY_CITY_NAME_MEC_MORIA (45,46) BUILDING_MEC_LM_MORIA = 1`), so the Lua side worked and the art didn't draw. The
same file at 1x drew and at 2.29x did not, so **size is a real factor**. Logs saved in
`~/civ5-backup-20261121-capitals/moria-compact-*/Logs-fulltile-failed`.

**Step 3 (installed ~17:12): back to compact (GROW 1)** so the user can check over several games that it draws every time.
After that: bisect GROW (e.g. 1.5) to find the largest size that always draws.

**Result 3 (user, ~17:20): compact Moria renders every time** over several games.

**Step 4 (installed ~17:25): every capital + every city-state city gets Moria's model, no fog of war.**
`landmarks.ALL_CAPITALS_TEST = True`: `MEC_Landmarks.lua` gives the first enabled landmark to every city where
`city:IsCapital()` or the owner `IsMinorCiv()`, whatever its name (still on the owner's turn after founding).
`landmarks.REVEAL_MAP = True`: at load, every plot is revealed and made visible for every human player's team
(`SetRevealed` + `ChangeVisibilityCount`, the same calls as the stock debug reveal in `InGame.lua`).
`Lua.log`: `MEC_Landmarks: TEST: fog of war removed ...` and one `... BUILDING_MEC_LM_MORIA = 1` line per city.
Both switches must go back to `False` before the pack is shared.

**Result 4 (user, ~17:30): only Moria drew; every other capital and city-state showed stock art.** `Lua.log`: 12 AI
capitals were founded, but only Moria was ever GIVEN the building (by its name, on the next turn). So this was not a
render failure: the "every capital" path never gave the building (it relied on `IsCapital()` + the owner's own
`PlayerDoTurn`). Fog removal worked (8000 plots).

**Step 5 (installed ~17:35): every city, given at founding.** `ALL_CITIES_TEST = True` (every city of every player,
no `IsCapital` check), `GIVE_AT_FOUNDING = True` (added in `PlayerCityFounded`), and every `PlayerDoTurn` now re-checks
ALL cities (not only that player's), so a city the founding event missed is fixed on the next turn of anyone.
Slow AI turns with no fog: the user's `UserSettings.ini` has `SinglePlayerQuickMovementEnabled = 0`, so every AI move
that is now visible is animated. Single player has no simultaneous-turn option; the reveal code does not touch turn mode.

**Result 5 (user, ~17:40): compact Moria drew in EVERY city and city-state** (given at founding, no fog), including
the user's second city. So the mechanism, at-founding giving, many copies and non-capital cities all work at compact size.

**Step 6 (installed ~17:45): full tile in every city.** `GROW = 24 / 10.5` again (art byte-identical to the failed
full-tile test of ~17:06), everything else as step 5. Shows which cities (if any) draw a whole-tile model.

**Result 6 (user, ~17:50): uniform full tile drew in only Barad-dûr, Rhûn and Umbar**; every other city (all ~30 were
given the building, per `Lua.log`) showed an EMPTY tile. Barad-dûr's tile also drew our big Barad models most of the
time, Mount Doom's (65,24) never: which cities fail depends on location and repeats.

**Step 7 (installed ~18:00): three ways to look bigger, one game.** Every city gets one of three Moria versions, all
whole-tile size in some way, all with the compact +-10.5 tree cut (`landmarks.py` rows `MORIA_SCALE/WIDE/TALL`):
- **A, game scale:** the compact `.gr2` that drew everywhere, byte-identical, shown at fScale 0.1143 (x2.29) through its
  own `.fxsxml` copy. Tests whether the limit is in the file's coordinates or in the size on screen.
- **B, wide and low:** footprint grown to the whole tile (+-24 x +-27.7), height kept at 12.7.
- **C, narrow and tall:** compact footprint (+-10.5), height grown to 29.

Assignment by position, `((14x + 12y) mod 17) mod 3` in `MEC_Landmarks.lua`: 10/10/10 on the fixed-start map, and the
three cities that drew in step 6 get one version each. Expected per city: `docs/moria_size_test_cities.txt`
(city-states may move between games; `Lua.log` names the building each city really got).

**Result 7 (user, ~18:10): HEIGHT is fine, WIDTH breaks it.** Every city was given its version (`Lua.log`, 31 cities):

| Version | Drew | Cities that drew |
|---|---|---|
| A, compact file at fScale x2.29 (whole tile on screen) | **0 / 11** | none (even Umbar, which drew the uniform full-size file in step 6) |
| B, wide and low (+-24, 12.7 high) | **1 / 10** | Rhûn (also drew in step 6) |
| C, narrow and tall (+-10.5, 29 high) | **11 / 11** | Rivendell, Northern Mirkwood, Edoras, Lake Town, Entwood, Rhosgobel, Smaug's Lair, Bree, Alatar, Rhovanion, Dale (user had missed Dale at first) |

So a model can be 29 units tall (more than double the compact height) and still draw, but a footprint that reaches the
whole tile fails almost everywhere, whether it's built into the file (B) or applied by the game's fScale (A). The
limit is horizontal: somewhere between +-10.5 (draws everywhere) and +-24 (fails almost everywhere). Logs saved in
`~/civ5-backup-20261121-capitals/moria-abc-*/Logs-abc-result`.

**Step 8 (built ~18:20, installed when the game closes): how wide can it be?** The compact model grown UNIFORMLY (no
distortion) to three footprints between the safe +-10.5 and the failing +-24: `MORIA_F14` (+-14, 16.9 high),
`MORIA_F17` (+-17, 20.6 high), `MORIA_F20` (+-20, 24.2 high); all heights under the proven 29, tree cut +-10.5, same
per-position split (11/10/11). Expected per city: `docs/moria_size_test_cities.txt`. The largest footprint that draws
everywhere becomes the size limit for every landmark.

**Result 8 (user, ~18:35): +-14 draws everywhere; +-17 and +-20 fail only in city-states.**

| Version | Drew | Empty tiles |
|---|---|---|
| +-14 (16.9 high) | **10 / 10** (4 majors incl. Moria, 6 city-states) | none |
| +-17 (20.6 high) | **7 / 10** (all 4 majors drew) | Himling, Lossoth, Tol Morwen (city-states) |
| +-20 (24.2 high) | **7 / 11** (all 3 majors drew) | Kingdom of Rhovanion, Rhosgobel, Lake Town, Smaug's Lair (city-states) |

Every one of the 7 failures is a city-state; every major civ city drew at all three sizes. (In step 7, the +-24 "wide"
version also failed in major cities: Erebor, Carn Dûn, Sirannon.) **+-14 is the proven safe footprint** (1.33x the
compact model, about 58 % of the tile's width). Between +-14 and +-24 the limit is lower for city-states than for
major civ cities; why is not known yet.

**Step 9 (built ~18:45): city-states only, +-15 / +-15.5 / +-16.** `TEST_MINORS_ONLY = True`: only city-states get a test
model; major civ cities behave normally (Moria keeps its compact model). Uniform growth like step 8, tree cut +-10.5.
Split `((9x + 5y) mod 17) mod 3` (`landmarks.TEST_HASH`): 6/7/6 city-states, and the 7 that failed in step 8 land on all
three sizes. Expected list: `docs/moria_size_test_cities.txt`. After this: lock the size for Moria (option 1).

**Result 9 (user, ~18:40): all 18 city-states drew** (+-15: 7, +-15.5: 6, +-16: 5), including six that failed at +-17/+-20
in step 8 (Himling, Lake Town, Smaug's Lair, Lossoth, Rhovanion, Tol Morwen; Rhosgobel was not founded this game).
Moria (compact, by name) drew; other major cities stock, as designed.
**Proven safe footprints:** city-states +-16, major civ cities +-20 (7/7 at +-17/+-20; only 3 of ~12 at +-24). Height up to 29.

**The tile is bigger than we assumed.** The user's screenshot of Dale (+-15 model) shows the model's 30-unit-wide base
covering ~320 px of a ~700 px wide tile: the tile is about **+-32 world units** to its flat sides, not +-24 (the old
`ENVELOPE` figure, calibrated on a scaled model in 2026-11-21 shots). So "full tile" (+-24) in steps 6-7 was only ~75 % of
the tile, and the safe +-16 covers ~half of it. The model's own ground plate (our terrain disc + dark skirt) is what reads
as a small hexagon sitting inside the tile. Screenshot: `~/civ5-backup-20261121-capitals/moria-cs-*/screenshot-dale-F15.png`.

## 13. Moria v2: as big as the game draws it (2026-11-24 ~19:00, installed, awaiting the user's check)

Rebuilt `tools/landmarks/models/moria.py` from the size limits of §12 (major civ cities: footprint +-20; Moria is always
a major civ's city):
- **No ground plate** (no terrain disc, no rim): the model stands on the game's own terrain, so no hexagon outline shows.
- **Removed** everything not needed: goblin palisade, banners, skull totem, ruined stair, firs.
- **New layout (lore):** the West-gate at the end of a bay of sheer cliffs; the ridges of the Misty Mountains wrap round
  the sides and run towards the camera; the Watcher's dark lake fills the bay; the two holly trees; Caradhras behind.
- **Size:** laid out in design units (+-10.5) and grown by 20/10.5, so it fits inside the exact box of the `+-20` test
  model that drew in every major civ city: x +-19.1, y -13.4..22.2, z -2.9..23.9; 8640 vertices; fScale 0.05;
  tree cut +-10.5 (as in every passing test); zeroed OBB, stock section layout.
- **Fixed:** `blib.terrain()` wrote its edge skirts facing inwards (back faces the game doesn't draw); now outwards.

**Check (installed):** `TEST_SCOPE = 'majors'`: every MAJOR civ city gets this final Moria at founding (city-states stock),
fog off. Then option 1: Moria by name only, fog back, test switches off.

**Result v2 (user, 4 runs, one launch each?, ~19:10):** city-states stock (as designed); all major capitals drew the v2
Moria except 1-2 per run, a different set each time: run 1 Rivendell; run 2 Rohan (Edoras); run 3 Rivendell + Northern
Mirkwood (the user's second city, founded on turn 2, drew); run 4 Rivendell + Erebor. Rivendell failed 3 of 4.
User's hypothesis: some rendering budget/limit is exhausted (1-2 failures, varying). Test: make Moria high fidelity
(much heavier) and compare.

## 14. Moria v3: high fidelity (2026-11-24 ~19:20, installed, same test as v2)

Same layout and size as v2 (inside the +-20 box: x +-19.6, y -13.4..21.8, z -2.9..23.6), but:
- **Geometry:** smooth shading, height field 92 x 98 with multi-octave rock relief and crags, a finely subdivided doors'
  wall (buried in the ridges at both ends), round foliage clusters, smooth tentacles: 16 441 vertices / 16 956 triangles
  (v2: 8 640 / 4 100; the largest stock wonders: ~22k vertices).
- **Textures:** new `tools/landmarks/bake.py` (used when a model sets `BAKE = True`): Smart UV unwrap of the whole model,
  procedural Blender materials (two-tone noise, colour by height with a ragged snow line on Caradhras, rock colour on
  steep slopes, distorted cracks, strata, moss on low gentle ground), baked base colour + ambient occlusion, SREF from
  per-material specular/reflection. **1024 DIFF / 512 SREF** (v2: 512 / 256).
- **The ithildin glow:** every line of the Doors of Durin (incl. letters, stars and rays, which are only painted) is
  rasterised into a soft two-level blue halo and painted on the doors' wall; the modelled lines use one solid swatch of
  colour (no tiny texture islands, no mip-map bleeding) and are staggered in depth so overlapping segments don't flicker.
- Fixed on the way: uv islands of tiny faces baked black between other islands (now solid swatch); `blib.terrain`
  skirts (§13).
Test unchanged: every major civ city gets it at founding, fog off. Compare the failure count with v2 (1-2 per run).

**Result v3 (user, ~19:35):** every major capital drew the high-fidelity Moria except Edoras (1 of ~12). The heavier
model (2x vertices, 4x texture memory) did not fail more than v2 (1-2 per run): no sign of an exhausted rendering budget.

## 15. Wrap-up (2026-11-24 ~19:40): Moria only

State left for the user to commit:
- `landmarks.ALL_CITIES_TEST = False`: only a city named Moria (key `TXT_KEY_CITY_NAME_MEC_MORIA`, or a typed alias such
  as "Khazad-dûm") gets `BUILDING_MEC_LM_MORIA`, at founding (`GIVE_AT_FOUNDING = True`); every PlayerDoTurn re-checks
  all cities (renames, captures). Other cities and city-states: stock.
- `landmarks.REVEAL_MAP = True` kept on purpose (testing the next models); **set False before sharing the pack.**
- Model: `tools/landmarks/models/moria.py` v3 (`BAKE = True` -> `tools/landmarks/bake.py`), 16 441 vertices, 1024 DIFF.
- Test machinery kept but off: `ALL_CITIES_TEST`, `TEST_SCOPE`, `TEST_HASH`, `size_test` rows (none left).
- Offline test: `build/venv/bin/python tools/landmarks/test_landmarks.py` (Moria only, at founding, fog off).

Rendering, what is known: (1) footprint is the main limit (height is not); (2) within the limit, 80-100 % of tiles draw,
the failures vary per game (Rivendell most often), no relation to model weight found; (3) the old "second city never
draws" was the footprint (ours were +-24). Open: the remaining ~10 % — revisit when more models exist.

## 16. Full Barad-dûr on every city (2026-11-24 ~19:45, installed, awaiting the user's test)

Same test as Moria's (§12): `ALL_CITIES_TEST = True`, `TEST_SCOPE = 'all'` (every city AND city-state, Moria included),
given at founding, fog off. The model is the unchanged full Barad-dûr from 2026-11-23 (`build/landmarks/out`, files of
16:10; not rebuilt): fortress + tower 47 high, footprint +-24 x +-27 (over the +-20 limit of §12), skinned Eye with the
gaze animation (`United_Nations_DecistionTree`), 8 fire effects + core blaze + beam on the Eye's bones, fScale 0.25.
Expectation from §12: a footprint over +-20 should fail in most cities; the question is whether the animated/effect
layers change that. Back to "Moria only": `ALL_CITIES_TEST = False`, Barad-dûr row `enabled=False`.

**Result §16 (user, ~19:55): full Barad-dûr v3 drew in only Annúminas and Carn Dûm** (2 of ~30); every other capital and
every city-state stayed an empty tile. Moria v3 in the same kind of test: 80-90 %.

## 17. Barad-dûr v4: built like Moria (2026-11-24 ~20:10, installed, same every-city test)

| | Moria v3 (80-90 %) | Barad-dûr v3 (2/30) | **Barad-dûr v4** |
|---|---|---|---|
| footprint | +-19.6 x -13.4..21.8 | +-24 x +-27 | **+-15.4 x +-17.3** (city-state-safe +-16) |
| height | 23.6 | 47 | **23.9** |
| fScale | 0.05 | 0.25 | **0.05** |
| parts | 1 static | static + skinned animated Eye | **1 static** (Eye modelled) |
| effects | none | 8 fires + blaze + beam | **none** |
| decision tree | Wonder | United Nations | **Wonder** |
| textures | baked 1024 | atlas 512 | **baked 1024** |
| tree cut | +-10.5 | +-7.5 | **+-10.5** |
| vertices | 16 441 | ~21k (+ Eye) | **19 211** |

`tools/landmarks/models/barad_dur.py` v4 (v3 in git history): no ground plate (a jagged black outcrop), hexagonal outer
wall with crenellations, spiked buttresses, six corner bastions, a glowing gate between two gate towers, the inner
terrace with six lesser towers and flying buttresses, the four-tier great tower (ribs, down-turned spikes, fiery slits),
the iron crown of two great horns (Catmull-Rom splines) and the static Eye (rim, flames, iris, core, slit pupil).
`bake.py`: UV islands smaller than `b.tiny_px` square pixels go on their material's solid colour swatch (Barad: 40).
Test: `ALL_CITIES_TEST`, scope 'all' (every city and city-state), at founding, fog off. If it draws like Moria, add back
the Eye's animation, then the fire, then the beam, one per test.

## 18. Root-cause probe: "invisible outriggers" (2026-11-24 ~21:10, installed, awaiting the user's test)

**Investigation findings this is based on** (static, exe + game files; details in the session report):
- Stock art keeps a strict footprint per art slot: palace slot 32 (city centre) +-4..6; land wonders/castle/colosseum
  (1/2/4) +-5..15, max ~+-20 (Red Fort, Pyramids); harbour/lighthouse up to +-23; mountain slot 64 +-22..30. Height is
  free (up to 54). Our measured limits (+-16 always, majors +-20, +-24 ~10 %) sit exactly at the land-wonder ceiling.
- Slot 32 places the model at the plot centre (terrain height, fixed rotation), no size check, then queues a city
  update. The city layout ("RoadLayout", tensor fields TF_Small_City / TF_Large_City, polygon overlap fixups) and the
  city-vis code use the CRT `rand()` (per process, not synced) -> render-side randomness. Its diagnostics are compiled
  out (log function 0x422eb0 is `xor al,al; ret`), so no log will ever show the failure.
- MEC's six `ArtInfoCulturalVariation` lines are a no-op in this exe: with them, PALACE/CASTLE/COLESSEUM are looked up
  plainly (undefined); without them as "EUROPEAN  PALACE" (double space from the trailing-space prefix), also
  undefined; the lookup is an exact strcmp. Base WonderModels.fpk DOES define EUROPEAN/ASIAN/AFRICAN/AMERICAN/
  MEDITERRANEAN PALACE/CASTLE/COLESSEUM (correcting §1.2).

**Question:** does the engine react to the landmark's BOUNDS, or to its VISIBLE geometry?

**Three versions in one game** (every city + city-state, given at founding, fog off; `TEST_HASH (4, 9, 20)`;
per-city list `docs/outrig_test_cities.txt`):

| | file | visible | bounding box / radius | earlier result |
|---|---|---|---|---|
| A control | `MEC_LM_Moria_Tall` (byte-identical to step 7) | +-10.5 x +-12.1, 29 high | same | 11/11 |
| **B probe** | `MEC_LM_Moria_Outrig` (`tools/landmarks/outrig_probe.py`) | **identical to A** | **= C** (x +-24, y +-27.7, r 27.7) | new |
| C positive control | `MEC_LM_Moria_Wide` (byte-identical to step 7) | +-24 x +-27.7, 12.7 high | same | 1/10 |

B = A's mesh + 6 triangles 0.1 units across at z -1 on the corners of C's hexagon (18 extra vertices).

**Reading the result** (A must draw and C must mostly fail, otherwise the run is not conclusive):
- B fails like C -> the engine reacts to the extent/bounds alone (culling, cell assignment, layout reservation from the
  bbox). Next: find the consumer of the bounds; a fix may be possible by keeping bounds small (e.g. split models).
- B draws like A -> the real geometry's coverage matters (overlap with the layout's houses/lots, stencil, depth).
  Next: a frame capture of a failing tile (draw calls issued or not).
- Mixed -> repeat 2 more games; compare per city.

Revert: Barad-dûr row `enabled=True` (v4 test) or remove the three `MORIA_*` probe rows; `TEST_HASH` back as needed.
Backup of the previous install + the Barad-dûr v4 run's Logs: `~/civ5-backup-20261121-capitals/outrig-20261124-211151`.

**Result §18 (user, 1 game, ~21:20). Assignments confirmed in `Lua.log` (31 cities; Northern Mirkwood not founded).
Logs: `~/civ5-backup-20261121-capitals/outrig-20261124-211151/Logs-outrig-result`.**

| Group | Drew | Empty |
|---|---|---|
| A control (Tall, visible +-10.5, bounds +-10.5) | **10 / 12** | Bag End, Shelob's Lair |
| **B probe (looks like A, bounds = C)** | **0 / 10** | all: Annúminas, Beorn's Hall, Bree, Erebor, Himling, Lake Town, Minas Tirith, Paths of the Dead, Rhosgobel, Rhûn |
| C positive control (Wide, +-24) | **0 / 10** | all |

**Conclusion (the clearest result of the whole investigation): the failure follows the model's BOUNDS, not its visible
geometry.** Six invisible 0.1-unit specks at +-24/27.7 turn a model that draws into one that blanks the whole tile
(houses too), exactly like the real wide model. Every city that drew had the small bounds; no city with the large
bounds drew, including Rhûn, which had drawn the wide model twice before. So overlap of visible geometry with houses,
stencil/depth effects, textures, vertex count and material are not the cause. Something in the engine reads the
landmark mesh's extent (from its vertices: the bone-binding OBBs are zeroed) and, above some size, the city's whole
model group stops drawing.

Still open:
1. **Which engine code consumes the bounds**, and the exact threshold rule (city-states fail from ~+-17, majors from
   ~+-20; earlier +-24 successes were rare). Candidates: city group bounds / culling cell assignment, or the city
   layout reserving the building's area. Static RE target: what `0x4e8b40` / `0x4de0b0` (instance into city group)
   compute from the mesh bounds, and who reads them.
2. **A second, smaller failure:** 2 of 12 small-bounds cities stayed empty (Bag End, Shelob's Lair), like the 1-2 per
   game seen with Moria v2/v3. It may be the same rule with a lower, random margin (render-side `rand()`), or the
   pre-existing bug the original mods show. Not separated yet.

Practical consequence until (1) is understood: every landmark's VERTEX extent (not just what looks visible) must stay
inside the proven envelope: +-16 for city-states, +-20 for majors, measured over all vertices of the building mesh.
Splitting a model into several smaller-bounds parts is an untested idea (it depends on whether the rule is per mesh or
per city group).

State left installed (test build, not for sharing): `ALL_CITIES_TEST` on with the three probe rows, `REVEAL_MAP` on,
Barad-dûr row off. To return to "Moria only": remove the three `MORIA_*` rows, `ALL_CITIES_TEST = False`.
