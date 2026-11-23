import fs from 'node:fs/promises'
import path from 'node:path'
import { readJson, writeJsonAtomic } from '../fileOperations/jsonStore'
import { isErrno } from '../fileOperations/hash'

/**
 * What the app installed, persisted in <dataDir>/state.json (outside the game folder).
 *
 * kind:
 *  - "added"    the file did not exist before; uninstall deletes it (only if its content is still ours)
 *  - "adopted"  an identical copy was already there (e.g. a manual install of the same build); nothing was
 *               written, uninstall deletes it like an added file
 *  - "replaced" a different file was there; it was backed up first, uninstall restores the backup
 */
export type ManagedKind = 'added' | 'adopted' | 'replaced'

export interface ManagedFile {
  destination: string
  installedSha256: string
  kind: ManagedKind
  /** "replaced" only: sha256 of the backed up original (= what uninstall must put back). */
  originalSha256?: string
}

export interface InstallRecord {
  installId: string
  modId: string
  modName: string
  modVersion: string
  buildId: string
  gamePath: string
  installedAt: string
  /** "uninstall-failed": restoring vanilla failed half way; retrying is safe (every step is idempotent). */
  status: 'installed' | 'uninstall-failed'
  /** Folders created inside the game folder, shallowest first. */
  createdDirs: string[]
  files: ManagedFile[]
}

export interface StateFile {
  schemaVersion: 1
  install: InstallRecord | null
}

/*
 * Journal (<dataDir>/journal.jsonl): written while an install runs, one JSON object per line, each line written
 * BEFORE the change it describes. If the app dies mid-install, the journal is the list of everything that may have
 * been touched, and recovery rolls it all back. A finished install moves the data into state.json and deletes it.
 */
export type JournalEntry =
  | { t: 'begin'; installId: string; modId: string; modName: string; modVersion: string; buildId: string; gamePath: string; startedAt: string }
  | { t: 'dir'; path: string }
  | ({ t: 'file' } & ManagedFile)

export class StateStore {
  readonly stateFile: string
  readonly journalFile: string

  constructor(dataDir: string) {
    this.stateFile = path.join(dataDir, 'state.json')
    this.journalFile = path.join(dataDir, 'journal.jsonl')
  }

  async read(): Promise<StateFile> {
    const s = await readJson<StateFile>(this.stateFile)
    if (!s) return { schemaVersion: 1, install: null }
    if (s.schemaVersion !== 1) throw new Error(`Unsupported state file version in ${this.stateFile}`)
    return s
  }

  async write(s: StateFile): Promise<void> {
    await writeJsonAtomic(this.stateFile, s)
  }

  async journalExists(): Promise<boolean> {
    try {
      await fs.access(this.journalFile)
      return true
    } catch {
      return false
    }
  }

  async startJournal(begin: JournalEntry): Promise<void> {
    await fs.mkdir(path.dirname(this.journalFile), { recursive: true })
    await fs.writeFile(this.journalFile, JSON.stringify(begin) + '\n', { flag: 'wx' })
  }

  async appendJournal(e: JournalEntry): Promise<void> {
    const fh = await fs.open(this.journalFile, 'a')
    try {
      await fh.write(JSON.stringify(e) + '\n')
      await fh.sync() // the entry must be on disk before the change it announces happens
    } finally {
      await fh.close()
    }
  }

  /** Rebuild an InstallRecord from the journal. A torn last line (crash while writing it) is ignored. */
  async readJournal(): Promise<InstallRecord | null> {
    let text: string
    try {
      text = await fs.readFile(this.journalFile, 'utf8')
    } catch (e) {
      if (isErrno(e, 'ENOENT')) return null
      throw e
    }
    const entries: JournalEntry[] = []
    for (const line of text.split('\n')) {
      if (!line.trim()) continue
      try {
        entries.push(JSON.parse(line) as JournalEntry)
      } catch {
        /* torn line */
      }
    }
    const begin = entries[0]
    if (!begin || begin.t !== 'begin') throw new Error(`Journal ${this.journalFile} is damaged (no begin entry)`)
    const rec: InstallRecord = {
      installId: begin.installId,
      modId: begin.modId,
      modName: begin.modName,
      modVersion: begin.modVersion,
      buildId: begin.buildId,
      gamePath: begin.gamePath,
      installedAt: begin.startedAt,
      status: 'installed',
      createdDirs: [],
      files: []
    }
    for (const e of entries.slice(1)) {
      if (e.t === 'dir') rec.createdDirs.push(e.path)
      else if (e.t === 'file') {
        const { t: _t, ...f } = e
        rec.files.push(f)
      }
    }
    return rec
  }

  async deleteJournal(): Promise<void> {
    await fs.rm(this.journalFile, { force: true })
  }
}
