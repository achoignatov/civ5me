import fs from 'node:fs/promises'
import path from 'node:path'
import { beforeEach, describe, expect, it } from 'vitest'
import { ModEngine } from '../src/main/core/modManager/engine'
import { loadRegistry, type LoadedMod } from '../src/main/core/modManager/manifest'
import { exists, faultyFs, makeGame, makeMod, makeStandardMod, snapshot, tmp, VANILLA_PKG, write } from './helpers'

let game: string
let data: string
let modsRoot: string
let mods: LoadedMod[]
let engine: ModEngine
let vanilla: Record<string, string>

const UPG = 'Assets/DLC/Shared/Upgrade1.Civ5Pkg'
const g = (rel: string) => path.join(game, ...rel.split('/'))
const read = (rel: string) => fs.readFile(g(rel), 'utf8')

async function reloadMods() {
  const r = await loadRegistry(modsRoot)
  expect(r.errors).toEqual([])
  mods = r.mods
}

beforeEach(async () => {
  game = await makeGame(await tmp('civ5mm-game-'))
  data = await tmp('civ5mm-data-')
  modsRoot = await tmp('civ5mm-mods-')
  await makeStandardMod(modsRoot, 'me')
  await reloadMods()
  engine = new ModEngine(data)
  vanilla = await snapshot(game)
})

describe('install / uninstall', () => {
  it('installs new files and replaces the vanilla file, keeping the backup outside the game folder', async () => {
    await engine.switchTo(game, 'me', mods)
    expect(await read(UPG)).toBe('<Civ5Package>modded me</Civ5Package>')
    expect(await read('Assets/DLC/Shared/me/Art/Units/unit.dds')).toBe('dds me')
    const { install } = await engine.state.read()
    expect(install?.modId).toBe('me')
    expect(install?.files.find((f) => f.destination === UPG)?.kind).toBe('replaced')
    expect(install?.files.filter((f) => f.kind === 'added')).toHaveLength(3)
    // backup of the original lives in the data folder
    expect(await fs.readFile(engine.backups.pathFor(install!.installId, UPG), 'utf8')).toBe(VANILLA_PKG)
    expect(Object.keys(await snapshot(game)).some((k) => /civ5mm|backup/i.test(k))).toBe(false)
    expect(await engine.inspect(game, mods)).toMatchObject({ kind: 'mod', modId: 'me' })
    // unrelated game files untouched
    const now = await snapshot(game)
    for (const [k, v] of Object.entries(vanilla)) if (k !== UPG) expect(now[k]).toBe(v)
  })

  it('switching back to vanilla restores the exact original game folder', async () => {
    await engine.switchTo(game, 'me', mods)
    const r = await engine.switchTo(game, 'vanilla', mods)
    expect(r.message).toMatch(/Vanilla/)
    expect(await snapshot(game)).toEqual(vanilla)
    expect(await engine.inspect(game, mods)).toMatchObject({ kind: 'vanilla' })
    expect((await engine.state.read()).install).toBeNull()
    expect(await exists(path.join(data, 'backups'))).toBe(true)
    expect(await fs.readdir(path.join(data, 'backups'))).toEqual([]) // backups of finished installs are removed
  })

  it('repeated installation is a no-op and creates no duplicates', async () => {
    await engine.switchTo(game, 'me', mods)
    const once = await snapshot(game)
    const r = await engine.switchTo(game, 'me', mods)
    expect(r.message).toMatch(/already active/)
    expect(await snapshot(game)).toEqual(once)
    expect((await engine.state.read()).install?.files).toHaveLength(4)
  })

  it('repeated uninstallation is a no-op', async () => {
    await engine.switchTo(game, 'me', mods)
    await engine.switchTo(game, 'vanilla', mods)
    await engine.switchTo(game, 'vanilla', mods)
    expect(await snapshot(game)).toEqual(vanilla)
  })

  it('switches between configurations and between two mods', async () => {
    await makeStandardMod(modsRoot, 'other')
    await reloadMods()
    for (let i = 0; i < 2; i++) {
      await engine.switchTo(game, 'me', mods)
      expect(await engine.inspect(game, mods)).toMatchObject({ kind: 'mod', modId: 'me' })
      await engine.switchTo(game, 'other', mods)
      expect(await engine.inspect(game, mods)).toMatchObject({ kind: 'mod', modId: 'other' })
      expect(await exists(g('Assets/DLC/Shared/me'))).toBe(false)
      expect(await read(UPG)).toBe('<Civ5Package>modded other</Civ5Package>')
      await engine.switchTo(game, 'vanilla', mods)
      expect(await snapshot(game)).toEqual(vanilla)
    }
  })

  it('updates to a new build of the same mod', async () => {
    await engine.switchTo(game, 'me', mods)
    await makeMod(modsRoot, 'me', [
      { source: 'Upgrade1.Civ5Pkg', destination: UPG, content: 'v2', mode: 'replace', original: VANILLA_PKG },
      { source: 'new.lua', destination: 'Assets/DLC/Shared/me/new.lua', content: 'new' }
    ])
    await reloadMods()
    expect((await engine.inspect(game, mods)).details.join()).toMatch(/different build/)
    await engine.switchTo(game, 'me', mods)
    expect(await read(UPG)).toBe('v2')
    expect(await exists(g('Assets/DLC/Shared/me/UI/InGame.lua'))).toBe(false)
    await engine.switchTo(game, 'vanilla', mods)
    expect(await snapshot(game)).toEqual(vanilla)
  })
})

