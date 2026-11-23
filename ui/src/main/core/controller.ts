import { detectGame, validateGameDir, type DetectEnv } from './gameDetection/detect'
import { gameCacheCandidates, isGameRunning } from './gameDetection/gameEnvironment'
import { loadRegistry, verifySources, type LoadedMod } from './modManager/manifest'
import { ModEngine } from './modManager/engine'
import type { SourceBuilder } from './modManager/sourceBuild'
import { clearGameCache } from './fileOperations/gameCache'
import { UserError, messageOf } from './fileOperations/errors'
import { VANILLA_ID, type AppStatus, type ConfigurationInfo, type GameInfo, type OperationResult, type Progress } from '@shared/types'

export interface ControllerOptions {
  dataDir: string
  modsRoot: string
  documentsDir: string
  detectEnv: DetectEnv
  /** Overridable for tests. */
  gameRunning?: () => Promise<boolean>
  /** Development only: rebuilds a mod from the repository before installing it (absent in packaged builds). */
  sourceBuilder?: SourceBuilder
}

/**
 * Glue between the UI and the core: owns detection, settings, the busy lock and progress reporting.
 * All paths stay in the main process; the renderer only receives AppStatus.
 */
export class Controller {
  private engine: ModEngine
  private game: GameInfo = { found: false, path: null, source: null, problem: null, searched: [] }
  private mods: LoadedMod[] = []
  private unavailable = new Map<string, string>()
  private rebuildable = new Set<string>()
  private registryErrors: string[] = []
  private busy = false
  private progressListener: (p: Progress) => void = () => {}

  constructor(private readonly opts: ControllerOptions) {
    this.engine = new ModEngine(opts.dataDir)
  }

  onProgress(fn: (p: Progress) => void): void {
    this.progressListener = fn
  }

  private refreshing: Promise<AppStatus> | null = null

  /** Full refresh: load mods, detect the game, inspect the installed state. Concurrent calls share one run. */
  async refresh(): Promise<AppStatus> {
    if (this.refreshing) return this.refreshing
    this.refreshing = (async () => {
      try {
        await this.exclusive(async () => {
          await this.loadMods()
          await this.detect()
        })
        return await this.status()
      } finally {
        this.refreshing = null
      }
    })()
    return this.refreshing
  }

  async getStatus(): Promise<AppStatus> {
    return this.status()
  }

  private async loadMods(): Promise<void> {
    const { mods, errors } = await loadRegistry(this.opts.modsRoot)
    this.mods = mods
    this.registryErrors = errors.map((e) => `${e.id}: ${e.error}`)
    this.unavailable.clear()
    this.rebuildable.clear()
    for (const m of mods) {
      if (this.opts.sourceBuilder && (await this.opts.sourceBuilder.available(m.manifest.id))) this.rebuildable.add(m.manifest.id)
      const problems = await verifySources(m)
      if (problems.length) {
        this.unavailable.set(m.manifest.id, `${problems.length} mod source file(s) missing or damaged (e.g. ${problems[0]}).`)
      }
    }
  }

  private async detect(): Promise<void> {
    const r = await detectGame(this.opts.detectEnv)
    this.game = { found: r.path !== null, path: r.path, source: r.source, problem: r.problem, searched: r.searched }
  }

  private async status(): Promise<AppStatus> {
    const configurations: ConfigurationInfo[] = [
      { id: VANILLA_ID, name: 'BNW Vanilla', version: null, description: 'The original Civilization V: Brave New World.', unavailable: null, rebuildsFromSource: false },
      ...this.mods.map((m) => {
        const rebuilds = this.rebuildable.has(m.manifest.id)
        return {
          id: m.manifest.id, name: m.manifest.name, version: m.manifest.version,
          description: m.manifest.description || null,
          // a mod rebuilt from source before installing is usable even if its current payload is stale or missing
          unavailable: rebuilds ? null : (this.unavailable.get(m.manifest.id) ?? null),
          rebuildsFromSource: rebuilds
        }
      })
    ]
    let active: AppStatus['active']
    if (!this.game.found || !this.game.path) {
      active = { kind: 'no-game', modId: null, label: 'Game not found', details: [] }
    } else {
      try {
        active = await this.engine.inspect(this.game.path, this.mods)
      } catch (e) {
        active = { kind: 'unknown', modId: null, label: 'Unknown / Inconsistent installation', details: [`Could not inspect the game files: ${messageOf(e)}`] }
      }
    }
    if (this.registryErrors.length) active = { ...active, details: [...active.details, ...this.registryErrors] }
    return { game: this.game, configurations, active, busy: this.busy }
  }

  /** Only ever called on an explicit user click; nothing installs or restores automatically. */
  async switchTo(id: string): Promise<OperationResult> {
    if (this.busy) return this.result(false, 'Another operation is still running.')
    return this.exclusive(async () => {
      try {
        if (!this.game.found || !this.game.path) throw new UserError('No valid Civilization V installation is selected.')
        const v = await validateGameDir(this.game.path)
        if (!v.valid) throw new UserError(`The game folder is no longer valid: ${v.reason}`)
        if (id !== VANILLA_ID && !this.mods.some((m) => m.manifest.id === id)) throw new UserError(`Unknown configuration "${id}".`)
        const gameRunning = () => this.isGameRunning()
        const running = 'Civilization V is running. Close the game first, then switch.'
        const notes: string[] = []
        if (id !== VANILLA_ID && this.rebuildable.has(id) && this.opts.sourceBuilder) {
          // development: install exactly what is in the repository now (committed or not)
          if (await gameRunning()) throw new UserError(running)
          notes.push(...(await this.opts.sourceBuilder.build(id, (p) => this.progressListener(p))))
          await this.loadMods()
          if (!this.mods.some((m) => m.manifest.id === id)) throw new UserError(`The rebuilt ${id} has no valid manifest; nothing was installed.`)
        }
        const why = this.unavailable.get(id)
        if (why) throw new UserError(`This configuration is unavailable: ${why}`)
        if (await gameRunning()) throw new UserError(running)
        const r = await this.engine.switchTo(this.game.path, id, this.mods, (p) => this.progressListener(p))
        const warnings = [...notes, ...r.warnings]
        if (r.touchedMods.some((m) => this.mods.find((x) => x.manifest.id === m)?.manifest.clearGameCache)) {
          this.progressListener({ phase: 'Clearing the game cache', done: 0, total: 1 })
          warnings.push(await clearGameCache(gameCacheCandidates(process.platform, this.game.path, this.opts.documentsDir), this.opts.dataDir))
        }
        return this.result(true, r.message, warnings)
      } catch (e) {
        return this.result(false, e instanceof UserError ? e.message : `Unexpected error: ${messageOf(e)}`)
      }
    })
  }

  /** True while a Civilization V process runs (polled by the UI every few seconds; read-only, never throws). */
  async isGameRunning(): Promise<boolean> {
    try {
      return await (this.opts.gameRunning ?? (() => isGameRunning(process.platform)))()
    } catch {
      return false
    }
  }

  private async result(ok: boolean, message: string, warnings: string[] = []): Promise<OperationResult> {
    const wasBusy = this.busy
    this.busy = false // status() should report the post-operation state
    const status = await this.status()
    this.busy = wasBusy
    return { ok, message, warnings, status }
  }

  private async exclusive<T>(fn: () => Promise<T>): Promise<T> {
    if (this.busy) throw new UserError('Another operation is still running.')
    this.busy = true
    try {
      return await fn()
    } finally {
      this.busy = false
    }
  }
}
