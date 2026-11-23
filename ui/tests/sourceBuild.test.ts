import fs from 'node:fs/promises'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { Controller } from '../src/main/core/controller'
import { GAME_FOLDER_NAME } from '../src/main/core/gameDetection/detect'
import { UserError } from '../src/main/core/fileOperations/errors'
import { RepoSourceBuilder, type SourceBuilder } from '../src/main/core/modManager/sourceBuild'
import { exists, makeGame, makeMod, makeStandardMod, snapshot, tmp, VANILLA_PKG, write } from './helpers'

const NODE = process.execPath

/** ui/ layout in a temp folder: ui/mods/<id>/mod.source.json + a fake ui/scripts/build-payload.mjs; repo = ui/.. */
async function repo(steps: unknown[], opts: { cwd?: string } = {}) {
  const root = await tmp()
  const ui = path.join(root, 'ui')
  const mods = path.join(ui, 'mods')
  await write(path.join(mods, 'me', 'mod.source.json'), JSON.stringify({ id: 'me', build: { cwd: opts.cwd ?? '..', steps } }))
  // the fake payload step records its arguments in the repo folder
  await write(path.join(ui, 'scripts', 'build-payload.mjs'),
    "import fs from 'node:fs'; fs.appendFileSync('order.txt', 'payload ' + process.argv.slice(2).join(' ') + '\\n')")
  const logs = path.join(root, 'logs')
  const b = new RepoSourceBuilder({ modsRoot: mods, logDir: logs, platform: process.platform, node: { command: NODE } })
  return { root, ui, mods, logs, b }
}

const step = (name: string, js: string, extra: Record<string, unknown> = {}) => ({ name, command: [NODE, '-e', js], ...extra })
const append = (s: string) => `require('fs').appendFileSync('order.txt', '${s}\\n')`

describe('RepoSourceBuilder (development rebuild)', () => {
  it('runs the steps in order in the repository folder, then regenerates the payload of that mod', async () => {
    const { root, b } = await repo([step('first', append('first')), step('second', append('second'))])
    expect(await b.available('me')).toBe(true)
    const phases: string[] = []
    const notes = await b.build('me', (p) => phases.push(p.phase))
    expect(await fs.readFile(path.join(root, 'order.txt'), 'utf8')).toBe('first\nsecond\npayload me\n')
    expect(phases).toEqual([
      'Rebuilding from the repository: first (1/3)',
      'Rebuilding from the repository: second (2/3)',
      'Rebuilding from the repository: Mod payload (3/3)'
    ])
    expect(notes[0]).toMatch(/^Rebuilt from the repository/)
  })

  it('stops at a failing step with its output and the log file; later steps do not run', async () => {
    const { root, logs, b } = await repo([
      step('broken', "console.error('KeyError: boom'); process.exit(3)"),
      step('never', append('never'))
    ])
    const err = await b.build('me', () => {}).catch((e) => e)
    expect(err).toBeInstanceOf(UserError)
    expect(err.message).toMatch(/"broken" failed \(exit code 3\)/)
    expect(err.message).toMatch(/KeyError: boom/)
    expect(err.message).toMatch(/Nothing was installed/)
    expect(err.message).toContain(path.join(logs, 'build-me.log'))
    expect(await exists(path.join(root, 'order.txt'))).toBe(false)
    expect(await fs.readFile(path.join(logs, 'build-me.log'), 'utf8')).toMatch(/KeyError: boom/)
  })

  it('skips an optional step whose program is missing, but fails on a missing required program', async () => {
    const missing = { name: 'models', command: ['civ5mm-no-such-program-xyz', '--x'], optional: true }
    const ok = await repo([missing, step('pack', append('pack'))])
    const notes = await ok.b.build('me', () => {})
    expect(notes.join('\n')).toMatch(/Skipped "models"/)
    expect(await fs.readFile(path.join(ok.root, 'order.txt'), 'utf8')).toBe('pack\npayload me\n')

    const bad = await repo([{ ...missing, optional: false }])
    await expect(bad.b.build('me', () => {})).rejects.toThrow(/needs the program "civ5mm-no-such-program-xyz"/)
  })

  it('runs every step with PWD set to the repository folder (Blender resolves -P paths against $PWD)', async () => {
    const { root, b } = await repo([step('pwd', "require('fs').writeFileSync('pwd.txt', process.env.PWD)")])
    await b.build('me', () => {})
    expect(await fs.readFile(path.join(root, 'pwd.txt'), 'utf8')).toBe(root)
  })

  it('is not available without a build section or when its folder does not exist', async () => {
    const { b, mods } = await repo([step('x', '0')], { cwd: '../no-such-folder' })
    expect(await b.available('me')).toBe(false)
    await write(path.join(mods, 'other', 'mod.source.json'), JSON.stringify({ id: 'other' }))
    expect(await b.available('other')).toBe(false)
    expect(await b.available('absent')).toBe(false)
  })
})

