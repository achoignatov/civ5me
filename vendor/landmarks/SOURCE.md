# Vendored landmark art

The exact files that drew in game, copied into the pack as-is by `tools/build_dlc.py` (`build_landmark_improvements`).
They are kept here because `build/` is not in git and Blender is not needed to build the pack. Every file in a
model's folder is packed (except `.md` / `.txt`).

| Folder | Model | Source | Drawn in game |
|---|---|---|---|
| `Moria/` | Moria v3: the West-gate, Doors of Durin, cliffs, Watcher's lake (baked textures, 16.4k vertices) | `tools/landmarks/models/moria.py` via `tools/landmarks/build_models.py`, gr2 rewritten with the stock section layout and zeroed OBBs (`tools/landmarks/probes.py`) | Test 2, 2026-11-24: on every city and city-state, as an improvement |
| `BaradDur/` | Barad-dûr v3, the Eye of Sauron: fortress + tower, skinned Eye with a 6 s look-around loop (`_Idle.gr2`), fire bones, the beam model effect (`MEC_EyeBeam*`), triggers (`FX_Triggers_MEC_LM_BaradDur.ftsxml`) | `tools/landmarks/models/barad_dur.py` as of commit 384416f (later edited into the static v4), same conversion; taken from the install of 2026-11-24 19:38 | As city art on 2026-11-22/23 (with animation and effects); as an improvement: first test of this release |

To replace a model: rebuild it, convert it the same way, copy the files here, and keep the file names that
`tools/landmarks/improvements.py` names.
