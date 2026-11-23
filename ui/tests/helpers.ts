import fs from 'node:fs/promises'
import os from 'node:os'
import path from 'node:path'
import { createHash } from 'node:crypto'
import type { FsOps } from '../src/main/core/fileOperations/fsOps'
import { realFsOps } from '../src/main/core/fileOperations/fsOps'

export const sha = (s: string | Buffer) => createHash('sha256').update(s).digest('hex')

const created: string[] = []

/** Fresh temp folder; every test works only inside folders like this, never on a real game install. */
export async function tmp(prefix = 'civ5mm-test-'): Promise<string> {
  const d = await fs.mkdtemp(path.join(os.tmpdir(), prefix))
  created.push(d)
  return d
}

/** Remove the temp folders created by this test file (called from tests/setup.ts). */
export async function removeTempDirs(): Promise<void> {
  for (const d of created.splice(0)) await fs.rm(d, { recursive: true, force: true })
}

export async function write(file: string, content: string | Buffer): Promise<void> {
  await fs.mkdir(path.dirname(file), { recursive: true })
  await fs.writeFile(file, content)
}

export const VANILLA_PKG = '<Civ5Package>vanilla upgrade 1</Civ5Package>'

/** A fake Civilization V BNW installation. */
export async function makeGame(dir: string, opts: { bnw?: boolean; exe?: boolean } = {}): Promise<string> {
  if (opts.exe !== false) await write(path.join(dir, 'CivilizationV.exe'), 'exe')
  await write(path.join(dir, 'Assets', 'UI', 'InGame.lua'), 'vanilla ingame')
  await write(path.join(dir, 'Assets', 'DLC', 'Shared', 'Upgrade1.Civ5Pkg'), VANILLA_PKG)
  await write(path.join(dir, 'Assets', 'DLC', 'Shared', 'UI', 'stock.xml'), 'stock')
  if (opts.bnw !== false) await write(path.join(dir, 'Assets', 'DLC', 'Expansion2', 'Expansion2.Civ5Pkg'), 'bnw')
  return dir
}

export interface FakeFile {
  source?: string
  destination: string
  content: string
  mode?: 'add' | 'replace'
  /** replace only */
  original?: string
  bundleOriginal?: boolean
}

/** Write mods/index.json + mods/<id>/{manifest.json,payload,originals} like build-payload.mjs does. */
export async function makeMod(modsRoot: string, id: string, files: FakeFile[], extra: Record<string, unknown> = {}): Promise<string> {
  const dir = path.join(modsRoot, id)
  const entries = []
  for (const f of files) {
    const source = f.source ?? f.destination.split('/').slice(-2).join('/')
    await write(path.join(dir, 'payload', ...source.split('/')), f.content)
    const e: Record<string, unknown> = { source, destination: f.destination, size: Buffer.byteLength(f.content), sha256: sha(f.content), mode: f.mode ?? 'add' }
    if (f.original !== undefined) {
      const o: Record<string, unknown> = { sha256: [sha(f.original)] }
      if (f.bundleOriginal) {
        o.bundled = `originals/${f.destination}`
        await write(path.join(dir, 'originals', ...f.destination.split('/')), f.original)
      }
      e.original = o
    }
    entries.push(e)
  }
  const manifest = { schemaVersion: 1, id, name: `${id} MOD`, version: '1', description: '', sourceRoot: 'payload', clearGameCache: false, files: entries, ...extra }
  await write(path.join(dir, 'manifest.json'), JSON.stringify(manifest, null, 1))
  let index: { mods: string[] } = { mods: [] }
  try {
    index = JSON.parse(await fs.readFile(path.join(modsRoot, 'index.json'), 'utf8'))
  } catch {
    /* new */
  }
  if (!index.mods.includes(id)) index.mods.push(id)
  await write(path.join(modsRoot, 'index.json'), JSON.stringify(index))
  return dir
}

/** The standard test mod: replaces Upgrade1.Civ5Pkg and adds files in a new MiddleEarth folder. */
export async function makeStandardMod(modsRoot: string, id = 'me', bundleOriginal = true): Promise<string> {
  return makeMod(modsRoot, id, [
    { source: 'Upgrade1.Civ5Pkg', destination: 'Assets/DLC/Shared/Upgrade1.Civ5Pkg', content: `<Civ5Package>modded ${id}</Civ5Package>`, mode: 'replace', original: VANILLA_PKG, bundleOriginal },
    { source: 'ME/UI/InGame.lua', destination: `Assets/DLC/Shared/${id}/UI/InGame.lua`, content: `ingame ${id}` },
    { source: 'ME/Art/unit.dds', destination: `Assets/DLC/Shared/${id}/Art/Units/unit.dds`, content: `dds ${id}` },
    { source: 'ME/Maps/map.lua', destination: `Assets/DLC/Shared/${id}/Maps/map.lua`, content: `map ${id}` }
  ])
}

/** relpath -> sha256 of every file under dir (used to prove the game folder is exactly as before). */
export async function snapshot(dir: string): Promise<Record<string, string>> {
  const out: Record<string, string> = {}
  async function walk(d: string) {
    for (const e of await fs.readdir(d, { withFileTypes: true })) {
      const p = path.join(d, e.name)
      if (e.isDirectory()) {
        out[path.relative(dir, p).split(path.sep).join('/') + '/'] = 'dir'
        await walk(p)
      } else out[path.relative(dir, p).split(path.sep).join('/')] = sha(await fs.readFile(p))
    }
  }
  await walk(dir)
  return out
}

export async function exists(p: string): Promise<boolean> {
  return fs.access(p).then(
    () => true,
    () => false
  )
}

/** FsOps that fails a chosen call with a given errno code. */
export function faultyFs(fail: { op: keyof FsOps; nth: number; code?: string; times?: number }): FsOps & { calls: Record<string, number> } {
  const calls: Record<string, number> = {}
  let failures = 0
  const wrap =
    <K extends keyof FsOps>(op: K) =>
    async (...args: Parameters<FsOps[K]>): Promise<void> => {
      calls[op] = (calls[op] ?? 0) + 1
      if (op === fail.op && calls[op] >= fail.nth && failures < (fail.times ?? 1)) {
        failures++
        const e = new Error(`injected ${fail.code ?? 'EACCES'} on ${op}`) as NodeJS.ErrnoException
        e.code = fail.code ?? 'EACCES'
        throw e
      }
      // @ts-expect-error spread of a tuple parameter
      return realFsOps[op](...args)
    }
  return { copyFile: wrap('copyFile'), rename: wrap('rename'), unlink: wrap('unlink'), mkdir: wrap('mkdir'), rmdir: wrap('rmdir'), calls }
}
