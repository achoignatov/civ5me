import fs from 'node:fs/promises'
import path from 'node:path'
import { resolveInside } from '../fileOperations/safePath'

/**
 * Backups live in the app's data folder (never in the game folder, never next to the mod sources):
 *   <dataDir>/backups/<installId>/<destination path>   originals replaced by an install
 *   <dataDir>/conflicts/<timestamp>/<destination path>  files changed by someone else that we had to overwrite
 *                                                       while restoring vanilla (kept for the user, never deleted)
 */
export class BackupStore {
  constructor(private readonly dataDir: string) {}

  installDir(installId: string): string {
    return resolveInside(path.join(this.dataDir, 'backups'), installId, 'install id')
  }

  pathFor(installId: string, destination: string): string {
    return resolveInside(this.installDir(installId), destination, 'backup path')
  }

  async ensureParent(file: string): Promise<void> {
    await fs.mkdir(path.dirname(file), { recursive: true })
  }

  /** Delete the backups of a finished/rolled back install. Only touches <dataDir>/backups/<installId>. */
  async remove(installId: string): Promise<void> {
    await fs.rm(this.installDir(installId), { recursive: true, force: true })
  }

  conflictPath(stamp: string, destination: string): string {
    return resolveInside(path.join(this.dataDir, 'conflicts', stamp), destination, 'conflict path')
  }
}
