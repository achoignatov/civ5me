#!/usr/bin/env node
// Generates, for every mod in mods/index.json that has a mod.source.json:
//   mods/<id>/payload/     copy of the files to install (incremental: unchanged files are not re-copied)
//   mods/<id>/originals/   copies of the vanilla files the mod replaces (for restoring after a manual install)
//   mods/<id>/manifest.json the file list with destinations, sizes, sha256 and add/replace modes
//
// A file is "replace" if it is listed in "replaces" (with the path of a copy of the vanilla file), otherwise "add".
// The script never touches anything outside mods/<id>/.
import fs from 'node:fs/promises'
import path from 'node:path'
import { createHash } from 'node:crypto'
import { createReadStream } from 'node:fs'
import { fileURLToPath } from 'node:url'

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const MODS = path.join(UI, 'mods')

const sha256 = (f) =>
  new Promise((res, rej) => {
    const h = createHash('sha256')
    createReadStream(f).on('error', rej).on('data', (d) => h.update(d)).on('end', () => res(h.digest('hex')))
  })

async function walk(dir, base = dir, out = []) {
  for (const e of await fs.readdir(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name)
    if (e.isSymbolicLink()) throw new Error(`symbolic links are not supported: ${p}`)
    if (e.isDirectory()) await walk(p, base, out)
    else if (e.isFile()) out.push(path.relative(base, p).split(path.sep).join('/'))
  }
  return out
}

async function sameFile(a, b) {
  try {
    const [sa, sb] = await Promise.all([fs.stat(a), fs.stat(b)])
    return sa.size === sb.size && Math.abs(sa.mtimeMs - sb.mtimeMs) < 2
  } catch {
    return false
  }
}

async function syncFile(src, dst) {
  if (await sameFile(src, dst)) return false
  await fs.mkdir(path.dirname(dst), { recursive: true })
  await fs.copyFile(src, dst)
  const st = await fs.stat(src)
  await fs.utimes(dst, st.atime, st.mtime)
  return true
}

async function pruneEmptyDirs(dir) {
  for (const e of await fs.readdir(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      const p = path.join(dir, e.name)
      await pruneEmptyDirs(p)
      if ((await fs.readdir(p)).length === 0) await fs.rmdir(p)
    }
  }
}

async function buildMod(id) {
  const modDir = path.join(MODS, id)
  const cfgFile = path.join(modDir, 'mod.source.json')
  let cfg
  try {
    cfg = JSON.parse(await fs.readFile(cfgFile, 'utf8'))
  } catch {
    console.log(`[${id}] no mod.source.json, keeping the existing manifest`)
    return
  }
  const payload = path.join(modDir, 'payload')
  const originals = path.join(modDir, 'originals')
  const files = []
  const wanted = new Set()
  let copied = 0
  for (const s of cfg.sources) {
    const from = path.resolve(UI, s.from)
    try {
      await fs.access(from)
    } catch {
      throw new Error(`[${id}] source folder ${from} does not exist. Build the mod first (see the project README).`)
    }
    // payload keeps the destination layout relative to "to", prefixed with the mapping index for uniqueness
    for (const rel of (await walk(from)).sort()) {
      const source = cfg.sources.length > 1 ? `${cfg.sources.indexOf(s)}/${rel}` : rel
      const destination = `${s.to}/${rel}`
      if (await syncFile(path.join(from, rel), path.join(payload, ...source.split('/')))) copied++
      wanted.add(source)
      const st = await fs.stat(path.join(from, rel))
      const entry = { source, destination, size: st.size, sha256: await sha256(path.join(from, rel)), mode: 'add' }
      const rep = cfg.replaces?.[destination]
      if (rep) {
        const orig = path.resolve(UI, rep.originalFrom)
        const bundled = `originals/${destination}`
        await syncFile(orig, path.join(modDir, ...bundled.split('/')))
        entry.mode = 'replace'
        entry.original = { sha256: [await sha256(orig)], bundled }
      }
      files.push(entry)
    }
  }
  for (const dest of Object.keys(cfg.replaces ?? {})) {
    if (!files.some((f) => f.destination === dest)) throw new Error(`[${id}] "replaces" lists ${dest}, which is not in the sources`)
  }
  // remove payload files that are no longer part of the build (only inside mods/<id>/payload)
  let removed = 0
  for (const rel of await walk(payload).catch(() => [])) {
    if (!wanted.has(rel)) {
      await fs.unlink(path.join(payload, ...rel.split('/')))
      removed++
    }
  }
  const wantedOriginals = new Set(files.filter((f) => f.original).map((f) => f.original.bundled.slice('originals/'.length)))
  for (const rel of await walk(originals).catch(() => [])) {
    if (!wantedOriginals.has(rel)) await fs.unlink(path.join(originals, ...rel.split('/')))
  }
  await pruneEmptyDirs(payload)
  await fs.mkdir(originals, { recursive: true })
  await pruneEmptyDirs(originals)

  const manifest = {
    schemaVersion: 1,
    id: cfg.id,
    name: cfg.name,
    version: cfg.version,
    description: cfg.description ?? '',
    sourceRoot: 'payload',
    clearGameCache: cfg.clearGameCache === true,
    files
  }
  await fs.writeFile(path.join(modDir, 'manifest.json'), JSON.stringify(manifest, null, 1) + '\n')
  const bytes = files.reduce((a, f) => a + f.size, 0)
  console.log(
    `[${id}] ${files.length} files (${(bytes / 1048576).toFixed(0)} MB), ${files.filter((f) => f.mode === 'replace').length} replace vanilla files; ` +
      `copied ${copied}, removed ${removed}`
  )
}

// usage: node scripts/build-payload.mjs [mod id ...]   (default: every mod in mods/index.json)
const { mods } = JSON.parse(await fs.readFile(path.join(MODS, 'index.json'), 'utf8'))
const only = process.argv.slice(2)
for (const id of only) if (!mods.includes(id)) throw new Error(`unknown mod "${id}" (not in mods/index.json)`)
for (const id of mods) if (!only.length || only.includes(id)) await buildMod(id)
