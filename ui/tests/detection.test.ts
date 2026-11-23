import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { detectGame, validateGameDir, GAME_FOLDER_NAME, type DetectEnv } from '../src/main/core/gameDetection/detect'
import { parseLibraryFolders } from '../src/main/core/gameDetection/vdf'
import { gameCacheCandidates } from '../src/main/core/gameDetection/gameEnvironment'
import { makeGame, tmp, write } from './helpers'

const env = (home: string, currentDirs: string[] = []): DetectEnv => ({ platform: 'linux', home, env: {}, currentDirs })

describe('validateGameDir', () => {
  it('accepts a BNW installation', async () => {
    const g = await makeGame(await tmp())
    expect(await validateGameDir(g)).toEqual({ valid: true, reason: null, isCiv: true })
  })
  it('rejects a folder without the game executable', async () => {
    const g = await makeGame(await tmp(), { exe: false })
    const v = await validateGameDir(g)
    expect(v.valid).toBe(false)
    expect(v.reason).toMatch(/CivilizationV\.exe/)
  })
  it('rejects Civ V without Brave New World', async () => {
    const v = await validateGameDir(await makeGame(await tmp(), { bnw: false }))
    expect(v.valid).toBe(false)
    expect(v.reason).toMatch(/Brave New World/)
  })
  it('rejects missing folders and files', async () => {
    const d = await tmp()
    expect((await validateGameDir(path.join(d, 'nope'))).valid).toBe(false)
    await write(path.join(d, 'file'), 'x')
    expect((await validateGameDir(path.join(d, 'file'))).valid).toBe(false)
  })
  it('rejects an empty folder', async () => {
    expect((await validateGameDir(await tmp())).valid).toBe(false)
  })
})

describe('detectGame', () => {
  it('uses the current folder / the app folder first', async () => {
    const home = await tmp()
    const steam = path.join(home, '.local/share/Steam')
    await makeGame(path.join(steam, 'steamapps', 'common', GAME_FOLDER_NAME))
    const custom = await makeGame(await tmp())
    const r = await detectGame(env(home, [await tmp(), custom]))
    expect(r).toMatchObject({ path: custom, source: 'cwd', problem: null })
  })
  it('finds the game in the default Steam library and in extra libraries from libraryfolders.vdf (Linux)', async () => {
    const home = await tmp()
    const steam = path.join(home, '.local/share/Steam')
    await write(path.join(steam, 'steamapps', 'libraryfolders.vdf'), '"libraryfolders"\n{\n "0"\n {\n  "path" "' + steam + '"\n }\n}')
    const game = await makeGame(path.join(steam, 'steamapps', 'common', GAME_FOLDER_NAME))
    expect(await detectGame(env(home, [await tmp()]))).toMatchObject({ path: game, source: 'default' })

    const home2 = await tmp()
    const lib = await tmp()
    const steam2 = path.join(home2, '.steam/steam')
    await write(path.join(steam2, 'steamapps', 'libraryfolders.vdf'), `"libraryfolders" { "0" { "path" "${steam2}" } "1" { "path" "${lib}" "apps" { "8930" "1" } } }`)
    const game2 = await makeGame(path.join(lib, 'steamapps', 'common', GAME_FOLDER_NAME))
    expect((await detectGame(env(home2))).path).toBe(game2)
  })
  it('Windows: finds the game via the Steam path from the registry, and also checks Program Files', async () => {
    const steam = await tmp()
    const game = await makeGame(path.join(steam, 'steamapps', 'common', GAME_FOLDER_NAME))
    const win = (registry: string[]): DetectEnv => ({
      platform: 'win32', home: 'C:\\Users\\x', env: { 'ProgramFiles(x86)': 'C:\\Program Files (x86)' }, currentDirs: [],
      registrySteamPaths: async () => registry
    })
    expect(await detectGame(win([steam]))).toMatchObject({ path: game, source: 'default' })
    const none = await detectGame(win([]))
    expect(none.path).toBeNull()
    expect(none.searched.some((d) => d.includes('Program Files (x86)') && d.includes(GAME_FOLDER_NAME))).toBe(true)
  })
  it('reports nothing found, lists what was checked, and says why a near miss was rejected', async () => {
    const here = await tmp()
    const r = await detectGame(env(await tmp(), [here]))
    expect(r).toMatchObject({ path: null, source: null, problem: null })
    expect(r.searched[0]).toBe(here)
    expect(r.searched.some((d) => d.includes('.local/share/Steam'))).toBe(true)

    const noBnw = await makeGame(await tmp(), { bnw: false })
    const r2 = await detectGame(env(await tmp(), [noBnw]))
    expect(r2.path).toBeNull()
    expect(r2.problem).toMatch(/Brave New World/)
  })
})

describe('helpers', () => {
  it('parses libraryfolders.vdf paths including Windows escapes', () => {
    const text = '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"C:\\\\Program Files (x86)\\\\Steam"\n\t\t"apps"\n\t\t{\n\t\t\t"8930"\t\t"1"\n\t\t}\n\t}\n\t"1"\n\t{\n\t\t"path"\t\t"D:\\\\Games"\n\t}\n}'
    expect(parseLibraryFolders(text)).toEqual(['C:\\Program Files (x86)\\Steam', 'D:\\Games'])
  })
  it('derives the Proton cache folder from the game folder', () => {
    const [c] = gameCacheCandidates('linux', `/lib/steamapps/common/${GAME_FOLDER_NAME}`, '/unused')
    expect(c).toBe("/lib/steamapps/compatdata/8930/pfx/drive_c/users/steamuser/Documents/My Games/Sid Meier's Civilization 5/cache")
  })
})
