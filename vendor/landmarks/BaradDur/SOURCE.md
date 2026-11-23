# Barad-dûr base model (the stable landmark asset)

`MEC_LM_BaradDur_Base.gr2` is the landmark model Barad-dûr shows by default (2026-11-24). It is **not made by us**:
it is `Blue_Mosque.gr2`, copied byte for byte from the community "Blue Mosque" wonder in a public Civ 5 multiplayer
mod pack, only renamed:

- https://github.com/clumsy/Civ5-MP_MODSPACK/tree/master/Mods/Wonder%20-%20Blue%20Mosque (downloaded 2026-11-23)
- Exported with *Granny Standard Exporter 2.8.21* from *3D Studio MAX*: a reworked copy of the stock Hagia Sophia.
- 3 models: hill variant `HBHagia_Sophia` (6356 verts), `TreeCut`, `Hagia_Sophia` (3016 verts). Plain-text names,
  uncompressed, BuildingShader materials.
- Its materials reference the game's own textures `Hagia_Sophia_DIFF/SREF.dds` and `HBHagiaSophia_DIFF/SREF.dds`
  (in the game's `WonderTextures.fpk`), so no texture files are shipped. It looks like a small Hagia Sophia.
- fScale 0.05 (the stock Hagia Sophia's); the `.fxsxml` is written by the build like the stock `hagia_sophia.fxsxml`.

Why: our own models (Blender + our Python .gr2 writer, tools/landmarks/) made the WHOLE city tile vanish in some
games; this file, shown through exactly the same mechanism, drew 5/5 in the user's test. It is the known-good
starting point to build on. See docs/CITY_MODELS.md §10.

**Licence:** the GitHub mod pack has no licence file, and the model is a modified Firaxis asset (Hagia Sophia).
It's used here as a test baseline for a fan mod; replace it with our own model before distributing the pack widely.
