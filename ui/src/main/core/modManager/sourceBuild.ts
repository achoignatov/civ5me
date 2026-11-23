import { spawn } from 'node:child_process'
import fs from 'node:fs/promises'
import { createWriteStream } from 'node:fs'
import path from 'node:path'
import { UserError, messageOf } from '../fileOperations/errors'
import type { Progress } from '@shared/types'

/**
 * Development only: rebuild a mod from the project's working tree (committed or not) right before it is installed,
 * so the app always installs exactly what is in the repository now.
 *
 * What to run is data, not code: the optional "build" section of mods/<id>/mod.source.json:
 *   "build": { "cwd": "..", "steps": [ { "name": "...", "command": ["python3", "tools/build.py"],
 *                                        "commandWin32": ["py", "-3", "tools/build.py"], "optional": false } ] }
 * cwd is relative to the ui/ folder. After the steps, the payload/manifest of that mod is regenerated with
 * scripts/build-payload.mjs. Commands run without a shell; their output goes to a log file.
 */
export interface BuildStep {
  name: string
  command: string[]
  commandWin32?: string[]
  /** If the program is not installed, skip the step with a warning instead of failing. */
  optional?: boolean
}

export interface SourceBuildConfig {
  cwd: string
  steps: BuildStep[]
}

export type ProgressFn = (p: Progress) => void

/** What the Controller needs; injectable so tests don't run real builds. */
export interface SourceBuilder {
  /** True when this mod can be rebuilt from source here. */
  available(modId: string): Promise<boolean>
  /** Rebuild the mod and regenerate its payload. Returns warnings/notes for the user; throws UserError on failure. */
  build(modId: string, progress: ProgressFn): Promise<string[]>
}

export interface RepoSourceBuilderOptions {
  /** ui/mods */
  modsRoot: string
  /** Where build logs are written (one file per mod, replaced on every build). */
  logDir: string
  platform: NodeJS.Platform
  /** How to run scripts/build-payload.mjs: a Node binary (in Electron: process.execPath + ELECTRON_RUN_AS_NODE). */
  node: { command: string; env?: Record<string, string> }
  env?: NodeJS.ProcessEnv
}

/** Runs one program; resolves with the exit code, rejects with the spawn error (e.g. ENOENT). Output -> log. */
function run(cmd: string[], cwd: string, env: NodeJS.ProcessEnv, log: NodeJS.WritableStream, tail: string[]): Promise<number> {
  return new Promise((resolve, reject) => {
    let child
    try {
      // PWD too: some programs (Blender) resolve relative paths against $PWD, not the real working directory
      child = spawn(cmd[0], cmd.slice(1), { cwd, env: { ...env, PWD: cwd }, shell: false, windowsHide: true })
    } catch (e) {
      reject(e)
      return
    }
    const onData = (d: Buffer) => {
      log.write(d)
      for (const line of d.toString('utf8').split(/\r?\n/)) {
        if (line.trim()) tail.push(line)
      }
      if (tail.length > 40) tail.splice(0, tail.length - 40)
    }
    child.stdout.on('data', onData)
    child.stderr.on('data', onData)
    child.on('error', reject)
    child.on('close', (code) => resolve(code ?? -1))
  })
}

export class RepoSourceBuilder implements SourceBuilder {
  constructor(private readonly opts: RepoSourceBuilderOptions) {}

  private get uiDir(): string {
    return path.dirname(path.resolve(this.opts.modsRoot))
  }

  async config(modId: string): Promise<SourceBuildConfig | null> {
    let raw: unknown
    try {
      raw = JSON.parse(await fs.readFile(path.join(this.opts.modsRoot, modId, 'mod.source.json'), 'utf8'))
    } catch {
      return null
    }
    const b = (raw as { build?: unknown }).build as { cwd?: unknown; steps?: unknown } | undefined
    if (!b || typeof b.cwd !== 'string' || !Array.isArray(b.steps)) return null
    const steps: BuildStep[] = []
    for (const s of b.steps as Record<string, unknown>[]) {
      const cmdOk = (c: unknown) => Array.isArray(c) && c.length > 0 && c.every((x) => typeof x === 'string')
      if (typeof s?.name !== 'string' || !cmdOk(s.command) || (s.commandWin32 !== undefined && !cmdOk(s.commandWin32))) {
        throw new UserError(`mods/${modId}/mod.source.json: every build step needs a "name" and a "command" (list of strings).`)
      }
      steps.push({ name: s.name, command: s.command as string[], commandWin32: s.commandWin32 as string[] | undefined, optional: s.optional === true })
    }
    const cwd = path.resolve(this.uiDir, b.cwd)
    try {
      if (!(await fs.stat(cwd)).isDirectory()) return null
    } catch {
      return null
    }
    return { cwd, steps }
  }

