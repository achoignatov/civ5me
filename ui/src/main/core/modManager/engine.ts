import fs from 'node:fs/promises'
import path from 'node:path'
import { randomUUID } from 'node:crypto'
import { resolveInside, relAncestors, samePath } from '../fileOperations/safePath'
import { sha256OrNull, isErrno } from '../fileOperations/hash'
import { realFsOps, type FsOps } from '../fileOperations/fsOps'
import { UserError, describeFsError, messageOf } from '../fileOperations/errors'
import { BackupStore } from '../backup/backupStore'
import { StateStore, type InstallRecord, type ManagedFile } from './state'
import { verifySources, sourcePath, bundledOriginalPath, type LoadedMod } from './manifest'
import { VANILLA_ID, type ActiveState, type Progress } from '@shared/types'

export type ProgressFn = (p: Progress) => void

export interface SwitchResult {
  message: string
  warnings: string[]
  /** Mods whose files were added/removed by this switch (used to decide whether to clear the game cache). */
  touchedMods: string[]
}

const TMP_SUFFIX = '.civ5mm-tmp'
const LIST_LIMIT = 5

function sample(xs: string[]): string {
  return xs.slice(0, LIST_LIMIT).join('\n  ') + (xs.length > LIST_LIMIT ? `\n  … and ${xs.length - LIST_LIMIT} more` : '')
}

/**
 * The generic, manifest-driven install engine. Knows nothing about MiddleEarth: it copies manifest files into the
 * game folder, backs up anything it overwrites, and can always undo what it did.
 *
 * Safety rules implemented here:
 *  - only paths listed in a manifest (or recorded in our own state/journal) are ever written or deleted;
 *  - an existing file is never overwritten before a verified backup exists;
 *  - a file is only deleted if its content is still byte-identical to what we installed;
 *  - every install is journaled; a failed or interrupted install is rolled back.
 */
export class ModEngine {
  readonly state: StateStore
  readonly backups: BackupStore

  constructor(
    readonly dataDir: string,
    private readonly fsOps: FsOps = realFsOps
  ) {
    this.state = new StateStore(dataDir)
    this.backups = new BackupStore(dataDir)
  }

  // ------------------------------------------------------------------ inspection

  /** Determine the real state of the game folder (hashes files; never trusts the last button press). */
  async inspect(gamePath: string, mods: LoadedMod[]): Promise<ActiveState> {
    if (await this.state.journalExists()) {
      return unknown('A previous switch was interrupted before it finished. Click either tile: the unfinished change is rolled back first.')
    }
    const { install } = await this.state.read()
    if (install) return this.inspectManaged(gamePath, install, mods)
    return this.inspectUnmanaged(gamePath, mods)
  }

  private async inspectManaged(gamePath: string, rec: InstallRecord, mods: LoadedMod[]): Promise<ActiveState> {
    if (!samePath(rec.gamePath, gamePath)) {
      return unknown(`This app installed ${rec.modName} into another game folder (${rec.gamePath}). Select that folder and switch it back to vanilla first.`)
    }
    if (rec.status === 'uninstall-failed') {
      return unknown(`Restoring vanilla failed part way through. Click the "Vanilla BNW" tile to retry.`)
    }
    const changed = await this.changedFiles(gamePath, rec)
    if (changed.length) {
      return unknown(
        `${changed.length} of ${rec.files.length} ${rec.modName} files were changed or removed outside this app ` +
          `(for example by a Steam update or "Verify integrity"):\n  ${sample(changed)}`,
        'Click a tile to repair: the app restores the recorded originals first.'
      )
    }
    const mod = mods.find((m) => m.manifest.id === rec.modId)
    const details: string[] = [
      `${rec.modName} version ${rec.modVersion}, build ${rec.buildId} (${rec.files.length} files), installed ${rec.installedAt}.`,
      'For multiplayer, every player must show the same build id.'
    ]
    if (!mod) details.push(`This mod is no longer registered in the app. You can still switch back to vanilla.`)
    else if (mod.buildId !== rec.buildId) {
      details.push(`A different build of ${mod.manifest.name} ships with this app. Click the ${mod.manifest.name} tile to update.`)
    }
    return { kind: 'mod', modId: rec.modId, label: rec.modName, details }
  }

