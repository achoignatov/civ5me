# Capital landmarks: how they work and how to add one

**Status 2026-11-24 night: the improvement approach works, and the first release is being checked.** Two render
tests drew a custom model on **every major capital and every city-state** in one game: Barad-dûr (static v4), then
Moria. This is now the project's only rendering path for custom city models.

**Release under test (installed 2026-11-24 22:27):** Moria (the Goblins' capital) shows our Moria model; Barad-dûr
(Mordor's capital) shows the Eye of Sauron with its animation, fires and beam; every other city and city-state shows
stock art. Fog of war is still off so both capitals can be checked; it goes back on in the release commit. Research and evidence:
[`CITY_ARCHITECTURE_RESEARCH.md`](CITY_ARCHITECTURE_RESEARCH.md). History of the old approach:
[`CITY_MODELS.md`](CITY_MODELS.md).

**Goal:** a custom 3D landmark for every Middle-earth capital (14 civs), later special cities and city-states.
**Out of scope (decided 2026-11-24):** models that change as the population grows. The native houses still grow
by themselves; the landmark never changes with population.

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

- A landmark is a **tile improvement** with no gameplay (no yields, no Build row, `Permanent`). Workers can never
  build it; only the script places it.
- The city's own art (houses, palace, wonders) is **never touched**. No `WonderDefines`, no dummy buildings.
- Founding and capture clear a city plot's improvement (`CvCity::init` in the game DLL), so the script re-applies it
  on those events and checks every city on every turn. Syncing twice changes nothing.
- Multiplayer: only `GameEvents` and synchronised data (players, plots, name **keys**), so every client sets the same
  plots. Never use the localised city name, and never index `GameInfo.X["TYPE"]` directly (it returned wrong rows
  in game on 2026-11-23); build lookups by iterating the rows.
- Logging: every change writes `MEC_LMI: ... -> <improvement>, plot now reports <improvement>` to `Lua.log`
  (read back from the game, so the log shows the real state).

## 2. Files

| Piece | Where |
|---|---|
| Landmark table, switches, XML/Lua generators | `tools/landmarks/improvements.py` |
| In-game script (template; the table is inserted at build time) | `tools/landmarks/MEC_LandmarkImprovements.lua` |
| Pack integration (art copy, fxsxml, GameData + text, Lua hook, database and file checks) | `tools/build_dlc.py` → `build_landmark_improvements()` |
| Offline Lua test (strict mock of the game API) | `tools/landmarks/test_improvements.py` |
| Vendored art that ships (exact files that drew in game) | `vendor/landmarks/<Model>/` (see its `SOURCE.md`) |
| Our Blender models | `tools/landmarks/models/*.py` (Barad-dûr, Moria, Mount Doom), `tools/capitals/models/*.py` (first-generation models of all 14 capitals and 26 city-states) |
| Blender driver, texture baking | `tools/landmarks/build_models.py`, `tools/landmarks/bake.py` → `build/landmarks/out/` |

Build and check:

```
python3 tools/build.py && python3 tools/build_dlc.py --zip     # improvement landmarks are the default (no Blender needed)
build/venv/bin/python tools/landmarks/test_improvements.py      # Lua logic test (needs lupa in build/venv)
python3 tools/build_dlc.py --zip --no-landmarks                 # pack without any landmarks
python3 tools/build_dlc.py --zip --landmark-buildings           # OLD city-art path (history only)
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
are `TimedTrigger` files on bones listed in `BoneUsage` (as the stock gold mine does). Effects named
`ART_DEF_VEFFECT_MEC_*` are defined in `MEDLC_LandmarkImprovements_VisEffects.xml` (and the beam's model effect in
`..._VisEffectModels.xml`), registered in the DLC package as `<VisEffectInfoDefines>` / `<VisEffectModelDefines>`.

## 4. Model rules (what is proven)

| Item | Proven in game (2026-11-24) | Notes |
|---|---|---|
| File | Barad-dûr v4 `.gr2` from our own writer (uncompressed, stock-like sections, zeroed OBB), 19.2k vertices, 1024² DIFF | The same file the old path could only draw at about two-thirds of this size |
| Size | `Scale` 0.12 on a ±308 × ±346 × 478 file = about **±37 × ±41, 57 tall** | Slightly wider than the hex: the walls overlap the neighbouring tiles, as the stock citadel does. Calibrate per model |
| Size, second model | Moria: `Scale` 0.094 on a ±391 × (−268..+435) × 471 file = about ±37 × (−25..+41), 44 tall | Drew everywhere too |
| Count | About 30 copies in one game, majors and city-states | |
| Coexistence | Houses and city buildings draw with it | The landmark covers part of the houses |
| Community art | Elven Battle Tower (Nexus Buddy 2 export) and stock citadel art also drew | |

**Being tested now (release build):** animation (the Eye's idle loop through `LandmarkDecisionTree`), particle
effects (fires) and the beam on an improvement, and two different landmarks in one game. Barad-dûr v3 is placed at
`Scale` 0.3 (about ±28 × ±33, 56 tall); its effect sizes were tuned for the old wonder `fScale` 0.25, so if the fires or
the beam look too big or too small, adjust `VIS_EFFECTS` in `improvements.py` (no model rebuild).
**Not yet proven:** repeat launches (several games in a row and in one process), models taller than 57.

**Authoring rules:** Z-up, origin at the hex centre, ground at z = 0. Keep the footprint inside the hex (aim for
≤ ±40 in-game units, i.e. file size × `Scale`), keep vertices ≤ 22k per model, textures 512–1024². Leave room in the
middle of the tile, or put the landmark on one side, so the houses stay visible. The old ±16/±20 city-art limits and
the `ENVELOPE` in `landmarks.py` do **not** apply to improvements.

## 5. Switches (`tools/landmarks/improvements.py`)

| Switch | Installed now (release under test) | Release commit | Use |
|---|---|---|---|
| `ALL_CITIES` | `None` | `None` | A landmark key: EVERY city and city-state gets it (render test of a new model) |
| `CONTROLS` | `[]` | `[]` | Control plots next to Mordor's capital (test 1 only) |
| `REVEAL_MAP` | `True` (fog off) | `False` | Lets you check every capital in one game |

## 6. The capital models

**Rules (done 2026-11-24):** a city gets a landmark when its name **key** is one of the row's `name_keys`
(the same with or without Dynamic City Naming), or a player typed one of its `aliases` (case-insensitive). Every
other city keeps stock art. A landmark follows the city's name, not its owner: a captured Barad-dûr keeps the Eye; a
city renamed away loses it on the next turn.

**Adding a capital (one at a time):**

1. Build the model in Blender (`tools/landmarks/models/<name>.py`, `tools/landmarks/build_models.py`), within §4.
2. Convert the `.gr2` like the others (stock section layout, zeroed OBBs) and copy the files to
   `vendor/landmarks/<Model>/`.
3. Add a row to `IMPROVEMENTS` (key, title, dir, gr2, textures, scale, name_keys, aliases; animation, bones and
   trigger only if it has them).
4. Render test: set `ALL_CITIES` to its key, build, install, check that every city and city-state draws it.
5. Set `ALL_CITIES = None`, build, check it appears only on its capital, commit.

| Civ | Capital (name key) | Model | Status |
|---|---|---|---|
| Mordor | Barad-dûr (`MEC_BARAD_DUR`) | Barad-dûr v3, the animated Eye (`vendor/landmarks/BaradDur`) | Release under test |
| Goblins | Moria (`MEC_MORIA`) | Moria v3 (`vendor/landmarks/Moria`) | Drew everywhere (test 2); release under test |
| Gondor | Minas Tirith (`MEC_MINAS_TIRITH`) | `tools/capitals/models/gondor.py` (first generation) | To rebuild |
| Dwarves | Erebor (`MEC_EREBOR`) | `tools/capitals/models/dwarves.py` | To rebuild |
| Hobbits | The Shire (`MEC_THE_SHIRE`) | `tools/capitals/models/hobbits.py` (Bag End) | To rebuild |
| High Elves | Rivendell (`MEC_RIVENDELL`) | `tools/capitals/models/high_elves.py` | To rebuild |
| Wood Elves | Northern Mirkwood (`MEC_NORTHERN_MIRKWOOD`) | `tools/capitals/models/wood_elves.py` | To rebuild |
| Isengard | Isengard (`MEC_ISENGARD`) | `tools/capitals/models/isengard.py` | To rebuild |
| Rohan | Edoras (`MEC_EDORAS`) | `tools/capitals/models/rohan.py` | To rebuild |
| Arnor | Annúminas (`MEC_ANNUMINAS`) | `tools/capitals/models/arnor.py` | To rebuild |
| Angmar | Carn Dûm (`MEC_CARN_DUN`) | `tools/capitals/models/angmar.py` | To rebuild |
| Easterlings | Rhûn (`MEC_RHUN`) | `tools/capitals/models/easterlings.py` | To rebuild |
| Southrons | Harad (`MEC_HARAD`) | `tools/capitals/models/southrons.py` | To rebuild |
| Umbar | Umbar (`MEC_UMBAR`) | `tools/capitals/models/umbar.py` | To rebuild |

"To rebuild" means the first-generation scripts exist but were made for the old envelope and pipeline; they need
porting to the `tools/landmarks` builder (as Moria and Barad-dûr were) and a size check against §4.


## 7. Why this works and the old approach failed randomly

**Short answer:** the old approach put our model *inside the city's own composite model*, a system built for small,
fixed pieces and full of hidden size checks and randomness. The new approach uses a *separate* system, the tile
improvements, which is built to draw one big model per tile. Nothing about the city can interfere with it.

**The old path (city art).** A city tile is drawn as one group: the culture's houses plus one model per building in
fixed art slots. Our landmark was a building in the palace slot. What we measured (`CITY_MODELS.md` §12–§18):

- Stock art in that slot is tiny (palace ±4–6 units). Our models failed more often the bigger they were, and the
  failure followed the mesh's **vertex bounds**, not what was visible: invisible specks at the corners made a small
  model fail 10 times out of 10 (§18).
- The failure depended on the **city's location and the game**, not on the file: the same file drew in one city and
  not in another, and drew in one launch but not the next. City-states had a smaller safe size than majors.
- When it failed, the **whole city group** stopped drawing, houses included, a fraction of a second after appearing.
- The engine lays out each city's houses with an **unsynchronised random generator**, and its layout logging is
  compiled out of the game, so nothing reports why a group is dropped.

The explanation that fits all of this (an inference: the exact code was never found) is that the city layout fits
building art into the space its random house layout leaves. A model whose bounds exceed the slot can collide with
that layout or be rejected by it. Whether it does depends on the random layout, the terrain and the city type, so
it looks random from outside. The original mods' sporadic vanishing cities may come from the same fragile system
(unproven).

**The new path (improvements).** An improvement is plot state, drawn by the landmark system that draws farms, mines
and citadels:

- One model per plot, placed at the plot centre with a fixed `SNAPSHOT` layout. There is no slot packing, no random
  house layout and no group shared with other models.
- It is designed for **tile-filling models**: stock improvements span ±45 to ±78 units (we measured 86 of them), so
  Barad-dûr at ±41 is ordinary for this system.
- The game DLL just hands the plot's improvement to the renderer, also on a city plot (`CvPlot::updateLayout`); the
  city's own art is never involved, so it cannot take the landmark down with it.
- The art is plain database rows, the same kind the pack already used for resources, instead of DLC-only
  `WonderDefines`.

The houses keep using the old system, which is fine: they are stock art, which that system handles reliably.
