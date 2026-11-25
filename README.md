# Middle Earth Multiplayer Pack

Yenyang's six Middle-earth mods merged into one pack that works in multiplayer, hotseat and single player. It installs into the game folder as DLC content; it doesn't use the Mods menu and doesn't need MPPatch.

| Original mod | What's in the pack |
|---|---|
| Middle Earth Civilizations (v 9) | All 14 civs, leaders, units, buildings, art, leader music, Wood Elf invisibility |
| Middle Earth City States (v 1) | All 26 Middle-earth city-states |
| Middle Earth Barbarians (v 3) | Goblin/Orc/Uruk barbarians |
| Middle Earth Only (v 3) | Removes the vanilla civs, city-states and unique units |
| Middle Earth Soundtrack (v 1) | Good/Evil peace and war soundtrack |
| Middle Earth True Start Location (v 2) | The Middle-earth maps, true start locations, natural wonders, resource rules, dynamic city naming |

## Install (every player)

All players must install the **same build**, or the game desyncs. The lobby can't check this for you (see "How it's packaged" below).

**A. Mod manager app (recommended).** [`ui/`](ui/README.md) is a small Windows/Linux app that switches the game between vanilla BNW and this pack with one click: it backs up the file it replaces, can restore vanilla, empties the game cache, and shows a build id that players can compare. Share `ui/release/Civ5-MiddleEarth-<version>-windows.exe` (built with `npm run build` in `ui/`) with your friends. Close Civilization V before clicking a tile.

**B. By hand:** `dist/MiddleEarth_DLC.zip`

1. Extract it into the game's `Assets/DLC` folder and let it **overwrite** `Shared/Upgrade1.Civ5Pkg`. Afterwards there is `Assets/DLC/Shared/MiddleEarth/` and a modified `Assets/DLC/Shared/Upgrade1.Civ5Pkg`.
   - Linux/Proton: `unzip -o MiddleEarth_DLC.zip -d ~/.local/share/Steam/steamapps/common/"Sid Meier's Civilization V"/Assets/DLC/`
   - Windows: extract into `C:\Program Files (x86)\Steam\steamapps\common\Sid Meier's Civilization V\Assets\DLC\` and confirm overwriting.
   - Updating an earlier hand install: delete `Assets/DLC/Shared/MiddleEarth/` first. Extracting never deletes files that a newer build no longer has.
2. With the game closed, empty `Documents/My Games/Sid Meier's Civilization 5/cache`.
   - Linux/Proton: `~/.local/share/Steam/steamapps/compatdata/8930/pfx/drive_c/users/steamuser/Documents/My Games/Sid Meier's Civilization 5/cache`

**Undo (by hand):** Steam → Civ V → Properties → Installed Files → *Verify integrity* restores the original `Upgrade1.Civ5Pkg`. Then delete `Assets/DLC/Shared/MiddleEarth` and empty the cache. A Steam update of the game can do the same verify on its own and disable the pack; install it again afterwards (in the app: click the **Middle Earth** tile).

Don't enable the six original Middle Earth mods (or the old `Middle Earth MP (v 1)` mod) in the Mods menu at the same time: the pack already contains them.

## Play in multiplayer

1. Start Civ 5 normally (not through the Mods menu): **Multiplayer → Standard Game → Host**.
2. In the staging room:
   - **Map Type:** *Middle-earth TSL: Third Age (Huge, World Wrap)* (the main map) or *Middle-earth TSL: Third Age (Large)*. Four more Standard/Huge/Large variants are listed too.
   - **Map Size:** Huge for the Huge maps, Large for the Large maps, Standard for the Standard maps. The map grid is fixed; the size setting controls game balance (tech costs, etc.).
   - **City-States:** with "Only TSL", set the slider to the **maximum**. The game picks random city-states and removes the ones without a start location, so a low slider leaves fewer than you asked for. The Huge map has 20 city-state locations, the Large map 18.
   - Set the Middle-earth options under the map type (see below).
3. Friends join, pick one of the 14 Middle-earth civs, and the host starts the game.

Single player and hotseat work the same way from their own setup screens.

## How it's packaged

**Why "Upgrade 1":** Civ 5 only registers DLC packages whose `<Key>` signature is valid, and that signature can't be produced for a new package. A standalone `Assets/DLC/MiddleEarth` package is silently ignored (tested). So the pack is attached to the existing free package "Upgrade 1", which every copy of Civ 5 has. Its signed header (GUID, SteamApp, Version, Ownership, Key, PTags) is kept byte-for-byte. Only a load priority (400, after BNW and every DLC) and the Middle-earth entries are added. Because of this the pack doesn't show up as its own entry under "DLC Allowed", and the lobby can't tell whether a player has it.

**How the mods are converted:** DLC packages accept only XML data, no SQL or mod Lua hooks. So the build computes the final modded database and writes it as plain XML. Replaying that XML on the vanilla database reproduces the modded database exactly. Text, audio, art and map scripts are converted to the official DLC formats. The in-game scripts (dynamic city naming, city-state cleanup, extra settler, Wood Elves) are loaded through an `InGame.lua` UI override, the way EUI and MP mod packs do it. This conflicts with EUI, which also overrides `InGame.lua`.