  private async changedFiles(gamePath: string, rec: InstallRecord): Promise<string[]> {
    const changed: string[] = []
    for (const f of rec.files) {
      const h = await sha256OrNull(resolveInside(gamePath, f.destination))
      if (h !== f.installedSha256) changed.push(`${f.destination} (${h === null ? 'missing' : 'modified'})`)
    }
    for (const f of rec.files) {
      if (f.kind !== 'replaced') continue
      const b = await sha256OrNull(this.backups.pathFor(rec.installId, f.destination))
      if (b !== f.originalSha256) changed.push(`backup of ${f.destination} (missing or damaged)`)
    }
    return changed
  }

  private async inspectUnmanaged(gamePath: string, mods: LoadedMod[]): Promise<ActiveState> {
    const problems: string[] = []
    const notes: string[] = []
    for (const mod of mods) {
      const s = await this.scanUnmanaged(gamePath, mod)
      const name = mod.manifest.name
      if (s.replaceMissing.length) {
        problems.push(`Game files that ${name} replaces are missing:\n  ${sample(s.replaceMissing)}\nUse Steam → Properties → Installed Files → Verify integrity.`)
      }
      if (s.replaceForeign.length) {
        problems.push(
          `These game files are not the original versions (changed by another tool or mod):\n  ${sample(s.replaceForeign)}\n` +
            `Use Steam → Properties → Installed Files → Verify integrity to get the originals back.`
        )
      }
      const total = mod.manifest.files.length
      const hasReplace = s.replaceTotal > 0
      if (s.identical === total) {
        problems.push(`${name} is installed, but not by this app (for example extracted manually from a zip). Click the ${name} tile to let the app manage it, or the "Vanilla BNW" tile to remove it.`)
      } else if (s.replaceModded.length) {
        problems.push(`${name} is partly installed outside this app (${s.identical} of ${total} files). Click the ${name} tile to complete it or the "Vanilla BNW" tile to remove it.`)
      } else if (s.identical > 0) {
        if (hasReplace) {
          notes.push(`${s.identical} inactive ${name} files are present (left over from a manual install). They don't affect the game; the "Vanilla BNW" tile removes them.`)
        } else {
          problems.push(`${name} is partly installed outside this app (${s.identical} of ${total} files).`)
        }
      }
    }
    if (problems.length) return unknown(...problems, ...notes)
    return { kind: 'vanilla', modId: null, label: 'Vanilla BNW', details: notes }
  }

  private async scanUnmanaged(gamePath: string, mod: LoadedMod) {
    const r = { identical: 0, replaceTotal: 0, replaceModded: [] as string[], replaceForeign: [] as string[], replaceMissing: [] as string[] }
    for (const f of mod.manifest.files) {
      const h = await sha256OrNull(resolveInside(gamePath, f.destination))
      if (h === f.sha256) r.identical++
      if (f.mode !== 'replace') continue
      r.replaceTotal++
      if (h === null) r.replaceMissing.push(f.destination)
      else if (h === f.sha256) r.replaceModded.push(f.destination)
      else if (f.original && !f.original.sha256.includes(h)) r.replaceForeign.push(f.destination)
    }
    return r
  }

  // ------------------------------------------------------------------ switching

  /**
   * Bring the game folder into the target configuration ("vanilla" or a mod id).
   * Order: roll back an interrupted operation -> remove the current managed mod -> remove unmanaged copies (vanilla
   * only) -> install the target mod.
   */
  async switchTo(gamePath: string, targetId: string, mods: LoadedMod[], progress: ProgressFn = () => {}): Promise<SwitchResult> {
    const warnings: string[] = []
    const touched = new Set<string>()
    const target = targetId === VANILLA_ID ? null : mods.find((m) => m.manifest.id === targetId)
    if (targetId !== VANILLA_ID && !target) throw new UserError(`Unknown configuration "${targetId}".`)

    if (await this.state.journalExists()) {
      const rec = await this.state.readJournal()
      warnings.push(...(await this.recover(progress)))
      if (rec) touched.add(rec.modId)
    }

    const { install } = await this.state.read()
    if (install) {
      if (!samePath(install.gamePath, gamePath)) {
        throw new UserError(`${install.modName} is installed by this app in another game folder (${install.gamePath}). Select that folder and switch it back to vanilla first.`)
      }
      if (target && install.modId === target.manifest.id && install.buildId === target.buildId && install.status === 'installed') {
        progress({ phase: 'Verifying installed files', done: 0, total: 1 })
        if ((await this.changedFiles(gamePath, install)).length === 0) {
          return { message: `${target.manifest.name} is already active. Nothing to do.`, warnings, touchedMods: [...touched] }
        }
      }
      warnings.push(...(await this.uninstall(progress)))
      touched.add(install.modId)
    }

    if (!target) {
      for (const mod of mods) {
        const w = await this.removeUnmanaged(gamePath, mod, progress)
        if (w) {
          warnings.push(...w)
          touched.add(mod.manifest.id)
        }
      }
      return { message: 'Vanilla BNW is now active.', warnings, touchedMods: [...touched] }
    }

    warnings.push(...(await this.install(gamePath, target, progress)))
    touched.add(target.manifest.id)
    return { message: `${target.manifest.name} is now active.`, warnings, touchedMods: [...touched] }
  }

