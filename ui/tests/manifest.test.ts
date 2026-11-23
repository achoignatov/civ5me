import fs from 'node:fs/promises'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { parseManifest, loadMod, loadRegistry, verifySources } from '../src/main/core/modManager/manifest'
import { resolveInside } from '../src/main/core/fileOperations/safePath'
import { makeMod, makeStandardMod, sha, tmp, write } from './helpers'

const file = (o: Record<string, unknown> = {}) => ({ source: 'a.txt', destination: 'Assets/a.txt', size: 1, sha256: sha('a'), mode: 'add', ...o })
const manifest = (o: Record<string, unknown> = {}) => ({ schemaVersion: 1, id: 'm', name: 'M', version: '1', sourceRoot: 'payload', files: [file()], ...o })

describe('parseManifest', () => {
  it('accepts a valid manifest and applies defaults', () => {
    const m = parseManifest(manifest())
    expect(m).toMatchObject({ id: 'm', clearGameCache: false, description: '' })
    expect(m.files[0].mode).toBe('add')
  })
  it.each([
    ['wrong schema', { schemaVersion: 2 }],
    ['reserved id', { id: 'vanilla' }],
    ['bad id', { id: 'Has Spaces' }],
    ['missing name', { name: '' }],
    ['no files', { files: [] }],
    ['sourceRoot escaping', { sourceRoot: '../x' }],
    ['traversal in destination', { files: [file({ destination: '../outside.txt' })] }],
    ['nested traversal', { files: [file({ destination: 'Assets/../../x' })] }],
    ['absolute destination', { files: [file({ destination: '/etc/passwd' })] }],
    ['drive letter', { files: [file({ destination: 'C:/Windows/x' })] }],
    ['backslashes', { files: [file({ destination: 'Assets\\x' })] }],
    ['traversal in source', { files: [file({ source: '../../secret' })] }],
    ['bad hash', { files: [file({ sha256: 'xyz' })] }],
    ['bad mode', { files: [file({ mode: 'delete' })] }],
    ['duplicate destination (case-insensitive)', { files: [file(), file({ destination: 'assets/A.txt' })] }],
    ['file used as folder', { files: [file(), file({ destination: 'Assets/a.txt/b' })] }],
    ['original on add file', { files: [file({ original: { sha256: [sha('o')] } })] }],
    ['original identical to mod file', { files: [file({ mode: 'replace', original: { sha256: [sha('a')] } })] }],
    ['bundled original escaping', { files: [file({ mode: 'replace', original: { sha256: [sha('o')], bundled: '../o' } })] }]
  ])('rejects %s', (_name, override) => {
    expect(() => parseManifest(manifest(override as Record<string, unknown>))).toThrow(/Invalid mod manifest/)
  })
  it('rejects non-objects', () => {
    expect(() => parseManifest(null)).toThrow()
    expect(() => parseManifest([])).toThrow()
  })
})

describe('resolveInside', () => {
  it('keeps paths inside the root', () => {
    expect(resolveInside('/game', 'Assets/x.xml')).toBe(path.resolve('/game/Assets/x.xml'))
    expect(() => resolveInside('/game', '../x')).toThrow()
    expect(() => resolveInside('/game', 'a/../../x')).toThrow()
  })
})

describe('loading mods', () => {
  it('loads a mod and verifies its sources', async () => {
    const mods = await tmp()
    await makeStandardMod(mods)
    const reg = await loadRegistry(mods)
    expect(reg.errors).toEqual([])
    expect(reg.mods[0].manifest.files).toHaveLength(4)
    expect(await verifySources(reg.mods[0])).toEqual([])
  })
  it('reports a missing manifest', async () => {
    const mods = await tmp()
    await write(path.join(mods, 'index.json'), JSON.stringify({ mods: ['ghost'] }))
    const reg = await loadRegistry(mods)
    expect(reg.mods).toEqual([])
    expect(reg.errors[0].error).toMatch(/manifest is missing/)
  })
  it('reports invalid JSON', async () => {
    const d = await tmp()
    await write(path.join(d, 'manifest.json'), '{ nope')
    await expect(loadMod(d)).rejects.toThrow(/not valid JSON/)
  })
  it('reports a missing registry', async () => {
    expect((await loadRegistry(await tmp())).errors[0].error).toMatch(/mod registry/)
  })
  it('detects missing and modified source files', async () => {
    const mods = await tmp()
    const dir = await makeStandardMod(mods)
    await fs.rm(path.join(dir, 'payload', 'ME', 'Maps', 'map.lua'))
    await fs.writeFile(path.join(dir, 'payload', 'ME', 'UI', 'InGame.lua'), 'tampered')
    const problems = await verifySources(await loadMod(dir))
    expect(problems).toHaveLength(2)
    expect(problems.join('\n')).toMatch(/map\.lua: missing/)
    expect(problems.join('\n')).toMatch(/InGame\.lua: content does not match/)
  })
  it('rejects symlinked sources', async () => {
    const mods = await tmp()
    const outside = await tmp()
    await write(path.join(outside, 'secret'), 'a')
    const dir = await makeMod(mods, 'x', [{ source: 'a.txt', destination: 'Assets/a.txt', content: 'a' }])
    await fs.rm(path.join(dir, 'payload', 'a.txt'))
    await fs.symlink(path.join(outside, 'secret'), path.join(dir, 'payload', 'a.txt'))
    expect((await verifySources(await loadMod(dir)))[0]).toMatch(/symbolic link/)
  })
})
