import fs from 'node:fs/promises'
import path from 'node:path'
import { execFile } from 'node:child_process'
import { CIV5_APP_ID } from './detect'

/**
 * Where Civ V keeps its cache folder (Documents/My Games/Sid Meier's Civilization 5/cache).
 * Linux/Proton: inside the game's Proton prefix, which Steam creates in the same library as the game:
 *   <library>/steamapps/compatdata/8930/pfx/drive_c/users/steamuser/Documents/My Games/...
 * Windows: the user's Documents folder.
 */
export function gameCacheCandidates(platform: NodeJS.Platform, gamePath: string, documentsDir: string): string[] {
  const tail = ['My Games', "Sid Meier's Civilization 5", 'cache']
  if (platform === 'win32') return [path.join(documentsDir, ...tail)]
  const steamapps = path.resolve(gamePath, '..', '..') // <library>/steamapps/common/<game> -> <library>/steamapps
  return [path.join(steamapps, 'compatdata', CIV5_APP_ID, 'pfx', 'drive_c', 'users', 'steamuser', 'Documents', ...tail)]
}

/** True when a Civilization V process is running (Windows: tasklist; Linux: /proc, which also sees Proton/Wine). */
export async function isGameRunning(platform: NodeJS.Platform): Promise<boolean> {
  if (platform === 'win32') {
    const out = await new Promise<string>((resolve) =>
      execFile('tasklist', ['/FO', 'CSV', '/NH'], { windowsHide: true }, (err, stdout) => resolve(err ? '' : stdout))
    )
    return /"civilizationv(_dx11|_tablet)?\.exe"/i.test(out)
  }
  if (platform !== 'linux') return false
  let pids: string[]
  try {
    pids = (await fs.readdir('/proc')).filter((p) => /^\d+$/.test(p))
  } catch {
    return false
  }
  for (const pid of pids) {
    try {
      // comm is truncated to 15 chars ("CivilizationV_D"), which is enough.
      const comm = (await fs.readFile(`/proc/${pid}/comm`, 'utf8')).trim().toLowerCase()
      if (comm.startsWith('civilizationv')) return true
    } catch {
      /* process vanished or not readable */
    }
  }
  return false
}

/** Windows: Steam's install path from the registry (HKCU SteamPath, HKLM InstallPath). */
export async function windowsRegistrySteamPaths(): Promise<string[]> {
  const queries: [string, string][] = [
    ['HKCU\\Software\\Valve\\Steam', 'SteamPath'],
    ['HKLM\\SOFTWARE\\WOW6432Node\\Valve\\Steam', 'InstallPath'],
    ['HKLM\\SOFTWARE\\Valve\\Steam', 'InstallPath']
  ]
  const out: string[] = []
  for (const [key, value] of queries) {
    const stdout = await new Promise<string>((resolve) =>
      execFile('reg', ['query', key, '/v', value], { windowsHide: true }, (err, so) => resolve(err ? '' : so))
    )
    const m = stdout.match(new RegExp(`${value}\\s+REG_\\w+\\s+(.+)`, 'i'))
    if (m) out.push(path.win32.normalize(m[1].trim()))
  }
  return out
}
