import fs from 'node:fs/promises'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { Controller } from '../src/main/core/controller'
import { GAME_FOLDER_NAME } from '../src/main/core/gameDetection/detect'
import { exists, makeGame, makeStandardMod, snapshot, tmp, write } from './helpers'

async function setup(opts: { running?: boolean; clearCache?: boolean } = {}) {
  const lib = await tmp()
  const game = await makeGame(path.join(lib, 'steamapps', 'common', GAME_FOLDER_NAME))
  const cache = path.join(lib, "steamapps/compatdata/8930/pfx/drive_c/users/steamuser/Documents/My Games/Sid Meier's Civilization 5/cache")
  await write(path.join(cache, 'Civ5CoreDatabase.db'), 'stale')
  const mods = await tmp()
  const modDir = await makeStandardMod(mods, 'me')
  if (opts.clearCache) {
    const m = JSON.parse(await fs.readFile(path.join(modDir, 'manifest.json'), 'utf8'))
    await fs.writeFile(path.join(modDir, 'manifest.json'), JSON.stringify({ ...m, clearGameCache: true }))
  }
  const data = await tmp()
  let running = opts.running ?? false
  const c = new Controller({
    dataDir: data, modsRoot: mods, documentsDir: '/unused',
    detectEnv: { platform: 'linux', home: await tmp(), env: {}, currentDirs: [game] },
    gameRunning: async () => running
  })
  return { c, game, cache, data, setRunning: (v: boolean) => (running = v) }
}

describe('Controller', () => {
  it('detects the game and reports vanilla with two configurations', async () => {
    const { c, game } = await setup()
    const s = await c.refresh()
    expect(s.game).toMatchObject({ found: true, path: game, source: 'cwd' })
    expect(s.active.kind).toBe('vanilla')
    expect(s.configurations.map((x) => x.name)).toEqual(['BNW Vanilla', 'me MOD'])
  })

  it('refuses to switch while the game is running', async () => {
    const { c, game } = await setup({ running: true })
    await c.refresh()
    const before = await snapshot(game)
    const r = await c.switchTo('me')
    expect(r.ok).toBe(false)
    expect(r.message).toMatch(/running/)
    expect(await snapshot(game)).toEqual(before)
  })

  it('reports whether the game is running (for the UI poll); a failing check counts as not running', async () => {
    const { c, setRunning } = await setup()
    expect(await c.isGameRunning()).toBe(false)
    setRunning(true)
    expect(await c.isGameRunning()).toBe(true)
    const broken = new Controller({
      dataDir: await tmp(), modsRoot: await tmp(), documentsDir: '/unused',
      detectEnv: { platform: 'linux', home: await tmp(), env: {}, currentDirs: [] },
      gameRunning: async () => {
        throw new Error('tasklist failed')
      }
    })
    expect(await broken.isGameRunning()).toBe(false)
  })

  it('switches, clears the cache (moved to the data folder) and reports the new state', async () => {
    const { c, cache, data } = await setup({ clearCache: true })
    await c.refresh()
    const r = await c.switchTo('me')
    expect(r.ok).toBe(true)
    expect(r.status.active).toMatchObject({ kind: 'mod', modId: 'me' })
    expect(r.warnings.join()).toMatch(/cache was emptied/)
    expect(await fs.readdir(cache)).toEqual([])
    expect(await exists(path.join(data, 'game-cache-previous', 'Civ5CoreDatabase.db'))).toBe(true)
    const v = await c.switchTo('vanilla')
    expect(v.status.active.kind).toBe('vanilla')
  })

  it('rejects unknown configurations', async () => {
    const { c } = await setup()
    await c.refresh()
    expect((await c.switchTo('nope')).message).toMatch(/Unknown configuration/)
  })

  it('reports a missing game', async () => {
    const c = new Controller({
      dataDir: await tmp(), modsRoot: await tmp(), documentsDir: '/unused',
      detectEnv: { platform: 'linux', home: await tmp(), env: {}, currentDirs: [await tmp()] }
    })
    const s = await c.refresh()
    expect(s.game.found).toBe(false)
    expect(s.game.searched.length).toBeGreaterThan(1)
    expect(s.active.kind).toBe('no-game')
    expect((await c.switchTo('vanilla')).ok).toBe(false)
  })
})
