# Civilization V Mod Manager

A small desktop app (Electron + React + TypeScript) that switches a Civilization V: Brave New World installation between:

- **Vanilla BNW**: the original game.
- **MiddleEarth MOD**: the Middle-earth multiplayer pack from this repository, installed straight into the game folder.

It works on Windows (native Steam) and Linux (Steam + Proton). For multiplayer, every player must have the **same build** installed. When a mod is active, the app shows a build id that players can compare.

## Quick start

Two ways to use this folder:

| | Command | Result |
|---|---|---|
| **Developing the mod** (repo checkout) | `npm install` once, then `npm run dev` | Rebuilds the mod from the repository as it is now (committed or not) and starts the app. Nothing is installed until you click a tile |
| **Sharing with friends** | `npm run build` | **One file:** `release/Civ5-MiddleEarth-<version>-windows.exe`. Friends just run it: Node/Electron and the mod are inside, nothing to install (no Node, Git or Python) |

```bash
cd ui
npm install
npm run dev
```

`npm run dev` needs what the mod build needs: Python 3 (`python3`, or `py -3` on Windows). The app never installs or restores anything on its own: at startup it only detects and inspects the game (read-only); switching happens only when you click a tile.

Other commands:

| Command | What it does |
|---|---|
| `npm run payload` | Regenerate `mods/middleearth/{manifest.json,payload/,originals/}` from `../dist/DLC_Shared/Shared` (incremental) |
| `npm test` | Run the unit and integration tests (Vitest; only temporary mock game folders) |
| `npm run typecheck` | Type-check main, preload and renderer |
| `npm run dev` | Rebuilds the mod (`build:mod`), starts the app with hot reload (installs nothing; click a tile) |
| `npm run build` | **Release build for friends:** rebuilds the mod from the repository (`npm run build:mod`), then produces a single portable `release/Civ5-MiddleEarth-<version>-windows.exe` with the mod inside |
| `npm run build:mod` | Only the mod: runs the `build` steps of every `mod.source.json` (`tools/build.py`, `tools/build_dlc.py`), then regenerates the payload |
| `npm run bundle` | Only the production JS bundle in `out/` (no mod rebuild, no packaging) |
| `npm start` | Run the production bundle |
| `npm run dist:linux` | Like `build`, but a Linux AppImage (`release/Civ5-MiddleEarth-<version>-linux.AppImage`) |
| `npm run dist:dir` | Unpacked app for the current OS from the existing payload (quick packaging check) |
| `npm run smoke` | Dev check: starts the built app hidden, does a **read-only** detection and inspection of the real game, and saves a screenshot plus status JSON to a temp folder |

**Development: always the current repository.** `npm run dev` builds the mod before the window opens (same steps as below, output in the terminal). Nothing is installed until you click a tile.

After that, while the app runs from this repository (`npm run dev` / `npm start`, i.e. not a packaged build), the **Middle Earth** tile first rebuilds the mod from the working tree as it is now (committed or not), then installs it. The steps come from the `build` section of `mods/middleearth/mod.source.json`:

1. `python3 tools/build.py`,
2. `python3 tools/build_dlc.py`,
3. this mod's payload (`scripts/build-payload.mjs middleearth`).

Custom city models are switched off (see `../docs/CITY_MODELS.md`), so there is no Blender step. To bring them back, re-add a `blender … tools/landmarks/build_models.py` step before step 1 and pass `--landmarks` to `build_dlc.py`.

The tile says "rebuilds from the repository first (dev)". Progress shows the running step. The result names the revision (e.g. `2725e68 + uncommitted changes`) and the build log (`<app data>/build-logs/build-middleearth.log`). If a step fails, nothing is installed and the error shows the step's last output. Installing again after a change rebuilds again and replaces the previous build (new build id). The **Vanilla BNW** tile never builds. Packaged apps (for players) never build; they install the payload they ship with. The rebuild code lives in `src/main/core/modManager/sourceBuild.ts`; other mods get it by adding a `build` section to their `mod.source.json`.

