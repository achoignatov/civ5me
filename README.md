# Middle Earth Multiplayer Pack

Yenyang's six Middle-earth mods merged into a single mod that works in multiplayer (via MPPatch), hotseat and single player:

| Original mod | What's in the pack |
|---|---|
| Middle Earth Civilizations (v 9) | All 14 civs, leaders, units, buildings, art, leader music, Wood Elf invisibility |
| Middle Earth City States (v 1) | All 26 Middle-earth city-states |
| Middle Earth Barbarians (v 3) | Goblin/Orc/Uruk barbarians |
| Middle Earth Only (v 3) | Removes the vanilla civs, city-states and unique units |
| Middle Earth Soundtrack (v 1) | Good/Evil peace and war soundtrack |
| Middle Earth True Start Location (v 2) | The Middle-earth maps, true start locations, natural wonders, resource rules, dynamic city naming |

## Two ways to install

**A. DLC build (recommended, no MPPatch needed):** `dist/MiddleEarth_DLC.zip`

1. Every player extracts it into the game's `Assets/DLC` folder and lets it **overwrite** `Shared/Upgrade1.Civ5Pkg`. Afterwards there is `Assets/DLC/Shared/MiddleEarth/` and a modified `Assets/DLC/Shared/Upgrade1.Civ5Pkg`.
   - Linux/Proton: `unzip -o MiddleEarth_DLC.zip -d ~/.local/share/Steam/steamapps/common/"Sid Meier's Civilization V"/Assets/DLC/`
   - Windows: extract into `C:\Program Files (x86)\Steam\steamapps\common\Sid Meier's Civilization V\Assets\DLC\` and confirm overwriting.
2. With the game closed, empty `Documents/My Games/Sid Meier's Civilization 5/cache`.
3. Start Civ 5 normally. Don't use the Mods menu, and don't enable the Middle Earth mods: the pack replaces them.
4. **Multiplayer → Standard Game → Host**, then choose a *Middle-earth TSL* map type.

It doesn't show up as its own entry under "DLC Allowed"; it rides inside the game's free "Upgrade 1" package, which every copy of Civ 5 has.

**Why "Upgrade 1":** Civ 5 only registers DLC packages whose `<Key>` signature is valid, and that signature can't be produced for a new package. A standalone `Assets/DLC/MiddleEarth` package is silently ignored (tested). So the pack is attached to the existing free package `Upgrade 1`. Its signed header (GUID, SteamApp, Version, Ownership, Key, PTags) is kept byte-for-byte. Only a load priority (400, after BNW and every DLC) and the Middle-earth entries are added. Tested on 2026-11-20: the game registers it, and its database then contains exactly the modded data.

**Important for multiplayer:** the lobby can't tell whether a player has the pack, because "Upgrade 1" exists either way. Every player must install the identical zip, or the game will desync.

**Undo:** Steam → Civ V → Properties → Installed Files → *Verify integrity* restores the original `Upgrade1.Civ5Pkg`. Then delete `Assets/DLC/Shared/MiddleEarth` and empty the cache. The same verify also removes the pack after Steam updates the game; just extract the zip again.

How it works: DLC packages accept only XML data, no SQL or mod Lua hooks. So the build computes the final modded database and writes it as plain XML. Replaying that XML on the vanilla database reproduces the modded database exactly. Text, audio, art and map scripts are converted to the official DLC formats. The in-game scripts (dynamic city naming, city-state cleanup, Wood Elves) are loaded through an `InGame.lua` UI override, the way EUI and MP mod packs do it. This conflicts with EUI, which also overrides `InGame.lua`.

Rebuild with `python3 tools/build.py && python3 tools/build_dlc.py --zip`.

**Easiest: the mod manager app** in [`ui/`](ui/README.md) switches the game between vanilla BNW and this DLC build with one click (backups, restore, cache clearing; Windows and Linux).

**B. Mod build (requires MPPatch):** `dist/Middle Earth MP (v 1).zip`. See below.

## Why the originals broke in multiplayer

Everything except True Start Location (TSL) is plain database/art content, and that already works with MPPatch. TSL didn't, for three reasons:

1. **It only worked from its own single-player setup screen.** That screen saved the chosen map and options to a per-PC file (`ModUserData`) and set a flag `LoadingMetsl = true`. The map initializer ran only when the flag was set. The MP lobby never shows that screen, so the initializer printed "Not loading from Metsl setup, do nothing". That's why you got no start locations, no resources and no natural wonders.
2. **It used `math.random`**, which is not synchronized between players. Even when it ran, each player would have generated different resources, causing desyncs.
3. **The original resource code mixes up X and Y** in several places (the "inversed" comments in the code), so neighbor checks looked at the wrong tiles.

## What was changed

- **Maps:** the six `.Civ5Map` files were decoded and converted to embedded Lua data (`METSL/LUA/METSL_MapData_*.lua`). The river bit format was verified geometrically: 1,057 of 1,062 river junctions connect and river mouths sit at the sea. Each map is now a normal **map script** that every player generates identically, listed as **"Middle-earth TSL: …"** in the map type list.
- **Settings:** all former setup-screen settings are now **map options** in the normal setup and MP staging room, and the game syncs them to every player:
  - City-State Placement: Only TSL / TSL + random / Totally random
  - Resources: Poor … Rich
  - Natural Wonders
  - Canonical Resource Regions
  - Civilization Start Resources
  - Dynamic City Naming, plus its two sub-options

  The two main maps (Huge World Wrap, Large) have all options. The four extra maps have start locations and random resources only, as in the original.
