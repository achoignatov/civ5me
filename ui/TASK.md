# Task: Build a React + Electron Mod Manager for Civilization V (BNW)

> This is the original task description (2026-11-22). The implemented app is documented in [README.md](README.md), which wins where the two differ. Main differences: there is no folder picker and no "change directory" option (the app searches the default Steam locations and its own folder; for a custom location, start the app from the game folder); the MiddleEarth files come from the project's DLC build (`Assets/DLC/Shared`: one replaced file, `Upgrade1.Civ5Pkg`, plus the added `MiddleEarth/` folder) rather than Lua/asset patches spread over the install; and nothing is ever installed or restored automatically, only when the user clicks a tile.

## 1. Project Overview

I have an existing multiplayer Civilization V: Brave New World (BNW) modification called **MiddleEarth**.

This is not a conventional Civilization V mod installed through the game's Mods menu. Instead, it works by patching the game's installation directory directly. It replaces, adds, or modifies certain Lua scripts, assets, and other game files in various locations within the Civilization V installation.

For multiplayer compatibility, **every human player must have exactly the same modded files installed**.

I want to build a lightweight desktop application using **React + Electron** that allows players to easily switch between:

- **Vanilla BNW** – the original, unmodified Civilization V: Brave New World experience.
- **MiddleEarth MOD** – the modified game experience, with all required mod files installed.

The application must work on:

- Windows (native Steam installation).
- Linux (Steam installation running Civilization V through Proton).

The application should initially be simple and functional. We will work on visual design, branding, and assets later.

Implement the application inside a new folder named `ui/` in the root of the existing project.

---

## 2. IMPORTANT: Inspect the Existing Project First

Before writing any code:

1. Inspect the existing project structure.
2. Identify the existing MiddleEarth mod files, Lua scripts, assets, and any other files that need to be installed into Civilization V.
3. Determine how the existing project is organized and where the source files for the mod are located.
4. Identify the exact destination paths inside the Civilization V installation directory for every modded file.
5. Determine which files must be removed or restored when switching back to vanilla BNW.
6. Identify whether the existing project already contains installation scripts, manifests, file mappings, or other relevant infrastructure.

**Do not assume file paths, invent file mappings, or arbitrarily copy the entire project into the game directory.**

Use the existing project as the source of truth.

If any necessary information is missing or ambiguous, document it and ask me before implementing the affected functionality.

Do not modify or reorganize existing project files unnecessarily. The Electron application must live in `ui/`.

---

## 3. Technology Stack

Use:

- Electron
- React
- TypeScript
- Vite
- Node.js
- A suitable lightweight CSS solution

Use current stable, mutually compatible versions of the dependencies.

The project must be independently installable and runnable from the `ui/` directory.

Suggested development commands:

- `npm install`
- `npm run dev`
- `npm run build`

Provide the necessary Electron configuration, Vite configuration, TypeScript configuration, and package scripts.

Follow Electron security best practices:

- `contextIsolation: true`
- `nodeIntegration: false`
- Use a preload script.
- Expose only explicitly required APIs through `contextBridge`.
- Do not expose unrestricted filesystem access to the React renderer.
- Perform filesystem operations in the Electron main process.

---

## 4. Game Detection

The application needs a simple and predictable Civilization V installation detection mechanism.

**Do not scan the entire filesystem.**

Use the following detection sequence:

### Step 1: Check the current directory

Check whether the current working directory contains a valid Civilization V installation.

The detection should verify the presence of recognizable game files and directories, not merely check whether a folder exists.

### Step 2: Check the default installation path

If the current directory is not a valid installation, check the expected default Steam installation location for the current operating system.

Account for:

**Windows:**
- The standard Steam installation location.
- Civilization V's standard Steam library installation path.

**Linux:**
- The standard Steam installation location.
- The standard Steam library layout.
- Civilization V's Steam installation directory when running through Proton.

Do not scan arbitrary disks or unrelated directories.

If Steam is installed in a nonstandard location, the user can manually locate the installation.

### Step 3: Manual Browse

If neither automatic check finds the game, show a folder browser allowing the user to select their Civilization V installation directory.

The application must validate the selected directory before accepting it.

If the selected directory is valid:

- Save the selected installation path.
- Automatically reuse it on subsequent launches.
- Validate it again when the application starts.
- If it no longer exists or is no longer valid, resume the normal detection process.

Use appropriate persistent application settings storage.

The user should not need to browse for the installation every time they launch the application.

### Detection UI

Show the detected game installation path somewhere in the interface.

Provide a way to change the selected installation directory manually, even if automatic detection succeeds.