  // ------------------------------------------------------------------ install

  /** Install a mod into a game folder that has no managed install. Rolls back on failure. Returns warnings. */
  async install(gamePath: string, mod: LoadedMod, progress: ProgressFn = () => {}): Promise<string[]> {
    if ((await this.state.read()).install) throw new UserError('Another configuration is still installed; remove it first.')
    if (await this.state.journalExists()) throw new UserError('An interrupted operation must be rolled back first.')
    const files = mod.manifest.files
    const name = mod.manifest.name

    // 1. sources
    let n = 0
    progress({ phase: `Checking ${name} files`, done: 0, total: files.length })
    const srcProblems = await verifySources(mod, () => progress({ phase: `Checking ${name} files`, done: ++n, total: files.length }))
    if (srcProblems.length) {
      throw new UserError(`${name} can't be installed: its source files are missing or damaged:\n  ${sample(srcProblems)}\n(Developers: run "npm run payload" in ui/. Players: reinstall the app.)`)
    }

    // 2. plan: decide for every file what to do, and refuse before changing anything if something is off
    type Step = ManagedFile & { src: string; backupFrom: string | null }
    const steps: Step[] = []
    const refusals: string[] = []
    n = 0
    for (const f of files) {
      progress({ phase: 'Checking game files', done: n++, total: files.length })
      const dest = resolveInside(gamePath, f.destination)
      let current: string | null
      try {
        current = await sha256OrNull(dest)
      } catch (e) {
        refusals.push(describeFsError(e, 'read', dest))
        continue
      }
      const base = { destination: f.destination, installedSha256: f.sha256, src: sourcePath(mod, f) }
      if (f.mode === 'add') {
        if (current === null) steps.push({ ...base, kind: 'added', backupFrom: null })
        else if (current === f.sha256) steps.push({ ...base, kind: 'adopted', backupFrom: null })
        // Unexpected file at a path the mod adds: keep it safe in a backup and put it back on uninstall.
        else steps.push({ ...base, kind: 'replaced', originalSha256: current, backupFrom: dest })
        continue
      }
      // mode "replace": the vanilla file must be there and must be genuine
      if (current === null) {
        refusals.push(`${f.destination} is missing from the game. Verify the game files in Steam first.`)
      } else if (current === f.sha256) {
        const bundled = bundledOriginalPath(mod, f)
        if (bundled) steps.push({ ...base, kind: 'replaced', originalSha256: (await sha256OrNull(bundled))!, backupFrom: bundled })
        else refusals.push(`${f.destination} already contains the ${name} version and no copy of the original is available. Verify the game files in Steam first.`)
      } else if (f.original && !f.original.sha256.includes(current)) {
        refusals.push(`${f.destination} is not the original game file (another mod or tool changed it). Verify the game files in Steam first.`)
      } else {
        steps.push({ ...base, kind: 'replaced', originalSha256: current, backupFrom: dest })
      }
    }
    if (refusals.length) throw new UserError(`${name} was not installed; nothing was changed:\n  ${sample(refusals)}`)
    await this.probeWritable(gamePath, files.map((f) => f.destination))

    // 3. execute, journaling each change before making it
    const installId = `${mod.manifest.id}-${Date.now()}-${randomUUID().slice(0, 8)}`
    await this.state.startJournal({
      t: 'begin', installId, modId: mod.manifest.id, modName: name, modVersion: mod.manifest.version,
      buildId: mod.buildId, gamePath, startedAt: new Date().toISOString()
    })
    const createdDirs: string[] = []
    try {
      n = 0
      for (const s of steps) {
        progress({ phase: `Installing ${name}`, done: n++, total: steps.length })
        await this.ensureDirs(gamePath, s.destination, createdDirs)
        const dest = resolveInside(gamePath, s.destination)
        const { src: _src, backupFrom, ...entry } = s
        if (s.kind === 'replaced') {
          const backup = this.backups.pathFor(installId, s.destination)
          await this.backups.ensureParent(backup)
          await this.op(() => this.fsOps.copyFile(backupFrom!, backup), 'back up', backupFrom!)
          if ((await sha256OrNull(backup)) !== s.originalSha256) throw new UserError(`Backup of ${s.destination} could not be verified.`)
        }
        await this.state.appendJournal({ t: 'file', ...entry })
        if (s.kind !== 'adopted') await this.placeFile(s.src, dest)
      }
      // 4. verify everything that should now be in the game folder
      n = 0
      for (const s of steps) {
        progress({ phase: 'Verifying installed files', done: n++, total: steps.length })
        const h = await sha256OrNull(resolveInside(gamePath, s.destination))
        if (h !== s.installedSha256) throw new UserError(`Verification failed: ${s.destination} does not contain the expected content after copying.`)
      }
    } catch (e) {
      throw await this.failAndRollBack(e, name, progress)
    }

    const rec: InstallRecord = {
      installId, modId: mod.manifest.id, modName: name, modVersion: mod.manifest.version, buildId: mod.buildId, gamePath,
      installedAt: new Date().toISOString(), status: 'installed', createdDirs,
      files: steps.map(({ src: _s, backupFrom: _b, ...m }) => m)
    }
    await this.state.write({ schemaVersion: 1, install: rec })
    await this.state.deleteJournal()
    const adopted = rec.files.filter((f) => f.kind === 'adopted').length
    return adopted ? [`${adopted} ${name} files were already present with the right content and were taken over.`] : []
  }

