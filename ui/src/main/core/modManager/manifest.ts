import fs from 'node:fs/promises'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { checkRelPath, resolveInside } from '../fileOperations/safePath'
import { sha256OrNull, isErrno } from '../fileOperations/hash'
import { UserError } from '../fileOperations/errors'
import { VANILLA_ID } from '@shared/types'

/*
 * Mod manifest (mods/<id>/manifest.json), schemaVersion 1:
 *
 * {
 *   "schemaVersion": 1,
 *   "id": "middleearth",                 // [a-z0-9-], also the configuration id
 *   "name": "MiddleEarth MOD",
 *   "version": "1",
 *   "description": "...",
 *   "sourceRoot": "payload",             // folder (inside the mod folder) holding the files to install
 *   "clearGameCache": true,              // empty the game's cache folder after switching to/from this mod
 *   "files": [
 *     { "source": "Upgrade1.Civ5Pkg",                       // relative to sourceRoot
 *       "destination": "Assets/DLC/Shared/Upgrade1.Civ5Pkg", // relative to the game folder
 *       "size": 11646, "sha256": "...",                     // of the source file
 *       "mode": "replace",                                  // "add" = new file, "replace" = overwrites a vanilla file
 *       "original": {                                       // replace only (optional)
 *         "sha256": ["..."],                                // accepted hashes of the vanilla file
 *         "bundled": "originals/Upgrade1.Civ5Pkg"           // copy of the vanilla file inside the mod folder
 *       } }
 *   ]
 * }
 *
 * "replace" files must exist in the game. If "original.sha256" is given, the file in the game must be one of those
 * versions (or byte-identical to the mod's version AND a bundled original must exist), otherwise installation is
 * refused, because we could not restore a genuine vanilla file later.
 */

export type FileMode = 'add' | 'replace'

export interface ManifestFile {
  source: string
  destination: string
  size: number
  sha256: string
  mode: FileMode
  original?: { sha256: string[]; bundled?: string }
}

export interface Manifest {
  schemaVersion: 1
  id: string
  name: string
  version: string
  description: string
  sourceRoot: string
  clearGameCache: boolean
  files: ManifestFile[]
}

export interface LoadedMod {
  manifest: Manifest
  /** Absolute folder containing manifest.json. */
  dir: string
  /** Absolute folder containing the files to install. */
  sourceDir: string
  /** Hash over the whole file list: identifies this exact build of the mod. */
  buildId: string
}

const HEX64 = /^[0-9a-f]{64}$/

function fail(file: string, msg: string): never {
  throw new UserError(`Invalid mod manifest ${file}: ${msg}`)
}

/** Validate untrusted JSON as a Manifest. Throws UserError describing the first problem. */
export function parseManifest(raw: unknown, file = 'manifest.json'): Manifest {
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) fail(file, 'not a JSON object')
  const m = raw as Record<string, unknown>
  if (m.schemaVersion !== 1) fail(file, `unsupported schemaVersion ${String(m.schemaVersion)} (expected 1)`)
  if (typeof m.id !== 'string' || !/^[a-z0-9][a-z0-9-]*$/.test(m.id)) fail(file, '"id" must match [a-z0-9-]+')
  if (m.id === VANILLA_ID) fail(file, `"id" must not be "${VANILLA_ID}" (reserved for the baseline)`)
  for (const k of ['name', 'version'] as const) {
    if (typeof m[k] !== 'string' || !(m[k] as string).trim()) fail(file, `"${k}" must be a non-empty string`)
  }
  if (m.description !== undefined && typeof m.description !== 'string') fail(file, '"description" must be a string')
  if (m.clearGameCache !== undefined && typeof m.clearGameCache !== 'boolean') fail(file, '"clearGameCache" must be boolean')
  let sourceRoot: string
  try {
    sourceRoot = checkRelPath(m.sourceRoot, 'sourceRoot')
  } catch (e) {
    fail(file, (e as Error).message)
  }
  if (!Array.isArray(m.files) || m.files.length === 0) fail(file, '"files" must be a non-empty array')

  const seen = new Map<string, string>()
  const files: ManifestFile[] = m.files.map((f: unknown, i: number): ManifestFile => {
    const where = `files[${i}]`
    if (typeof f !== 'object' || f === null) fail(file, `${where} is not an object`)
    const e = f as Record<string, unknown>
    let source: string, destination: string
    try {
      source = checkRelPath(e.source, `${where}.source`)
      destination = checkRelPath(e.destination, `${where}.destination`)
    } catch (err) {
      fail(file, (err as Error).message)
    }
    // Destinations are compared case-insensitively: the game runs on Windows semantics (Proton too).
    const key = destination.toLowerCase()
    if (seen.has(key)) fail(file, `${where}.destination "${destination}" is listed twice`)
    seen.set(key, destination)
    if (typeof e.size !== 'number' || !Number.isInteger(e.size) || e.size < 0) fail(file, `${where}.size must be a non-negative integer`)
    if (typeof e.sha256 !== 'string' || !HEX64.test(e.sha256)) fail(file, `${where}.sha256 must be 64 lowercase hex chars`)
    if (e.mode !== 'add' && e.mode !== 'replace') fail(file, `${where}.mode must be "add" or "replace"`)
    const out: ManifestFile = { source, destination, size: e.size, sha256: e.sha256, mode: e.mode }
    if (e.original !== undefined) {
      if (e.mode !== 'replace') fail(file, `${where}.original is only allowed for mode "replace"`)
      const o = e.original as Record<string, unknown>
      if (typeof o !== 'object' || o === null) fail(file, `${where}.original must be an object`)
      if (!Array.isArray(o.sha256) || o.sha256.length === 0 || !o.sha256.every((h) => typeof h === 'string' && HEX64.test(h))) {
        fail(file, `${where}.original.sha256 must be a non-empty array of sha256 hashes`)
      }
      if (o.sha256.includes(e.sha256)) fail(file, `${where}: the mod file is identical to an original version`)
      out.original = { sha256: o.sha256 as string[] }
      if (o.bundled !== undefined) {
        try {
          out.original.bundled = checkRelPath(o.bundled, `${where}.original.bundled`)
        } catch (err) {
          fail(file, (err as Error).message)
        }
      }
    }
    return out
  })
  // A file can't also be the parent folder of another file.
  for (const key of seen.keys()) {
    const parts = key.split('/')
    for (let i = 1; i < parts.length; i++) {
      if (seen.has(parts.slice(0, i).join('/'))) fail(file, `"${parts.slice(0, i).join('/')}" is both a file and a folder`)
    }
  }
  return {
    schemaVersion: 1,
    id: m.id,
    name: (m.name as string).trim(),
    version: (m.version as string).trim(),
    description: typeof m.description === 'string' ? m.description : '',
    sourceRoot,
    clearGameCache: m.clearGameCache === true,
    files
  }
}