**Why not MPPatch:** the first version of this pack was a normal mod for the Mods menu, played in multiplayer through MPPatch. MPPatch (v0.2.0-alpha.2) refuses the current Steam build of Civ 5 ("unknown version", upstream issue Lymia/MPPatch#102), and the DLC packaging needs no third-party patcher at all. The mod build (`dist/Middle Earth MP (v 1)`) is still produced, but only as the input of the DLC build.

## Why the originals broke in multiplayer

Everything except True Start Location (TSL) is plain database/art content. TSL wasn't multiplayer-capable, for three reasons:

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
  - Extra Starting Settler (new): every civ starts with 2 Settlers instead of 1

  The two main maps (Huge World Wrap, Large) have all options. The four extra maps have true start locations with random resources, as in the original; their options are City-State Placement, Resources and Extra Starting Settler.
- **Randomness:** only the synchronized game RNGs are used (`Map.Rand` during map generation, `Game.Rand` in game).
- **Coordinates:** the resource placement code is ported with correct X/Y throughout.
- **City-states under "Only TSL":** the game picks the city-states. Those without a start location on the chosen map are removed on turn 0, as the original did. The removal is deterministic on every client.
- **Dynamic city naming:** stores the text key, so each player sees the name in their own game language.
- **Wood Elves script:** fixed an undefined range variable, a crash on dead units, a territory check that always tested player 0's territory, and logging on every unit move.
- **One pack:** the database result was checked to be identical to loading the six originals in order.
- **Hobbits loading screen:** a new 4K (3840×2160) picture of the Shire at sunset, rendered in Blender by `tools/splash/` (no AI image). It replaces `DOM_Hobbits.dds` and fills the whole screen: the pack overrides the front-end `LoadScreen.lua`, which stretches the pictures listed in `tools/splash/MEDLC_FullscreenDOM.lua` to cover the screen. Every other civ keeps its stock 1024×768 picture.

## What to check in a test game

- Every civ starts at its canonical location: Hobbits in the Shire, Gondor in Minas Tirith, Mordor next to the Ephel Dúath, and so on.
- Resources are visible on the map, including the civ-specific ones near each capital (e.g. horses for Rohan, iron and coal for Mordor).
- Natural wonders are present: Amon Súl, Tolfalas, the Stone of Erech, Echoriath, and on the small islet in the south-west corner the Lonely Mountain wonder slot, as in the original.
- City-states are at their canonical places (Bree, Dale, Lake-town, …).
- The Middle-earth soundtrack and leader music play.
- Founding a city at a named place renames it (e.g. a Hobbit city at Hobbiton). This needs "Dynamic City Naming" on.
- With "Extra Starting Settler" on, every civ has two Settlers on turn 0.
- Several turns pass without a desync.

Known issue: cities sometimes don't draw (city missing at founding, or vanishing when it grows). The six original mods had the same sporadic problem. Our landmarks don't use the city's own art, so they are not affected ([`docs/LANDMARKS.md`](docs/LANDMARKS.md)).

## If something doesn't work

Turn on logging. Close the game, edit `config.ini` (in `Documents/My Games/Sid Meier's Civilization 5/`) and set `LoggingEnabled = 1`, then reproduce the problem. Afterwards, look in `Logs/Lua.log` for lines starting with `METSL`. Map generation prints every placed start and resource count, and the in-game script prints what it removed, renamed and gave out. Lines with `Runtime Error` point to script bugs. Also check `Logs/Database.log` for errors. Send me those two files.

## Rebuilding / development

```bash
python3 tools/build.py              # merged mod      -> dist/Middle Earth MP (v 1)   (input of the next step)
python3 tools/build_dlc.py --zip    # DLC pack        -> dist/DLC_Shared/Shared + dist/MiddleEarth_DLC.zip
```

The mod manager's `npm run dev` / `npm run build` (in `ui/`) run both steps themselves. Simulation needs `pip install lupa`.

```
tools/build.py        merge the six mods into dist/Middle Earth MP (v 1) (+ --zip)
tools/build_dlc.py    convert it into the "Upgrade 1" DLC pack (dist/DLC_Shared/Shared, + --zip).
                      Also writes dist/DLC/MiddleEarth, a standalone package the game ignores (kept for reference).
tools/civ5map.py      Civ5Map reader          tools/map2lua.py   Civ5Map -> Lua map data
tools/rivertest.py    river edge decoding     tools/flowtest.py  river flow decoding
tools/render.py       print a Civ5Map as text (terrain check)
tools/dbreplay.py     replay mod XML/SQL on a copy of the game DB and report errors
tools/mockciv.lua     mock of the Civ5 map Lua API   tools/simulate.py  run a map script through it (Lua 5.1 via lupa)
tools/testmatrix.py / determinism.py / ingametest.py / dlctest.py   test runs
tools/splash/         the Hobbits loading-screen picture: shire.py (Blender scene, Cycles) + post.py (haze, glow,
                      tonemap, writes the DDS); the result is committed as src/MEC/Hobbits/Art/DOM_Hobbits.dds
tools/landmarks/      capital landmark models and their pack integration (see below; tools/capitals/ = model library + drafts)
vendor/landmarks/     the landmark art that ships (exact files that drew in game)
src/                  new and replaced files (map scripts, METSL Lua, fixed Wood Elves script, art fixes)
vendor/civ5/          files copied from the stock game (vanilla DB, InGame.lua, LoadScreen.lua, Upgrade1.Civ5Pkg, palace .gr2 template)
mods/                 the untouched original mods
ui/                   the mod manager app (Electron), see ui/README.md
build/, dist/         generated (not in git): venv, Blender output, temp DBs / built mod + DLC + zips
```

Custom city landmarks (2026-11-24) are **tile improvements** that a script places on a capital's tile; the city's own art is never touched. **Moria** (the Goblins' capital) shows our model of the West-gate of Moria, and **Barad-dûr** (Mordor's capital) shows the Dark Tower as in the films, 242 units high and two hexes wide, with the Eye of Sauron, which looks around, burns and casts its beam. Every other city and city-state uses stock art. The art ships from `vendor/landmarks/`, so building the pack needs no Blender. `python3 tools/build_dlc.py --no-landmarks` builds the pack without them. How it works and how to build the next capital: [`docs/LANDMARKS.md`](docs/LANDMARKS.md).
