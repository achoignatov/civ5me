#!/usr/bin/env node
// Rebuilds every mod from the repository, then regenerates its payload, so the packaged app ships the latest build.
// The steps are the "build" section of mods/<id>/mod.source.json (the same ones the dev app runs before installing).
// A step marked "optional" is skipped with a warning when its program isn't installed (e.g. Blender).
//
// usage: node scripts/build-mod.mjs [mod id ...]   (default: every mod in mods/index.json)
import fs from 'node:fs/promises'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const MODS = path.join(UI, 'mods')

function run(cmd, cwd) {
  console.log(`\n$ ${cmd.join(' ')}   (in ${cwd})`)
  const r = spawnSync(cmd[0], cmd.slice(1), { cwd, stdio: 'inherit', env: { ...process.env, PWD: cwd }, windowsHide: true })
  return r.error ? { error: r.error } : { code: r.status ?? -1 }
}

const { mods } = JSON.parse(await fs.readFile(path.join(MODS, 'index.json'), 'utf8'))
const only = process.argv.slice(2)
for (const id of only) if (!mods.includes(id)) throw new Error(`unknown mod "${id}" (not in mods/index.json)`)

for (const id of mods) {
  if (only.length && !only.includes(id)) continue
  let cfg
  try {
    cfg = JSON.parse(await fs.readFile(path.join(MODS, id, 'mod.source.json'), 'utf8'))
  } catch {
    console.log(`[${id}] no mod.source.json, nothing to build`)
    continue
  }
  const build = cfg.build
  if (build?.steps?.length) {
    const cwd = path.resolve(UI, build.cwd ?? '.')
    for (const [i, step] of build.steps.entries()) {
      const cmd = process.platform === 'win32' && step.commandWin32 ? step.commandWin32 : step.command
      console.log(`\n[${id}] step ${i + 1}/${build.steps.length}: ${step.name}`)
      const r = run(cmd, cwd)
      if (r.error?.code === 'ENOENT' && step.optional) {
        console.warn(`[${id}] WARNING: skipped "${step.name}": "${cmd[0]}" is not installed (its last output is used)`)
        continue
      }
      if (r.error) throw new Error(`[${id}] "${step.name}" could not start: ${r.error.message}`)
      if (r.code !== 0) throw new Error(`[${id}] "${step.name}" failed with exit code ${r.code}`)
    }
  }
  const r = run([process.execPath, path.join(UI, 'scripts', 'build-payload.mjs'), id], UI)
  if (r.error || r.code !== 0) throw new Error(`[${id}] payload generation failed`)
}