`npm start`, `npm run dist:dir` and `npm run payload` use the existing `../dist` build; `npm run dev` and `npm run build` build it themselves.

### Building the exe for friends

`npm run build` (works on Linux without Wine, and on Windows) makes one file, `release/Civ5-MiddleEarth-<version>-windows.exe`. (`release/win-unpacked/` is a by-product; ignore it.) Send a friend that file; they run it, and the **Middle Earth** tile copies the bundled mod into their game (with backup; the **Vanilla BNW** tile restores it). The exe never builds anything and never installs on its own: the friend clicks the tile.

- **Windows:** a portable exe that carries Electron (Chromium + Node) and the mod. Nothing to install: it unpacks itself to a temp folder on every start, so the first window takes a few seconds. It has Electron's default icon and version info (editing exe resources from Linux would need Wine). It isn't signed, so SmartScreen warns: "More info" -> "Run anyway".
- **Linux (optional, `npm run dist:linux`):** an AppImage. `chmod +x` it, then run it (needs FUSE, which most distributions have).
- The file carries the whole payload (~285 MB uncompressed, ~235 MB download). All players must use the same build (compare the build id in the app).
- After changing the mod, run `npm run build` again and send the new exe: an old exe installs the old build.

## Using the app

1. Start it. It looks for the game in this order:
   1. the current folder and the app's own folder (for the portable Windows exe: the folder of the `.exe` you started; for the AppImage: the folder of the `.AppImage`),
   2. the default Steam locations (`~/.local/share/Steam`, `~/.steam/steam`, Flatpak and Snap Steam on Linux; registry and `Program Files` on Windows), including every library listed in Steam's `libraryfolders.vdf`.

   It never scans disks and there is no folder picker. **Game installed in a custom location?** Put the app into the game folder (Steam → Library → right-click *Sid Meier's Civilization V* → Manage → Browse local files) and start it from there. If nothing is found, the installation section turns into a red alert with these steps and the list of checked folders. A valid folder contains `CivilizationV.exe`, `Assets/` and `Assets/DLC/Expansion2` (BNW).
2. **Close Civilization V**. The app refuses to switch while the game runs.
3. Click the **Vanilla BNW** or **Middle Earth** tile. Progress is shown; all buttons and tiles are locked while an operation runs. While Civilization V is running (checked every 5 seconds) a yellow bar at the bottom says so and both tiles are locked.
4. After a switch the game cache is emptied (see below). Start the game normally.

> **Pack installed by hand (from `MiddleEarth_DLC.zip`)?** The app shows *Unknown / Inconsistent: installed, but not by this app*. Click the **Middle Earth** tile to let the app take it over: identical files are adopted, different ones are backed up and replaced, and the original `Upgrade1.Civ5Pkg` is taken from the bundled copy. Or click the **Vanilla BNW** tile to remove it.

## What gets installed (derived from the project)

The source of truth is the DLC "Shared" build produced by `tools/build_dlc.py` (`dist/DLC_Shared/Shared`, identical to `dist/MiddleEarth_DLC.zip`). It maps 1:1 onto `<game>/Assets/DLC/Shared/`:

| Game path | Type | Notes |
|---|---|---|
| `Assets/DLC/Shared/Upgrade1.Civ5Pkg` | **replaces** a vanilla file | Free "Upgrade 1" package with Middle-earth entries added (signed header unchanged). Vanilla copy: `vendor/civ5/Upgrade1_original.Civ5Pkg` (sha256 `1a817a89…`) |
| `Assets/DLC/Shared/MiddleEarth/**` (835 files) | **added** | Gameplay XML, text, audio, art, map scripts, UI Lua |

After switching, the game's cache folder is emptied (the project README requires this):
- Linux/Proton: `<steam library>/steamapps/compatdata/8930/pfx/drive_c/users/steamuser/Documents/My Games/Sid Meier's Civilization 5/cache`
- Windows: `Documents\My Games\Sid Meier's Civilization 5\cache`

The cache is not deleted. It's moved to the app's data folder as `game-cache-previous` (replacing the previous one). The game rebuilds it.

Nothing else is touched. `config.ini`, the MODS folder and other DLC folders stay as they are. The standalone `dist/DLC/MiddleEarth` build (ignored by the game) and the intermediate mod build (`dist/Middle Earth MP (v 1)`, only the input of `build_dlc.py`) are not installed.

## Architecture

```
ui/
├── mods/
│   ├── index.json                   registry: which mod folders are available
│   └── middleearth/
│       ├── mod.source.json          hand-written: where the build comes from, which files replace vanilla
│       ├── manifest.json            generated: every file with destination, size, sha256, add/replace
│       ├── payload/                 generated (git-ignored): the files to install
│       └── originals/               generated (git-ignored): copies of the vanilla files the mod replaces
├── scripts/build-payload.mjs        generates manifest/payload/originals from ../dist
├── src/
│   ├── shared/types.ts              IPC data types (AppStatus, OperationResult, ManagerApi)
│   ├── main/                        Electron main process: all filesystem work happens here
│   │   ├── index.ts                 window, security settings, IPC handlers
│   │   └── core/                    plain Node, no Electron imports (unit-testable)
│   │       ├── controller.ts        detection + settings + busy lock + progress + cache clearing
│   │       ├── gameDetection/       detect.ts (validation, search order), vdf.ts, gameEnvironment.ts
│   │       │                        (running-game check, cache location, Windows registry)
│   │       ├── modManager/          manifest.ts (parse/validate/registry), engine.ts (install,
│   │       │                        uninstall, rollback, inspection), state.ts (state file + journal)
│   │       ├── backup/              backupStore.ts (where backups and conflict copies live)
│   │       └── fileOperations/      safe paths, hashing, injectable fs ops, errors, atomic JSON, cache
│   ├── preload/index.ts             contextBridge: exposes window.civ5mm (4 calls + progress events)
│   └── renderer/                    React UI (no Node access; talks only to window.civ5mm)
└── tests/                           Vitest: detection, manifest, engine, controller, real payload
```

Security: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, strict CSP, navigation and new windows blocked, single instance lock. The renderer can only ask for status, refresh, whether the game is running, and switch to a configuration id. The id is validated in main, and the renderer never sends paths.

Vanilla isn't a mod. It's the baseline: "switch to vanilla" means "undo whatever is installed". Switching from mod A to mod B means: restore vanilla, then install B.

## The mod manifest

`manifest.json` (generated; schema in `src/main/core/modManager/manifest.ts`):

```jsonc
{
  "schemaVersion": 1,
  "id": "middleearth",              // configuration id, [a-z0-9-]
  "name": "MiddleEarth MOD",        // shown in messages; the tile title comes from LOOK in SwitchButtons.tsx (falls back to this name)
  "version": "1",
  "description": "...",
  "sourceRoot": "payload",          // folder inside the mod folder that holds the files
  "clearGameCache": true,
  "files": [
    { "source": "Upgrade1.Civ5Pkg", "destination": "Assets/DLC/Shared/Upgrade1.Civ5Pkg",
      "size": 11646, "sha256": "7496…", "mode": "replace",
      "original": { "sha256": ["1a81…"], "bundled": "originals/Assets/DLC/Shared/Upgrade1.Civ5Pkg" } },
    { "source": "MiddleEarth/UI/InGame.lua", "destination": "Assets/DLC/Shared/MiddleEarth/UI/InGame.lua",
      "size": 43489, "sha256": "…", "mode": "add" }
  ]
}
```

- `mode: "add"`: a new file. `mode: "replace"`: overwrites a vanilla file, which must exist. If `original.sha256` is given, the game's file must be one of those versions, or the app refuses to install and suggests Steam's *Verify integrity*.
- `original.bundled`: a copy of the vanilla file, used when the game already contains the mod's version (manual install), so a genuine original can still be restored.
- All paths are relative, use `/`, and are validated: no `..`, no absolute paths, no drive letters, no backslashes. Destinations must be unique (case-insensitive). Source files must be regular files (no symlinks) inside `sourceRoot`, and their hashes are checked before every install.
- The *build id* is a hash over all `(mode, destination, sha256)` entries, so it identifies one exact build.

### Adding another mod

1. Create `mods/<id>/mod.source.json` (copy the MiddleEarth one): `sources` maps a build folder to a game folder, and `replaces` lists every game file the mod overwrites, with the path of an original copy.
2. Add `<id>` to `mods/index.json`.
3. `npm run payload`. A new tile **<name>** appears (add artwork in `src/renderer/src/assets` + `LOOK` in `SwitchButtons.tsx`). No engine code changes.

(You can also hand-write `manifest.json` + `payload/` and skip `mod.source.json`.)

## Backups, state and recovery

App data folder (`app.getPath('userData')`):
- Linux: `~/.config/Civilization V Mod Manager/`
- Windows: `%APPDATA%\Civilization V Mod Manager\`

| File/folder | Purpose |
|---|---|
| `state.json` | The managed install: mod id/version/build, game path, every file it manages with its hash and kind (`added`, `adopted` or `replaced`), folders it created |
| `journal.jsonl` | Exists only while an install runs (or after one was interrupted) |
| `backups/<installId>/…` | Originals of every file that was overwritten |
| `conflicts/<time>/…` | Copies of files someone else changed that had to be overwritten while restoring vanilla (never deleted automatically) |
| `game-cache-previous/` | The game cache moved away at the last switch |

**Install:**
1. Check every source file's hash.
2. Plan every file and refuse before changing anything if a vanilla file is missing or foreign.
3. Check write permission.
4. For each file: write a journal line first, then back up the existing file (verified by hash), then write the new file through a temp file and rename.
5. Re-hash every installed file.
6. Write `state.json` and delete the journal.

If anything fails, everything in the journal is rolled back and the game is unchanged. If even the rollback fails (or the app is killed), the journal stays. The app then shows *Unknown / Inconsistent*, and the next click rolls back first.

**Restore vanilla:** for each managed file, newest first:
- **Added or adopted file:** deleted only if its content is still exactly what was installed. Otherwise it's left in place, with a warning.
- **Replaced file:** restored from the backup and verified. If someone else had changed it meanwhile, that version is first saved to `conflicts/`.

Folders the install created are removed only if empty. Every step is idempotent, so a failed restore can simply be retried. Backups are deleted only after a fully successful restore.

**State detection** (on start and after every operation) re-hashes the files and never trusts the last button press. It reports **Unknown / Inconsistent** when:
- files were changed outside the app (for example a Steam update or *Verify integrity* restored `Upgrade1.Civ5Pkg`),
- a previous operation was interrupted,
- the mod is present but wasn't installed by the app,
- a vanilla file was modified by something else.

In each case the message explains what to click.

## Assumptions about the MiddleEarth project

- `dist/DLC_Shared/Shared` (from `tools/build_dlc.py`, the "Upgrade 1" packaging) is the current, working build. It is identical to `dist/MiddleEarth_DLC.zip`.
- The only vanilla file it replaces is `Assets/DLC/Shared/Upgrade1.Civ5Pkg`. `vendor/civ5/Upgrade1_original.Civ5Pkg` is a genuine copy of the stock file and is the same on Windows and Linux (same Steam depot). Every other file goes into the new `Assets/DLC/Shared/MiddleEarth/` folder.
- Emptying the game cache after switching is required in both directions (README: install step 2 and "Undo").
- Players don't also enable the old `Middle Earth MP (v 1)` mod or the six original mods in the Mods menu.

## Remaining manual steps / open issues

- Steam updates or *Verify integrity* put back the stock `Upgrade1.Civ5Pkg`. The app then shows *Unknown / Inconsistent*; click the **Middle Earth** tile to repair.
- After changing the mod, run `npm run build` again and redistribute the exe. Friends must use the same build id.
- No custom app icon or exe version info yet (editing exe resources from Linux needs Wine); nothing is code-signed.
- On Windows the running-game check uses `tasklist`, and on Linux `/proc`. If the game runs under an unusual process name, close it manually before switching.