describe('Controller with a source builder', () => {
  async function setup(builder: (mods: string) => SourceBuilder) {
    const lib = await tmp()
    const game = await makeGame(path.join(lib, 'steamapps', 'common', GAME_FOLDER_NAME))
    const mods = await tmp()
    await makeStandardMod(mods, 'me')
    const c = new Controller({
      dataDir: await tmp(), modsRoot: mods, documentsDir: '/unused',
      detectEnv: { platform: 'linux', home: await tmp(), env: {}, currentDirs: [game] },
      gameRunning: async () => false,
      sourceBuilder: builder(mods)
    })
    return { c, game, mods }
  }

  /** A fake build that produces a NEW version of the mod (different file contents). */
  const rebuilding = (calls: string[]) => (mods: string): SourceBuilder => ({
    available: async (id) => id === 'me',
    build: async (id) => {
      calls.push(id)
      await makeMod(mods, 'me', [
        { source: 'Upgrade1.Civ5Pkg', destination: 'Assets/DLC/Shared/Upgrade1.Civ5Pkg', content: `<Civ5Package>modded v${calls.length + 1}</Civ5Package>`, mode: 'replace', original: VANILLA_PKG, bundleOriginal: true },
        { source: 'ME/UI/InGame.lua', destination: 'Assets/DLC/Shared/me/UI/InGame.lua', content: `ingame v${calls.length + 1}` }
      ])
      return [`Rebuilt from the repository (test ${calls.length}).`]
    }
  })

  it('rebuilds the mod before installing it and installs the rebuilt files', async () => {
    const calls: string[] = []
    const { c, game } = await setup(rebuilding(calls))
    const s = await c.refresh()
    expect(s.configurations.find((x) => x.id === 'me')?.rebuildsFromSource).toBe(true)
    expect(s.configurations.find((x) => x.id === 'vanilla')?.rebuildsFromSource).toBe(false)
    const r = await c.switchTo('me')
    expect(r.ok).toBe(true)
    expect(calls).toEqual(['me'])
    expect(r.warnings[0]).toMatch(/Rebuilt from the repository/)
    expect(await fs.readFile(path.join(game, 'Assets/DLC/Shared/me/UI/InGame.lua'), 'utf8')).toBe('ingame v2')
    // installing again rebuilds again and replaces the previous build (a new build id)
    const r2 = await c.switchTo('me')
    expect(r2.ok).toBe(true)
    expect(calls).toEqual(['me', 'me'])
    expect(await fs.readFile(path.join(game, 'Assets/DLC/Shared/me/UI/InGame.lua'), 'utf8')).toBe('ingame v3')
    expect(await fs.readFile(path.join(game, 'Assets/DLC/Shared/Upgrade1.Civ5Pkg'), 'utf8')).toBe('<Civ5Package>modded v3</Civ5Package>')
    // vanilla never builds, and restores the original files
    const v = await c.switchTo('vanilla')
    expect(v.ok).toBe(true)
    expect(calls).toEqual(['me', 'me'])
    expect(await fs.readFile(path.join(game, 'Assets/DLC/Shared/Upgrade1.Civ5Pkg'), 'utf8')).toBe(VANILLA_PKG)
  })


  it('packaged app (no source builder): installs the bundled payload as is, never runs a build', async () => {
    const lib = await tmp()
    const game = await makeGame(path.join(lib, 'steamapps', 'common', GAME_FOLDER_NAME))
    const mods = await tmp()
    await makeStandardMod(mods, 'me')
    // even if a build section were shipped, it must be ignored: a step that would leave a marker if it ran
    const marker = path.join(await tmp(), 'built.txt')
    await write(path.join(mods, 'me', 'mod.source.json'), JSON.stringify({
      id: 'me', build: { cwd: '.', steps: [{ name: 'x', command: [NODE, '-e', `require('fs').writeFileSync(${JSON.stringify(marker)}, 'ran')`] }] }
    }))
    const c = new Controller({
      dataDir: await tmp(), modsRoot: mods, documentsDir: '/unused',
      detectEnv: { platform: 'win32', home: await tmp(), env: {}, currentDirs: [game] },
      gameRunning: async () => false
    })
    const s = await c.refresh()
    expect(s.configurations.every((x) => !x.rebuildsFromSource)).toBe(true)
    const r = await c.switchTo('me')
    expect(r.ok).toBe(true)
    expect(r.warnings.some((w) => /Rebuilt/.test(w))).toBe(false)
    expect(await exists(marker)).toBe(false)
    expect(await fs.readFile(path.join(game, 'Assets/DLC/Shared/me/UI/InGame.lua'), 'utf8')).toBe('ingame me')
    expect(await fs.readFile(path.join(game, 'Assets/DLC/Shared/Upgrade1.Civ5Pkg'), 'utf8')).toBe('<Civ5Package>modded me</Civ5Package>')
  })

  it('installs nothing when the build fails', async () => {
    const { c, game } = await setup(() => ({
      available: async () => true,
      build: async () => {
        throw new UserError('Could not rebuild me: "DLC pack" failed (exit code 1). Nothing was installed.')
      }
    }))
    await c.refresh()
    const before = await snapshot(game)
    const r = await c.switchTo('me')
    expect(r.ok).toBe(false)
    expect(r.message).toMatch(/"DLC pack" failed/)
    expect(await snapshot(game)).toEqual(before)
  })

  it('does not start a build while the game is running', async () => {
    const calls: string[] = []
    const lib = await tmp()
    const game = await makeGame(path.join(lib, 'steamapps', 'common', GAME_FOLDER_NAME))
    const mods = await tmp()
    await makeStandardMod(mods, 'me')
    const c = new Controller({
      dataDir: await tmp(), modsRoot: mods, documentsDir: '/unused',
      detectEnv: { platform: 'linux', home: await tmp(), env: {}, currentDirs: [game] },
      gameRunning: async () => true,
      sourceBuilder: rebuilding(calls)(mods)
    })
    await c.refresh()
    const r = await c.switchTo('me')
    expect(r.ok).toBe(false)
    expect(r.message).toMatch(/running/)
    expect(calls).toEqual([])
  })
})
