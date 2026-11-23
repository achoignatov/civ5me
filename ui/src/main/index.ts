import path from 'node:path'
import os from 'node:os'
import { app, BrowserWindow, ipcMain, screen, shell } from 'electron'
import { Controller } from './core/controller'
import { RepoSourceBuilder } from './core/modManager/sourceBuild'
import { windowsRegistrySteamPaths } from './core/gameDetection/gameEnvironment'
import { UserError, messageOf } from './core/fileOperations/errors'
import type { OperationResult } from '@shared/types'

// Mods ship next to the app: <resources>/mods when packaged, ui/mods in development.
const modsRoot = app.isPackaged ? path.join(process.resourcesPath, 'mods') : path.join(app.getAppPath(), 'mods')

let win: BrowserWindow | null = null
let controller: Controller

// Development-only smoke test (npm run smoke): hidden window, separate data folder, read-only refresh through the
// real preload/IPC path, screenshot + status JSON written to CIV5MM_SMOKE_OUT, then quit. Never switches anything.
const smokeOut = !app.isPackaged ? process.env.CIV5MM_SMOKE_OUT : undefined
if (smokeOut) app.setPath('userData', path.join(smokeOut, 'userData'))

function createWindow(): void {
  // 1170x1014 by default, but never larger than the screen's work area (e.g. small laptop screens).
  const area = screen.getPrimaryDisplay().workAreaSize
  win = new BrowserWindow({
    show: !smokeOut,
    width: Math.min(1170, area.width),
    height: Math.min(1014, area.height),
    minWidth: 520,
    minHeight: 460,
    title: 'Civilization V Mod Manager',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  })
  // The renderer never navigates or opens windows; external links go to the system browser.
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https:\/\//.test(url)) void shell.openExternal(url)
    return { action: 'deny' }
  })
  win.webContents.on('will-navigate', (e) => e.preventDefault())

  if (smokeOut) {
    win.webContents.once('did-finish-load', async () => {
      const status = await win!.webContents.executeJavaScript('window.civ5mm.refresh()')
      await new Promise((r) => setTimeout(r, 1500))
      const img = await win!.webContents.capturePage()
      const fs = await import('node:fs/promises')
      await fs.writeFile(path.join(smokeOut, 'smoke.png'), img.toPNG())
      await fs.writeFile(path.join(smokeOut, 'status.json'), JSON.stringify(status, null, 2))
      app.quit()
    })
  }
  if (!app.isPackaged && process.env.ELECTRON_RENDERER_URL) void win.loadURL(process.env.ELECTRON_RENDERER_URL)
  else void win.loadFile(path.join(__dirname, '../renderer/index.html'))
}

function registerIpc(): void {
  ipcMain.handle('status:get', () => controller.getStatus())
  ipcMain.handle('status:refresh', () => controller.refresh())
  ipcMain.handle('game:running', () => controller.isGameRunning())
  ipcMain.handle('config:switch', (_e, id: unknown) => {
    if (typeof id !== 'string' || !/^[a-z0-9-]{1,64}$/.test(id)) throw new Error('invalid configuration id')
    return guard(() => controller.switchTo(id))
  })
}

async function guard(fn: () => Promise<OperationResult>): Promise<OperationResult> {
  try {
    return await fn()
  } catch (e) {
    return { ok: false, message: e instanceof UserError ? e.message : `Unexpected error: ${messageOf(e)}`, warnings: [], status: await controller.getStatus() }
  }
}

if (!app.requestSingleInstanceLock()) {
  // Two instances switching files at the same time would be unsafe.
  app.quit()
} else {
  app.on('second-instance', () => {
    if (win) {
      if (win.isMinimized()) win.restore()
      win.focus()
    }
  })
  void app.whenReady().then(() => {
    controller = new Controller({
      dataDir: app.getPath('userData'),
      modsRoot,
      documentsDir: app.getPath('documents'),
      // development (running from the repository): rebuild the mod from the working tree before installing it
      sourceBuilder: app.isPackaged ? undefined : new RepoSourceBuilder({
        modsRoot,
        logDir: path.join(app.getPath('userData'), 'build-logs'),
        platform: process.platform,
        node: { command: process.execPath, env: { ELECTRON_RUN_AS_NODE: '1' } }
      }),
      detectEnv: {
        platform: process.platform,
        home: os.homedir(),
        env: process.env,
        // Step 1 of detection: the current directory and the folder the app itself is in. For the portable exe that is
        // the folder of the .exe the user started (PORTABLE_EXECUTABLE_FILE), not the temp folder it unpacks to; for
        // the AppImage the folder of the .AppImage. Putting the app into a custom game folder is how it finds that game.
        currentDirs: [...new Set([process.cwd(), path.dirname(process.env.PORTABLE_EXECUTABLE_FILE ?? process.env.APPIMAGE ?? process.execPath)])],
        registrySteamPaths: process.platform === 'win32' ? windowsRegistrySteamPaths : undefined
      }
    })
    controller.onProgress((p) => win?.webContents.send('progress', p))
    registerIpc()
    createWindow()
  })
  app.on('window-all-closed', () => app.quit())
}