  async available(modId: string): Promise<boolean> {
    try {
      return (await this.config(modId)) !== null
    } catch {
      return false
    }
  }

  async build(modId: string, progress: ProgressFn): Promise<string[]> {
    const cfg = await this.config(modId)
    if (!cfg) throw new UserError(`${modId} has no source build configured.`)
    const env = { ...(this.opts.env ?? process.env) }
    const payloadScript = path.join(this.uiDir, 'scripts', 'build-payload.mjs')
    const steps: BuildStep[] = [
      ...cfg.steps,
      { name: 'Mod payload', command: [this.opts.node.command, payloadScript, modId] }
    ]
    await fs.mkdir(this.opts.logDir, { recursive: true })
    const logFile = path.join(this.opts.logDir, `build-${modId}.log`)
    const log = createWriteStream(logFile)
    const warnings: string[] = []
    try {
      for (const [i, step] of steps.entries()) {
        progress({ phase: `Rebuilding from the repository: ${step.name} (${i + 1}/${steps.length})`, done: 0, total: 0 })
        const cmd = this.opts.platform === 'win32' && step.commandWin32 ? step.commandWin32 : step.command
        const stepEnv = step.name === 'Mod payload' ? { ...env, ...(this.opts.node.env ?? {}) } : env
        log.write(`\n===== ${step.name}: ${cmd.join(' ')}  (in ${cfg.cwd})\n`)
        const tail: string[] = []
        let code: number
        try {
          code = await run(cmd, cfg.cwd, stepEnv, log, tail)
        } catch (e) {
          if ((e as NodeJS.ErrnoException).code === 'ENOENT') {
            if (step.optional) {
              warnings.push(`Skipped "${step.name}": the program "${cmd[0]}" is not installed (its last output is used).`)
              continue
            }
            throw new UserError(`Could not rebuild ${modId}: "${step.name}" needs the program "${cmd[0]}", which was not found. Install it (and make sure it is on the PATH), then try again. Nothing was installed.`)
          }
          throw new UserError(`Could not rebuild ${modId}: "${step.name}" could not be started (${messageOf(e)}). Nothing was installed.`)
        }
        if (code !== 0) {
          throw new UserError(
            `Could not rebuild ${modId}: "${step.name}" failed (exit code ${code}). Nothing was installed.\n` +
              `Last output:\n  ${tail.slice(-8).join('\n  ')}\nFull log: ${logFile}`
          )
        }
      }
    } finally {
      await new Promise<void>((r) => log.end(() => r()))
    }
    const rev = await this.revision(cfg.cwd, env)
    warnings.unshift(`Rebuilt from the repository${rev ? ` (${rev})` : ''}. Build log: ${logFile}`)
    return warnings
  }

  /** "4d8b1a2" or "4d8b1a2 + uncommitted changes"; null when git is not available. */
  private async revision(cwd: string, env: NodeJS.ProcessEnv): Promise<string | null> {
    const out = async (args: string[]) => {
      const lines: string[] = []
      const sink = { write: () => true } as unknown as NodeJS.WritableStream
      const code = await run(['git', ...args], cwd, env, sink, lines)
      return code === 0 ? lines : null
    }
    try {
      const head = await out(['rev-parse', '--short', 'HEAD'])
      if (!head?.length) return null
      const dirty = await out(['status', '--porcelain', '--untracked-files=normal'])
      return dirty && dirty.length ? `${head[0]} + uncommitted changes` : head[0]
    } catch {
      return null
    }
  }
}