  private async failAndRollBack(e: unknown, name: string, progress: ProgressFn): Promise<UserError> {
    const cause = messageOf(e)
    try {
      const w = await this.recover(progress)
      return new UserError(`Installing ${name} failed: ${cause}\nAll changes were rolled back; the game is unchanged.` + (w.length ? `\n${w.join('\n')}` : ''))
    } catch (re) {
      return new UserError(
        `Installing ${name} failed: ${cause}\nRolling back also failed: ${messageOf(re)}\n` +
          `The game folder is in an inconsistent state. Fix the problem above and click the "Vanilla BNW" tile to finish the rollback.`
      )
    }
  }

  /** Roll back an interrupted/failed install from the journal. Throws if something could not be undone. */
  async recover(progress: ProgressFn = () => {}): Promise<string[]> {
    const rec = await this.state.readJournal()
    if (!rec) return []
    const { warnings, errors } = await this.undo(rec, progress, 'Rolling back')
    if (errors.length) throw new UserError(`Could not roll back the interrupted operation:\n  ${sample(errors)}`)
    await this.backups.remove(rec.installId)
    await this.state.deleteJournal()
    return warnings
  }

  // ------------------------------------------------------------------ uninstall

  /** Remove the managed install and restore every original. Safe to retry after a failure. */
  async uninstall(progress: ProgressFn = () => {}): Promise<string[]> {
    const st = await this.state.read()
    const rec = st.install
    if (!rec) return []
    const { warnings, errors } = await this.undo(rec, progress, 'Restoring vanilla files')
    if (errors.length) {
      await this.state.write({ schemaVersion: 1, install: { ...rec, status: 'uninstall-failed' } })
      throw new UserError(`Restoring vanilla failed for ${errors.length} file(s):\n  ${sample(errors)}\nFix the problem and click the "Vanilla BNW" tile again (retrying is safe).`)
    }
    await this.state.write({ schemaVersion: 1, install: null })
    await this.backups.remove(rec.installId)
    return warnings
  }