Display an informative status when the game cannot be found.

---

## 5. Operating System and Proton Compatibility

The application must support both Windows and Linux.

On Linux, Civilization V runs through Steam Proton. However, the mod manager must operate directly on the actual game installation directory on the Linux filesystem.

Important considerations:

- Do not assume Windows-style paths on Linux.
- Do not assume a fixed Steam installation location.
- Handle Linux filesystem permissions and file access errors gracefully.
- Do not require the user to interact with Proton prefixes.
- Do not assume the game is installed in the default Steam library.
- Do not use Windows-specific filesystem operations.
- Use Node.js filesystem APIs and cross-platform path handling.

The application should modify the actual Civilization V installation files, not a copied game directory or a Proton virtual Windows installation.

---

## 6. Main UI

For the initial implementation, keep the UI extremely simple.

The main screen should contain:

1. Application title: **Civilization V Mod Manager**
2. Detected Civilization V installation path.
3. Current installation state:
   - Vanilla BNW
   - MiddleEarth MOD
   - Unknown / Inconsistent installation
4. Two prominent buttons:

   **Use BNW Vanilla**

   **Use MiddleEarth MOD**

5. A small status/message area showing the result of the most recent operation.

The buttons must be disabled when no valid Civilization V installation has been detected.

The UI should clearly communicate which configuration is currently active.

Do not spend time implementing sophisticated visual styling, animations, artwork, or branding. Use a clean, functional layout that we can redesign later.

---

## 7. Switching Between Vanilla and MiddleEarth

This is the core functionality of the application.

### Use MiddleEarth MOD

When the user clicks this button:

1. Validate the Civilization V installation.
2. Locate all necessary MiddleEarth source files in the existing project.
3. Install/extract/copy the required files into their exact destination locations inside the Civilization V installation.
4. Create any required directories.
5. Replace the corresponding vanilla files where necessary.
6. Preserve unrelated game files.
7. Verify that the installation operation completed successfully.
8. Update the application state to MiddleEarth MOD.

The operation should be deterministic and repeatable.

Running the operation multiple times must not produce duplicate files or an inconsistent installation.

### Use BNW Vanilla

When the user clicks this button:

1. Identify all files installed or modified by MiddleEarth.
2. Remove the modded files from the Civilization V installation.
3. Restore any original vanilla files that were replaced.
4. Remove any mod-specific files that were added.
5. Preserve unrelated game files.
6. Verify that the restoration completed successfully.
7. Update the application state to Vanilla BNW.

**Critical requirement: Switching back to vanilla must genuinely restore the original BNW experience.**

Simply deleting modded files is not sufficient if the mod overwrote existing vanilla files.

Before overwriting any original game file, the application must preserve the original version so it can be restored later.

Never assume that deleting a file will restore its vanilla equivalent.

### Important safety requirements

- Never delete files that do not belong to the mod manager.
- Never perform broad directory cleanup.
- Never overwrite a vanilla file without preserving its original contents.
- Never assume that an existing file belongs to MiddleEarth just because it has the same filename.
- Never silently ignore failed copy, deletion, or restoration operations.
- Handle partial failures safely.
- Validate destination paths to prevent path traversal.
- Do not allow mod source files to escape their designated source directory.
- Do not leave the game in an unknown partially modified state without informing the user.

Use a reliable backup and restoration mechanism.

If an operation fails halfway through, implement rollback or another recovery strategy so the installation does not remain unnecessarily inconsistent.

---

## 8. Extensible Architecture: Multiple Mods in the Future

Although the initial application only needs to support Vanilla BNW and MiddleEarth, its architecture must anticipate supporting multiple game configurations in the future.

For example, we may eventually want to add several other independent mods.

**Do not hardcode MiddleEarth-specific installation logic throughout the application.**

Instead, design a generic mod management system.

A suggested architecture:

```text
ui/
├── src/
│   ├── main/
│   │   ├── index.ts
│   │   ├── gameDetection/
│   │   ├── modManager/
│   │   ├── fileOperations/
│   │   └── backup/
│   │
│   ├── preload/
│   │   └── index.ts
│   │
│   ├── renderer/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── styles/
│   │   └── App.tsx
│   │
│   └── shared/
│       ├── types/
│       └── interfaces/
│
├── mods/
│   └── middleearth/
│       └── manifest.json
│
├── package.json
└── ...
```

This is a suggested structure, not a rigid requirement. Improve it if you have a better architectural approach.

### Mod manifest

Each mod should be represented by a manifest describing its installation requirements.

For example, the manifest could contain:

- Mod identifier.
- Display name.
- Version.
- Description.
- Source file locations.
- Destination file locations relative to the Civilization V installation.
- Whether a file replaces an existing vanilla file or is newly added.
- Any other information needed for safe installation and restoration.

The mod manager should read the manifest and execute generic installation and uninstallation operations.

Adding another mod in the future should ideally involve:

1. Adding its source files.
2. Adding its manifest.
3. Registering it in the available mod configurations.

We should not need to rewrite the core file-management engine for every new mod.

### Vanilla BNW as a configuration

Treat Vanilla BNW as the baseline configuration, not as another mod that requires its own set of installation files.

The architecture should support switching between Vanilla and any registered mod.

The initial UI only needs to expose the two configurations currently available.

---

## 9. Installation State and Reliability

The application must be able to determine the current game configuration reliably.

Do not rely exclusively on React state or assume that the last button clicked represents the actual installation state.

Persist a small installation-state record outside the game directory containing information such as:

- Managed game installation path.
- Currently active configuration.
- Installed mod identifier and version.
- Files managed by the application.
- Backup locations.
- Any information required for recovery.

On application startup:

1. Load the saved configuration.
2. Validate the game installation.
3. Inspect the managed files as necessary.
4. Determine whether the installation matches the recorded state.
5. If the state cannot be verified, report it as Unknown / Inconsistent rather than incorrectly claiming that a configuration is active.

The application must also handle situations where a user manually changes game files outside the application.

Keep the backup mechanism separate from the mod source files.

Do not store backups inside the game's installation directory.

---

## 10. User Experience and Error Handling

Provide clear feedback for:

- Game not found.
- Invalid installation directory.
- Missing mod source files.
- Missing manifest.
- Permission errors.
- Insufficient filesystem permissions.
- Failed file extraction or copying.
- Failed backup or restoration.
- Successful switching.
- Inconsistent installation state.

Show progress during longer operations.

Prevent users from triggering another installation operation while one is already running.

If administrator/root permissions are required, explain the issue clearly. Do not automatically request elevated privileges or silently attempt unsafe workarounds.

---

## 11. Implementation Expectations

I want a working application, not just a prototype or a collection of UI components.

Please:

1. Inspect the existing project before implementation.
2. Create the `ui/` project.
3. Implement game detection for Windows and Linux.
4. Implement persistent game installation path configuration.
5. Implement the generic manifest-driven mod installation engine.
6. Implement reliable vanilla backup and restoration.
7. Implement the initial two-button interface.
8. Implement progress and error reporting.
9. Ensure Electron security best practices.
10. Make the application buildable for both Windows and Linux.

Use TypeScript throughout the application wherever practical.

Separate filesystem logic from the React UI.

Keep the renderer unaware of direct filesystem paths beyond the limited information explicitly exposed by the main process.

Add useful comments for non-obvious logic.

---

## 12. Testing

Include tests for the critical file-management functionality.

At minimum, test:

- Valid game installation detection.
- Invalid installation detection.
- Manifest parsing and validation.
- Installing a mod that adds new files.
- Installing a mod that replaces vanilla files.
- Restoring replaced vanilla files.
- Removing newly added mod files.
- Repeated installation.
- Repeated uninstallation.
- Switching between configurations.
- Handling missing source files.
- Handling failed file operations.
- Recovery from partial installation.
- Protection against deleting unmanaged game files.

Use temporary test directories and mocked game installations. **Never use the actual Civilization V installation directory for automated tests.**

---

## 13. Deliverables

When finished, provide:

1. The complete implementation inside `ui/`.
2. A clear explanation of the project architecture.
3. Instructions for installing dependencies and running in development mode.
4. Instructions for building Windows and Linux versions.
5. An explanation of how the mod manifest works.
6. An explanation of how backups and restoration work.
7. A list of any assumptions made about the existing MiddleEarth project.
8. A list of any remaining manual steps or unresolved issues.

Make sure the application can be developed and built independently of the rest of the project.

---

## 14. Final Instructions

Prioritize correctness and data safety over speed.

The most important requirement is that switching between Vanilla BNW and MiddleEarth must be reliable and reversible.

The second most important requirement is a clean, extensible architecture that allows us to introduce additional mod configurations later.

Do not implement unnecessary features.

Do not modify existing game files during development or testing.

Do not make assumptions about the mod's file mappings. Derive them from the existing project and ask me when clarification is necessary.

**Start by inspecting the existing project and reporting your findings, especially the files that need to be installed, replaced, and restored. Then proceed with implementation once the required mappings are understood.**
