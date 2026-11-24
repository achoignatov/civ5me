# Middle-earth City Graphics — Architecture Research

2026-11-24 · Exported from the Claude Doc https://claude.ai/artifact/Emn6PzanPSx4g57gPuEaSy (the online copy has the drawn diagram and comments).

> **OUTCOME (2026-11-24 evening): confirmed in game.** Prototype step 1 answered Q1: the game **does** draw an
> improvement on a city plot. Barad-dûr (our own v4 file, `Scale` 0.12, about ±41 units, 57 tall) drew on every
> major capital and every city-state in one game, and all three controls drew (Barad-dûr on a plain tile, the Elven
> Battle Tower, stock citadel art). Approach C is adopted; the D1 adjacent-tile fallback is not needed.
>
> **Decisions since:** population-based evolution is **dropped** (the user: landmarks won't change as cities grow),
> so the population tiers in §8 and prototype step 4 no longer apply. Next goal: a custom landmark for every capital.
> The working doc is now [`LANDMARKS.md`](LANDMARKS.md) (how it works, files, model rules, capital roadmap, and why
> this path works when the old one failed). The rest of this file is the research as written before the test.

## Answer in one paragraph

Starting over, I would not put landmarks into the city's own art at all. I would draw them as **tile improvements**, placed and swapped by synced Lua. Improvement art is plain database rows that a normal mod can ship. The engine draws it for every revealed plot. Stock improvements routinely fill the whole hex (±45 to ±78 units), and the Lua call `Plot:SetImprovementType` exists and is MP-safe from `GameEvents`. City art (Approach A) is the one place where we have measured hard limits: ±16 to ±20 footprints and roughly 1 empty tile in 10 even inside them.

**Recommendation: Approach C, a hybrid.** The native city keeps its houses, which already grow with population. A landmark improvement on the city plot carries each civilization's identity, and tiers swap with population. If the engine refuses to draw improvements on a *city* plot, the same system moves the landmark onto an adjacent tile (Approach D1). That needs no new technique at all.

**One question decides everything and has not been tested: does the engine draw an improvement on a plot that holds a city?** The game DLL clearly passes it to the renderer (verified in source, §4). One fantasy modder says it works. Nobody has published proof. That is prototype step 1, and it takes one game launch.

**Evidence labels used below:** **Verified** = I read the file or source, or we measured it in game. **Inference** = follows from verified facts but untested. **Hypothesis** = needs an experiment.

## 1. What the fantasy improvement project actually does

It converts fantasy buildings into **ordinary Civ5 tile improvements**. It does not touch city graphics. The [thread](https://forums.civfanatics.com/threads/civ-fantasy-improvement-graphic-conversions.557045/) (Nomad or What, 2015 to 2017, one page) is a catalogue with download links, not a how-to. I took the implementation from the files.

**Models listed:** Elven Battle Tower, Elven Barracks, Isengard Wizard Tower (all BFME II), Isengard Fortress (image only, never released), Scorpion Nest and Watchtower (Civ4 ports).

**On cities (verified quote, post #15):** asked whether the city model can be changed, the author answered: "Not quite. You can enlarge an improvement graphic over the city tile, however." He planned it for dwarven mountain cities. He also says "the actual CiV city graphics and the buildings/wonders in them are unable to be modified". That is too strong: we did draw custom building art. But it matches how fragile that path proved.

### How a model is wired in (verified: [Elven Barracks mod](https://forums.civfanatics.com/resources/bfmeii-lotr-elven-barracks.26014/), downloaded and unpacked)

| Piece | Exact content |
| --- | --- |
| Packaging | Normal mod `.modinfo`. Every art file is `import="1"` (VFS). `ReloadLandmarkSystem=1`, `SupportsMultiplayer=1`. No DLC. |
| `ArtDefine_LandmarkTypes` | `ART_DEF_IMPROVEMENT_ELVEN_BARRACKS`, LandmarkType `Improvement` |
| `ArtDefine_Landmarks` | Era `Any`, State `Constructed` → `Elven_Barracks.fxsxml`, State `Pillaged` → `Elven_Barracks_pil.fxsxml`. Scale `1`, LayoutHandler `RANDOM`, ResourceType `ART_DEF_RESOURCE_NONE`, TerrainContour `1` |
| `ArtDefine_StrategicView` | TileType `Improvement`, Asset `sv_landmark.dds` (stock icon) |
| `Improvements` | `IMPROVEMENT_ELVEN_BARRACKS`, `ArtDefineTag` → the art type, `Permanent=1` |
| `.fxsxml` | One `Mesh` (gr2), textures (own DIFF + ground bib + height map, stock `blacksref_SREF`, stock environment maps), `DecisionTree StaticLandmarkDecisionTree.ddtxml`, a `TimedTrigger` on model `Box01`, bones `Point01` and `FX_PillagedSmoke` |
| `.gr2` | Exported by **Nexus Buddy 2** from **Blender 2.49** (read from the file header). Z-up, UnitsPerMeter 39.37. Built on the stock **Holy Site** template: its ground material `Plane01-ground` points at `Holy_Site_GRND_PIL_DIFF.dds` |
| Lua | None. Built by workers through a normal `Build` row. |

**Size (measured with our gr2 reader):** both the Barracks and the Battle Tower span **x,y ±46, height 15.6 and 27.5**. The ±46 comes from the Holy Site ground plane. Stock improvements are the same scale (see §4).

## 2. What we can reuse

The most useful find is that **we already own a known-working conversion**. Middle Earth Civilizations v9 ships Nomad's Elven Battle Tower as `Wood Elves/Art/Improvements/Battle_Tower_B.gr2` (built) and `Battle_Tower_P.gr2` (pillaged), imported into VFS. Its improvement XML (`Wood Elves/XML/Void/Wood_Elves_Improvement_Sentry_Tower.xml`) is switched off (`import="0"`, in `Void/`). So the art loads but nothing uses it. That is the ideal prototype model: no download, no conversion, already in our pack.

| Reusable item | Where | Use |
| --- | --- | --- |
| Elven Battle Tower gr2 + textures | ME Civs v9, Wood Elves/Art/Improvements | Prototype model, step 3 |
| Elven Barracks mod (gr2, fxsxml, SQL) | Downloaded to the session scratchpad (re-download from the resource page) | The exact row and fxsxml template for our landmarks |
| Isengard Wizard Tower, Scorpion Nest, Watchtower | CivFanatics downloads 24336, 24338, 24339 | Optional. The site blocks scripted downloads, so you would fetch them by hand |
| Stock improvement templates (Holy Site, Citadel, Customs House) | `Resource/Common/ImprovementModels.fpk` | Reference skeletons and sizes for our gr2 writer |
| Synced-Lua patterns (name keys, `GameEvents`, iteration-built lookups) | `tools/landmarks/MEC_Landmarks.lua` | Carries over almost unchanged; only the action changes from "give building" to "set improvement" |
| Our Blender models, `bake.py`, gr2 writer | `tools/landmarks`, `tools/capitals` | The models are reusable. The writer needs an improvement-template mode (§7) |

**Not reusable:** the palace-slot or landmark-building art path itself (`WonderDefines`, DisplayPosition 32) and its size envelope. Those exist only because of city art.

## 3. What native city graphics can and cannot do

A city tile is two layers: **houses**, chosen per culture, era and population inside the exe, and **building art**, one model per building the city has, placed in fixed art slots. Neither layer is keyed by city or by civilization except through the six hardcoded cultures.

| Change | Layer | Verdict | Basis |
| --- | --- | --- | --- |
| New model for a building (palace, wonder, dummy landmark) | XML `WonderDefines` | Possible, **DLC packaging only** (mods cannot add `WonderDefines`) | Verified in game, Nov 21 to 24 |
| Which city gets a building | Lua `City:SetNumRealBuilding` from `GameEvents` | Possible, MP-safe | Verified in game |
| Size of building art | Exe, per art slot | **Hard limit.** Palace slot ±4 to 6 stock. We reached ±16 for city-states and ±20 for majors, and about 1 empty capital in 10 even inside that | Verified in game (§12 to §18 of CITY_MODELS.md) |
| Why oversized art fails | Exe reads the mesh **vertex bounds** (invisible outrigger test: 0 of 10 drew) | Not fixable from XML or Lua | Verified in game (§18) |
| Re-skin a whole culture's houses (e.g. Polynesian → orc huts) | XML `CityDefines` / `BuildingArtInfos`, DLC only | Possible. Applies to every civ using that culture | Community-verified (Leugi), not tested by us |
| New culture (house set) for ME | Exe enum of 6 cultures | **Impossible** without the closed graphics code | Community consensus |
| Hide houses for one city | Exe | **Impossible**. Only culture-wide | Verified (tried and reverted) |
| Anything in the renderer (draw distance, bounds, slots) | Exe | Needs engine patching; out of scope | Our disassembly |
| DLL changes | `CvGameCoreDLL` | Possible, but the DLL never decides *how* a city is drawn; it only reports state | Verified in DLL source |

**The MEC city-disappearance note.** `MEC_UnitArtInfoCulturalVariation.xml` sets `ArtInfoCulturalVariation=false` on every building. With the flag on, the exe looks up `<ArtStylePrefix> <tag>` (e.g. `EUROPEAN  PALACE`, note the double space from the mod's trailing-space prefix), fails, and the tile used to blank. Turning the flag off avoided the blank but also removed palace, castle and colosseum art. It is a symptom of the same fragile path, and it is **not** the cause of our failures: it was proven a no-op for our landmarks.

**Conclusion: Approach A is viable only for small, centre-of-tile pieces.** It cannot carry a tile-filling Barad-dûr, and its residual failure rate has no known fix.

## 4. Improvement overlays: what holds and what is open

Everything the game core does with an improvement on a city plot is favourable. The one unknown is the exe's renderer. Source: the original Firaxis BNW DLL ([Gedemon/Civ5-DLL](https://github.com/Gedemon/Civ5-DLL), files `CvPlot.cpp`, `CvCity.cpp`, `Lua/CvLuaPlot.cpp`).

| Question | Answer | Status |
| --- | --- | --- |
| Can Lua put an improvement on a city plot? | Yes. `Plot:SetImprovementType` calls `CvPlot::setImprovementType` directly, with no validity check. The `isCity()` refusal is only in `canHaveImprovement` (worker builds) | **Verified** (source) |
| Does the DLL still send it to the renderer? | Yes. `CvPlot::updateLayout` hides the *resource* on city plots but passes the improvement and its state to `GameplayPlotStateChange` unchanged | **Verified** (source) |
| Does the exe actually draw it on a city plot? | The fantasy modder says yes (post #15). Nobody has published proof | **Hypothesis**, test 1 |
| What removes it? | City founding (`CvCity::init` clears the plot), so also **capture** (capture rebuilds the city through `init`). City destruction replaces it with city ruins. Goody huts, barbarian camps, feature loss (only if `RequiresFeature`) | **Verified** (source) |
| Events to re-apply it | `GameEvents.PlayerCityFounded`, `CityCaptureComplete`, `SetPopulation`, `PlayerDoTurn`; all run in the game core on every client | **Verified** (hook calls in source) |
| Can enemies pillage it? | Pillage needs a unit standing on the plot. Enemy units cannot stand in an enemy city | **Inference** |
| Size | Stock improvements fill the hex: citadel ±45, customs house ±45 × 23 tall, mines up to +78. Nomad's models ±46 | **Verified** (measured 86 stock gr2) |
| Visibility, fog, war | Uses `getRevealedImprovementType`, so each player sees the last state they revealed, like any improvement | **Verified** (source) |
| Save / load | Improvement is plot state; saved like any improvement | **Inference** |
| Multiplayer | Plot state set from `GameEvents` is deterministic. Our landmark Lua already ran this way in MP. Nomad's mod is `SupportsMultiplayer=1` | **Inference** |
| One model per civ, per tier | One `Improvements` row + art type per model. No count limit seen | **Verified** (schema) |
| Overwritten by other mechanics | Nothing in the DLL rewrites a city plot's improvement except the cases above | **Verified** (grep of every `setImprovementType(NO_IMPROVEMENT)`) |
| Hiding the native houses | Not per city (§3). The landmark must coexist with houses or sit beside them | **Verified** |

**Advantages:** normal-mod packaging, tile-sized models, built-in Constructed/Pillaged states, strategic-view icon, Lua control of exactly which plot shows what, and a proven community workflow.

**Disadvantages:** houses still draw under it; the improvement shows in the plot tooltip; and it must be re-applied after capture. If the exe skips improvements on city plots, the landmark has to sit on a neighbouring tile.

## 5. Comparison and ranking

**Ranking: 1. C Hybrid · 2. D1 Adjacent landmark (C's fallback) · 3. B Overlay with houses removed · 4. A Native replacement.** Rows marked * depend on test 1 (improvement drawn on a city plot).

| Criterion | A Native replacement | B Improvement overlay | C Hybrid (houses + landmark) | D1 Landmark on adjacent tile |
| --- | --- | --- | --- | --- |
| Rendering reliability | Measured ~90% per capital inside limits; no fix known | Expected stock-level * | Expected stock-level * | Stock-level; it is a plain improvement |
| Model size | ±16 (city-states), ±20 (majors) | Whole hex, ±45 like stock * | Whole hex, shaped around the houses * | Whole hex |
| Customization freedom | Low (small centrepiece) | High | High | High |
| Different model per civ | Yes, one building per model | Yes, one improvement per model | Yes | Yes |
| Population evolution | Houses only (automatic) | Lua swaps tiers | Houses grow automatically + Lua landmark tiers | Lua swaps tiers |
| Lua | Give or remove a building | Set improvement on events | Same as B | Same, plus choosing the tile |
| XML complexity | `WonderDefines` + Buildings rows, DLC only | 4 small tables, normal mod rows | Same as B | Same as B |
| Multiplayer | Works (verified) | Expected to work (same sync pattern) | Same as B | Same as B |
| Maintenance | High: size envelope, per-launch failures | Low | Low | Low, plus tile-choice edge cases |
| Compatibility with the 6 mods | DLC-only art, touches Buildings | Additive rows only | Additive rows only | Uses up one workable tile; may displace a farm or mine |

**Why B ranks below C:** removing the houses is possible only culture-wide (DLC `CityDefines`), which costs the built-in population growth and touches every civ sharing a culture. C keeps that for free.

**Other alternatives considered and dropped:**

- **Re-skinned culture house sets** (D2). Valid and community-proven, but only 6 sets shared by 14 civs, DLC-only, and big art work. Worth it later as polish for C.
- **Real wonders in slot 64** (D3). Larger stock envelope (±22 to 30), but the same city-art path and failure modes as A.
- **Natural-wonder or feature art** (D4). Cities cannot be founded on natural wonders, and features are terrain-wide.
- **Static prop units** (D5). Units do render in cities, but they are selectable, block stacking and are killed or captured. Not a known community technique.

## 6. The six original mods as a content library

None of the six mods defines city graphics. They only choose a stock culture per civ. They already use the improvement-art tables, so the landmark system adds rows of a kind the pack already loads.

| Concern | File(s) | Relevance |
| --- | --- | --- |
| Civ art styles | `Middle Earth Civilizations (v 9)/<Civ>/XML/Civ_<Civ>.xml` (e.g. Hobbits: `ARTSTYLE_EUROPEAN`, prefix `"EUROPEAN "` with a trailing space) | Decides which stock house set each civ gets. Not changed by C |
| City graphics | none | No `CityDefines` or `WonderDefines` in any of the six |
| Building art flags | `Middle Earth Civilizations (v 9)/XML/MEC_UnitArtInfoCulturalVariation.xml` | Turns off cultural variation on all buildings (§3). Harmless to C |
| Improvement art already in use | `Middle Earth True Start Location (v 2)/SQL/METSL_Art.sql` (`ArtDefine_Landmarks` for Mithril, Mushrooms, Timber) | Proof that our merged pack already loads improvement art rows |
| Unique improvements | `Hobbits_Improvement.xml` (reuses `ART_DEF_IMPROVEMENT_POLDER`), `Southron_Improvement.xml`, `Lorien_Elves_Improvements.xml` | No conflict; our improvements use new types |
| Disabled improvement + art | `Wood Elves/XML/Void/Wood_Elves_Improvement_Sentry_Tower.xml`, art in `Wood Elves/Art/Improvements/` | Our prototype model (§2) |
| Lua that touches cities | `METSL_InGame.lua`, `METSL_CityNames.lua` (Dynamic City Naming via `SetName(key)`); Wood Elves Lua is all in `Void/` | Landmark Lua must match by name key, as it does today |
| Improvement removal | `Middle Earth Only (v 3)/SQL/Improvements/YRA_Delete_Improvements.sql` | **Check before step 2** that it deletes by explicit type, so our new rows survive |
| Unit art | per-civ `Art/Units/*/…ArtDefines.xml`, `Edited Animations/` | Unrelated to cities |

`ReloadLandmarkSystem=1` is set by ME Civs, ME Barbarians and our merged `.modinfo` (`tools/build.py:144`), which is what improvement art needs.

## 7. Asset pipeline: Blender to GR2

Keep our Blender models and our own gr2 writer, and change the **template** they are written into: from the palace or wonder skeleton to the stock improvement skeleton that Nomad's working models use. The community route (Blender 2.49 → Nexus Buddy 2, or 3ds Max with the Granny exporter) is Windows-only and dated. Our writer has already produced models the game draws.

| Topic | Standard for landmark improvements |
| --- | --- |
| Template | Stock Holy Site or Citadel gr2 from `ImprovementModels.fpk`: model `Box01`, bone `Point01` (+ `FX_PillagedSmoke`), all geometry weighted to `Point01` |
| Coordinates | Z-up, origin at hex centre, ground at z = 0, UnitsPerMeter 39.37 (read from Nomad's file) |
| Scale | Art-define `Scale` = 1. Model in improvement units, the hex ≈ ±45 like the citadel. Calibrate once in test 2 |
| Footprint | Up to the stock improvement envelope (±45 x,y). Height: stock up to 23 (customs house), Nomad's tower 27.5; we test taller in step 10 |
| Mesh budget | ≤ 8k vertices per model like stock improvements (citadel 7.8k), under 32k per mesh (16-bit indices) |
| Materials | `BuildingShader`-style static material, DIFF + SREF, stock environment maps listed in the fxsxml |
| Textures | DXT `.dds`, 512–1024 px; ground "bib" + `_H` height map like the Barracks |
| States | `Constructed` and `Pillaged` art rows (pillaged can reuse the same model at first) |
| Effects | Later only: `TimedTrigger` on `Point01`/FX bones, as stock improvements do |
| LOD | None in stock improvements; not needed |

**Validation, before any launch:** compare each output gr2 against the template (same type tree, same bone and model names, bounds inside the envelope, vertex count), render a preview, and check that every texture named in the fxsxml exists. These are the same checks we already have, pointed at a new template.

## 8. Recommended architecture: landmark improvements driven by one rules table

One data table says which landmark a city should show. One synced Lua script makes the plot match that table whenever something relevant happens. The art is ordinary improvement rows. Nothing in the city's own art is touched.

```
GameEvents (synced)            Sync(city)                        City plot
  PlayerCityFounded    --->      wanted = rules lookup   --->      landmark improvement
  CityCaptureComplete            differs: SetImprovementType       (adjacent if Q1 fails)
  SetPopulation                  same: do nothing                        |
  PlayerDoTurn                         | lookup                          v
  Game load: all cities                v                           Art rows (normal mod)
                                Rules table                          Improvements row
                                  1 special city name key            ArtDefine_Landmarks
                                  2 capital of the civ               .fxsxml + .gr2
                                  3 civ city, population tier            |
                                  4 none: leave the plot                 v
Native houses                                                      City tile on screen
  culture + era + population  -------------------------------->    civ landmark from Lua +
  untouched by us                                                  houses that grow on their own
```

The city's own art is never touched: houses come from the engine, and the landmark is plot state that Lua sets.

### Parts

1. **Rules table** (`Landmarks` in Lua, generated from one Python source). Each row: match key, model per population tier. Lookup order, first match wins:
    1. **Special location** by city name key (Barad-dûr, Minas Tirith, Erebor), any population.
    2. **Capital** of a civ (`city:IsCapital()`), with its own tiers.
    3. **Ordinary city** of a civ, tiers such as 1–3, 4–6, 7+.
    4. Nothing: the plot stays as the game left it.
2. **Art rows**, one set per model: `ArtDefine_LandmarkTypes`, `ArtDefine_Landmarks` (Constructed + Pillaged), `ArtDefine_StrategicView`, and an `Improvements` row named `IMPROVEMENT_MEC_LM_<MODEL>` with no yields, no builds and `Permanent=1`. No `Build` row, so workers can never place them.
3. **Sync script** (`MEC_Landmarks.lua`, in the synced game context). A single function `Sync(city)`: compute the wanted improvement from the table, compare with `plot:GetImprovementType()`, call `SetImprovementType` only when it differs. Called from:
    - `GameEvents.PlayerCityFounded` and `CityCaptureComplete` (founding and capture clear the plot),
    - `GameEvents.SetPopulation` (tier changes),
    - `GameEvents.PlayerDoTurn` for all the player's cities (safety net and renames),
    - load game: one pass over all cities.
4. **Placement policy**, one switch: `ON_CITY` (default) or `ADJACENT` (D1 fallback). Adjacent picks a fixed neighbour by a deterministic rule (first non-water, non-wonder plot in a fixed direction order). It is only used if test 1 fails.

### Rules that keep it reliable

- Lookups by iterating `GameInfo.Improvements()` into maps at load. No string indexing, which returned wrong rows before.
- Match by name **key** only, never the localised name (MP desync).
- Idempotent: running `Sync` twice changes nothing. Safe after load, rename, capture or replay.
- Only `GameEvents`, never UI `Events`, so every client computes the same plot state.
- Every model ships behind a per-row `enabled` flag. A model is enabled only after it passes the template check (§7) and one in-game sighting.

### Coexisting with houses

The houses stay. Each landmark is modelled with an open area in the middle, where the houses cluster, or as a ring or backdrop: Barad-dûr's tower to one side with walls around the town, the Hobbit hill around the smials. This is the same choice stock improvements make next to roads and rivers. Later, as polish, the six culture house sets can be re-skinned (D2).

## 9. Prototype plan

One civ (Mordor), one model (the Elven Battle Tower we already ship), then widen one variable at a time. Each step has a pass rule. A failed step stops the plan. Every launch is yours to start.

1. **Does the engine draw an improvement on a city plot?** Add `IMPROVEMENT_MEC_LM_TEST` with the Battle Tower art. Lua sets it on Mordor's capital at founding and, as a control, on one empty plot next to it. *Pass:* tower visible on both. *If only the control draws:* switch to `ADJACENT` and continue; the rest of the plan is unchanged.
2. **Scale calibration.** Same game: read where the tower sits relative to the houses and the hex edge. Pick the `Scale` for later models. No new art.
3. **Consistency.** 5 new games (fresh process each, then 3 games in one process, the case that broke city art). *Pass:* drawn 100%.
4. **Growth.** Two tiers (tower at pop 1–2, Barracks at 3+). Grow the city with Lua or by playing. *Pass:* swaps on the turn it grows, both ways after starvation.
5. **Capture.** Another player takes the city. *Pass:* landmark is back after capture, matching the new owner's rule (or gone if the new owner has none).
6. **Save and reload.** Save, quit to the menu, reload, and also reload from a fresh process. *Pass:* identical.
7. **Many cities.** Every city of every civ gets the tower (test switch). *Pass:* all drawn, including city-states and late-founded cities.
8. **Multiplayer.** Two players over MPPatch, steps 4–6 repeated. *Pass:* both screens agree, no desync.
9. **First own model: Barad-dûr**, written into the improvement template (§7) at the stock envelope (±45, tower height ≤ 27). Same pass rules as 3.
10. **Second own model: Bag End / Hobbit hill.** Then raise height to find the real limit, then effects (Eye flames) one at a time.

Only after step 10 do we add civs and tiers in bulk, from the rules table.

## 10. Open questions and the experiment for each

| # | Question | Experiment | Prototype step |
| --- | --- | --- | --- |
| Q1 | Does the exe draw an improvement on a city plot? | Tower on capital + control on a neighbour plot | 1 |
| Q2 | How do improvement units map to the hex and to the houses? | Screenshot of the tower beside the houses | 2 |
| Q3 | Does improvement art have a per-launch failure like city art? | 5 fresh games + 3 games in one process | 3 |
| Q4 | Is there a height or bounds limit for improvements? | Same model at heights 27, 40, 55 | 10 |
| Q5 | Do the city tooltip or plot panel show the improvement in an ugly way? | Look at the plot tooltip; hide with a text key if needed | 1 |
| Q6 | Does `YRA_Delete_Improvements.sql` delete by pattern? | Read the file before building step 1 | before 1 |
| Q7 | Does the AI treat the city plot differently (yields, tile value)? | Zero-yield improvement; watch one AI game | 7 |
| Q8 | Does our gr2 writer output, in the improvement template, draw like Nexus Buddy output? | Barad-dûr vs the Battle Tower in the same game | 9 |

Things I could not do: the CivFanatics download pages block scripted downloads, so the Isengard Wizard Tower, Scorpion Nest and Watchtower files were not inspected; the Barracks archive came through and was. The "How ArtStyle system works" link (thread 510343) opens an unrelated diplomacy thread, and the "Customization: mods and guides" link (539480) returns 404. I used the tutorials linked from the fantasy thread instead.

## Sources

- [CiV Fantasy Improvement Graphic Conversions](https://forums.civfanatics.com/threads/civ-fantasy-improvement-graphic-conversions.557045/) (Nomad or What), post #15 on city tiles
- [BFMEII: LOTR Elven Barracks](https://forums.civfanatics.com/resources/bfmeii-lotr-elven-barracks.26014/), files inspected: `.modinfo`, `SQL/Elven_Barracks.sql`, `Art/*.fxsxml`, `Art/*.ftsxml`, `Art/*.gr2`
- [How to Convert Civ4 Buildings into Civ5 Tile improvements](https://forums.civfanatics.com/threads/how-to-convert-civ4-buildings-into-civ5-tile-improvements.528771/) (Ekmek): Blender 2.49 + Nexus Buddy, Holy Site template
- [Add a new building and improvement with 3D model](https://forums.civfanatics.com/threads/add-a-new-building-and-improvement-with-3d-model.477464/) (Danrell): improvement fScale 1 vs wonder 0.05
- [Guide to 3D Modding in Civilization V](https://forums.civfanatics.com/threads/guide-to-3d-modding-in-civilization-v.548457/) (Civitar)
- [Current modding limitations post-DLL](https://forums.civfanatics.com/threads/current-modding-limitations-post-dll-modding-related-bugs-and-sdk-issues.490050/)
- [Firaxis BNW DLL source mirror](https://github.com/Gedemon/Civ5-DLL): `CvPlot::updateLayout`, `CvPlot::canHaveImprovement`, `CvPlot::setImprovementType`, `CvCity::init` (line 319), `CvLuaPlot::lSetImprovementType`, hook calls `SetPopulation`, `CityCaptureComplete`, `PlayerCityFounded`
- Local: `mods/` (six original mods), stock `ImprovementModels.fpk` (86 models measured), `docs/CITY_MODELS.md` §1 and §12–§18 (our in-game measurements)