- **Randomness:** only the synchronized game RNGs are used (`Map.Rand` during map generation, `Game.Rand` in game).
- **Coordinates:** the resource placement code is ported with correct X/Y throughout.
- **City-states under "Only TSL":** the game picks the city-states. Those without a start location on the chosen map are removed on turn 0, as the original did. The removal is deterministic on every client.
- **Dynamic city naming:** stores the text key, so each player sees the name in their own game language.
- **Wood Elves script:** fixed an undefined range variable, a crash on dead units, a territory check that always tested player 0's territory, and logging on every unit move.
- **One mod:** all six original mods are blocked by this pack so they can't be loaded twice. The database result was checked to be identical to loading the six originals in order.

## Install (every player)

All players need **MPPatch** and the **same** version of this pack.

1. In the Civ 5 **Mods** menu, untick the six original Middle Earth mods. You can also delete them from the MODS folder.
2. Extract `dist/Middle Earth MP (v 1).zip` into your MODS folder. You should end up with `MODS/Middle Earth MP (v 1)/Middle Earth MP (v 1).modinfo`.
   - Linux/Proton (your setup): `~/.local/share/Steam/steamapps/compatdata/8930/pfx/drive_c/users/steamuser/Documents/My Games/Sid Meier's Civilization 5/MODS/`
   - Windows: `Documents\My Games\Sid Meier's Civilization 5\MODS\`

   ```bash
   unzip "dist/Middle Earth MP (v 1).zip" -d ~/.local/share/Steam/steamapps/compatdata/8930/pfx/drive_c/users/steamuser/Documents/My\ Games/Sid\ Meier\'s\ Civilization\ 5/MODS/
   ```
3. Recommended once: with the game closed, delete the contents of the `cache` folder next to `MODS` (the game rebuilds it).

## Play in multiplayer

1. **Mods** menu → enable only **Middle Earth Multiplayer Pack** → use MPPatch's **Multiplayer** button → host a game.
2. In the staging room:
   - **Map Type:** *Middle-earth TSL: Third Age (Huge, World Wrap)* (the main map) or *Middle-earth TSL: Third Age (Large)*.
   - **Map Size:** Huge for the Huge maps, Large for the Large maps, Standard for the Standard maps. The map grid is fixed; the size setting controls game balance (tech costs, etc.).
   - **City-States:** with "Only TSL", set the slider to the **maximum**. The game picks random city-states and removes the ones without a start location, so a low slider leaves fewer than you asked for. The Huge map has 20 city-state locations, the Large map 18.
   - Set the Middle-earth options under the map type.
3. Friends join, pick civs (only the 14 Middle-earth civs exist), and the host starts the game.

## What to check in the first test

- Every civ starts at its canonical location: Hobbits in the Shire, Gondor in Minas Tirith, Mordor next to the Ephel Dúath, and so on.
- Resources are visible on the map, including the civ-specific ones near each capital (e.g. horses for Rohan, iron and coal for Mordor).
- Natural wonders are present: Amon Súl, Tolfalas, the Stone of Erech, Echoriath, and on the small islet in the south-west corner the Lonely Mountain wonder slot, as in the original.
- City-states are at their canonical places (Bree, Dale, Lake-town, …).
- The Middle-earth soundtrack and leader music play.
- Founding a city at a named place renames it (e.g. a Hobbit city at Hobbiton). This needs "Dynamic City Naming" on.
- Several turns pass without a desync.

## If something doesn't work

Turn on logging. Close the game, edit `config.ini` (next to `MODS`) and set `LoggingEnabled = 1`, then reproduce the problem. Afterwards, look in `Logs/Lua.log` for lines starting with `METSL`. Map generation prints every placed start and resource count, and the in-game script prints what it removed and renamed. Also check `Logs/Database.log` for errors. Send me those two files.

## Rebuilding / development

```
tools/civ5map.py      Civ5Map reader          tools/map2lua.py   Civ5Map -> Lua map data
tools/rivertest.py    river edge decoding     tools/flowtest.py  river flow decoding
tools/dbreplay.py     replay mod XML/SQL on a copy of the game DB and report errors
tools/mockciv.lua     mock of the Civ5 map Lua API   tools/simulate.py  run a map script through it (Lua 5.1 via lupa)
tools/testmatrix.py / determinism.py / ingametest.py   test runs
tools/build.py        assemble dist/Middle Earth MP (v 1) (+ --zip)
src/                  new and replaced files (map scripts, METSL Lua, fixed Wood Elves script)
vendor/civ5/          files copied from the stock game (vanilla DB, InGame.lua, Upgrade1.Civ5Pkg, palace .gr2 template)
mods/                 the untouched original mods
build/, dist/         generated (not in git): venv, Blender output, temp DBs / built mod + DLC + zips
```

Custom city landmark models are **switched off** (2026-11-23): every city uses stock art. The work in progress (per city name; Barad-dûr so far) stays in the repo and is built in with `python3 tools/build_dlc.py --landmarks`; see [`docs/CITY_MODELS.md`](docs/CITY_MODELS.md). Preview a landmark's model, animation and effects as a GIF without the game: `blender -b --factory-startup -P tools/landmarks/render_gif.py -- barad_dur`.

`python3 tools/build.py --zip` rebuilds the pack. Simulation needs `pip install lupa`.
