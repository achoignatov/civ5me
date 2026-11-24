# Capital landmarks: how they work and how to add one

**Status 2026-11-24: the improvement approach works.** In the first in-game test, Barad-dûr drew on **every major
capital and every city-state** in one game (about 30 tiles), at a size the old city-art approach never drew. This is
now the project's only rendering path for custom city models. Research and evidence:
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
| Our Blender models | `tools/landmarks/models/*.py` (Barad-dûr, Moria, Mount Doom), `tools/capitals/models/*.py` (first-generation models of all 14 capitals and 26 city-states) |
| Blender driver, texture baking | `tools/landmarks/build_models.py`, `tools/landmarks/bake.py` → `build/landmarks/out/` |

Build and check:

```
python3 tools/build.py && python3 tools/build_dlc.py --zip     # improvement landmarks are the default
build/venv/bin/python tools/landmarks/test_improvements.py      # Lua logic test (needs lupa in build/venv)
python3 tools/build_dlc.py --zip --no-landmarks                 # pack without any landmarks
python3 tools/build_dlc.py --zip --landmark-buildings           # OLD city-art path (history only)
```

The build fails if a model file is missing, if an `.fxsxml` names a file that is neither in the pack nor in the
game's own `.fpk` packs, if the rows change anything but the four tables below, or if a landmark has a Build row.

## 3. One landmark = these rows (generated from `improvements.IMPROVEMENTS`)

| Table | Row |
|---|---|
| `ArtDefine_LandmarkTypes` | `ART_DEF_IMPROVEMENT_MEC_LM_<KEY>`, LandmarkType `Improvement` |
| `ArtDefine_Landmarks` | Era `Any`, State `Constructed` and `Pillaged` → `MEC_LMI_<Key>.fxsxml`, `Scale`, LayoutHandler `SNAPSHOT`, ResourceType `ART_DEF_RESOURCE_ALL`, TerrainContour 1 |
| `ArtDefine_StrategicView` | TileType `Improvement`, an icon (`SV_Citadel.dds` for now) |
| `Improvements` | `IMPROVEMENT_MEC_LM_<KEY>`, `ArtDefineTag`, `Permanent`, no yields, text `TXT_KEY_IMPROVEMENT_MEC_LM_<KEY>` |

The `.fxsxml` is written like the stock improvement files (`Anc_Citadel.fxsxml`): one mesh plus its textures, no
decision tree.

## 4. Model rules (what is proven)

| Item | Proven in game (2026-11-24) | Notes |
|---|---|---|
| File | Barad-dûr v4 `.gr2` from our own writer (uncompressed, stock-like sections, zeroed OBB), 19.2k vertices, 1024² DIFF | The same file the old path could only draw at about two-thirds of this size |
| Size | `Scale` 0.12 on a ±308 × ±346 × 478 file = about **±37 × ±41, 57 tall** | Slightly wider than the hex: the walls overlap the neighbouring tiles, as the stock citadel does. Calibrate per model |
| Count | About 30 copies in one game, majors and city-states | |
| Coexistence | Houses and city buildings draw with it | The landmark covers part of the houses |
| Community art | Elven Battle Tower (Nexus Buddy 2 export) and stock citadel art also drew | |

**Not yet proven:** repeat launches (several games in a row and in one process), animation, particle effects, models
taller than 57, more than one landmark type per game. Treat each as a test the first time it is used.

**Authoring rules:** Z-up, origin at the hex centre, ground at z = 0. Keep the footprint inside the hex (aim for
≤ ±40 in-game units, i.e. file size × `Scale`), keep vertices ≤ 22k per model, textures 512–1024². Leave room in the
middle of the tile, or put the landmark on one side, so the houses stay visible. The old ±16/±20 city-art limits and
the `ENVELOPE` in `landmarks.py` do **not** apply to improvements.

## 5. Current switches (`tools/landmarks/improvements.py`)

| Switch | Installed value (test build) | Before sharing the pack |
|---|---|---|
| `ALL_CITIES` | `'BARAD_DUR'`: every city gets Barad-dûr | Replace with per-capital rules (§6 step 1) |
| `CONTROLS` | A Barad-dûr, B Elven Battle Tower, C stock citadel, next to Mordor's capital | `[]` (they take workable tiles) |
| `REVEAL_MAP` | `True` (no fog of war for human players) | `False` |

## 6. Ground work for the capital models

**Step 1, the rules table (code, next prompt).** Replace `ALL_CITIES` with a lookup in this order, first match wins:
(1) the city's name key (`TXT_KEY_CITY_NAME_MEC_*`, plus typed aliases), (2) the capital of a civ
(`city:IsCapital()` and the owner's civ type), (3) nothing. A city that no longer matches (renamed, captured) loses
our improvement. Remove the controls, switch the fog back on, extend `test_improvements.py`.

**Step 2, one model at a time.** Each new model: build in Blender → write the `.gr2` → add one row → build → in-game
check on every city (the `ALL_CITIES` test mode) → then bind it to its capital only.

| Civ | Capital (name key) | Model source we have | Status |
|---|---|---|---|
| Mordor | Barad-dûr (`MEC_BARAD_DUR`) | `tools/landmarks/models/barad_dur.py` (v4, static Eye) | **Draws** (2026-11-24) |
| Goblins | Moria (`MEC_MORIA`) | `tools/landmarks/models/moria.py` (v3, baked) | Drew in the old path; to re-test as an improvement |
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

**Step 3, effects (later).** The Eye's animation, fire and beam worked in the old path's files
(`docs/CITY_MODELS.md` §6). Stock improvements use `TimedTrigger` files on bones; add one effect at a time and test
each.

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