describe('refusals and failures', () => {
  it('refuses to install when source files are missing, without touching the game', async () => {
    await fs.rm(path.join(modsRoot, 'me', 'payload', 'ME', 'Maps', 'map.lua'))
    await expect(engine.switchTo(game, 'me', mods)).rejects.toThrow(/missing or damaged/)
    expect(await snapshot(game)).toEqual(vanilla)
    expect(await engine.state.journalExists()).toBe(false)
  })

  it('refuses when the vanilla file was changed by something else', async () => {
    await write(g(UPG), 'someone else modded this')
    const before = await snapshot(game)
    await expect(engine.switchTo(game, 'me', mods)).rejects.toThrow(/not the original game file/)
    expect(await snapshot(game)).toEqual(before)
    expect((await engine.inspect(game, mods)).kind).toBe('unknown')
  })

  it('refuses when a replaced vanilla file is missing', async () => {
    await fs.rm(g(UPG))
    await expect(engine.switchTo(game, 'me', mods)).rejects.toThrow(/missing from the game/)
  })

  it.each([
    ['copyFile', 3],
    ['copyFile', 1], // the backup copy itself fails
    ['rename', 2],
    ['mkdir', 2]
  ] as const)('rolls back completely when %s #%d fails', async (op, nth) => {
    const ffs = faultyFs({ op, nth })
    const e = new ModEngine(data, ffs)
    await expect(e.switchTo(game, 'me', mods)).rejects.toThrow(/rolled back; the game is unchanged/)
    expect(await snapshot(game)).toEqual(vanilla)
    expect(await e.state.journalExists()).toBe(false)
    expect((await e.state.read()).install).toBeNull()
    // and it works afterwards
    await engine.switchTo(game, 'me', mods)
    expect(await engine.inspect(game, mods)).toMatchObject({ kind: 'mod' })
  })

  it('explains permission errors', async () => {
    const e = new ModEngine(data, faultyFs({ op: 'copyFile', nth: 2, code: 'EACCES' }))
    await expect(e.switchTo(game, 'me', mods)).rejects.toThrow(/Permission denied/)
  })

  it('recovers from an interrupted installation (rollback itself failed, journal left behind)', async () => {
    // copy #5 fails (after two mod files were placed), and the rollback can't delete them -> half installed
    const ffs = faultyFs({ op: 'copyFile', nth: 5 })
    const broken = new ModEngine(data, {
      ...ffs,
      unlink: async (p) => {
        if (!p.endsWith('.civ5mm-tmp')) {
          const err = new Error('injected') as NodeJS.ErrnoException
          err.code = 'EBUSY'
          throw err
        }
        return fs.unlink(p).catch(() => undefined)
      }
    })
    await expect(broken.switchTo(game, 'me', mods)).rejects.toThrow(/Rolling back also failed/)
    expect(await engine.state.journalExists()).toBe(true)
    expect(await snapshot(game)).not.toEqual(vanilla)
    const st = await engine.inspect(game, mods)
    expect(st.kind).toBe('unknown')
    expect(st.details.join()).toMatch(/interrupted/)
    // a later switch (with a working filesystem) rolls back first
    await engine.switchTo(game, 'vanilla', mods)
    expect(await snapshot(game)).toEqual(vanilla)
    expect(await engine.state.journalExists()).toBe(false)
  })

  it('recovers from a crash where the journal ends with a torn line', async () => {
    const ffs = faultyFs({ op: 'copyFile', nth: 4 })
    const broken = new ModEngine(data, { ...ffs, unlink: async () => Promise.reject(Object.assign(new Error('x'), { code: 'EIO' })) })
    await expect(broken.switchTo(game, 'me', mods)).rejects.toThrow()
    await fs.appendFile(engine.state.journalFile, '{"t":"file","destin')
    await engine.switchTo(game, 'me', mods)
    expect(await engine.inspect(game, mods)).toMatchObject({ kind: 'mod' })
    await engine.switchTo(game, 'vanilla', mods)
    expect(await snapshot(game)).toEqual(vanilla)
  })

  it('a failed uninstall can be retried', async () => {
    await engine.switchTo(game, 'me', mods)
    const e = new ModEngine(data, faultyFs({ op: 'rename', nth: 1 }))
    await expect(e.switchTo(game, 'vanilla', mods)).rejects.toThrow(/Restoring vanilla failed/)
    expect((await engine.inspect(game, mods)).kind).toBe('unknown')
    await engine.switchTo(game, 'vanilla', mods)
    expect(await snapshot(game)).toEqual(vanilla)
  })
})

