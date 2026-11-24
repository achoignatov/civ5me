# Vendored landmark art

The exact files that drew in game, copied into the pack as-is by `tools/build_dlc.py` (`build_landmark_improvements`).
They are kept here because `build/` is not in git and Blender is not needed to build the pack. Every file in a
model's folder is packed (except `.md` / `.txt`).

| Folder | Model | Source | Drawn in game |
|---|---|---|---|
| `MinasTirith/` | Minas Tirith (Gondor's capital, 2026-11-25): static part = Mount Mindolluin + terraces, walls, prow (28.1k vertices, 2048² baked); skinned part = battlements, bastions, gates, ~350 houses, the Citadel, the White Tree (still bone) + the King's banner (swings, 6 s loop), 25.7k, 2048² | `tools/landmarks/models/minas_tirith.py` via `build_models.py`, every `.gr2` converted with `probes.to_stock_sections(zero_obb=True)` | Not yet: installed 2026-11-25 for the user's test |
| `Moria4/` | Moria v4, the West-gate (production since 2026-11-25): massif height field (29.3k vertices, 2048² baked) + skinned part (22.9k: doors, holly trees, lake, rocks still; the Watcher's tentacles sway), the additive ithildin glow model effect `MEC_DurinGlow*` | `tools/landmarks/models/moria_v4.py` via `build_models.py`, every `.gr2` converted with `probes.to_stock_sections(zero_obb=True)` | Not yet: installed 2026-11-25 for the user's test |
| `Moria/` | (not packed since v4) Moria v3: the West-gate, Doors of Durin, cliffs, Watcher's lake (baked textures, 16.4k vertices) | `tools/landmarks/models/moria.py` via `tools/landmarks/build_models.py`, gr2 rewritten with the stock section layout and zeroed OBBs (`tools/landmarks/probes.py`) | Test 2, 2026-11-24: on every city and city-state, as an improvement |
| `BaradDur/` | (not packed since v5) Barad-dûr v3, the Eye of Sauron: fortress + tower, skinned Eye with a 6 s look-around loop (`_Idle.gr2`), fire bones, the beam model effect (`MEC_EyeBeam*`), triggers (`FX_Triggers_MEC_LM_BaradDur.ftsxml`) | `tools/landmarks/models/barad_dur.py` as of commit 384416f (later edited into the static v4), same conversion; taken from the install of 2026-11-24 19:38 | As city art on 2026-11-22/23 (with animation and effects); as an improvement: first test of this release |
| `BaradDur5/` | Barad-dûr v5, the film's Dark Tower (production, at `Scale` 0.5): crag, five-stage spire with clinging turrets, two-pronged crown (2048² baked, 30.5k vertices); skinned Eye with the 6 s look-around loop, Eye fires, blaze, tower braziers and the beam (`MEC_EyeBeam*`, tilt 38°) | `tools/landmarks/models/barad_dur_v5.py` via `build_models.py` (2026-11-24 night), every `.gr2` converted with `probes.to_stock_sections(zero_obb=True)` | Size-ladder test 2026-11-24: ×0.5 to ×2 on 30 cities, all drew with animation and effects |

To replace a model: rebuild it, convert it the same way, copy the files here, and keep the file names that
`tools/landmarks/improvements.py` names.