  /**
   * Undo the files of a record (install record or journal), newest first. Never stops at the first error so as much
   * as possible gets restored; every step is idempotent so the whole thing can be re-run.
   */
  private async undo(rec: InstallRecord, progress: ProgressFn, phase: string): Promise<{ warnings: string[]; errors: string[] }> {
    const warnings: string[] = []
    const errors: string[] = []
    const stamp = new Date().toISOString().replace(/[:.]/g, '-')
    const files = [...rec.files].reverse()
    let n = 0
    for (const f of files) {
      progress({ phase, done: n++, total: files.length })
      const dest = resolveInside(rec.gamePath, f.destination)
      try {
        await this.removeIfExists(dest + TMP_SUFFIX)
        const current = await sha256OrNull(dest)
        if (f.kind === 'added' || f.kind === 'adopted') {
          if (current === null) continue
          if (current === f.installedSha256) await this.op(() => this.fsOps.unlink(dest), 'delete', dest)
          else warnings.push(`${f.destination} was changed after installation and was left in place.`)
          continue
        }
        // replaced: put the original back
        if (current === f.originalSha256) continue
        const backup = this.backups.pathFor(rec.installId, f.destination)
        if ((await sha256OrNull(backup)) !== f.originalSha256) {
          errors.push(`${f.destination}: the backup of the original is missing or damaged. Verify the game files in Steam.`)
          continue
        }
        if (current !== null && current !== f.installedSha256) {
          // Someone else put a different file here; keep a copy before restoring the original over it.
          const keep = this.backups.conflictPath(stamp, f.destination)
          await this.backups.ensureParent(keep)
          await this.op(() => this.fsOps.copyFile(dest, keep), 'save a copy of', dest)
          warnings.push(`${f.destination} had been changed outside this app; that version was saved to ${keep} before restoring the original.`)
        }
        await this.ensureDirs(rec.gamePath, f.destination, null)
        await this.placeFile(backup, dest)
        if ((await sha256OrNull(dest)) !== f.originalSha256) errors.push(`${f.destination}: restored file could not be verified.`)
      } catch (e) {
        errors.push(messageOf(e))
      }
    }
    // Folders that held adopted files existed before the install (manual copy of the mod); prune them if now empty.
    const adoptedGone = rec.files.filter((f) => f.kind === 'adopted').map((f) => f.destination)
    await this.pruneEmptyDirs(rec.gamePath, adoptedGone, rec.files.filter((f) => f.kind === 'replaced').map((f) => f.destination))
    for (const d of [...rec.createdDirs].reverse()) {
      const abs = resolveInside(rec.gamePath, d)
      try {
        await this.fsOps.rmdir(abs)
      } catch (e) {
        if (isErrno(e, 'ENOENT')) continue
        if (isErrno(e, 'ENOTEMPTY') || isErrno(e, 'EEXIST')) warnings.push(`Folder ${d} was kept because it contains files that don't belong to this app.`)
        else errors.push(describeFsError(e, 'remove folder', abs))
      }
    }
    return { warnings, errors }
  }

  /**
   * Remove a copy of a mod that this app did not install (e.g. extracted from a zip by hand). Only files that are
   * byte-identical to the mod's own files are deleted, and replaced vanilla files are restored from the bundled
   * original. Returns null if there was nothing to do.
   */
  async removeUnmanaged(gamePath: string, mod: LoadedMod, progress: ProgressFn = () => {}): Promise<string[] | null> {
    const files = mod.manifest.files
    const toRestore: { f: (typeof files)[number]; bundled: string }[] = []
    const toDelete: string[] = []
    const refusals: string[] = []
    for (const f of files) {
      const h = await sha256OrNull(resolveInside(gamePath, f.destination))
      if (h !== f.sha256) continue
      if (f.mode === 'add') toDelete.push(f.destination)
      else {
        const bundled = bundledOriginalPath(mod, f)
        if (bundled && f.original!.sha256.includes((await sha256OrNull(bundled)) ?? '')) toRestore.push({ f, bundled })
        else refusals.push(`${f.destination} contains the ${mod.manifest.name} version and no original copy is available. Verify the game files in Steam.`)
      }
    }
    if (!toRestore.length && !toDelete.length && !refusals.length) return null
    if (refusals.length) throw new UserError(`Could not remove ${mod.manifest.name}:\n  ${sample(refusals)}`)
    await this.probeWritable(gamePath, files.map((f) => f.destination))
    const total = toRestore.length + toDelete.length
    let n = 0
    // Restore replaced files first: that already deactivates the mod even if a later delete fails.
    for (const { f, bundled } of toRestore) {
      progress({ phase: `Removing ${mod.manifest.name}`, done: n++, total })
      await this.placeFile(bundled, resolveInside(gamePath, f.destination))
    }
    for (const rel of toDelete) {
      progress({ phase: `Removing ${mod.manifest.name}`, done: n++, total })
      const abs = resolveInside(gamePath, rel)
      await this.op(() => this.fsOps.unlink(abs), 'delete', abs)
    }
    await this.pruneEmptyDirs(gamePath, toDelete, files.filter((f) => f.mode === 'replace').map((f) => f.destination))
    return [`Removed a copy of ${mod.manifest.name} that was installed outside this app (${toDelete.length} files deleted, ${toRestore.length} original files restored).`]
  }