describe('protection of files that are not ours', () => {
  it('keeps user files placed inside folders the mod created', async () => {
    await engine.switchTo(game, 'me', mods)
    await write(g('Assets/DLC/Shared/me/UI/user-notes.txt'), 'mine')
    const r = await engine.switchTo(game, 'vanilla', mods)
    expect(await read('Assets/DLC/Shared/me/UI/user-notes.txt')).toBe('mine')
    expect(r.warnings.join()).toMatch(/kept because it contains files/)
    expect(await read(UPG)).toBe(VANILLA_PKG)
  })

  it('does not delete an installed file that was changed afterwards', async () => {
    await engine.switchTo(game, 'me', mods)
    await write(g('Assets/DLC/Shared/me/Maps/map.lua'), 'edited by the user')
    expect((await engine.inspect(game, mods)).kind).toBe('unknown')
    const r = await engine.switchTo(game, 'vanilla', mods)
    expect(await read('Assets/DLC/Shared/me/Maps/map.lua')).toBe('edited by the user')
    expect(r.warnings.join()).toMatch(/changed after installation/)
  })

  it('backs up and restores an unrelated file that sits where the mod adds one', async () => {
    await write(g('Assets/DLC/Shared/me/UI/InGame.lua'), 'pre-existing, not ours')
    const before = await snapshot(game)
    await engine.switchTo(game, 'me', mods)
    expect(await read('Assets/DLC/Shared/me/UI/InGame.lua')).toBe('ingame me')
    await engine.switchTo(game, 'vanilla', mods)
    expect(await snapshot(game)).toEqual(before)
  })

  it('a replaced file changed later (e.g. Steam verify) is detected and repaired', async () => {
    await engine.switchTo(game, 'me', mods)
    await write(g(UPG), VANILLA_PKG) // Steam "verify integrity" put the original back
    const st = await engine.inspect(game, mods)
    expect(st.kind).toBe('unknown')
    expect(st.details.join()).toMatch(/changed or removed outside/)
    await engine.switchTo(game, 'me', mods)
    expect(await engine.inspect(game, mods)).toMatchObject({ kind: 'mod' })
    await engine.switchTo(game, 'vanilla', mods)
    expect(await snapshot(game)).toEqual(vanilla)
  })

  it('keeps a copy of a foreign file found in place of a replaced file when restoring', async () => {
    await engine.switchTo(game, 'me', mods)
    await write(g(UPG), 'third version')
    const r = await engine.switchTo(game, 'vanilla', mods)
    expect(await read(UPG)).toBe(VANILLA_PKG)
    const saved = r.warnings.join().match(/saved to (.+?) before/)?.[1]
    expect(saved && (await fs.readFile(saved, 'utf8'))).toBe('third version')
  })

  it('never writes outside the game folder even with a malicious manifest', async () => {
    await write(path.join(modsRoot, 'evil', 'manifest.json'), JSON.stringify({
      schemaVersion: 1, id: 'evil', name: 'Evil', version: '1', sourceRoot: 'payload',
      files: [{ source: 'x', destination: '../outside.txt', size: 1, sha256: 'a'.repeat(64), mode: 'add' }]
    }))
    await write(path.join(modsRoot, 'index.json'), JSON.stringify({ mods: ['me', 'evil'] }))
    const r = await loadRegistry(modsRoot)
    expect(r.mods.map((m) => m.manifest.id)).toEqual(['me'])
    expect(r.errors[0].error).toMatch(/Invalid mod manifest/)
  })
})

