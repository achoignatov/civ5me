import fs from 'node:fs/promises'
import path from 'node:path'
import { parseLibraryFolders } from './vdf'
import { isErrno } from '../fileOperations/hash'
import type { GameSource } from '@shared/types'

export const GAME_FOLDER_NAME = "Sid Meier's Civilization V"
export const CIV5_APP_ID = '8930'

export interface Validation {
  valid: boolean
  /** Why the folder is not a usable Civilization V: Brave New World installation. */
  reason: string | null
  /** The folder does contain Civilization V, but something is missing (e.g. Brave New World). */
  isCiv: boolean
}

/**
 * A folder is a Civ V BNW installation when it contains the game executable, the Assets folder and the
 * Brave New World expansion (Assets/DLC/Expansion2). Names are matched case-insensitively because Steam
 * on Linux keeps Windows casing but users may copy installs around.
 */
export async function validateGameDir(dir: string): Promise<Validation> {
  const st = await statOrNull(dir)
  if (!st) return { valid: false, reason: `Folder "${dir}" does not exist.`, isCiv: false }
  if (!st.isDirectory()) return { valid: false, reason: `"${dir}" is not a folder.`, isCiv: false }
  let names: string[]
  try {
    names = await fs.readdir(dir)
  } catch (e) {
    return { valid: false, reason: `Cannot read "${dir}": ${(e as Error).message}`, isCiv: false }
  }
  const lower = new Set(names.map((n) => n.toLowerCase()))
  if (!lower.has('civilizationv.exe') && !lower.has('civilizationv_dx11.exe')) {
    return { valid: false, reason: `"${dir}" does not contain CivilizationV.exe; it is not a Civilization V installation folder.`, isCiv: false }
  }
  const assets = await childDir(dir, 'Assets')
  if (!assets) return { valid: false, reason: `"${dir}" has no Assets folder; the installation looks incomplete.`, isCiv: true }
  const dlc = await childDir(assets, 'DLC')
  const bnw = dlc && (await childDir(dlc, 'Expansion2'))
  if (!bnw) {
    return { valid: false, reason: `Civilization V was found in "${dir}", but Brave New World (Assets/DLC/Expansion2) is not installed.`, isCiv: true }
  }
  return { valid: true, reason: null, isCiv: true }
}

async function statOrNull(p: string) {
  try {
    return await fs.stat(p)
  } catch (e) {
    if (isErrno(e, 'ENOENT') || isErrno(e, 'ENOTDIR')) return null
    throw e
  }
}

/** Find a child directory by name, case-insensitively. */
async function childDir(dir: string, name: string): Promise<string | null> {
  let names: string[]
  try {
    names = await fs.readdir(dir)
  } catch {
    return null
  }
  const hit = names.find((n) => n.toLowerCase() === name.toLowerCase())
  if (!hit) return null
  const p = path.join(dir, hit)
  const st = await statOrNull(p)
  return st?.isDirectory() ? p : null
}

export interface DetectEnv {
  platform: NodeJS.Platform
  home: string
  env: Record<string, string | undefined>
  /** Directories checked in step 1: the current working directory and the folder the app itself is in. */
  currentDirs: string[]
  /** Windows only: Steam install paths read from the registry. */
  registrySteamPaths?: () => Promise<string[]>
}

/** Standard Steam root folders for the OS (not a disk scan: a fixed, short list). */
export async function steamRoots(env: DetectEnv): Promise<string[]> {
  if (env.platform === 'win32') {
    const roots = env.registrySteamPaths ? await env.registrySteamPaths().catch(() => []) : []
    for (const v of ['ProgramFiles(x86)', 'ProgramFiles']) {
      const pf = env.env[v]
      if (pf) roots.push(path.win32.join(pf, 'Steam'))
    }
    roots.push('C:\\Program Files (x86)\\Steam')
    return dedupe(roots)
  }
  const h = env.home
  return dedupe([
    path.join(h, '.local/share/Steam'),
    path.join(h, '.steam/steam'),
    path.join(h, '.steam/root'),
    path.join(h, '.var/app/com.valvesoftware.Steam/.local/share/Steam'), // Flatpak Steam
    path.join(h, 'snap/steam/common/.local/share/Steam') // Snap Steam
  ])
}

/** Every Steam library folder listed in <steamRoot>/steamapps/libraryfolders.vdf, plus the roots themselves. */
export async function steamLibraries(env: DetectEnv): Promise<string[]> {
  const libs: string[] = []
  for (const root of await steamRoots(env)) {
    libs.push(root)
    try {
      const text = await fs.readFile(path.join(root, 'steamapps', 'libraryfolders.vdf'), 'utf8')
      libs.push(...parseLibraryFolders(text))
    } catch {
      /* no Steam at this root */
    }
  }
  return dedupe(libs)
}

export async function defaultGameCandidates(env: DetectEnv): Promise<string[]> {
  return (await steamLibraries(env)).map((lib) => path.join(lib, 'steamapps', 'common', GAME_FOLDER_NAME))
}

export interface DetectResult {
  path: string | null
  source: GameSource | null
  /** Every folder that was checked, in order (shown to the user when nothing was found). */
  searched: string[]
  /** A checked folder that contains Civilization V but can't be used (e.g. Brave New World missing). */
  problem: string | null
}

/**
 * Detection order: the current folder / the app's own folder -> the default Steam locations (Steam libraries) ->
 * nothing. There is no folder picker: a game in a custom location is found by starting the app from inside the game
 * folder.
 */
export async function detectGame(env: DetectEnv): Promise<DetectResult> {
  const searched: string[] = []
  let problem: string | null = null
  const check = async (dir: string) => {
    searched.push(dir)
    const v = await validateGameDir(dir)
    if (!v.valid && v.isCiv && !problem) problem = v.reason
    return v.valid
  }
  for (const dir of dedupe(env.currentDirs.map((d) => path.resolve(d)))) {
    if (await check(dir)) return { path: dir, source: 'cwd', searched, problem: null }
  }
  for (const dir of await defaultGameCandidates(env)) {
    if (await check(dir)) return { path: await realOr(dir), source: 'default', searched, problem: null }
  }
  return { path: null, source: null, searched, problem }
}

async function realOr(p: string): Promise<string> {
  try {
    return await fs.realpath(p)
  } catch {
    return p
  }
}

function dedupe(xs: string[]): string[] {
  const seen = new Set<string>()
  return xs.filter((x) => {
    const k = path.normalize(x).replace(/[\\/]+$/, '')
    if (seen.has(k)) return false
    seen.add(k)
    return true
  })
}