export function buildIdOf(m: Manifest): string {
  const h = createHash('sha256')
  for (const f of m.files) h.update(`${f.mode}\0${f.destination}\0${f.sha256}\n`)
  return h.digest('hex').slice(0, 16)
}

export async function loadMod(modDir: string): Promise<LoadedMod> {
  const file = path.join(modDir, 'manifest.json')
  let text: string
  try {
    text = await fs.readFile(file, 'utf8')
  } catch (e) {
    if (isErrno(e, 'ENOENT')) throw new UserError(`Mod manifest is missing: ${file}`)
    throw e
  }
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch (e) {
    throw new UserError(`Mod manifest ${file} is not valid JSON: ${(e as Error).message}`)
  }
  const manifest = parseManifest(raw, file)
  return { manifest, dir: modDir, sourceDir: resolveInside(modDir, manifest.sourceRoot, 'sourceRoot'), buildId: buildIdOf(manifest) }
}

export function sourcePath(mod: LoadedMod, f: ManifestFile): string {
  return resolveInside(mod.sourceDir, f.source, 'source')
}

export function bundledOriginalPath(mod: LoadedMod, f: ManifestFile): string | null {
  return f.original?.bundled ? resolveInside(mod.dir, f.original.bundled, 'original.bundled') : null
}

/**
 * Check that every source file (and bundled original) exists and matches its hash.
 * Returns a list of problems (empty = OK). Symlinks are rejected so nothing outside the mod folder is read.
 */
export async function verifySources(mod: LoadedMod, onFile?: () => void): Promise<string[]> {
  const problems: string[] = []
  for (const f of mod.manifest.files) {
    const src = sourcePath(mod, f)
    const p = await checkRegularFile(src)
    if (p) problems.push(`${f.source}: ${p}`)
    else {
      const h = await sha256OrNull(src)
      if (h !== f.sha256) problems.push(`${f.source}: content does not match the manifest`)
    }
    const orig = bundledOriginalPath(mod, f)
    if (orig) {
      const q = await checkRegularFile(orig)
      if (q) problems.push(`${f.original!.bundled}: ${q}`)
      else if (!f.original!.sha256.includes((await sha256OrNull(orig)) ?? '')) {
        problems.push(`${f.original!.bundled}: bundled original does not match original.sha256`)
      }
    }
    onFile?.()
  }
  return problems
}

async function checkRegularFile(p: string): Promise<string | null> {
  try {
    const st = await fs.lstat(p)
    if (st.isSymbolicLink()) return 'is a symbolic link (not allowed)'
    if (!st.isFile()) return 'is not a regular file'
    return null
  } catch (e) {
    if (isErrno(e, 'ENOENT') || isErrno(e, 'ENOTDIR')) return 'missing'
    return (e as Error).message
  }
}

/**
 * Load all registered mods. mods/index.json lists the registered mod folder names:
 *   { "mods": ["middleearth"] }
 * A mod that fails to load is returned as an error entry so the UI can show why it's unavailable.
 */
export async function loadRegistry(modsRoot: string): Promise<{ mods: LoadedMod[]; errors: { id: string; error: string }[] }> {
  const indexFile = path.join(modsRoot, 'index.json')
  let ids: string[]
  try {
    const raw = JSON.parse(await fs.readFile(indexFile, 'utf8')) as { mods?: unknown }
    if (!Array.isArray(raw.mods) || !raw.mods.every((x) => typeof x === 'string')) throw new Error('"mods" must be an array of folder names')
    ids = raw.mods as string[]
  } catch (e) {
    return { mods: [], errors: [{ id: '(registry)', error: `Cannot read mod registry ${indexFile}: ${(e as Error).message}` }] }
  }
  const mods: LoadedMod[] = []
  const errors: { id: string; error: string }[] = []
  for (const id of ids) {
    try {
      const mod = await loadMod(resolveInside(modsRoot, checkRelPath(id, 'mod folder'), 'mod folder'))
      if (mods.some((m) => m.manifest.id === mod.manifest.id)) throw new Error(`duplicate mod id "${mod.manifest.id}"`)
      mods.push(mod)
    } catch (e) {
      errors.push({ id, error: (e as Error).message })
    }
  }
  return { mods, errors }
}
