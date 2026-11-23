import fs from 'node:fs/promises'

/**
 * Every filesystem call that changes something goes through this object, so tests can inject failures
 * (e.g. "the 5th copy fails with EACCES") without touching real permissions.
 */
export interface FsOps {
  copyFile(src: string, dst: string): Promise<void>
  rename(src: string, dst: string): Promise<void>
  unlink(file: string): Promise<void>
  mkdir(dir: string): Promise<void>
  rmdir(dir: string): Promise<void>
}

export const realFsOps: FsOps = {
  copyFile: (s, d) => fs.copyFile(s, d),
  rename: (s, d) => fs.rename(s, d),
  unlink: (f) => fs.unlink(f),
  mkdir: async (d) => {
    await fs.mkdir(d)
  },
  rmdir: (d) => fs.rmdir(d)
}