describe('installs made outside the app', () => {
  async function manualInstall() {
    const m = mods[0]
    for (const f of m.manifest.files) await write(g(f.destination), await fs.readFile(path.join(m.sourceDir, f.source)))
  }

  it('is reported as unknown, and "vanilla" removes it using the bundled original', async () => {
    await manualInstall()
    const st = await engine.inspect(game, mods)
    expect(st.kind).toBe('unknown')
    expect(st.details.join()).toMatch(/not by this app/)
    const r = await engine.switchTo(game, 'vanilla', mods)
    expect(r.warnings.join()).toMatch(/installed outside this app/)
    expect(await snapshot(game)).toEqual(vanilla)
  })

  it('can be taken over by installing; uninstall then restores the original', async () => {
    await manualInstall()
    const r = await engine.switchTo(game, 'me', mods)
    expect(r.warnings.join()).toMatch(/taken over/)
    expect(await engine.inspect(game, mods)).toMatchObject({ kind: 'mod', modId: 'me' })
    await engine.switchTo(game, 'vanilla', mods)
    expect(await snapshot(game)).toEqual(vanilla)
  })

  it('refuses when the original is not available', async () => {
    modsRoot = await tmp()
    await makeStandardMod(modsRoot, 'me', false)
    await reloadMods()
    await manualInstall()
    await expect(engine.switchTo(game, 'me', mods)).rejects.toThrow(/no copy of the original/)
    await expect(engine.switchTo(game, 'vanilla', mods)).rejects.toThrow(/no original copy/)
  })

  it('leftover inactive files are reported but count as vanilla', async () => {
    await write(g('Assets/DLC/Shared/me/Maps/map.lua'), 'map me')
    const st = await engine.inspect(game, mods)
    expect(st.kind).toBe('vanilla')
    expect(st.details.join()).toMatch(/inactive/)
    await engine.switchTo(game, 'vanilla', mods)
    expect(await snapshot(game)).toEqual(vanilla)
  })
})