  // ------------------------------------------------------------------ helpers

  /**
   * Remove folders that became empty after deleting `deleted` files. Folders containing (or above) files in
   * `protect` are vanilla folders and are never removed; non-empty folders are always kept.
   */
  private async pruneEmptyDirs(gamePath: string, deleted: string[], protect: string[]): Promise<void> {
    const protectedDirs = new Set(protect.flatMap((d) => relAncestors(d.toLowerCase())))
    const dirs = [...new Set(deleted.flatMap(relAncestors))].filter((d) => !protectedDirs.has(d.toLowerCase()))
    dirs.sort((a, b) => b.split('/').length - a.split('/').length)
    for (const d of dirs) {
      try {
        await this.fsOps.rmdir(resolveInside(gamePath, d))
      } catch {
        /* not empty or already gone: keep it */
      }
    }
  }

  /** Copy via a temp file + rename so the destination is never left half-written. */
  private async placeFile(src: string, dest: string): Promise<void> {
    const tmp = dest + TMP_SUFFIX
    await this.op(() => this.fsOps.copyFile(src, tmp), 'write', dest)
    try {
      await this.op(() => this.fsOps.rename(tmp, dest), 'replace', dest)
    } catch (e) {
      await this.removeIfExists(tmp)
      throw e
    }
  }

  private async removeIfExists(p: string): Promise<void> {
    try {
      await this.fsOps.unlink(p)
    } catch (e) {
      if (!isErrno(e, 'ENOENT')) throw new UserError(describeFsError(e, 'delete', p))
    }
  }

  /** Create missing parent folders of a destination; when `journal` is given they are recorded for removal. */
  private async ensureDirs(gamePath: string, destination: string, journal: string[] | null): Promise<void> {
    for (const rel of relAncestors(destination).reverse()) {
      const abs = resolveInside(gamePath, rel)
      try {
        const st = await fs.stat(abs)
        if (!st.isDirectory()) throw new UserError(`"${abs}" should be a folder but is a file.`)
        continue
      } catch (e) {
        if (e instanceof UserError || !isErrno(e, 'ENOENT')) throw e
      }
      if (journal) {
        await this.state.appendJournal({ t: 'dir', path: rel })
        journal.push(rel)
      }
      await this.op(() => this.fsOps.mkdir(abs), 'create folder', abs)
    }
  }

  /** Fail early with a clear permission message instead of half way through the copy. */
  private async probeWritable(gamePath: string, destinations: string[]): Promise<void> {
    const dirs = new Set<string>()
    for (const d of destinations) {
      for (const rel of relAncestors(d)) {
        const abs = resolveInside(gamePath, rel)
        if (await exists(abs)) {
          dirs.add(abs)
          break
        }
      }
    }
    for (const dir of dirs) {
      const probe = path.join(dir, `.civ5mm-write-test-${process.pid}`)
      try {
        await fs.writeFile(probe, '')
        await fs.unlink(probe)
      } catch (e) {
        throw new UserError(describeFsError(e, 'write into', dir))
      }
    }
  }

  private async op(fn: () => Promise<void>, action: string, target: string): Promise<void> {
    try {
      await fn()
    } catch (e) {
      if (e instanceof UserError) throw e
      throw new UserError(describeFsError(e, action, target))
    }
  }
}

function unknown(...details: string[]): ActiveState {
  return { kind: 'unknown', modId: null, label: 'Unknown / Inconsistent installation', details }
}

async function exists(p: string): Promise<boolean> {
  try {
    await fs.stat(p)
    return true
  } catch {
    return false
  }
}
